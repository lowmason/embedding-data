'''Define, submit, and download the IPUMS CPS extracts for the embedding benchmark.

Usage:
    uv run embedding-data cps --dry-run
    uv run embedding-data cps
    uv run embedding-data cps monthly --start 2026-08

Requires an IPUMS CPS account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run writes each definition to
data/preview/cps/<set>/extract.json. A real run gives each extract its own
directory, data/raw/cps/<set>/cps_<number>/, with the submitted extract.json and
the delivered .csv.gz and .xml; records each file in data/raw/manifest.jsonl; and
writes Parquet to data/derived/cps/<set>/. --data-dir moves the whole data root.

The key is needed even for --dry-run,
because sample IDs come from the IPUMS sample catalog: monthly IDs end in b or
s depending on whether a supplement was fielded, and October 2025 does not exist.

monthly: every basic monthly sample from --start (default and earliest 2025-01, the
    first month on the 2022 Census industry codes; occupation has used 2018 codes since
    2020), labor force members only, with the panel IDs and dependent-interviewing
    flags (EMPSAME, ACTSAME) needed for month-to-month job transitions.
asec: every ASEC from 2025 on, all persons, with longest-job-last-year codes
    (INDLY, OCCLY), 160 replicate weights, and state-to-state migration.

IPUMS CPS carries Census industry and occupation codes, not NAICS or SOC strings;
IND, OCC, INDLY, and OCCLY are written as zero-padded 4-character strings so
they join cleanly to the Census code lists that give NAICS and SOC equivalents.
'''

import os
import re
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import ipums_conversion, ipums_delivery, paths

DOTENV_PATH = paths.PROJECT_ROOT / '.env'

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


ASEC_FIRST_YEAR = 2025
# January 2025 is the first month on the 2022 Census industry codes (spec R4.3).
MONTHLY_FIRST = '2025-01'
SAMPLE_ID = re.compile(r'^cps(\d{4})_(\d{2})([bs])$')

VARIABLES = {
    'monthly': [
        'CPSIDP', 'CPSIDV', 'MISH',                         # panel linking
        'WTFINL', 'LNKFW1MWT', 'EARNWT',                    # weights
        'IND', 'OCC', 'CLASSWKR', 'EMPSAME', 'ACTSAME',     # job and dependent coding
        'LABFORCE', 'EMPSTAT', 'UHRSWORK1',                 # labor force
        'EARNWEEK2', 'HOURWAGE2', 'PAIDHOUR', 'ELIGORG',    # earner study
        'AGE', 'SEX', 'EDUC',                               # worker profile
        'STATEFIP', 'REGION', 'METFIPS', 'COUNTY',          # geography
    ],
    'asec': [
        'CPSIDP', 'CPSIDV',                                 # link to monthly records
        'ASECWT', 'REPWTP',                                 # weights
        'IND', 'OCC', 'CLASSWKR', 'INDLY', 'OCCLY', 'CLASSWLY',
        'LABFORCE', 'EMPSTAT', 'WKSWORK1', 'UHRSWORKLY',
        'INCWAGE',
        'AGE', 'SEX', 'EDUC',
        'STATEFIP', 'REGION', 'METFIPS', 'COUNTY',
        'MIGRATE1', 'MIGSTA1', 'WHYMOVE',                   # migration
    ],
}

CODE_COLUMNS = ipums_conversion.CODE_COLUMNS
SCHEMA_OVERRIDES = ipums_conversion.CPS_SCHEMA_OVERRIDES


def parse_month(text: str) -> tuple[int, int]:
    '''Parse YYYY-MM into a (year, month) tuple.'''
    year, month = text.split('-')
    return int(year), int(month)


def select_samples(catalog: dict[str, str], name: str, start: tuple[int, int]) -> list[str]:
    '''Choose sample IDs from the IPUMS CPS catalog ({id: description}).'''
    chosen = {}
    for sample_id, description in catalog.items():
        match = SAMPLE_ID.match(sample_id)
        if match is None:
            continue
        year, month, suffix = int(match[1]), int(match[2]), match[3]
        is_asec = 'ASEC' in description
        if name == 'asec':
            keep = is_asec and year >= ASEC_FIRST_YEAR
        else:
            keep = not is_asec and (year, month) >= start
        # One file per month; prefer the basic file if a supplement file also exists.
        if keep and ((year, month) not in chosen or suffix == 'b'):
            chosen[(year, month)] = sample_id
    return [chosen[key] for key in sorted(chosen)]


def build_extract(name: str, samples: list[str]) -> MicrodataExtract:
    '''Define one benchmark extract.'''
    extract = MicrodataExtract(
        collection='cps',
        samples=samples,
        variables=VARIABLES[name],
        description=f'CPS embedding benchmark: {name}',
        data_format='csv',
        data_quality_flags=True,
    )
    if name == 'monthly':
        # Labor force only (employed or unemployed); unemployed records carry the
        # industry and occupation of the last job, so U-to-E moves are usable too.
        extract.select_cases('LABFORCE', ['2'])
    else:
        # Adds INCWAGE_CPIU_2010 so pooled ASEC years share constant dollars.
        extract.adjust_monetary_values('INCWAGE')
    return extract


def csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path:
    '''Convert a delivered gzip CSV without replacing an existing Parquet.'''
    return ipums_conversion.convert(csv_gz, parquet_path, 'cps')


@app.command(help=__doc__.splitlines()[0])
def main(
    extracts: Annotated[
        list[str] | None,
        typer.Argument(help='monthly and/or asec (default: both)'),
    ] = None,
    start: Annotated[
        str,
        typer.Option('--start', help='First monthly sample, YYYY-MM.'),
    ] = MONTHLY_FIRST,
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
    extracts = extracts or ['monthly', 'asec']

    unknown = sorted(set(extracts).difference(VARIABLES))
    if unknown:
        raise typer.BadParameter(
            'unknown extract(s): ' + ', '.join(unknown), param_hint='extracts'
        )

    if convert_only:
        if dry_run:
            raise typer.BadParameter('--convert-only cannot be combined with --dry-run')
        if start != MONTHLY_FIRST:
            raise typer.BadParameter('--start cannot be combined with --convert-only')
        for parquet in ipums_conversion.recover(data_dir, 'cps', extracts):
            typer.echo(f'wrote {parquet}')
        return

    start_month = parse_month(start)
    if 'monthly' in extracts and start_month < parse_month(MONTHLY_FIRST):
        raise typer.BadParameter(
            f'{start} is before {MONTHLY_FIRST}, the first month on 2022 Census industry codes',
            param_hint="'--start'",
        )

    load_dotenv(dotenv_path=DOTENV_PATH)
    api_key = os.environ.get('IPUMS_API_KEY')
    if not api_key:
        typer.echo(
            f'Set IPUMS_API_KEY in {DOTENV_PATH} (https://account.ipums.org/api_keys).', err=True
        )
        raise typer.Exit(code=1)
    client = IpumsApiClient(api_key)
    catalog = client.get_all_sample_info('cps')

    for name in extracts:
        samples = select_samples(catalog, name, start_month)
        if not samples:
            typer.echo(f'{name}: no matching samples in the IPUMS CPS catalog', err=True)
            raise typer.Exit(code=1)
        extract = build_extract(name, samples)
        summary = f'{name}: {len(samples)} samples, {samples[0]} to {samples[-1]}'
        if dry_run:
            preview = ipums_delivery.write_preview(extract, data_dir, 'cps', name)
            typer.echo(f'{summary}; wrote {preview}')
            continue

        typer.echo(summary)
        extract_dir = ipums_delivery.deliver(client, extract, data_dir, 'cps', name)
        for csv_gz in sorted(extract_dir.glob('*.csv.gz')):
            parquet = ipums_delivery.parquet_path(data_dir, 'cps', name, csv_gz)
            typer.echo(f'{name}: wrote {csv_to_parquet(csv_gz, parquet)}')


if __name__ == '__main__':
    app()
