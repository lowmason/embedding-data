'''Download OSHA ITA Form 300A summaries and case-detail data, and build their Parquet tables.

Usage:
    uv run embedding-data osha
    uv run embedding-data osha summary
    uv run embedding-data osha case-detail --data-dir /tmp/osha-data

summary: every Form 300A summary file the ITA data page (https://www.osha.gov/itadata)
    lists, 2016 through the current year, and the summary data dictionaries. A year's file
    goes to data/raw/osha/summary/<year>/ under the name OSHA gives it. The current year's
    name carries its submission through-date, so a later release arrives beside the
    earlier one and is recorded as a new manifest entry with its through-date. A summary
    file found on disk but not in the manifest stops the run, because nothing can record
    it after the fact; a file OSHA replaces under an unchanged name is not detected. Then
    data/derived/osha/ita_300a_summary.parquet is rebuilt from each year's latest release
    (embedding_data.ita_summary), and rows per year are printed beside OSHA's published
    submission counts.
case-detail: the 2025 case-detail CSV and its dictionary, one row per injury or illness
    (Forms 300 and 301), acquired but feeding no target. An existing case-detail file
    missing from the manifest draws a warning naming the backfill command. The CSV is
    converted to data/derived/osha only when that Parquet is absent; delete it to rebuild.

Raw files go to data/raw/osha, and each download is recorded in data/raw/manifest.jsonl
with its URL, retrieval time, SHA-256, and httpx version. A file that already exists there
is kept as delivered and not downloaded again, and one that is absent but still recorded
fails the run before any download, so the original is restored rather than replaced.
--data-dir moves the whole data root.

The CSVs mix encodings: most non-ASCII text is Windows-1252, a few rows are UTF-8
(embedding_data.osha_encoding). The case-detail CSV is transcoded to a temporary UTF-8 copy
beside the Parquet and sunk to Parquet. Code columns stay strings even where the data
dictionary calls them numeric (zip_code has already lost its leading zeros upstream;
SOC_code reads 00-9900 when unassigned); counts become Int64, dates and times become Date
and Time, and a value that does not parse fails the conversion.
'''

import shlex
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import httpx
import polars as pl
import polars.selectors as cs
import typer

from embedding_data import ita_catalog, ita_summary, manifest, paths
from embedding_data.ita_catalog import file_name
from embedding_data.osha_encoding import decode_line

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


SETS = ('summary', 'case-detail')
CSV_URL = (
    'https://www.osha.gov/sites/default/largefiles/'
    'ITA_Case_Detail_Data_2025_through_08-31-2026.csv'
)
DICTIONARY_URL = 'https://www.osha.gov/sites/default/files/case_detail_data_dictionary_2026.pdf'

# osha.gov's CloudFront distribution answers 403 to httpx's default and to descriptive
# user agents, and 200 to a browser one (checked 2026-10-12, over HTTP/2 and HTTP/1.1).
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
)
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
CHUNK_SIZE = 1024 * 1024
BACKFILL_COMMAND = 'uv run --locked python -m embedding_data.raw_backfill'

INTEGER_COLUMNS = [
    'ID', 'establishment_ID', 'naics_year', 'establishment_type', 'Size',
    'annual_average_employees', 'total_hours_worked', 'incident_outcome',
    'dafw_num_away', 'djtr_num_tr', 'type_of_incident', 'time_unknown', 'year_of_filing',
]
FLOAT_COLUMNS = ['SOC_probability']
DATE_COLUMNS = ['date_of_incident', 'date_of_death', 'date_submitted']
TIME_COLUMNS = ['time_started_work', 'time_of_incident']


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''HTTP/2 client that osha.gov will serve.'''
    return httpx.Client(
        http2=True,
        follow_redirects=True,
        headers={'User-Agent': USER_AGENT},
        timeout=TIMEOUT,
        transport=transport,
    )


def is_recorded(manifest_path: Path, raw_file: Path) -> bool:
    '''Whether the manifest has an entry for raw_file.'''
    path = raw_file.relative_to(manifest_path.parent).as_posix()
    return any(entry.path == path for entry in manifest.read_manifest(manifest_path))


def refuse_replacement(manifest_path: Path, raw_file: Path) -> None:
    '''Exit before any download: a replacement could differ from the recorded hash.'''
    recorded = manifest.entry_for(manifest_path, raw_file)
    typer.echo(
        f'{raw_file.name}: error: the raw file is missing but recorded in {manifest_path} '
        f'with SHA-256 {recorded.sha256[:12]}...; restore the original file (its hash must '
        'match) rather than downloading a replacement. This command will not re-download '
        'over an existing record.',
        err=True,
    )
    raise typer.Exit(code=1)


def refuse_unrecorded(manifest_path: Path, raw_file: Path) -> None:
    '''Exit before any download: an unrecorded summary file on disk has no provenance.'''
    typer.echo(
        f'{raw_file.name}: error: the file exists but is not recorded in {manifest_path}, so '
        'its provenance is unknown; move it aside so this command downloads and records it.',
        err=True,
    )
    raise typer.Exit(code=1)


def download(client: httpx.Client, url: str, destination: Path) -> None:
    '''Stream url to a .part file and rename it only once the body is complete.'''
    partial = destination.with_name(destination.name + '.part')
    try:
        with client.stream('GET', url) as response:
            response.raise_for_status()
            with partial.open('wb') as file:
                for chunk in response.iter_bytes(CHUNK_SIZE):
                    file.write(chunk)
        expected = response.headers.get('Content-Length')
        if expected is not None and response.num_bytes_downloaded != int(expected):
            raise httpx.RemoteProtocolError(
                f'{url}: received {response.num_bytes_downloaded:,} of {int(expected):,} bytes',
                request=response.request,
            )
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    size = destination.stat().st_size
    typer.echo(f'wrote {destination} ({response.http_version}, {size:,} bytes)')


def record_download(manifest_path: Path, destination: Path, url: str, **provenance) -> None:
    '''Hash a finished download and append its manifest entry.'''
    entry = manifest.describe_file(
        destination,
        manifest_path.parent,
        retrieved_at=datetime.now(UTC),
        client='httpx',
        client_version=version('httpx'),
        source_url=url,
        **provenance,
    )
    manifest.append_entries(manifest_path, [entry])


def csv_to_parquet(csv_path: Path, parquet_path: Path) -> Path:
    '''Transcode the raw CSV to a temporary UTF-8 copy beside parquet_path; sink typed Parquet.'''
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    utf8_path = parquet_path.with_suffix('.utf8.csv')
    partial = parquet_path.with_name(parquet_path.name + '.part')
    try:
        # Splitting on b'\n' is safe for both encodings: neither uses 0x0A inside a character.
        with csv_path.open('rb') as src, utf8_path.open('w', encoding='utf-8', newline='') as dst:
            dst.writelines(decode_line(line) for line in src)

        lf = pl.scan_csv(utf8_path, infer_schema=False).with_columns(
            cs.by_name(INTEGER_COLUMNS, require_all=False).cast(pl.Int64),
            cs.by_name(FLOAT_COLUMNS, require_all=False).cast(pl.Float64),
            cs.by_name(DATE_COLUMNS, require_all=False).str.to_date('%m/%d/%Y'),
            cs.by_name(TIME_COLUMNS, require_all=False).str.to_time('%H:%M'),
        )
        lf.sink_parquet(partial)
        partial.replace(parquet_path)
    finally:
        utf8_path.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
    return parquet_path


def acquire_summary(data_dir: Path) -> None:
    '''Download each listed summary file not yet on disk, then rebuild the stacked table.'''
    raw = ita_summary.summary_dir(data_dir)
    manifest_path = paths.manifest_path(data_dir)
    with make_client() as client:
        page = client.get(ita_catalog.PAGE_URL)
        page.raise_for_status()
        try:
            catalog = ita_catalog.parse_catalog(page.text, str(page.url))
            ita_catalog.check_complete(catalog)
        except ValueError as error:
            typer.echo(f'{ita_catalog.PAGE_URL}: error: {error}', err=True)
            raise typer.Exit(code=1) from None
        destinations = {
            release.url: raw / str(release.year) / file_name(release.url)
            for release in catalog.releases
        }
        destinations |= {url: raw / file_name(url) for url in catalog.dictionaries}
        for destination in destinations.values():
            recorded = is_recorded(manifest_path, destination)
            if not destination.exists() and recorded:
                refuse_replacement(manifest_path, destination)
            if destination.exists() and not recorded:
                refuse_unrecorded(manifest_path, destination)
        for url, destination in destinations.items():
            if destination.exists():
                typer.echo(f'{destination.name}: exists, keeping it as delivered')
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            download(client, url, destination)
            record_download(
                manifest_path, destination, url,
                through_date=ita_catalog.through_date(destination.name),
            )
    table = ita_summary.build_summary_table(data_dir)
    typer.echo(f'wrote {table}')
    for line in ita_summary.report_lines(ita_summary.totals_report(table)):
        typer.echo(line)


def acquire_case_detail(data_dir: Path) -> None:
    '''Download the case-detail CSV and dictionary if absent; convert the CSV once.'''
    raw = paths.raw_dir(data_dir, 'osha')
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = paths.manifest_path(data_dir)
    destinations = {url: raw / file_name(url) for url in (DICTIONARY_URL, CSV_URL)}
    for destination in destinations.values():
        if not destination.exists() and is_recorded(manifest_path, destination):
            refuse_replacement(manifest_path, destination)
    with make_client() as client:
        for url, destination in destinations.items():
            if destination.exists():
                typer.echo(f'{destination.name}: exists, keeping it as delivered')
                if not is_recorded(manifest_path, destination):
                    typer.echo(
                        f'{destination.name}: warning: not recorded in {manifest_path}; to '
                        f'record it, run {BACKFILL_COMMAND} '
                        f'--data-dir {shlex.quote(str(data_dir))}',
                        err=True,
                    )
                continue
            download(client, url, destination)
            record_download(manifest_path, destination, url)

    csv_path = raw / file_name(CSV_URL)
    parquet_path = paths.derived_dir(data_dir, 'osha') / csv_path.with_suffix('.parquet').name
    if parquet_path.exists():
        typer.echo(f'{parquet_path.name}: exists, not converting again')
        return
    typer.echo(f'wrote {csv_to_parquet(csv_path, parquet_path)}')


@app.command(help=__doc__.splitlines()[0])
def main(
    sets: Annotated[
        list[str] | None,
        typer.Argument(help='summary and/or case-detail (default: both)'),
    ] = None,
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/ and derived/.'),
    ] = paths.DATA_DIR,
) -> None:
    sets = sets or list(SETS)
    unknown = sorted(set(sets).difference(SETS))
    if unknown:
        raise typer.BadParameter('unknown set(s): ' + ', '.join(unknown), param_hint='sets')
    if 'summary' in sets:
        acquire_summary(data_dir)
    if 'case-detail' in sets:
        acquire_case_detail(data_dir)


if __name__ == '__main__':
    app()
