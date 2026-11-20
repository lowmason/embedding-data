'''The Stage 5 V12 fixture chain: synthetic raw TRI files to two verified, replay-equal bundles.

The chain starts from synthetic CSV files in the recorded header layout, with made-up D&B
numbers. It imports them into a temporary data root, builds a real Stage 4 bundle, then
builds, verifies, rebuilds and compares, all with external access blocked. A passing chain
shows software readiness. It is never a benchmark.
'''

import json
import socket
from datetime import date
from itertools import permutations
from pathlib import Path

import dotenv
import httpx
import polars as pl
import pytest
import tri_fixtures
from tri_fixtures import (
    V12_DATE,
    V12_DNB,
    V12_RUNS,
    production_layout,
    run_tri_v12,
    seed_tri_files,
    v12_rows,
    write_tri_csv,
)

from embedding_data import tri_bundle, tri_codes, tri_parent_links, tri_raw
from embedding_data.tri_bundle import FILES, TABLES, run_directory

NODE = 'naics:2022:national_industry:'
OTHER_DAY = date(2025, 12, 1)
RENAMED = '17. RENAMED PARENT CELL'
FAILURE_LINE = ('TRI parent links build failed: validation; run {run_id}; '
                'path derived/epa_tri/parent-links/{run_id}\n')
DNB_LABEL = 'numerator:dnb_key_sensitivity:true'
FEDERAL_LABEL = 'numerator:federal_sensitivity:true'


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    '''One run of the chain, shared by the tests that only read its bundles.

    The guards of the chain are released when it returns, so they do not outlive the fixture.
    '''
    with pytest.MonkeyPatch.context() as patch:
        return run_tri_v12(tmp_path_factory.mktemp('tri_v12'), patch)


def table(result: dict, name: str) -> pl.DataFrame:
    '''One table of the first bundle.'''
    return pl.read_parquet(result['first'] / (name + '.parquet'))


def recorded_codes(result: dict) -> dict:
    '''The codes run and detached pin that the first bundle records.'''
    return json.loads((result['first'] / 'inputs.json').read_text())['codes']


def codes_nodes(result: dict) -> frozenset[str]:
    '''The national-industry node IDs of the Stage 4 bundle that the first bundle cites.'''
    codes = recorded_codes(result)
    return tri_codes.select_nodes(result['data_dir'], codes['run_id'],
                                  codes_outputs_sha256=codes['outputs_sha256']).node_ids


def cross_year_non_pairs(years: pl.DataFrame) -> set[tuple[str, str]]:
    '''Ordered node pairs that one owner holds in different years and no owner holds in one.

    Only eligible facility-years count, because only they have an owner key and a node.
    '''
    by_owner: dict[str, dict[int, set[str]]] = {}
    for row in years.filter(pl.col('owner_key').is_not_null()).iter_rows(named=True):
        by_year = by_owner.setdefault(row['owner_key'], {})
        by_year.setdefault(row['reporting_year'], set()).add(row['naics_2022_node_id'])
    same_year, pooled = set(), set()
    for by_year in by_owner.values():
        for nodes in by_year.values():
            same_year |= set(permutations(nodes, 2))
        pooled |= set(permutations(set().union(*by_year.values()), 2))
    return pooled - same_year


def decoded_dnb_leaks(directory: Path) -> list[str]:
    '''The `file:column` names of Parquet string cells that hold a V12 D&B number.

    Compression can hide a string from a byte scan, so this reads each file with Polars. A
    column of a type other than string, list of string, number or boolean fails the check,
    because the scan would not cover it.
    '''
    numbers = list(V12_DNB)
    found = []
    for file in sorted(directory.glob('*.parquet')):
        frame = pl.read_parquet(file)
        for name, dtype in frame.schema.items():
            if dtype == pl.String:
                cell = pl.col(name).str.contains_any(numbers)
            elif dtype == pl.List(pl.String):
                cell = pl.col(name).list.eval(pl.element().str.contains_any(numbers)).list.any()
            elif dtype.is_numeric() or dtype == pl.Boolean:
                continue
            else:
                raise AssertionError(f'{file.name}:{name} has a type the scan does not cover')
            if frame.select(cell.any()).item():
                found.append(f'{file.name}:{name}')
    return found


def seed_changed_header(data_dir: Path, directory: Path, processed_as_of: date) -> None:
    '''Import a second snapshot whose 2023 file renames the standardized-parent header cell.'''
    rows = v12_rows()
    seed_tri_files(data_dir, directory, {2022: rows[2022], 2024: rows[2024]}, processed_as_of)
    changed = directory / 'changed' / tri_raw.file_name(2023)
    changed.parent.mkdir(parents=True)
    write_tri_csv(changed, 2023, rows[2023])
    cell = production_layout(2023).columns['standardized_parent'].encode()
    body = changed.read_bytes()
    assert cell in body
    changed.write_bytes(body.replace(cell, RENAMED.encode(), 1))
    tri_raw.import_file(data_dir, 2023, changed, processed_as_of=processed_as_of)


# Plan tests.

def test_v12_chain_is_offline_verified_and_replay_equal(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)
    assert result['comparison']['equal'] is True
    assert result['first_verification']['outputs_sha256'] == result['first_pin']
    assert result['second_verification']['outputs_sha256'] == result['second_pin']
    for name, run_id in zip(('first', 'second'), V12_RUNS, strict=True):
        assert result[name] == run_directory(result['data_dir'], run_id)
        assert result[name + '_verification']['run_id'] == run_id
        assert result[name + '_verification']['processed_as_of'] == V12_DATE.isoformat()
    comparison = result['comparison']
    assert comparison['report_equal'] is True
    assert comparison['trust_established'] is False
    assert set(comparison['tables']) == set(TABLES)
    for equal in comparison['tables'].values():
        assert equal['schema_equal'] is True
        assert equal['values_equal'] is True
        assert equal['first_rows'] == equal['second_rows'] > 0


def test_v12_compares_the_first_bundle_with_the_second(tmp_path, monkeypatch):
    # `compare_runs` returns no run identity, so only a spy shows which bundles it received.
    calls, returned = [], []
    real = tri_bundle.compare_runs

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        returned.append(real(*args, **kwargs))
        return returned[-1]

    monkeypatch.setattr(tri_bundle, 'compare_runs', spy)
    result = run_tri_v12(tmp_path, monkeypatch)
    assert calls == [((result['first'], result['second']), {})]
    assert result['first'] != result['second']
    assert len(returned) == 1
    assert returned[0] is result['comparison']


def test_v12_fixture_holds_every_required_case(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)
    years = pl.read_parquet(result['first'] / 'tri_facility_years.parquet')
    links = pl.read_parquet(result['first'] / 'tri_parent_links.parquet')
    support = pl.read_parquet(result['first'] / 'tri_parent_link_support.parquet')
    assert set(years['reporting_year']) == {2022, 2023, 2024}
    assert (years['n_forms'] >= 2).any()
    assert set(years['exclusion_reason'].drop_nulls()) == {
        'naics_conflict', 'naics_not_2022', 'parent_conflict', 'federal'}
    assert years['flag_parent_mixed_blank'].any()
    assert years.filter(pl.col('reporting_year') == 2023)[
        'foreign_parent_names'].list.len().max() > 0
    assert years['owner_key'].str.starts_with('facility:').any()
    assert support.filter(pl.col('j_dnb') != pl.col('j_owners')).height > 0
    assert links.filter(pl.col('n_unweighted') >= 1).height > 0
    non_pairs = cross_year_non_pairs(years)
    assert (NODE + '562211', NODE + '562910') in non_pairs
    for a, b in non_pairs:
        assert links.filter((pl.col('unit_a') == a) & (pl.col('unit_b') == b)).is_empty()
        assert support.filter((pl.col('unit_a') == a) & (pl.col('unit_b') == b)).is_empty()


def test_no_dnb_number_in_any_bundle_byte_or_failure_line(tmp_path, monkeypatch, cli_runner):
    result = run_tri_v12(tmp_path, monkeypatch)
    data_dir = result['data_dir']
    raw = b''.join(file.read_bytes() for file in tri_raw.select_files(data_dir, V12_DATE).values())
    assert all(number.encode() in raw for number in V12_DNB)
    for run in ('first', 'second'):
        files = sorted(result[run].iterdir())
        assert {file.name for file in files} == {*FILES, 'outputs.json'}
        for file in files:
            body = file.read_bytes()
            assert not any(number.encode() in body for number in V12_DNB), file.name
        assert decoded_dnb_leaks(result[run]) == []

    codes = recorded_codes(result)
    root = run_directory(data_dir, 'v12_header').parent
    before = sorted(path.name for path in root.iterdir())
    assert before == sorted(V12_RUNS)
    seed_changed_header(data_dir, tmp_path / 'other-originals', OTHER_DAY)
    with pytest.raises(ValueError, match='changed header') as error:
        tri_bundle.build(data_dir, 'v12_direct', codes_run=codes['run_id'],
                         codes_outputs_sha256=codes['outputs_sha256'],
                         processed_as_of=OTHER_DAY)
    assert not any(number in str(error.value) for number in V12_DNB)

    outcome = cli_runner.invoke(tri_parent_links.app, [
        'build', 'v12_header', '--data-dir', str(data_dir), '--codes-run', codes['run_id'],
        '--codes-outputs-sha256', codes['outputs_sha256'],
        '--processed-as-of', OTHER_DAY.isoformat()])
    assert outcome.exit_code == 2
    assert outcome.stdout == ''
    assert outcome.stderr == FAILURE_LINE.format(run_id='v12_header')
    assert not any(number in outcome.output for number in V12_DNB)
    assert str(data_dir) not in outcome.output
    assert sorted(path.name for path in root.iterdir()) == before


# One test for each required case, so that dropping a case from `v12_rows` fails by name.

def multi_form(result):
    years = table(result, 'tri_facility_years')
    forms = years.filter((pl.col('n_form_r') >= 1) & (pl.col('n_form_a') >= 1)
                         & ~pl.col('flag_parent_mixed_blank')
                         & pl.col('exclusion_reason').is_null())
    assert forms.height >= 1
    assert (forms['n_forms'] == forms['n_form_r'] + forms['n_form_a']).all()
    assert forms['owner_key'].str.starts_with('parent:').all()


def primary_code_conflict(result):
    years = table(result, 'tri_facility_years')
    conflict = years.filter(pl.col('exclusion_reason') == 'naics_conflict')
    assert conflict.height >= 1
    assert (conflict['primary_naics_values'].list.len() > 1).all()
    assert conflict['naics_2022_node_id'].is_null().all()
    assert conflict['owner_key'].is_null().all()


def parent_conflict(result):
    years = table(result, 'tri_facility_years')
    conflict = years.filter(pl.col('exclusion_reason') == 'parent_conflict')
    assert conflict.height >= 1
    assert (conflict['parent_names'].list.len() > 1).all()
    assert conflict['owner_key'].is_null().all()
    # The conflicted facility-year belongs to each named parent, so a parent that is also
    # eligible in that industry is a partial owner there.
    marginals = table(result, 'tri_parent_link_marginals')
    partial = marginals.filter(
        pl.col('node_id').is_in(conflict['naics_2022_node_id'].implode()))
    assert partial['n_owners_partial'].max() >= 1


def mixed_blank(result):
    years = table(result, 'tri_facility_years')
    mixed = years.filter(pl.col('flag_parent_mixed_blank'))
    assert mixed.height >= 1
    assert (mixed['n_forms'] >= 2).all()
    assert (mixed['parent_names'].list.len() == 1).all()
    assert mixed['exclusion_reason'].is_null().all()
    assert mixed['owner_key'].str.starts_with('parent:').all()


def self_owned(result):
    years = table(result, 'tri_facility_years')
    own = years.filter(pl.col('owner_key').str.starts_with('facility:'))
    assert own.height >= 1
    assert (own['parent_names'].list.len() == 0).all()
    assert own['exclusion_reason'].is_null().all()
    assert (own['owner_key'] == 'facility:' + own['trifd']).all()
    # It counts in `n(a)`, but a parent-only denominator leaves it out.
    marginals = table(result, 'tri_parent_link_marginals')
    own_nodes = marginals.filter(pl.col('node_id').is_in(own['naics_2022_node_id'].implode()))
    assert (own_nodes['n_owners'] > own_nodes['n_parent_owners']).any()


def federal(result):
    years = table(result, 'tri_facility_years')
    flagged = years.filter(pl.col('exclusion_reason') == 'federal')
    assert flagged.height >= 1
    assert flagged['owner_key'].is_null().all()
    marked = list(production_layout(2023).values['federal_yes'])
    assert flagged['federal_values'].explode().is_in(marked).all()
    # The federal sensitivity adds it back to a cell that the headline already has.
    support = table(result, 'tri_parent_link_support')
    cells = support.filter(pl.col('j_including_federal') != pl.col('j_owners'))
    assert cells.height >= 1
    links = table(result, 'tri_parent_links').join(cells, on=['unit_a', 'unit_b'])
    assert links['flags'].list.contains(FEDERAL_LABEL).all()


def code_outside_naics_2022(result):
    years = table(result, 'tri_facility_years')
    outside = years.filter(pl.col('exclusion_reason') == 'naics_not_2022')
    assert outside.height >= 1
    assert (outside['primary_naics_values'].list.len() == 1).all()
    codes = outside['primary_naics_values'].list.first()
    assert codes.str.contains('^[0-9]{6}$').all()
    nodes = codes_nodes(result)
    assert not any(NODE + code in nodes for code in codes)
    assert outside['naics_2022_node_id'].is_null().all()
    assert outside['owner_key'].is_null().all()


def dnb_grouping_differs(result):
    support = table(result, 'tri_parent_link_support')
    differs = support.filter(pl.col('j_dnb') != pl.col('j_owners'))
    assert differs.height >= 1
    links = table(result, 'tri_parent_links').join(differs, on=['unit_a', 'unit_b'])
    assert links.height == differs.height
    assert links['flags'].list.contains(DNB_LABEL).all()


def same_year_pair(result):
    links = table(result, 'tri_parent_links')
    support = table(result, 'tri_parent_link_support')
    for a, b in (('324110', '325211'), ('325211', '324110')):
        cell = {'unit_a': NODE + a, 'unit_b': NODE + b}
        link = links.filter(**cell)
        assert link['n_unweighted'].to_list() == [1]
        cell_support = support.filter(**cell).row(0, named=True)
        assert (cell_support['j_owners'], cell_support['j_2022'], cell_support['j_2023'],
                cell_support['j_2024']) == (1, 0, 1, 0)


def cross_year_non_pair(result):
    years = table(result, 'tri_facility_years')
    non_pairs = cross_year_non_pairs(years)
    mirrored = {(NODE + '562211', NODE + '562910'), (NODE + '562910', NODE + '562211')}
    assert mirrored <= non_pairs
    links = table(result, 'tri_parent_links')
    for a, b in mirrored:
        assert links.filter((pl.col('unit_a') == a) & (pl.col('unit_b') == b)).is_empty()
    # Each industry has an owner, so the owner count of the pooled years still shows it.
    marginals = table(result, 'tri_parent_link_marginals')
    for code in ('562211', '562910'):
        assert marginals.filter(node_id=NODE + code)['n_owners'].to_list() == [1]


def foreign_parent_2023(result):
    years = table(result, 'tri_facility_years')
    foreign = years.filter((pl.col('reporting_year') == 2023)
                           & (pl.col('foreign_parent_names').list.len() > 0))
    assert foreign.height >= 1
    assert foreign['exclusion_reason'].is_null().all()
    # The foreign parent is a diagnostic. The owner is the U.S. parent.
    assert (foreign['owner_key'] == 'parent:' + foreign['parent_names'].list.first()).all()


CASES = [multi_form, primary_code_conflict, parent_conflict, mixed_blank, self_owned, federal,
         code_outside_naics_2022, dnb_grouping_differs, same_year_pair, cross_year_non_pair,
         foreign_parent_2023]


@pytest.mark.parametrize('case', CASES, ids=lambda case: case.__name__)
def test_v12_fixture_holds_the_case(chain, case):
    case(chain)


# Properties of the fixture and of the chain.

def test_v12_dnb_lists_every_number_of_the_rows_and_each_has_nine_digits():
    cells = set()
    for year, rows in v12_rows().items():
        cells |= {row[production_layout(year).columns['parent_dnb']] for row in rows}
    numbers = cells - set(production_layout(2023).values['no_dnb']) - {''}
    assert numbers == set(V12_DNB)
    assert len(set(V12_DNB)) == len(V12_DNB)
    assert all(len(number) == 9 and number.isdigit() for number in V12_DNB)


def test_v12_rows_cover_the_window_with_nodes_of_the_codes_bundle(chain):
    assert set(v12_rows()) == {2022, 2023, 2024}
    assert all(rows for rows in v12_rows().values())
    nodes = codes_nodes(chain)
    for code in ('325199', '331110', '562211'):
        assert NODE + code in nodes
    years = table(chain, 'tri_facility_years')
    assert set(years['naics_2022_node_id'].drop_nulls()) <= nodes


def test_the_decoded_scan_finds_a_number_in_a_string_or_a_list_cell(tmp_path):
    number = V12_DNB[0]
    pl.DataFrame({'text': ['a', f'x {number} y'], 'count': [1, 2]}).write_parquet(
        tmp_path / 'string.parquet')
    pl.DataFrame({'flags': [['a'], ['b', number]]}).write_parquet(tmp_path / 'list.parquet')
    pl.DataFrame({'flags': [['a'], []], 'text': ['b', None]}).write_parquet(
        tmp_path / 'clean.parquet')
    assert decoded_dnb_leaks(tmp_path) == ['list.parquet:flags', 'string.parquet:text']
    pl.DataFrame({'nested': [[['a']]]}).write_parquet(tmp_path / 'nested.parquet')
    with pytest.raises(AssertionError, match='type the scan does not cover'):
        decoded_dnb_leaks(tmp_path)


def test_v12_chain_blocks_external_access_before_it_seeds_anything(tmp_path, monkeypatch):
    checked = []

    def spy(name):
        real = getattr(tri_fixtures, name)

        def checking(*args, **kwargs):
            with pytest.raises(AssertionError, match='external access'):
                socket.create_connection(('example.invalid', 80))
            with pytest.raises(AssertionError, match='external access'):
                dotenv.load_dotenv()
            with pytest.raises(AssertionError, match='external access'):
                httpx.Client()
            with pytest.raises(AssertionError, match='external access'):
                httpx.AsyncClient()
            checked.append(name)
            return real(*args, **kwargs)
        monkeypatch.setattr(tri_fixtures, name, checking)

    spy('seed_codes_bundle')
    spy('seed_tri_files')
    run_tri_v12(tmp_path, monkeypatch)
    assert checked == ['seed_codes_bundle', 'seed_tri_files']
