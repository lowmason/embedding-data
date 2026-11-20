'''Stage 14 vendor-link bundles: build, verify and compare one immutable directory.

Every raw file is synthetic. The module fixture builds a real Stage 4 codes bundle from the
committed Stage 10 fixtures, seeds a small three-year window of subaward ZIPs and one SAM.gov
extract in the invented test registries into a pristine `tmp_path` data root, copies that
root and builds the run `FIRST` in the copy. A test that changes raw data copies the pristine
root, or seeds a root of its own. The UEIs and amounts are made up. `DNB_SENTINEL` stands in
for D&B Open Data. Fixture results show software readiness only, never benchmarks.
'''

import json
import re
import shutil
import tempfile
from dataclasses import asdict, replace
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import polars as pl
import pytest
from polars.testing import assert_frame_equal
from target_fixtures import forbid_external_access
from vendor_link_fixtures import (  # noqa: F401
    DNB_SENTINEL,
    TEST_EXTRACT_LAYOUT,
    TEST_SUBAWARD_LAYOUTS,
    extract_line,
    module_file,
    no_live_sam,
    seed_codes_bundle,
    seed_raw,
    subaward_record,
    subprocess_modules,
    write_subaward_zip,
)

from embedding_data import (
    code_build,
    ita_summary,
    manifest,
    paths,
    sam_access,
    sam_raw,
    target_contract,
    target_io,
    usaspending_raw,
    vendor_link_bundle,
    vendor_link_codes,
    vendor_link_layouts,
    vendor_link_pairs,
    vendor_link_readers,
    vendor_link_targets,
)
from embedding_data.vendor_link_bundle import (
    CONTRACTS,
    FILES,
    SOFTWARE_FILES,
    TABLES,
    build,
    compare_runs,
    freeze_software,
    ordered_equal,
    run_directory,
    verify_bundle,
)

WINDOW = (2024, 2025, 2026)
SNAPSHOT = date(2026, 11, 20)
# The extract month differs from the snapshot month, as in production.
MONTH = '2026-10'
FIRST = 'vlb_first_q7'
MEMBER = 'Contracts_Subawards_1.csv'
EXTRACT_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261002.dat'
BOM_YEAR = 2025
NODE = 'naics:2022:national_industry:'
TEST_REGISTRIES = {'subaward_layouts': TEST_SUBAWARD_LAYOUTS,
                   'extract_layout': TEST_EXTRACT_LAYOUT}
P1, P2, P3, P4 = 'PRIMEA000001', 'PRIMEB000002', 'PRIMEC000003', 'PRIMED000004'
S1, S2, S3, S4, S5, S6 = ('SUBAWA000001', 'SUBAWB000002', 'SUBAWC000003', 'SUBAWD000004',
                          'SUBAWE000005', 'SUBAWF000006')
OTHER = 'OTHERX000009'
UEIS = (P1, P2, P3, P4, S1, S2, S3, S4, S5, S6, OTHER)
SUBAWARD_PATHS = tuple(
    f'usaspending/subcontracts/2026-11-20/FY{year}/FY{year}_Contracts_Subawards_'
    f'{"bom" if year == BOM_YEAR else "fixture"}.zip' for year in WINDOW)
EXTRACT_PATH = ('sam/entity-extract/public-monthly-v2/2026-10/'
                'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261002.ZIP')
NAMED_FILES = {'src/embedding_data/usaspending_subaward_headers.json',
               'src/embedding_data/sam_extract_layout.json', 'pyproject.toml', 'uv.lock'}
INPUT_FIELDS = {'run_id', 'contracts', 'codes', 'raw', 'snapshot', 'sam_month', 'window',
                'registries', 'rules', 'software', 'execution'}
COUNT_KEYS = {'reports', 'usable_by_fiscal_year', 'firms', 'pairs', 'join_coverage', 'trigger',
              'extract', 'missing_fields'}
LINK_KEYS = {'n_suppliers', 'n_buyers', 'n_pairs', 'diagonal', 'cells_only_intra_group',
             'n_unweighted_distribution', 'subcontractors_per_prime',
             'primes_per_subcontractor'}
OWN_KEYS = {'contracts', 'snapshot', 'sam_month', 'window', 'bom', 'tables', 'limits',
            'universe', 'size_gate'}
# The spec's Methodological limits bullets, each joined into one line.
LIMITS = [
    'The population is federal prime contractors and the subcontractors they report. It is '
    'not all firms or all business-to-business trade.',
    'Industries are SAM.gov registrations at the extract date. A firm whose industry changed '
    'after a subaward counts under its new code. A firm whose registration expired more than '
    '6 months before the extract is missing.',
    'A subcontractor with a UEI only has no code. Its links are lost. Join coverage measures '
    'this loss.',
    'Codes, links and amounts are self-reported and unvalidated. That codes are self-reported '
    'is also what the KYB use tests.',
    "One primary code per firm hides a firm's other industries. Other codes are diagnostics "
    'only.',
    'Corporate groups are seen only through reported parent UEIs. A group with no reported '
    'parent stays in the headline cells.',
    'One firm can hold several UEIs. This project cannot join them.',
    'The window spans the move of subaward reporting from FSRS.gov to SAM.gov on 2025-03-08. '
    'Counts by year and month show any break, but no correction is made.',
    'USAspending revises its data. A later snapshot is a new run with a new pin.',
    'Counts come from all reports, not a sample. Standard errors are `none`.',
    'Vendor links, TRI parent links and ITA co-ownership measure different relations. '
    'Excluding intra-group pairs keeps vendor links apart from ownership. The protocol '
    'section, O18, decides which families may judge one another.',
]
# The window's reports by file year. FY2024: three usable reports, a blank prime UEI and a
# report outside the window. FY2025: a repeated row, an intra-group pair (the subcontractor's
# parent is the prime) and a prime last updated before the D&B cutoff. FY2026: a
# subcontractor not in SAM.gov, an unparseable amount, a second prime in 236220 and a second
# subcontractor in 541512. P1 and S1 share 541511, a diagonal cell.
WINDOW_ROWS = {
    2024: [dict(prime=P1, sub=S1, action='2024-03-01', amount='1000.00'),
           dict(prime=P1, sub=S2, action='2024-04-01', amount='250.50'),
           dict(prime=P2, sub=S2, action='2024-05-01', amount='75.25'),
           dict(prime='', sub=S1, action='2024-03-01', amount='9.00'),
           dict(prime=P1, sub=S1, action='2022-05-01', amount='5.00')],
    2025: [dict(prime=P1, sub=S1, action='2025-01-15', amount='500.00'),
           dict(prime=P1, sub=S1, action='2025-01-15', amount='500.00'),
           dict(prime=P2, sub=S4, action='2025-02-01', amount='1200.00'),
           dict(prime=P2, sub=S5, action='2025-03-01', amount='10.00', sub_parent_uei=P2),
           dict(prime=P3, sub=S2, action='2025-04-01', amount='20.00')],
    2026: [dict(prime=P1, sub=S3, action='2026-01-10', amount='30.00'),
           dict(prime=P2, sub=S2, action='2026-02-01', amount='n/a'),
           dict(prime=P4, sub=S4, action='2026-03-01', amount='40.00'),
           dict(prime=P1, sub=S6, action='2026-04-01', amount='15.00')],
}
FIRM_CODES = {P1: '541511', P2: '236220', P4: '236220', S1: '541511', S2: '541512',
              S4: '336411', S5: '541512', S6: '541512', OTHER: '5415X1'}


def exactly(message):
    return pytest.raises(ValueError, match=f'^{re.escape(message)}$')


def report(prime, sub, action, amount='', *, year, **fields):
    values = {'prime_uei': prime, 'sub_uei': sub, 'action_date': action, 'amount': amount,
              'subaward_type': 'sub-contract'} | fields
    return subaward_record(TEST_SUBAWARD_LAYOUTS[year], **values)


def window_reports(changes=None):
    '''The window's records by year. `changes` maps `(year, index)` to replacing fields.'''
    rows = {year: [dict(row) for row in rows] for year, rows in WINDOW_ROWS.items()}
    for (year, index), values in (changes or {}).items():
        rows[year][index] |= values
    return {year: [report(**row, year=year) for row in rows[year]] for year in rows}


def firm(uei, code, *, update='20250115'):
    return extract_line(TEST_EXTRACT_LAYOUT, uei=uei, registration_status='A',
                        last_update_date=update, primary_naics=code,
                        naics_code_string=f'{code}Y', evs_source='SAM')


def skipped_line(uei):
    '''An extract line of `uei` with one field more than the layout's 40.'''
    fields = firm(uei, '541511').split('|')
    fields[4:4] = [DNB_SENTINEL]
    return '|'.join(fields)


def window_firms(changes=None):
    '''The firms of `FIRM_CODES`, with `changes` replacing codes by UEI; P3 last updated in
    2021; and S3 on a line of the wrong field count only, so it stays not in SAM.gov.'''
    lines = [firm(uei, code) for uei, code in (FIRM_CODES | (changes or {})).items()]
    return [*lines, firm(P3, '541512', update='20210101'), skipped_line(S3)]


def seed(data_dir, originals, *, reports=None, firms=None, years=WINDOW,
         layouts=TEST_SUBAWARD_LAYOUTS, bom_years=(BOM_YEAR,)):
    '''Seed the window's raw files into `data_dir`, one member per year. The members of
    `bom_years` start with a BOM and are written and imported here, because `seed_raw`
    writes no BOM.'''
    reports = window_reports() if reports is None else reports
    seed_raw(data_dir, originals,
             {year: {MEMBER: reports[year]} for year in years if year not in bom_years},
             window_firms() if firms is None else firms, snapshot=SNAPSHOT, month=MONTH,
             subaward_layouts=layouts, extract_layout=TEST_EXTRACT_LAYOUT,
             extract_member=EXTRACT_MEMBER)
    for year in bom_years:
        file = originals / f'FY{year}_Contracts_Subawards_bom.zip'
        write_subaward_zip(file, layouts[year], {MEMBER: reports[year]}, bom=True)
        usaspending_raw.import_file(data_dir, year, file, snapshot=SNAPSHOT)


def build_in(data_dir, run_id, codes, **overrides):
    run, pin = codes
    options = dict(codes_run=run, codes_outputs_sha256=pin, snapshot=SNAPSHOT,
                   sam_month=MONTH, **TEST_REGISTRIES) | overrides
    return build(data_dir, run_id, **options)


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    '''A pristine seeded root, and a copy of it that holds the published run `FIRST`.'''
    root = tmp_path_factory.mktemp('vendor_links')
    codes_root = root / 'codes'
    codes = seed_codes_bundle(codes_root / 'data', codes_root / 'originals')
    bundle = codes_root / 'data' / 'derived' / 'codes' / codes[0]
    pristine = root / 'pristine'
    shutil.copytree(bundle, pristine / 'derived' / 'codes' / codes[0])
    seed(pristine, root / 'originals')
    data_dir = root / 'data'
    shutil.copytree(pristine, data_dir)
    first = build_in(data_dir, FIRST, codes)
    return SimpleNamespace(root=root, bundle=bundle, pristine=pristine, data_dir=data_dir,
                           codes=codes, first=first, directory=Path(first['directory']),
                           pin=first['outputs_sha256'])


def build_run(built, run_id, *, data_dir=None, **overrides):
    return build_in(built.data_dir if data_dir is None else data_dir, run_id, built.codes,
                    **overrides)


def verify(built, directory=None, pin=None, *, data_dir=None, **registries):
    return verify_bundle(built.directory if directory is None else directory,
                         built.data_dir if data_dir is None else data_dir,
                         expected_outputs_sha256=built.pin if pin is None else pin,
                         **(TEST_REGISTRIES | registries))


def fresh_root(built, tmp_path):
    '''A copy of the pristine seeded data root.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(built.pristine, data_dir)
    return data_dir


def seeded_root(built, tmp_path, **changes):
    '''A data root with the codes bundle and the window seeded with `changes`.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(built.bundle, data_dir / 'derived' / 'codes' / built.codes[0])
    seed(data_dir, tmp_path / 'originals', **changes)
    return data_dir


def run_root(data_dir):
    return run_directory(data_dir, FIRST).parent


def tree(root):
    '''Every path under `root`, with the bytes of each file.'''
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in sorted(root.rglob('*'))}


def no_publication(data_dir, run_id):
    root = run_root(data_dir)
    return not (root / run_id).exists() and not (root / (run_id + '.part')).exists()


def read(directory, name):
    return json.loads((directory / name).read_text())


def copy_bundle(built, destination, name=FIRST):
    target = destination / name
    shutil.copytree(built.directory, target)
    return target


def repin(directory):
    '''Rewrite `outputs.json` for the current bundle bytes and return its new pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def edit_json(directory, name, change):
    value = read(directory, name)
    change(value)
    target_io.write_json(directory / name, value)
    return repin(directory)


def edit_table(directory, name, change):
    file = directory / (name + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    return repin(directory)


def first_row(column, value):
    '''Replace the value of one column in the first row only.'''
    return lambda frame: frame.with_columns(
        pl.when(pl.int_range(pl.len()).eq(0)).then(pl.lit(value)).otherwise(pl.col(column))
        .cast(frame.schema[column]).alias(column))


def set_path(*keys_and_value):
    *keys, value = keys_and_value

    def change(document):
        for key in keys[:-1]:
            document = document[key]
        document[keys[-1]] = value
    return change


def delete_path(*keys):
    def change(document):
        for key in keys[:-1]:
            document = document[key]
        del document[keys[-1]]
    return change


def keys_anywhere(value):
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in keys_anywhere(item)}
    if isinstance(value, list):
        return {key for item in value for key in keys_anywhere(item)}
    return set()


def only_file(directory):
    (file,) = directory.iterdir()
    return file


def flip_byte(file):
    data = bytearray(file.read_bytes())
    data[len(data) // 2] ^= 0xFF
    file.write_bytes(bytes(data))


def renamed(year):
    '''The test layout of `year` with its unmapped `description` cell renamed.'''
    layout = TEST_SUBAWARD_LAYOUTS[year]
    return replace(layout, header=tuple('description_text' if cell == 'description' else cell
                                        for cell in layout.header))


def table_rows(directory):
    return {name: pl.scan_parquet(directory / (name + '.parquet')).select(pl.len()).collect()
            .item() for name in TABLES}


def stage_products(data_dir, codes, scratch):
    '''The four tables, the report counts and the estimate report of the seeded window,
    straight from the Task 4-10 functions with the test registries.'''
    layouts, layout = TEST_SUBAWARD_LAYOUTS, TEST_EXTRACT_LAYOUT
    run, pin = codes
    node_ids = vendor_link_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin).node_ids
    files = usaspending_raw.select_files(data_dir, SNAPSHOT)
    extract_file = sam_raw.select_extract(data_dir, MONTH)
    rows = vendor_link_readers.read_subawards(files, layouts, scratch).rows
    reported = vendor_link_pairs.reports(rows, layouts)
    usable = reported.filter(pl.col('report_status') == 'usable')
    extract = vendor_link_readers.read_extract(extract_file, layout)
    unreadable = vendor_link_readers.unreadable_extract_lines(extract_file, layout)
    firms = vendor_link_pairs.firms(usable, extract, layout, node_ids)
    pairs = vendor_link_pairs.pairs(usable, firms)
    counts = vendor_link_pairs.report_counts(reported, firms, pairs, extract, layouts, layout,
                                             node_ids, unreadable)
    links = vendor_link_targets.estimate(pairs, snapshot=SNAPSHOT, month=MONTH)
    tables = {'vendor_links': links.targets, 'vendor_link_marginals': links.marginals,
              'vendor_link_support': links.support, 'vendor_link_pairs': pairs}
    return tables, json.loads(json.dumps(counts)), json.loads(json.dumps(links.report))


# ---- plan tests

def test_build_publishes_the_exact_file_set_and_detached_pin(built):
    # 7 files; outputs.json excludes itself; the pin equals sha256(outputs.json)
    directory = built.directory
    assert directory == run_directory(built.data_dir, FIRST)
    assert sorted(path.name for path in directory.iterdir()) == sorted([*FILES, 'outputs.json'])
    assert len(list(directory.iterdir())) == 7
    outputs = read(directory, 'outputs.json')
    assert 'outputs.json' not in outputs
    assert outputs == target_io.inventory(directory, list(FILES))
    assert built.first == {'run_id': FIRST, 'directory': str(directory),
                           'outputs_sha256': manifest.sha256_file(directory / 'outputs.json')}
    assert not (run_root(built.data_dir) / (FIRST + '.part')).exists()


def test_verify_passes_then_refuses_a_changed_byte_report_or_pin(built, tmp_path):
    assert verify(built) == {'run_id': FIRST, 'outputs_sha256': built.pin,
                             'rows': table_rows(built.directory)}
    changed_byte = copy_bundle(built, tmp_path / 'byte')
    flip_byte(changed_byte / 'vendor_link_support.parquet')
    with exactly('vendor_link_support.parquet: inventory hash or size differs'):
        verify(built, changed_byte)
    changed_report = copy_bundle(built, tmp_path / 'report')
    pin = edit_json(changed_report, 'report.json', set_path('size_gate', 'passed'))
    with exactly('published report differs from the recomputation'):
        verify(built, changed_report, pin)
    with exactly('detached inventory checksum differs'):
        verify(built, pin='0' * 64)


def prepare_refusal(change, built, tmp_path):
    '''The data root, run ID and build options of one refusal.'''
    if change == 'occupied_final':
        return built.data_dir, FIRST, {}
    if change == 'codes_pin':
        return built.data_dir, 'refused_codes_pin', {'codes_outputs_sha256': 'f' * 64}
    if change == 'other_registry':
        # The committed registries hold the real header and member names.
        return built.data_dir, 'refused_other_registry', {'subaward_layouts': None,
                                                           'extract_layout': None}
    if change == 'raw_byte':
        data_dir = fresh_root(built, tmp_path)
        flip_byte(only_file(usaspending_raw.snapshot_dir(data_dir, SNAPSHOT, 2026)))
    elif change == 'header':
        data_dir = seeded_root(built, tmp_path,
                               layouts=TEST_SUBAWARD_LAYOUTS | {2025: renamed(2025)})
    elif change == 'sub_grant':
        data_dir = seeded_root(built, tmp_path, reports=window_reports(
            {(2026, 1): {'subaward_type': 'sub-grant'}}))
    elif change == 'malformed_code':
        data_dir = seeded_root(built, tmp_path, firms=window_firms({P1: '54151A'}))
    else:
        data_dir = seeded_root(built, tmp_path, years=(2024, 2025))
    return data_dir, 'refused_' + change, {}


BUILD_REFUSALS = {
    'raw_byte': 'raw file changed',
    'header': 'changed header',
    'sub_grant': 'subaward type is not sub-contract',
    'malformed_code': 'malformed primary NAICS code',
    'occupied_final': 'run or staging name already exists',
    'codes_pin': 'detached inventory checksum differs',
    'other_registry': 'unexpected ZIP member',
    'missing_year': 'missing or extra raw file',
}


@pytest.mark.parametrize('change', ['raw_byte', 'header', 'sub_grant', 'malformed_code',
                                    'occupied_final', 'codes_pin', 'other_registry',
                                    'missing_year'])
def test_build_refuses(change, built, tmp_path):
    data_dir, run_id, options = prepare_refusal(change, built, tmp_path)
    root = run_root(data_dir)
    before = tree(root)
    with exactly(BUILD_REFUSALS[change]):
        build_run(built, run_id, data_dir=data_dir, **options)
    assert tree(root) == before
    assert not (root / (run_id + '.part')).exists()
    assert (root / run_id).exists() == (change == 'occupied_final')


def test_leftover_staging_is_refused_and_untouched(built, tmp_path):
    # create <id>.part with one file; build with <id> raises; the .part bytes are unchanged
    # and no <id> exists; build with a fresh ID succeeds
    leftover = run_root(built.data_dir) / 'killed.part'
    leftover.mkdir()
    (leftover / 'vendor_links.parquet').write_bytes(b'bytes of a killed build')
    with exactly('run or staging name already exists'):
        build_run(built, 'killed')
    assert tree(leftover) == {'vendor_links.parquet': b'bytes of a killed build'}
    assert not run_directory(built.data_dir, 'killed').exists()
    result = build_run(built, 'fresh_after_kill')
    assert sorted(path.name for path in Path(result['directory']).iterdir()) == sorted(
        [*FILES, 'outputs.json'])


def test_software_change_before_publication_fails_without_a_final(monkeypatch, built):
    real = vendor_link_bundle.freeze_software
    calls = []

    def changing():
        calls.append(True)
        frozen = real()
        return frozen if len(calls) == 1 else {**frozen, 'python': 'changed'}

    monkeypatch.setattr(vendor_link_bundle, 'freeze_software', changing)
    with exactly('executing software changed before publication'):
        build_run(built, 'software')
    assert len(calls) == 2
    assert no_publication(built.data_dir, 'software')


def test_failure_removes_only_its_own_staging(built, monkeypatch):
    root = run_root(built.data_dir)
    other = root / 'other_run.part'
    other.mkdir()
    (other / 'kept.bin').write_bytes(b'staging of another run')
    before = tree(root)
    seen = []

    def failing(pair_table, *, snapshot, month):
        seen.append(sorted(path.name for path in (root / 'failed.part').rglob('*')))
        raise ValueError('estimate failed')

    monkeypatch.setattr(vendor_link_targets, 'estimate', failing)
    with exactly('estimate failed'):
        build_run(built, 'failed')
    assert '.scratch' in seen[0]
    assert tree(root) == before
    assert no_publication(built.data_dir, 'failed')
    shutil.rmtree(other)


def test_compare_runs_equal_and_unequal(built, tmp_path):
    replay = build_run(built, 'replay')
    rows = table_rows(built.directory)
    assert compare_runs(built.directory, Path(replay['directory'])) == {
        'equal': True,
        'tables': {name: {'schema_equal': True, 'values_equal': True,
                          'first_rows': rows[name], 'second_rows': rows[name]}
                   for name in TABLES},
        'report_equal': True,
        'trust_established': False,
    }
    tampered = tmp_path / 'replay'
    shutil.copytree(replay['directory'], tampered)
    edit_table(tampered, 'vendor_link_support', first_row('n_reports', 99))
    unequal = compare_runs(built.directory, tampered)
    assert (unequal['equal'], unequal['report_equal'], unequal['trust_established']) == (
        False, True, False)
    assert {name: unequal['tables'][name]['values_equal'] for name in TABLES} == {
        name: name != 'vendor_link_support' for name in TABLES}


def test_report_has_no_run_identity_or_uei(built):
    text = (built.directory / 'report.json').read_text()
    execution = read(built.directory, 'inputs.json')['execution']
    assert not keys_anywhere(json.loads(text)) & {
        'run_id', 'created_at', 'commit', 'dirty', 'execution', 'directory', 'path', 'sha256',
        'outputs_sha256'}
    for value in (FIRST, *UEIS, DNB_SENTINEL, str(built.root), 'raw/', 'derived/',
                  execution['commit'], execution['created_at']):
        assert value not in text
    assert not re.search(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:', text)


def test_software_files_cover_the_bundle_import_closure():
    loaded = subprocess_modules('embedding_data.vendor_link_bundle')
    assert {module_file(m) for m in loaded} <= set(vendor_link_bundle.SOFTWARE_FILES)


# ---- constants, helpers and software identity

def test_contract_constants():
    assert TABLES == ('vendor_links', 'vendor_link_marginals', 'vendor_link_support',
                      'vendor_link_pairs')
    assert FILES == ('vendor_links.parquet', 'vendor_link_marginals.parquet',
                     'vendor_link_support.parquet', 'vendor_link_pairs.parquet', 'inputs.json',
                     'report.json')
    assert CONTRACTS == {'pairs': 'vendor-link-pairs-v1', 'vendor_links': 'vendor-links-v1',
                         'targets': 'targets-v1',
                         'subaward_headers': 'usaspending-subaward-headers-v1',
                         'extract_layout': 'sam-extract-layout-v1'}
    assert CONTRACTS == {'pairs': vendor_link_pairs.CONTRACT,
                         'vendor_links': vendor_link_targets.CONTRACT,
                         'targets': target_contract.SCHEMA_VERSION,
                         'subaward_headers': vendor_link_layouts.SUBAWARD_VERSION,
                         'extract_layout': vendor_link_layouts.EXTRACT_VERSION}
    assert vendor_link_bundle.SOFTWARE_ROOT == paths.PROJECT_ROOT


def test_run_directory_is_under_the_vendor_links_root(tmp_path):
    assert run_directory(tmp_path, 'run_1') == (
        tmp_path / 'derived' / 'usaspending' / 'vendor-links' / 'run_1')
    for unsafe in ('../escape', '.hidden', 'a/b', '', 'run.part', '-run'):
        with exactly('unsafe run ID'):
            run_directory(tmp_path, unsafe)


def test_software_files_equal_the_measured_closure_plus_the_named_files():
    closure = {module_file(module)
               for name in ('embedding_data.vendor_link_bundle',
                            'embedding_data.usaspending_vendor_links')
               for module in subprocess_modules(name)}
    assert set(SOFTWARE_FILES) == closure | NAMED_FILES
    assert len(SOFTWARE_FILES) == len(set(SOFTWARE_FILES))
    assert all((paths.PROJECT_ROOT / name).is_file() for name in SOFTWARE_FILES)


def test_bundle_module_loads_no_dotenv_ipumspy_or_census_access():
    loaded = subprocess_modules('embedding_data.vendor_link_bundle', prefix=None)
    assert not {'dotenv', 'ipumspy', 'embedding_data.ipums_census_access'} & loaded


def test_subprocess_modules_filters_by_prefix_and_module_file_maps_names():
    everything = subprocess_modules('embedding_data.paths', prefix=None)
    assert {'embedding_data', 'embedding_data.paths', 'json'} <= everything
    assert subprocess_modules('embedding_data.paths') == {
        name for name in everything if name.startswith('embedding_data')}
    assert module_file('embedding_data') == 'src/embedding_data/__init__.py'
    assert module_file('embedding_data.target_io') == 'src/embedding_data/target_io.py'


def test_freeze_software_records_files_python_and_dependencies():
    frozen = freeze_software()
    assert set(frozen) == {'files', 'python', 'python_full', 'implementation', 'dependencies',
                           'uv_lock_sha256'}
    assert list(frozen['files']) == list(SOFTWARE_FILES)
    for name, record in frozen['files'].items():
        file = paths.PROJECT_ROOT / name
        assert record == {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
    assert frozen['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    assert frozen['dependencies']['polars'] == pl.__version__


ORDERED = pl.LazyFrame({'n': [1, 2, None], 'labels': [['a'], [], None]},
                       schema={'n': pl.Int64, 'labels': pl.List(pl.String)})
ORDERED_CASES = {
    'identical': (ORDERED, True, True, 3),
    'null_against_value': (ORDERED.with_columns(pl.col('n').fill_null(3)), True, False, 3),
    'list_value': (ORDERED.with_columns(labels=pl.Series([['a'], ['b'], None])), True, False,
                   3),
    'row_order': (ORDERED.reverse(), True, False, 3),
    'extra_null_row': (pl.concat([ORDERED, pl.LazyFrame({'n': [None], 'labels': [None]},
                                                        schema=ORDERED.collect_schema())]),
                       True, False, 4),
    'dtype': (ORDERED.with_columns(pl.col('n').cast(pl.Int32)), False, False, 3),
    'column_order': (ORDERED.select('labels', 'n'), False, False, 3),
}


@pytest.mark.parametrize('case', ORDERED_CASES)
def test_ordered_equal_compares_order_values_and_schema(case):
    second, schema_equal, values_equal, rows = ORDERED_CASES[case]
    assert ordered_equal(ORDERED, second) == {'schema_equal': schema_equal,
                                              'values_equal': values_equal,
                                              'first_rows': 3, 'second_rows': rows}


def test_ordered_equal_accepts_empty_frames():
    empty = ORDERED.clear()
    assert ordered_equal(empty, empty) == {'schema_equal': True, 'values_equal': True,
                                           'first_rows': 0, 'second_rows': 0}


# ---- build contents

def test_bundle_tables_and_report_equal_the_stage_functions(built, tmp_path):
    tables, counts, links = stage_products(built.data_dir, built.codes, tmp_path)
    for name in TABLES:
        assert_frame_equal(pl.read_parquet(built.directory / (name + '.parquet')), tables[name])
    report_ = read(built.directory, 'report.json')
    assert (set(counts), set(links)) == (COUNT_KEYS, LINK_KEYS)
    assert set(report_) == OWN_KEYS | COUNT_KEYS | LINK_KEYS
    assert {key: report_[key] for key in COUNT_KEYS} == counts
    assert {key: report_[key] for key in LINK_KEYS} == links


def test_fixture_window_reaches_every_wire(built):
    report_ = read(built.directory, 'report.json')
    assert report_['reports']['total']['by_status'] == {
        'uei_unusable': 1, 'action_date_invalid': 0, 'outside_window': 1, 'usable': 12}
    assert report_['reports']['total']['duplicate_rows'] == 1
    assert report_['usable_by_fiscal_year'] == {'2024': 3, '2025': 5, '2026': 4}
    assert report_['pairs'] == {'self_link': 0, 'intra_group': 1, 'prime_ineligible': 1,
                                'sub_ineligible': 1, 'eligible': 6, 'total': 9}
    assert report_['extract']['unreadable_lines'] == 1
    assert report_['extract']['unreadable_firms_not_in_sam'] == {'prime': 0,
                                                                 'subcontractor': 1, 'all': 1}
    assert report_['extract']['malformed_unread_rows'] == 1
    assert report_['firms']['all']['dnb_era_record'] == 1
    assert report_['diagonal'] == {'cells': 1, 'pairs': 1, 'share_of_pairs': 1 / 6}
    assert report_['bom'] == [BOM_YEAR]
    targets = pl.read_parquet(built.directory / 'vendor_links.parquet')
    assert targets.height == 8
    assert set(targets['universe']) == {
        vendor_link_targets.UNIVERSE.format(snapshot='2026-11-20', month=MONTH)}
    intra = targets.filter(pl.col('flags').list.contains(vendor_link_targets.INTRA_LABEL))
    assert intra.select('measure', 'unit_a', 'unit_b', 'value').rows() == [
        ('supplier_share', NODE + '541512', NODE + '236220', 0.5)]


def test_inputs_record_selection_and_provenance(built):
    inputs = read(built.directory, 'inputs.json')
    assert set(inputs) == INPUT_FIELDS
    assert (inputs['run_id'], inputs['contracts']) == (FIRST, CONTRACTS)
    run, pin = built.codes
    assert inputs['codes'] == {
        'run_id': run, 'outputs_sha256': pin,
        'outputs': read(built.data_dir / 'derived' / 'codes' / run, 'outputs.json')}
    entries = {entry.path: json.loads(json.dumps(asdict(entry)))
               for entry in manifest.read_manifest(paths.manifest_path(built.data_dir))}
    assert set(entries) == {*SUBAWARD_PATHS, EXTRACT_PATH}
    assert inputs['raw'] == {'subawards': [entries[path] for path in SUBAWARD_PATHS],
                             'extract': entries[EXTRACT_PATH]}
    assert (inputs['snapshot'], inputs['sam_month'], inputs['window']) == (
        '2026-11-20', MONTH, list(WINDOW))
    assert inputs['registries'] == json.loads(json.dumps({
        'subaward_headers': vendor_link_layouts.subaward_layouts_json(TEST_SUBAWARD_LAYOUTS),
        'extract_layout': vendor_link_layouts.extract_layout_json(TEST_EXTRACT_LAYOUT)}))
    assert inputs['software'] == freeze_software()
    execution = inputs['execution']
    assert set(execution) == {'commit', 'dirty', 'created_at'}
    assert re.fullmatch(r'[0-9a-f]{40}', execution['commit'])
    assert isinstance(execution['dirty'], bool)
    assert datetime.fromisoformat(execution['created_at']).tzinfo is not None


def test_rules_hold_one_sentence_for_each_part(built):
    rules = read(built.directory, 'inputs.json')['rules']
    assert set(rules) == {'report', 'corporate_group', 'firm', 'pair', 'measure'}
    for text in rules.values():
        assert isinstance(text, str) and text and '. ' not in text
    assert all(word in rules['corporate_group'] for word in ('parent', 'prime', 'subcontractor'))
    assert all(word in rules['measure'] for word in ('supplier_share', 'buyer_share'))


@pytest.mark.parametrize('part, statuses', [
    ('report', vendor_link_pairs.REPORT_STATUSES), ('firm', vendor_link_pairs.FIRM_STATUSES),
    ('pair', vendor_link_pairs.PAIR_STATUSES)])
def test_rules_name_their_statuses_in_check_order(built, part, statuses):
    text = read(built.directory, 'inputs.json')['rules'][part]
    positions = [re.search(rf'\b{re.escape(status)}\b', text).start() for status in statuses]
    assert positions == sorted(positions)


def test_report_records_contracts_window_tables_limits_and_universe(built):
    report_ = read(built.directory, 'report.json')
    outputs = read(built.directory, 'outputs.json')
    assert report_['contracts'] == CONTRACTS
    assert (report_['snapshot'], report_['sam_month'], report_['window']) == (
        '2026-11-20', MONTH, list(WINDOW))
    assert report_['tables'] == {
        name: {key: outputs[name + '.parquet'][key] for key in ('rows', 'columns', 'schema')}
        for name in TABLES}
    assert report_['limits'] == LIMITS
    assert report_['universe'] == vendor_link_targets.UNIVERSE.format(snapshot='2026-11-20',
                                                                      month=MONTH)
    assert report_['size_gate'] == 'pending'


def test_none_registries_load_through_the_module_at_call_time(built, monkeypatch):
    calls = []

    def subawards():
        calls.append('subaward_headers')
        return TEST_SUBAWARD_LAYOUTS

    def extract():
        calls.append('extract_layout')
        return TEST_EXTRACT_LAYOUT

    monkeypatch.setattr(vendor_link_layouts, 'load_subaward_layouts', subawards)
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', extract)
    result = build_run(built, 'loaded', subaward_layouts=None, extract_layout=None)
    assert calls == ['subaward_headers', 'extract_layout']
    directory = Path(result['directory'])
    verify_bundle(directory, built.data_dir, expected_outputs_sha256=result['outputs_sha256'])
    assert calls == ['subaward_headers', 'extract_layout'] * 2
    assert compare_runs(built.directory, directory)['equal'] is True


def test_explicit_registries_need_no_loader(built, monkeypatch):
    def forbidden():
        raise AssertionError('a committed registry was loaded')

    monkeypatch.setattr(vendor_link_layouts, 'load_subaward_layouts', forbidden)
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', forbidden)
    result = build_run(built, 'explicit')
    verify(built, Path(result['directory']), result['outputs_sha256'])


@pytest.mark.parametrize('missing', ['subaward_headers', 'extract_layout'])
def test_only_a_missing_registry_is_loaded(built, monkeypatch, missing):
    def forbidden():
        raise AssertionError('a supplied registry was loaded')

    loaders = {'subaward_headers': ('load_subaward_layouts', TEST_SUBAWARD_LAYOUTS),
               'extract_layout': ('load_extract_layout', TEST_EXTRACT_LAYOUT)}
    for kind, (name, value) in loaders.items():
        monkeypatch.setattr(vendor_link_layouts, name,
                            (lambda value=value: value) if kind == missing else forbidden)
    registries = TEST_REGISTRIES | {
        'subaward_layouts' if missing == 'subaward_headers' else 'extract_layout': None}
    result = build_run(built, 'mixed_' + missing, **registries)
    verify(built, Path(result['directory']), result['outputs_sha256'], **registries)


@pytest.mark.parametrize('bom_years', [(), (2024, 2026)])
def test_report_lists_every_bom_year_in_order(built, tmp_path, bom_years):
    data_dir = seeded_root(built, tmp_path, bom_years=bom_years)
    result = build_run(built, 'bom', data_dir=data_dir)
    assert read(Path(result['directory']), 'report.json')['bom'] == list(bom_years)


def ragged(built, tmp_path):
    reports = window_reports()
    reports[2026][2] = [*reports[2026][2], 'one cell too many']
    return seeded_root(built, tmp_path, reports=reports), {}


def other_extract_framing(built, tmp_path):
    return built.data_dir, {'extract_layout': replace(TEST_EXTRACT_LAYOUT,
                                                      bof_prefix='BOF OTHER V2 00000000 ')}


def other_record_end(built, tmp_path):
    return built.data_dir, {'extract_layout': replace(TEST_EXTRACT_LAYOUT, record_end='!fin')}


def other_extract_member(built, tmp_path):
    return built.data_dir, {'extract_layout': replace(
        TEST_EXTRACT_LAYOUT, member_pattern=r'SAM_PUBLIC_UTF-8_MONTHLY_V2_[0-9]{8}\.DAT')}


MORE_REFUSALS = {
    'ragged_subaward_record': (ragged, 'ragged subaward record'),
    'extract_framing': (other_extract_framing, 'missing extract framing'),
    'extract_record_end': (other_record_end, 'missing record end'),
    'extract_member': (other_extract_member, 'unexpected extract member'),
}


@pytest.mark.parametrize('case', MORE_REFUSALS)
def test_build_refuses_a_ragged_record_or_another_extract_layout(built, tmp_path, case):
    prepare, message = MORE_REFUSALS[case]
    data_dir, options = prepare(built, tmp_path)
    before = tree(run_root(data_dir))
    with exactly(message):
        build_run(built, 'refused_' + case, data_dir=data_dir, **options)
    assert tree(run_root(data_dir)) == before


def broken_pairs(real):
    def pairs(usable, firm_table):
        return real(usable, firm_table).with_columns(pl.col('n_reports') + 1)
    return pairs


def broken_estimate(real):
    def estimate(pair_table, *, snapshot, month):
        result = real(pair_table, snapshot=snapshot, month=month)
        return replace(result, support=result.support.with_columns(pl.col('s_suppliers') + 1))
    return estimate


RECOMPUTED_CASES = {
    'pairs': (vendor_link_pairs, 'pairs', broken_pairs,
              'pair reports differ from the usable reports'),
    'estimate': (vendor_link_targets, 'estimate', broken_estimate,
                 'vendor-link support does not match the target cells'),
}


@pytest.mark.parametrize('case', RECOMPUTED_CASES)
def test_build_validates_the_pairs_and_the_estimate(built, monkeypatch, case):
    module, name, breaker, message = RECOMPUTED_CASES[case]
    monkeypatch.setattr(module, name, breaker(getattr(module, name)))
    with exactly(message):
        build_run(built, 'invalid_' + case)
    assert no_publication(built.data_dir, 'invalid_' + case)


@pytest.mark.parametrize('case', RECOMPUTED_CASES)
def test_verify_validates_the_recomputation(built, monkeypatch, case):
    module, name, breaker, message = RECOMPUTED_CASES[case]
    monkeypatch.setattr(module, name, breaker(getattr(module, name)))
    with exactly(message):
        verify(built)


@pytest.mark.parametrize('years', [(2024, 2025), (2023, 2024, 2025, 2026)])
def test_build_refuses_layouts_outside_the_window(built, years):
    layouts = {year: replace(TEST_SUBAWARD_LAYOUTS[min(max(year, 2024), 2026)], year=year)
               for year in years}
    with exactly('subaward registry years differ from the window'):
        build_run(built, 'window', subaward_layouts=layouts)
    assert no_publication(built.data_dir, 'window')


def test_build_keeps_its_scratch_inside_its_staging(built, monkeypatch):
    staging = run_root(built.data_dir) / 'scratched.part'
    real = vendor_link_readers.read_subawards
    seen = []

    def observe(files, layouts, scratch):
        seen.append(scratch)
        return real(files, layouts, scratch)

    monkeypatch.setattr(vendor_link_readers, 'read_subawards', observe)
    result = build_run(built, 'scratched')
    assert seen == [staging / '.scratch']
    assert not (Path(result['directory']) / '.scratch').exists()


def test_build_reads_the_registries_and_the_skipped_lines(built, monkeypatch):
    real = vendor_link_pairs.report_counts
    seen = []

    def observe(*args, **kwargs):
        bound = dict(zip(('reported', 'firm_table', 'pair_table', 'extract', 'layouts',
                          'layout', 'node_ids', 'unreadable'), args)) | kwargs
        # The subaward rows are scanned from the build's scratch, so count them now.
        seen.append(bound | {'reported': bound['reported'].select(pl.len()).collect().item()})
        return real(*args, **kwargs)

    monkeypatch.setattr(vendor_link_pairs, 'report_counts', observe)
    build_run(built, 'counted')
    (bound,) = seen
    assert bound['layouts'] is TEST_SUBAWARD_LAYOUTS
    assert bound['layout'] is TEST_EXTRACT_LAYOUT
    assert bound['unreadable'].height == 1
    assert bound['reported'] == 14


# Each case rewrites one table right after it is first written, so that the build's own
# check of the serialized tables must refuse it. No validator reads the universe text.
SERIALIZED_CASES = {
    'universe': ('vendor_links.parquet', first_row('universe', 'another universe'),
                 'vendor_links: serialized table differs from the in-memory result'),
    'pairs': ('vendor_link_pairs.parquet', first_row('pair_status', 'unknown'),
              'pair table holds an unknown status'),
    'marginals': ('vendor_link_marginals.parquet', first_row('n_suppliers_partial', 9),
                  'vendor-link marginals differ from the pair table'),
}


@pytest.mark.parametrize('case', SERIALIZED_CASES)
def test_build_checks_the_serialized_tables(built, monkeypatch, case):
    name, change, message = SERIALIZED_CASES[case]
    real = pl.LazyFrame.sink_parquet
    rewritten = []

    def corrupt(self, path, *args, **kwargs):
        result = real(self, path, *args, **kwargs)
        # DataFrame.write_parquet sinks through this method too, so rewrite only once.
        if Path(path).name == name and not rewritten:
            rewritten.append(path)
            change(pl.read_parquet(path)).write_parquet(path)
        return result

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', corrupt)
    run_id = 'serialized_' + case
    with exactly(message):
        build_run(built, run_id)
    assert rewritten
    assert no_publication(built.data_dir, run_id)


def change_codes(data_dir, codes):
    file = data_dir / 'derived' / 'codes' / codes[0] / 'naics_edges.parquet'
    file.write_bytes(file.read_bytes() + b'changed')


def rewrite_manifest(data_dir, change):
    file = paths.manifest_path(data_dir)
    lines = []
    for line in file.read_text().splitlines():
        entry = change(json.loads(line))
        if entry is not None:
            lines.append(json.dumps(entry))
    file.write_text('\n'.join(lines) + '\n')


def change_citation(data_dir, codes):
    rewrite_manifest(data_dir, lambda entry: entry | {'retrieved_at': '2000-01-01T00:00:00+00:00'}
                     if entry['path'] == SUBAWARD_PATHS[0] else entry)


def change_raw_bytes(data_dir, codes):
    flip_byte(only_file(usaspending_raw.snapshot_dir(data_dir, SNAPSHOT, 2026)))


def drop_extract_entry(data_dir, codes):
    rewrite_manifest(data_dir, lambda entry: None if entry['path'] == EXTRACT_PATH else entry)


RECHECK_CASES = {
    'codes': (change_codes, '^selected codes inputs changed$'),
    'citation': (change_citation, 'cited raw provenance changed$'),
    'raw_bytes': (change_raw_bytes, 'the raw file has changed since it was downloaded$'),
    'unrecorded': (drop_extract_entry, '^a cited raw file is not recorded$'),
}


@pytest.mark.parametrize('case', RECHECK_CASES)
def test_build_rechecks_inputs_before_publication(built, tmp_path, monkeypatch, case):
    change, message = RECHECK_CASES[case]
    data_dir = fresh_root(built, tmp_path)
    real = target_io.write_json

    def changing(file, value):
        real(file, value)
        if file.name == 'report.json':
            change(data_dir, built.codes)

    monkeypatch.setattr(target_io, 'write_json', changing)
    with pytest.raises(ValueError, match=message):
        build_run(built, 'rechecked', data_dir=data_dir)
    assert no_publication(data_dir, 'rechecked')


def test_build_refuses_an_extra_staging_file(built, monkeypatch):
    real = target_io.write_json

    def stray(file, value):
        real(file, value)
        if file.name == 'report.json':
            (file.parent / 'stray.txt').write_text('stray')

    monkeypatch.setattr(target_io, 'write_json', stray)
    with exactly('staged bundle files differ from the bundle file set'):
        build_run(built, 'stray')
    assert no_publication(built.data_dir, 'stray')


def test_build_refuses_a_final_that_appears_before_publication(built, monkeypatch):
    real = vendor_link_bundle.freeze_software
    final = run_directory(built.data_dir, 'appeared')
    calls = []

    def appear():
        calls.append(True)
        if len(calls) == 2:
            final.mkdir()
        return real()

    monkeypatch.setattr(vendor_link_bundle, 'freeze_software', appear)
    with exactly('final run name already exists'):
        build_run(built, 'appeared')
    assert final.is_dir() and not any(final.iterdir())
    assert not (run_root(built.data_dir) / 'appeared.part').exists()
    final.rmdir()


def test_symlinked_staging_is_never_removed(built, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    staging = run_root(built.data_dir) / 'swapped.part'

    def swap(*args, **kwargs):
        staging.rename(decoy)
        (decoy / 'kept.txt').write_text('kept')
        staging.symlink_to(decoy, target_is_directory=True)
        raise ValueError('stop after the swap')

    monkeypatch.setattr(vendor_link_codes, 'select_nodes', swap)
    with pytest.raises(ValueError, match='symlink in registered destination'):
        build_run(built, 'swapped')
    assert (decoy / 'kept.txt').read_text() == 'kept'
    staging.unlink()


def test_symlinked_scratch_is_never_removed(built, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    real = target_contract.write_targets

    def swap(frame, destination):
        scratch = destination.parent / '.scratch'
        scratch.rename(decoy)
        scratch.symlink_to(decoy, target_is_directory=True)
        return real(frame, destination)

    monkeypatch.setattr(target_contract, 'write_targets', swap)
    with pytest.raises(ValueError, match='symlink in registered destination'):
        build_run(built, 'scratch_swapped')
    assert (decoy / 'subawards').is_dir()
    assert no_publication(built.data_dir, 'scratch_swapped')


# ---- verify

def test_verify_authenticates_the_pin_before_reading_anything(built, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('verify read inputs before the pin was authenticated')

    monkeypatch.setattr(vendor_link_codes, 'select_nodes', forbidden)
    monkeypatch.setattr(usaspending_raw, 'select_files', forbidden)
    monkeypatch.setattr(vendor_link_readers, 'read_subawards', forbidden)
    with exactly('detached inventory checksum differs'):
        verify(built, pin='0' * 64)


def test_verify_refuses_an_unpublished_name_and_a_malformed_pin(built, tmp_path):
    partial = copy_bundle(built, tmp_path, name=FIRST + '.part')
    with exactly('an interrupted bundle is not published'):
        verify(built, partial)
    for pin in (built.pin.upper(), built.pin[:-1], built.pin + '0', None, 7):
        with exactly('invalid detached checksum'):
            verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=pin,
                          **TEST_REGISTRIES)


def add_directory(directory):
    (directory / 'extra').mkdir()
    return manifest.sha256_file(directory / 'outputs.json')


def add_file(directory):
    (directory / 'extra.json').write_text('{}\n')
    return manifest.sha256_file(directory / 'outputs.json')


def remove_inputs(directory):
    (directory / 'inputs.json').unlink()
    return manifest.sha256_file(directory / 'outputs.json')


def change_unpinned(directory):
    file = directory / 'report.json'
    file.write_text(file.read_text().replace('"pending"', '"changed"'))
    return manifest.sha256_file(directory / 'outputs.json')


def drop_inventory_schema(directory):
    outputs = read(directory, 'outputs.json')
    for name in TABLES:
        for key in ('rows', 'columns', 'schema'):
            del outputs[name + '.parquet'][key]
    target_io.write_json(directory / 'outputs.json', outputs)
    return manifest.sha256_file(directory / 'outputs.json')


LAYOUT_CASES = {
    'extra_directory': (add_directory, 'bundle file set differs'),
    'extra_file': (add_file, 'bundle file set differs'),
    'missing_file': (remove_inputs, 'bundle file set differs'),
    'unpinned_change': (change_unpinned, 'report.json: inventory hash or size differs'),
    'inventory_without_schema': (drop_inventory_schema, 'output inventory records differ'),
}


@pytest.mark.parametrize('case', LAYOUT_CASES)
def test_verify_refuses_the_bundle_layout_before_any_recomputation(built, tmp_path,
                                                                   monkeypatch, case):
    def forbidden(*args, **kwargs):
        raise AssertionError('verify recomputed before the bundle layout was checked')

    change, message = LAYOUT_CASES[case]
    directory = copy_bundle(built, tmp_path)
    pin = change(directory)
    monkeypatch.setattr(vendor_link_codes, 'select_nodes', forbidden)
    with exactly(message):
        verify(built, directory, pin)


def duplicate_key(text):
    return text.replace('{\n', '{\n  "size_gate": "pending",\n', 1)


def not_a_number(text):
    return text.replace('"size_gate": "pending"', '"size_gate": NaN', 1)


def extra_newline(text):
    return text + '\n'


JSON_CASES = {
    'report_duplicate_key': ('report.json', duplicate_key, 'duplicate JSON key'),
    'report_nan': ('report.json', not_a_number, 'non-finite JSON number'),
    'report_noncanonical': ('report.json', extra_newline, 'report.json: not canonical JSON'),
    'inputs_noncanonical': ('inputs.json', extra_newline, 'inputs.json: not canonical JSON'),
    'outputs_noncanonical': ('outputs.json', extra_newline, 'outputs.json: not canonical JSON'),
    'report_not_json': ('report.json', lambda text: 'not json\n', 'report.json: not valid JSON'),
    'report_not_object': ('report.json', lambda text: '[]\n', 'report.json: not a JSON object'),
}


@pytest.mark.parametrize('case', JSON_CASES)
def test_verify_reads_json_strictly(built, tmp_path, case):
    name, change, message = JSON_CASES[case]
    directory = copy_bundle(built, tmp_path)
    file = directory / name
    file.write_text(change(file.read_text()))
    if name != 'outputs.json':
        outputs = read(directory, 'outputs.json')
        outputs[name] = target_io.file_record(file)
        target_io.write_json(directory / 'outputs.json', outputs)
    with exactly(message):
        verify(built, directory, manifest.sha256_file(directory / 'outputs.json'))


def rename_copy(built, tmp_path):
    return copy_bundle(built, tmp_path, name='renamed'), built.pin


def edit_copy(name, change):
    def apply(built, tmp_path):
        directory = copy_bundle(built, tmp_path)
        return directory, edit_json(directory, name, change)
    return apply


RECORDED_CASES = {
    'renamed': (rename_copy, 'recorded run ID differs from the directory'),
    'input_contracts': (edit_copy('inputs.json', set_path('contracts', 'pairs', 'other')),
                        'contract versions differ'),
    'report_contracts': (edit_copy('report.json', set_path('contracts', 'targets', 'other')),
                         'contract versions differ'),
    'missing_field': (edit_copy('inputs.json', delete_path('rules')),
                      'recorded inputs are malformed'),
    'extra_field': (edit_copy('inputs.json', set_path('extra', 1)),
                    'recorded inputs are malformed'),
    'snapshot_text': (edit_copy('inputs.json', set_path('snapshot', 'not a date')),
                      'recorded inputs are malformed'),
    'month_text': (edit_copy('inputs.json', set_path('sam_month', '2026-13')),
                   'recorded inputs are malformed'),
    'codes_run_type': (edit_copy('inputs.json', set_path('codes', 'run_id', 7)),
                       'recorded inputs are malformed'),
    'codes_missing': (edit_copy('inputs.json', delete_path('codes', 'outputs_sha256')),
                      'recorded inputs are malformed'),
    'report_universe': (edit_copy('report.json', set_path('universe', 'another universe')),
                        'recorded universe differs'),
    'snapshot_date': (edit_copy('inputs.json', set_path('snapshot', '2026-11-21')),
                      'recorded universe differs'),
    'month_value': (edit_copy('inputs.json', set_path('sam_month', '2026-09')),
                    'recorded universe differs'),
    'registries': (edit_copy('inputs.json', set_path('registries', 'extract_layout',
                                                     'field_count', 41)),
                   'recorded registries differ from the supplied ones'),
    'software': (edit_copy('inputs.json', set_path('software', 'python', 'other')),
                 'executing software differs from the build'),
    'codes_pin': (edit_copy('inputs.json', set_path('codes', 'outputs_sha256', '0' * 64)),
                  'detached inventory checksum differs'),
    'rules': (edit_copy('inputs.json', set_path('rules', 'pair', 'other')),
              'recorded inputs differ from the recomputation'),
    'raw': (edit_copy('inputs.json', set_path('raw', 'extract', 'client', 'other')),
            'recorded inputs differ from the recomputation'),
    'window': (edit_copy('inputs.json', set_path('window', [2024, 2025])),
               'recorded inputs differ from the recomputation'),
    'codes_outputs': (edit_copy('inputs.json', set_path('codes', 'outputs', {})),
                      'recorded inputs differ from the recomputation'),
    'report': (edit_copy('report.json', set_path('size_gate', 'passed')),
               'published report differs from the recomputation'),
    'report_count': (edit_copy('report.json', set_path('pairs', 'eligible', 99)),
                     'published report differs from the recomputation'),
    'report_limits': (edit_copy('report.json', set_path('limits', LIMITS[:-1])),
                      'published report differs from the recomputation'),
}


@pytest.mark.parametrize('case', RECORDED_CASES)
def test_verify_refuses_recorded_differences(built, tmp_path, case):
    prepare, message = RECORDED_CASES[case]
    directory, pin = prepare(built, tmp_path)
    with exactly(message):
        verify(built, directory, pin)


def test_verify_keeps_the_recorded_execution(built, tmp_path):
    directory = copy_bundle(built, tmp_path)

    def change(inputs):
        inputs['execution'] = {'commit': '0' * 40, 'dirty': True,
                               'created_at': '2000-01-01T00:00:00+00:00'}

    pin = edit_json(directory, 'inputs.json', change)
    assert verify(built, directory, pin)['outputs_sha256'] == pin


def test_verify_refuses_supplied_registries_that_differ(built):
    other_layout = replace(TEST_EXTRACT_LAYOUT, layout='Another fixture layout')
    with exactly('recorded registries differ from the supplied ones'):
        verify(built, extract_layout=other_layout)
    with exactly('recorded registries differ from the supplied ones'):
        verify(built, subaward_layouts=TEST_SUBAWARD_LAYOUTS | {2026: renamed(2026)})
    with exactly('recorded registries differ from the supplied ones'):
        verify(built, subaward_layouts=None, extract_layout=None)


TABLE_TAMPERS = {
    'vendor_links': first_row('value', 0.25),
    'vendor_link_marginals': first_row('n_suppliers_partial', 9),
    'vendor_link_support': first_row('n_reports', 99),
    'vendor_link_pairs': first_row('n_reports', 99),
}


@pytest.mark.parametrize('name', TABLES)
def test_verify_detects_each_table_tamper(built, tmp_path, name):
    directory = copy_bundle(built, tmp_path)
    pin = edit_table(directory, name, TABLE_TAMPERS[name])
    with exactly(name + ': published table differs from the recomputation'):
        verify(built, directory, pin)


def test_verify_recomputes_from_the_recorded_selection(built, monkeypatch):
    seen = {}
    for module, name in ((vendor_link_codes, 'select_nodes'), (usaspending_raw, 'select_files'),
                         (sam_raw, 'select_extract')):
        def observe(*args, real=getattr(module, name), name=name, **kwargs):
            seen[name] = (args[1:], kwargs)
            return real(*args, **kwargs)
        monkeypatch.setattr(module, name, observe)
    verify(built)
    run, pin = built.codes
    assert seen == {'select_nodes': ((run,), {'codes_outputs_sha256': pin}),
                    'select_files': ((SNAPSHOT,), {}),
                    'select_extract': ((MONTH,), {})}


def test_verify_recomputes_in_a_temporary_directory_outside_the_data_root(built, monkeypatch):
    before = tree(built.data_dir)
    real = vendor_link_readers.read_subawards
    seen = []

    def observe(files, layouts, scratch):
        seen.append((scratch, tree(built.data_dir)))
        return real(files, layouts, scratch)

    monkeypatch.setattr(vendor_link_readers, 'read_subawards', observe)
    verify(built)
    ((scratch, during),) = seen
    assert scratch.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert not scratch.resolve().is_relative_to(built.data_dir.resolve())
    assert not scratch.exists()
    assert during == before
    assert tree(built.data_dir) == before


def raw_changed(data_dir):
    flip_byte(only_file(usaspending_raw.snapshot_dir(data_dir, SNAPSHOT, 2024)))


def citation_changed(data_dir):
    rewrite_manifest(data_dir, lambda entry: entry | {'client': 'another client'}
                     if entry['path'] == EXTRACT_PATH else entry)


AFTER_BUILD_CASES = {
    'raw_bytes': (raw_changed, 'raw file changed'),
    'citation': (citation_changed, 'recorded inputs differ from the recomputation'),
}


@pytest.mark.parametrize('case', AFTER_BUILD_CASES)
def test_verify_refuses_raw_inputs_changed_after_the_build(built, tmp_path, case):
    change, message = AFTER_BUILD_CASES[case]
    data_dir = fresh_root(built, tmp_path)
    result = build_run(built, 'later', data_dir=data_dir)
    change(data_dir)
    with exactly(message):
        verify(built, Path(result['directory']), result['outputs_sha256'], data_dir=data_dir)


# ---- compare

def test_compare_runs_refuses_unpublished_or_uninventoried(built, tmp_path):
    partial = copy_bundle(built, tmp_path, name='copy.part')
    with exactly('compared bundles must be published'):
        compare_runs(built.directory, partial)
    with exactly('compared bundles must be published'):
        compare_runs(tmp_path / 'absent', built.directory)
    changed = copy_bundle(built, tmp_path, name='changed')
    change_unpinned(changed)
    with exactly('report.json: inventory hash or size differs'):
        compare_runs(changed, built.directory)
    uninventoried = copy_bundle(built, tmp_path, name='uninventoried')
    (uninventoried / 'outputs.json').unlink()
    with exactly('outputs.json: bundle JSON file is missing'):
        compare_runs(built.directory, uninventoried)


def test_compare_runs_reports_a_report_difference_and_skips_inputs(built, tmp_path):
    edited = copy_bundle(built, tmp_path / 'report')
    edit_json(edited, 'report.json', set_path('size_gate', 'passed'))
    result = compare_runs(built.directory, edited)
    assert (result['equal'], result['report_equal']) == (False, False)
    assert all(table['values_equal'] and table['schema_equal']
               for table in result['tables'].values())
    other_inputs = copy_bundle(built, tmp_path / 'inputs')
    edit_json(other_inputs, 'inputs.json', set_path('rules', 'pair', 'other'))
    assert compare_runs(built.directory, other_inputs)['equal'] is True


@pytest.mark.parametrize('name', TABLES)
def test_compare_runs_names_each_differing_table(built, tmp_path, name):
    tampered = copy_bundle(built, tmp_path)
    edit_table(tampered, name, TABLE_TAMPERS[name])
    result = compare_runs(built.directory, tampered)
    assert result['equal'] is False
    assert {table: result['tables'][table]['values_equal'] for table in TABLES} == {
        table: table != name for table in TABLES}


# ---- offline and upstream

def test_build_verify_and_compare_use_no_network_or_credentials(built, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline command attempted external access')

    forbid_external_access(monkeypatch)
    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    monkeypatch.setattr(sam_access, 'read_credential', forbidden)
    monkeypatch.setenv('SAM_API_KEY', 'FAKE-OFFLINE-KEY')
    result = build_run(built, 'offline')
    directory = Path(result['directory'])
    assert verify(built, directory, result['outputs_sha256'])['run_id'] == 'offline'
    assert compare_runs(built.directory, directory)['equal'] is True


def test_build_verify_and_compare_run_no_upstream_builder(built, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Stage 14 ran an upstream builder or an acquisition')

    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    monkeypatch.setattr(code_build, 'build', forbidden)
    for module in (usaspending_raw, sam_raw):
        monkeypatch.setattr(module, 'acquire', forbidden)
        monkeypatch.setattr(module, 'import_file', forbidden)
    result = build_run(built, 'no_upstream')
    directory = Path(result['directory'])
    assert verify(built, directory, result['outputs_sha256'])['run_id'] == 'no_upstream'
    assert compare_runs(built.directory, directory)['equal'] is True
