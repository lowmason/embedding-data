'''Define, submit, and download the IPUMS USA extracts for the ACS embedding benchmark.

Usage:
    uv run embedding-data acs --dry-run  # write extract definitions only
    uv run embedding-data acs core       # submit, wait, download, convert
    uv run embedding-data acs core vintage five_year

Requires an IPUMS USA account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run needs neither the key nor network
access; it writes each definition to data/preview/acs/<set>/extract.json. A real
run gives each extract its own directory, data/raw/acs/<set>/usa_<number>/, with
the submitted extract.json and the delivered .csv.gz and .xml; records each file
in data/raw/manifest.jsonl; and writes Parquet to data/derived/acs/<set>/.
--data-dir moves the whole data root (default: data/ under the project root).

Each extract is employed persons only, as CSV, with IPUMS data quality flags
(Q-prefixed columns such as QIND and QOCC mark Census-allocated values). The
downloaded .csv.gz is converted to Parquet with the alphanumeric code columns
kept as strings. When pooling the two core years, halve PERWT and REPWTP1-80
for annual-average totals; compositions and shares are unaffected.
'''

import os
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import ipums_conversion, ipums_delivery, paths

DOTENV_PATH = paths.PROJECT_ROOT / '.env'

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

SCHEMA_OVERRIDES = ipums_conversion.ACS_SCHEMA_OVERRIDES


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


def csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path:
  '''Convert a delivered gzip CSV without replacing an existing Parquet.'''
  return ipums_conversion.convert(csv_gz, parquet_path, 'acs')


@app.command(help=__doc__.splitlines()[0])
def main(
  extracts: Annotated[
    list[str] | None,
    typer.Argument(help=f'one or more of: {", ".join(SAMPLE_SETS)} (default: core)'),
  ] = None,
  data_dir: Annotated[
    Path,
    typer.Option('--data-dir', help='Data root holding raw/, derived/, and preview/.'),
  ] = paths.DATA_DIR,
  dry_run: Annotated[
    bool,
    typer.Option('--dry-run', help='Write definitions to preview/ without submitting.'),
  ] = False,
  convert_only: Annotated[
    bool,
    typer.Option('--convert-only', help='Recover missing Parquet offline.'),
  ] = False,
) -> None:
  extracts = extracts or ['core']

  unknown = sorted(set(extracts).difference(SAMPLE_SETS))
  if unknown:
    raise typer.BadParameter('unknown extract(s): ' + ', '.join(unknown), param_hint='extracts')

  if convert_only:
    if dry_run:
      raise typer.BadParameter('--convert-only cannot be combined with --dry-run')
    for parquet in ipums_conversion.recover(data_dir, 'acs', extracts):
      typer.echo(f'wrote {parquet}')
    return

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
    extract = build_extract(name)
    if client is None:
      preview = ipums_delivery.write_preview(extract, data_dir, 'acs', name)
      typer.echo(f'{name}: wrote {preview}')
      continue

    extract_dir = ipums_delivery.deliver(client, extract, data_dir, 'acs', name)
    for csv_gz in sorted(extract_dir.glob('*.csv.gz')):
      parquet = ipums_delivery.parquet_path(data_dir, 'acs', name, csv_gz)
      typer.echo(f'{name}: wrote {csv_to_parquet(csv_gz, parquet)}')


if __name__ == '__main__':
  app()
