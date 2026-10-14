import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl
from code_fixtures import seed_code_tree
from geography_fixtures import seed_geography_tree
from ita_fixtures import record, write_release, year_file

from embedding_data import code_build, geography_build, ita_summary, manifest, paths
from embedding_data.target_inputs import SelectedInputs, select

def golden_source_rows() -> dict[int, list[dict[str, str]]]:
    years = {year: [record(year, naics_code='111111', naics_year='2022',
                            street_address='Exact A', city='Fixture Town',
                            state='AL', zip_code='00001')]
             for year in range(2016, 2026)}
    specifications = [
        ('23001', '111111', '2022', 'Exact A', 'AL', '00001'),
        ('23001', '111111', '2022', 'Exact A', 'AL', '00001'),
        ('23003', '111112', '2022', 'Exact A', 'AL', '00001'),
        ('23004', '111111', '2022', 'No match', 'AL', '00001'),
        ('23005', '111112', '2022', 'Exact B', 'VA', '00004'),
        ('23006', '111111', '2017', 'Exact A', 'AL', '00001'),
        ('23007', '999999', '2022', 'Exact A', 'AL', '00001'),
        ('23008', '111111', '0', 'Exact A', 'AL', '00001'),
        ('23009', '111111', '2022', 'No match', 'AL', '00003'),
        ('23010', '111111', '2022', 'Exact excluded', 'AL', '00001'),
        ('23011', '111111', '2022', 'Exact A', 'PR', '00001'),
        ('23012', '111111', '2017', 'Exact C', 'VA', '99999'),
    ]
    years[2023] = [record(2023, id=identifier, establishment_id=identifier,
                          naics_code=code, naics_year=vintage, street_address=street,
                          city='Fixture Town', state=state, zip_code=zipcode)
                   for identifier, code, vintage, street, state, zipcode in specifications]
    years[2023][2].update(annual_average_employees='0', total_hours_worked='-1', size='1')
    return years


def seed_inputs(data_dir: Path) -> SelectedInputs:
    code_registry = seed_code_tree(data_dir, include_summary=False)
    for year, rows in golden_source_rows().items():
        write_release(data_dir, year, year_file(year, rows))
    for name in ['summary_data_dictionary.pdf', 'ITA_Data_Dictionary.pdf']:
        file = data_dir / 'raw/osha/summary' / name
        file.write_bytes(b'%PDF-1.4\n% Fixture documentary evidence\n%%EOF\n')
        entry = manifest.describe_file(
            file, data_dir / 'raw', retrieved_at=datetime(2026, 10, 14, tzinfo=UTC),
            client='fixture', client_version='1')
        manifest.append_entries(paths.manifest_path(data_dir), [entry])
    ita_summary.build_summary_table(data_dir)
    codes = code_build.build(data_dir, 'fixture_codes', registry=code_registry)
    geography_registry = seed_geography_tree(data_dir)
    geography = geography_build.build(data_dir, 'fixture_geography', registry=geography_registry)
    return select(data_dir, 'fixture_codes', 'fixture_geography',
                  codes_outputs_sha256=manifest.sha256_file(codes / 'outputs.json'),
                  geography_outputs_sha256=manifest.sha256_file(geography / 'outputs.json'))


def corrupt_selected(data_dir, selected, defect):
    '''Damage one contract, repinning lower layers only for semantic defect tests.'''
    from embedding_data import target_io

    codes = selected.canonical.parent
    geography = selected.geography['geography_nodes'].parent
    outputs_file = codes / 'outputs.json'
    outputs = json.loads(outputs_file.read_text())
    report_file = codes / 'report.json'
    report = json.loads(report_file.read_text())
    if defect == 'detached_hash':
        outputs_file.write_text(outputs_file.read_text() + ' ')
        return
    if defect == 'file_hash':
        report_file.write_text(report_file.read_text() + ' ')
        return
    if defect == 'size':
        outputs['report.json']['size'] += 1
    elif defect == 'missing_file':
        report_file.unlink()
        return
    elif defect == 'extra_file':
        (codes / 'extra.txt').write_text('extra')
        return
    elif defect == 'schema':
        report['tables']['naics_nodes.parquet']['schema']['code'] = 'Int64'
        target_io.write_json(report_file, report)
    elif defect == 'row_count':
        report['tables']['naics_nodes.parquet']['rows'] += 1
        target_io.write_json(report_file, report)
    elif defect == 'raw_bytes':
        file = data_dir / 'raw' / selected.provenance['raw'][0]['path']
        file.write_bytes(file.read_bytes() + b'changed')
        return
    elif defect == 'source_hash':
        selected.summary.write_bytes(selected.summary.read_bytes() + b'changed')
        return
    elif defect == 'source_order':
        pl.read_parquet(selected.summary).reverse().write_parquet(selected.summary)
        inputs_file = codes / 'inputs.json'
        inputs = json.loads(inputs_file.read_text())
        inputs['source_parquet'].update(
            sha256=manifest.sha256_file(selected.summary), size=selected.summary.stat().st_size)
        target_io.write_json(inputs_file, inputs)
    elif defect == 'canonical_order':
        pl.read_parquet(selected.canonical).reverse().write_parquet(selected.canonical)
    elif defect == 'native_flags':
        frame = pl.read_parquet(selected.canonical)
        frame.with_columns(pl.when(pl.col('year_filing_for').eq(2025))
                           .then(True).otherwise(pl.col('flag_naics_crosswalked'))
                           .alias('flag_naics_crosswalked')).write_parquet(selected.canonical)
    elif defect == 'native_node_level':
        file = selected.codes['naics_nodes']
        frame = pl.read_parquet(file)
        frame.with_columns(pl.when(pl.col('level').eq('national_industry'))
                           .then(pl.lit('industry')).otherwise(pl.col('level'))
                           .alias('level')).write_parquet(file)
    elif defect == 'geography_edge':
        file = selected.geography['geography_edges']
        frame = pl.read_parquet(file)
        frame.with_columns(pl.lit('invalid').alias('edge_type')).write_parquet(file)
        outputs_file = geography / 'outputs.json'
        outputs = json.loads(outputs_file.read_text())
    else:
        raise ValueError(f'unknown test defect {defect}')
    for name, file_stats in outputs.items():
        file = outputs_file.parent / name
        file_stats['sha256'] = manifest.sha256_file(file)
        if not (defect == 'size' and name == 'report.json'):
            file_stats['size'] = file.stat().st_size
    target_io.write_json(outputs_file, outputs)
    family = 'geography' if defect == 'geography_edge' else 'codes'
    selected.provenance[family]['outputs_sha256'] = manifest.sha256_file(outputs_file)


def install_implemented_software_boundary(monkeypatch):
    import importlib.util

    from embedding_data import ita_assignment_prepare as preparation

    modules = tuple(name for name in preparation.FROZEN_MODULES
                    if importlib.util.find_spec('embedding_data.' + name) is not None)
    monkeypatch.setattr(preparation, 'FROZEN_MODULES', modules)


def prepared_tree(data_dir: Path, *, batch_limit: int = 10_000):
    from unittest.mock import patch

    from embedding_data import ita_assignment_prepare as preparation

    selected = seed_inputs(data_dir)
    with patch.object(preparation, 'BATCH_LIMIT', batch_limit):
        preparation.prepare(
            data_dir, 'requests', 'fixture_codes', 'fixture_geography',
            codes_outputs_sha256=selected.provenance['codes']['outputs_sha256'],
            geography_outputs_sha256=selected.provenance['geography']['outputs_sha256'])
    return preparation.check_preparation(data_dir, 'requests')


def submitted_edge_cases():
    return pl.DataFrame({
        'street_address': [None, '', '1 Main St', '1 MAIN ST', '1 Main St ',
                           'Café "A",\nFloor 2', '', 'Excluded'],
        'city': ['', None, 'Town', 'Town', 'Town', 'Québec', None, 'Town'],
        'state': ['', '', 'AL', 'AL', 'AL', 'AL', None, 'PR'],
        'zip_code': [None, 'invalid', '12345-6789', '123456789', '1234', '00001', '', '00001'],
    })


def census_client(requests: list[dict], *, fail_batch: int | None = None) -> httpx.Client:
    '''Serve the actual multipart Census protocol without network or source data.'''
    import csv
    import hashlib
    import io
    from email import policy
    from email.parser import BytesParser

    batch = 0

    def serve(request):
        nonlocal batch
        call = {'method': request.method, 'url': str(request.url)}
        requests.append(call)
        if request.url.path.endswith('/benchmarks'):
            return httpx.Response(200, json={
                'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': 7}]})
        if request.url.path.endswith('/vintages'):
            assert request.url.params['benchmark'] == '7'
            return httpx.Response(200, json={
                'vintages': [{'vintageName': 'ACS2025_Current', 'id': 999}]})
        assert request.method == 'POST'
        assert request.url.path.endswith('/geographies/addressbatch')
        message = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: ' + request.headers['content-type'] + '\r\n\r\n').encode()
            + request.read())
        parts = {part.get_param('name', header='content-disposition'): part
                 for part in message.iter_parts()}
        payload = parts['addressFile'].get_payload(decode=True)
        call.update(benchmark=parts['benchmark'].get_content().strip(),
                    vintage=parts['vintage'].get_content().strip(),
                    request_sha256=hashlib.sha256(payload).hexdigest())
        if batch == fail_batch:
            raise httpx.ReadError('fixture interrupted batch', request=request)
        batch += 1
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        counties = {'Exact A': '01001', 'Exact B': '51510', 'Exact C': '51001',
                    'Exact excluded': '72001'}
        for identifier, street, _city, _state, _zip in csv.reader(
                io.StringIO(payload.decode('utf-8'))):
            if street in counties:
                county = counties[street]
                writer.writerow([identifier, '', 'Match', 'Exact', '', '', '', '',
                                 county[:2], county[2:], '', ''])
            else:
                writer.writerow([identifier, '', 'Tie' if street == 'Tie' else 'No_Match'])
        body = output.getvalue().encode()
        return httpx.Response(200, headers={'Content-Length': str(len(body))},
                              stream=httpx.ByteStream(body))

    return httpx.Client(transport=httpx.MockTransport(serve), timeout=600)


def assignment_inputs(tmp_path, *, status='Match', kind='Exact', returned='01001',
                      zip_code='00001', state='AL', street='1 Main', city='Town'):
    from geography_fixtures import source_frames

    from embedding_data import geography_hud, geography_tables
    from embedding_data.ita_assignment_prepare import request_frames
    from embedding_data.target_inputs import CANONICAL_SCHEMA

    sources = source_frames(tmp_path)
    counties = geography_tables.assemble(sources)['county_reference']
    hud = geography_hud.lookup(geography_hud.annotate(sources['hud'], counties))
    row = dict.fromkeys(CANONICAL_SCHEMA)
    row.update(year_filing_for=2023, id=1, establishment_id=99,
               street_address=street, city=city,
               state=state, zip_code=zip_code)
    canonical = pl.DataFrame([row], schema=CANONICAL_SCHEMA).lazy()
    index, requests = request_frames(canonical)
    responses = requests.select('request_id').with_columns(
        pl.lit(status, dtype=pl.String).alias('geocode_status'),
        pl.lit(kind, dtype=pl.String).alias('match_type'),
        pl.lit(returned, dtype=pl.String).alias('geocode_county_geoid'))
    return canonical, index, responses, hud, counties


def assignment_case(census_status, match_type, returned_county, zip_code, state):
    from tempfile import TemporaryDirectory

    from embedding_data.ita_assignment import assign

    with TemporaryDirectory() as directory:
        inputs = assignment_inputs(Path(directory), status=census_status, kind=match_type,
                                   returned=returned_county, zip_code=zip_code, state=state)
        return assign(*inputs).collect().row(0, named=True)


def assigned_tree(data_dir: Path) -> tuple[pl.LazyFrame, pl.DataFrame, pl.DataFrame]:
    from unittest.mock import patch

    from embedding_data import ita_assignment_acquire as acquisition
    from embedding_data.ita_assignment import assign

    prepared = prepared_tree(data_dir)
    with patch.object(acquisition, 'make_client', lambda: census_client([])):
        acquisition.acquire(data_dir, prepared.directory.name)
    evidence = acquisition.read_evidence(data_dir, prepared)
    selected = prepared.selected
    counties = pl.read_parquet(selected.geography['county_reference'])
    assignments = assign(pl.scan_parquet(selected.canonical),
                         pl.scan_parquet(prepared.source_index), evidence.responses,
                         pl.read_parquet(selected.geography['hud_zip_lookup']), counties)
    return assignments, pl.read_parquet(selected.codes['naics_nodes']), counties
