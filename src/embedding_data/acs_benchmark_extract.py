'''Define, submit, and download the IPUMS USA extracts for the ACS embedding benchmark.

Usage:
    uv run embedding-data acs --dry-run  # write extract definitions only
    uv run embedding-data acs core       # submit, wait, download, convert
    uv run embedding-data acs core vintage five_year

Requires an IPUMS USA account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run needs neither the key nor network
access. Downloads default to data/raw/acs under the project root, with one
subdirectory per extract set.

Each extract is employed persons only, as CSV, with IPUMS data quality flags
(Q-prefixed columns such as QIND and QOCC mark Census-allocated values). The
downloaded .csv.gz is converted to Parquet with the alphanumeric code columns
kept as strings. When pooling the two core years, halve PERWT and REPWTP1-80
for annual-average totals; compositions and shares are unaffected.
'''

import gzip
import json
import os
import shutil
from pathlib import Path
from typing import Annotated

import polars as pl
import typer
from dotenv import load_dotenv
from ipumspy import IpumsApiClient, MicrodataExtract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = PROJECT_ROOT / '.env'
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'raw' / 'acs'

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


# core: natively coded on 2022 NAICS, 2018 SOC, and 2020 PUMAs.
# vintage: same SOC and PUMA vintages, but 2017 NAICS (vintage-shift test).
# five_year: ~2.5x core's sample, but industry codes and PUMAs for pre-2023
#   respondents are Census crosswalks/allocations; keep MULTYEAR to subset.
SAMPLE_SETS = {
  'core': ['us2023a', 'us2024a'],
  'vintage': ['us2022a'],
  'five_year': ['us2024c'],  # 2020-2024 ACS 5-year; confirm on the IPUMS sample ID list
}

VARIABLE_GROUPS = {
  'weights': ['PERWT', 'REPWTP'],
  'industry': ['INDNAICS', 'IND'],
  'occupation': ['OCCSOC', 'OCC'],
  'universe': ['EMPSTAT', 'CLASSWKR', 'GQ'],
  'profile': [
    'EDUC', 'DEGFIELD', 'DEGFIELD2', 'INCWAGE', 'INCEARN',
    'UHRSWORK', 'WKSWORK2', 'AGE', 'SEX',
  ],
  'residence': ['STATEFIP', 'REGION', 'PUMA', 'COUNTYFIP', 'MET2023', 'MET2023ERR'],
  'workplace': ['PWSTATE2', 'PWPUMA00', 'PWMET23', 'PWMET23ERR', 'TRANWORK', 'TRANTIME'],
  'migration': ['MIGRATE1', 'MIGPLAC1', 'MIGPUMA1', 'MIGMET23'],
}

# Codes like '31M' and '1110XX' must not be parsed as numbers, and the
# CPI-adjusted wage has decimals that a short inference window can miss.
SCHEMA_OVERRIDES = {
  'INDNAICS': pl.String,
  'OCCSOC': pl.String,
  'INCWAGE_CPIU_2010': pl.Float64,
}


def build_extract(name: str) -> MicrodataExtract:
  '''Define one benchmark extract from its sample set.'''
  variables = [v for group in VARIABLE_GROUPS.values() for v in group]
  if name == 'five_year':
    variables.append('MULTYEAR')

  extract = MicrodataExtract(
    collection='usa',
    samples=SAMPLE_SETS[name],
    variables=variables,
    description=f'ACS embedding benchmark: {name}',
    data_format='csv',
    data_quality_flags=True,
  )
  # Employed (general code 1, which includes armed forces; EMPSTATD separates
  # them). Drop this line to keep all persons, e.g. for migration flows.
  extract.select_cases('EMPSTAT', ['1'])
  # Adds INCWAGE_CPIU_2010 so pooled years share constant dollars.
  extract.adjust_monetary_values('INCWAGE')
  return extract


def csv_to_parquet(csv_gz: Path) -> Path:
  '''Stream-decompress an IPUMS .csv.gz to disk, then sink it to Parquet lazily.'''
  csv_path = csv_gz.with_suffix('')
  with gzip.open(csv_gz, 'rb') as src, csv_path.open('wb') as dst:
    shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)

  parquet_path = csv_path.with_suffix('.parquet')
  (
    pl.scan_csv(csv_path, schema_overrides=SCHEMA_OVERRIDES, infer_schema_length=100_000)
    .sink_parquet(parquet_path)
  )
  csv_path.unlink()
  return parquet_path


@app.command(help=__doc__.splitlines()[0])
def main(
  extracts: Annotated[
    list[str] | None,
    typer.Argument(help=f'one or more of: {", ".join(SAMPLE_SETS)} (default: core)'),
  ] = None,
  out: Annotated[
    Path,
    typer.Option('--out', help='Directory for extract downloads.'),
  ] = DEFAULT_OUTPUT_DIR,
  dry_run: Annotated[
    bool,
    typer.Option('--dry-run', help='Write definitions without submitting.'),
  ] = False,
) -> None:
  extracts = extracts or ['core']

  unknown = sorted(set(extracts).difference(SAMPLE_SETS))
  if unknown:
    raise typer.BadParameter('unknown extract(s): ' + ', '.join(unknown), param_hint='extracts')

  # Definitions need no catalog lookup, so a dry run reads no key and stays offline.
  client = None
  if not dry_run:
    load_dotenv(dotenv_path=DOTENV_PATH)
    api_key = os.environ.get('IPUMS_API_KEY')
    if not api_key:
      typer.echo(
        f'Set IPUMS_API_KEY in {DOTENV_PATH} (https://account.ipums.org/api_keys).', err=True
      )
      raise typer.Exit(code=1)
    client = IpumsApiClient(api_key)

  for name in extracts:
    out_dir = out / name
    out_dir.mkdir(parents=True, exist_ok=True)
    extract = build_extract(name)
    definition = out_dir / 'extract.json'
    definition.write_text(json.dumps(extract.build(), indent=2))

    if client is None:
      typer.echo(f'{name}: wrote {definition}')
      continue

    client.submit_extract(extract)
    typer.echo(f'{name}: submitted extract {extract.extract_id}, waiting')
    client.wait_for_extract(extract)
    client.download_extract(extract, download_dir=out_dir)
    for csv_gz in sorted(out_dir.glob('*.csv.gz')):
      typer.echo(f'{name}: wrote {csv_to_parquet(csv_gz)}')


if __name__ == '__main__':
  app()
