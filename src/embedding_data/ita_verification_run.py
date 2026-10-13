'''Explicit ITA reference/geocode acquisition and offline verification reports.'''

import csv
import json
import re
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl
import typer

from embedding_data import ita_county_verification as county
from embedding_data import ita_references as refs
from embedding_data import ita_summary, manifest, paths
from embedding_data import ita_verification as verify
from embedding_data.osha_benchmark_download import record_download

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
GEOCODER = 'https://geocoding.geo.census.gov/geocoder'
BENCHMARK = 'Public_AR_Current'
VINTAGE = 'ACS2025_Current'
BATCH_LIMIT = 10_000

def make_client() -> httpx.Client:
    return httpx.Client(http2=True, follow_redirects=True, timeout=600)

def run_dir(data_dir: Path, run_id: str) -> Path:
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', run_id):
        raise ValueError('run_id must contain only letters, digits, hyphens and underscores')
    return paths.derived_dir(data_dir, 'osha') / 'verification' / run_id

def write_json(file: Path, value) -> None:
    file.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n')

def source_entries(data_dir: Path, table: Path, hud: Path) -> list[dict]:
    raw_root = paths.manifest_path(data_dir).parent
    summary_paths = pl.scan_parquet(table).select('source_file').unique().collect()['source_file']
    files = [raw_root / name for name in summary_paths]
    files.extend(
        refs.reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1])
        for url in refs.TITLE_FILES.values()
    )
    files.append(hud)
    return [
        asdict(manifest.entry_for(paths.manifest_path(data_dir), file))
        for file in sorted(set(files))
    ]

def prepare(data_dir: Path, hud: Path, run_id: str) -> Path:
    directory = run_dir(data_dir, run_id)
    if directory.exists():
        raise ValueError(f'{directory}: run already exists; use a new run_id')
    manifest.entry_for(paths.manifest_path(data_dir), hud)
    titles = refs.read_titles(data_dir)
    table = ita_summary.build_summary_table(data_dir)
    candidates = county.zip_candidates(county.read_hud(hud))
    sample = county.stratified_sample(pl.scan_parquet(table), candidates)
    inventory = source_entries(data_dir, table, hud)
    directory.mkdir(parents=True)
    sample.write_parquet(directory / 'sample.parquet')
    requests = directory / 'requests'
    requests.mkdir()
    for start in range(0, sample.height, BATCH_LIMIT):
        file = requests / f'{start // BATCH_LIMIT:04d}.csv'
        with file.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            for row in sample.slice(start, BATCH_LIMIT).iter_rows(named=True):
                writer.writerow(
                    [
                        row['row_key'], row['street_address'] or '', row['city'] or '',
                        row['state'] or '', row['zip_key'] or ''
                    ]
                )
    write_json(
        directory / 'inputs.json', {
            'raw_inputs': inventory,
            'hud_path': hud.relative_to(paths.manifest_path(data_dir).parent).as_posix(),
            'table_sha256': manifest.sha256_file(table),
            'sample_sha256': manifest.sha256_file(directory / 'sample.parquet'),
            'requests': {
                file.name: manifest.sha256_file(file)
                for file in sorted(requests.glob('*.csv'))
            },
            'algorithm': 'ita-verification-v1',
            'sample_salt': county.SAMPLE_SALT,
            'per_stratum': 8,
            'versions': {
                name: version(name)
                for name in ('polars', 'httpx', 'fastexcel')
            },
            'title_counts': titles.group_by('vintage').len().sort('vintage').to_dicts(),
            'code_sha256': {
                file.name: manifest.sha256_file(file)
                for file in (
                    Path(verify.__file__),
                    Path(county.__file__),
                    Path(refs.__file__),
                    Path(__file__),
                    Path(manifest.__file__),
                    Path(ita_summary.__file__),
                )
            },
        }
    )
    return directory

def check_inputs(data_dir: Path, directory: Path) -> dict:
    inputs = json.loads((directory / 'inputs.json').read_text())
    raw_root = paths.manifest_path(data_dir).parent
    for item in inputs['raw_inputs']:
        current = manifest.entry_for(paths.manifest_path(data_dir), raw_root / item['path'])
        if current.sha256 != item['sha256']:
            raise ValueError('input inventory differs from current raw provenance')
    checks = {
        directory / 'sample.parquet': inputs['sample_sha256'],
        paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME: inputs['table_sha256']
    }
    checks.update(
        {
            directory / 'requests' / name: digest
            for name, digest in inputs['requests'].items()
        }
    )
    for file, expected in checks.items():
        if manifest.sha256_file(file) != expected:
            raise ValueError(f'{file}: verification input changed')
    for name, expected in inputs['code_sha256'].items():
        if manifest.sha256_file(Path(__file__).parent / name) != expected:
            raise ValueError(f'{name}: verification code changed; prepare a new run')
    for name, expected in inputs['versions'].items():
        if version(name) != expected:
            raise ValueError(f'{name}: dependency version changed; prepare a new run')
    return inputs

def acquire_geocodes(data_dir: Path, run_id: str) -> None:
    directory = run_dir(data_dir, run_id)
    inputs = check_inputs(data_dir, directory)
    raw_relative = f'census-geocoder/{run_id}'
    responses = []
    with make_client() as client:
        benchmarks = refs.fetch_reference(
            data_dir, client, GEOCODER + '/benchmarks', raw_relative + '/benchmarks.json'
        )
        options = json.loads(benchmarks.read_text())['benchmarks']
        matches = [item for item in options if item['benchmarkName'] == BENCHMARK]
        if len(matches) != 1:
            raise ValueError('requested Census benchmark unavailable or ambiguous')
        benchmark_id = matches[0]['id']
        vintages = refs.fetch_reference(
            data_dir, client, GEOCODER + f'/vintages?benchmark={benchmark_id}',
            raw_relative + '/vintages.json'
        )
        options = json.loads(vintages.read_text())['vintages']
        matches = [item for item in options if item['vintageName'] == VINTAGE]
        if len(matches) != 1:
            raise ValueError('requested Census geography vintage unavailable or ambiguous')
        vintage_id = matches[0]['id']
        for name, request_hash in sorted(inputs['requests'].items()):
            request_file = directory / 'requests' / name
            with request_file.open(newline='', encoding='utf-8') as stream:
                expected_ids = {row[0] for row in csv.reader(stream)}
            destination = refs.reference_path(data_dir, raw_relative + f'/{request_hash}.csv')
            if not refs.existing_reference(data_dir, destination):
                with request_file.open('rb') as stream:
                    response = client.post(
                        GEOCODER + '/geographies/addressbatch',
                        data={
                            'benchmark': benchmark_id,
                            'vintage': vintage_id
                        },
                        files={'addressFile': (name, stream, 'text/csv')}
                    )
                response.raise_for_status()
                parsed = county.parse_geocodes(response.text)
                if expected_ids != set(parsed['row_key'].to_list()):
                    raise ValueError('Census batch response IDs differ from request IDs')
                partial = destination.with_name(destination.name + '.part')
                try:
                    partial.write_bytes(response.content)
                    partial.replace(destination)
                finally:
                    partial.unlink(missing_ok=True)
                record_download(
                    paths.manifest_path(data_dir), destination,
                    GEOCODER + '/geographies/addressbatch'
                )
            parsed = county.parse_geocodes(destination.read_text())
            if expected_ids != set(parsed['row_key'].to_list()):
                raise ValueError('Census batch response IDs differ from request IDs')
            responses.append(
                asdict(manifest.entry_for(paths.manifest_path(data_dir), destination))
            )
    write_json(
        directory / 'geocoding.json', {
            'benchmark': BENCHMARK,
            'benchmark_id': benchmark_id,
            'vintage': VINTAGE,
            'vintage_id': vintage_id,
            'responses': responses,
            'catalogs': [
                asdict(manifest.entry_for(paths.manifest_path(data_dir), file))
                for file in (benchmarks, vintages)
            ],
            'acquisition_start': min(item['retrieved_at'] for item in responses),
            'acquisition_end': max(item['retrieved_at'] for item in responses),
            'benchmark_snapshot_limit': (
                'Current address data can change between batches, including resumed acquisition; '
                'catalogs identify the request options, not a frozen address-source snapshot.'
            ),
        }
    )

def markdown_table(records: list[dict]) -> str:
    if not records:
        return '(No rows.)\n'
    columns = list(records[0])

    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')

    return '\n'.join(
        [
            '| ' + ' | '.join(columns) + ' |',
            '| ' + ' | '.join('---' for _ in columns) + ' |',
            *['| ' + ' | '.join(cell(row[name]) for name in columns) + ' |' for row in records],
        ]
    ) + '\n'

def measure(data_dir: Path, run_id: str) -> dict:
    directory = run_dir(data_dir, run_id)
    inputs = check_inputs(data_dir, directory)
    geocoding = json.loads((directory / 'geocoding.json').read_text())
    raw_root = paths.manifest_path(data_dir).parent
    frames = []
    for item in [*geocoding['catalogs'], *geocoding['responses']]:
        entry = manifest.entry_for(paths.manifest_path(data_dir), raw_root / item['path'])
        if entry.sha256 != item['sha256']:
            raise ValueError('geocoding inventory differs from raw provenance')
    for item in geocoding['responses']:
        frames.append(county.parse_geocodes((raw_root / item['path']).read_text()))
    lf = pl.scan_parquet(paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME)
    descriptions = verify.description_report(lf, refs.read_titles(data_dir))
    quality = verify.quality_report(lf)
    pairs = sorted(set([(year, year + 1) for year in range(2016, 2025)] + [(2023, 2025)]))
    links = [verify.link_report(lf, first, second) for first, second in pairs]
    strata, overall = county.county_report(
        pl.read_parquet(directory / 'sample.parquet'), pl.concat(frames)
    )
    result = {
        'inputs': inputs,
        'geocoding': geocoding,
        'v1': descriptions.to_dicts(),
        'quality': quality.to_dicts(),
        'v2': links,
        'v3_overall': overall,
        'v3_strata': strata.to_dicts()
    }
    descriptions.write_parquet(directory / 'v1.parquet')
    quality.write_parquet(directory / 'quality.parquet')
    strata.write_parquet(directory / 'v3-strata.parquet')
    write_json(directory / 'v2.json', links)
    write_json(directory / 'reports.json', result)
    text = '# ITA V1–V3 measurements\n\nMeasurement report; decisions are not yet adopted.\n\n'
    text += '## Inputs and versions\n\n```json\n' + json.dumps(
        {
            'inputs': inputs,
            'geocoding': geocoding
        }, indent=2, sort_keys=True
    ) + '\n```\n\n'
    for heading, records in [
        ('V1', result['v1']), ('Quality', result['quality']), ('V2', result['v2']),
        ('V3 sample totals', [overall])
    ]:
        text += f'## {heading}\n\n' + markdown_table(records) + '\n'
    text += (
        '## Interpretation\n\nCounts retain their denominators. V1 flags overlap. '
        'V2 confirms only unique-ID links with a known matching EIN and address. '
        'V3 coverage differs from assignment and conditional agreement. '
        'Weighted V3 summaries estimate the distinct-row sampling population; '
        'they are not unweighted sample percentages or accuracy estimates.\n'
    )
    (directory / 'finding.md').write_text(text)
    return result

@app.command('references')
def references_command(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')) -> None:
    refs.acquire_titles(data_dir)

@app.command('import-hud')
def import_hud_command(
    workbook: Path, quarter: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    typer.echo(refs.import_hud(data_dir, workbook, quarter))

@app.command('sample')
def sample_command(
    hud: Path, run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    typer.echo(prepare(data_dir, hud, run_id))

@app.command('geocode')
def geocode_command(
    run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    acquire_geocodes(data_dir, run_id)

@app.command('measure')
def measure_command(
    run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    result = measure(data_dir, run_id)
    typer.echo(f"measured {sum(row['n_rows'] for row in result['v1']):,} ITA rows")

if __name__ == '__main__':
    app()
