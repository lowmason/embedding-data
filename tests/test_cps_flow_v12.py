'''The V12 fixture chain: raw CPS files to replay-equal Stage 11 job-flow bundles, offline.

Synthetic monthly and ASEC deliveries are recorded in a temporary manifest and converted by
the unchanged converter. Real Stage 4, Stage 7 and Stage 8 bundles are built from them, and
the Stage 11 references are imported from synthetic stand-ins. Then `build`, `verify`, a
second `build` and `compare_runs` run. Fixture results are software readiness, never
benchmarks.
'''

import json
import shutil
from pathlib import Path

import polars as pl
import pytest
from cps_flow_fixtures import V12_IDS, V12_RUNS, cps_flow_case, run_cps_flow_v12

from embedding_data import (
    acs_mapping_bundle,
    cps_flow_bundle,
    cps_flow_references,
    ipums_verification_run,
    manifest,
    paths,
)
from embedding_data.cps_flow_bundle import SOFTWARE_FILES, TABLES, run_directory, verify_bundle

CLASSIFICATION = Path(__file__).parent / 'fixtures/acs_mapping/classification'
IND, OCC = 'feature:cps_industry_category:', 'feature:cps_occupation_category:'
MONTHLY_SET, ASEC_SET = 'cps-basic-2025-01-to-2026-09', 'cps-asec-2025-2026'
NO_ACCESS = {'network': 0, 'environment_file': 0, 'live_client': 0}
EE_IND = ['monthly_ee:industry:sensitivity', 'monthly_ee:industry:strict']
EE_OCC = ['monthly_ee:occupation:sensitivity', 'monthly_ee:occupation:strict']
UE_ALL = ['monthly_ue:industry:sensitivity', 'monthly_ue:industry:strict',
          'monthly_ue:occupation:sensitivity', 'monthly_ue:occupation:strict']
# The first-exclusion funnels of the case, by hand from `cps_flow_case`.
UE_FUNNEL = {'weight_null': 0, 'weight_zero': 0, 'origin_new_worker_22': 0,
             'origin_not_unemployed_21': 5, 'destination_not_employed': 0,
             'code_not_in_universe': 0, 'eligible': 2}
ASEC_FUNNEL = {'weight_nonpositive': 0, 'not_employed': 0, 'last_year_code_not_in_universe': 1,
               'current_code_not_in_universe': 0, 'same_category': 1, 'eligible': 2}
FUNNELS = {
    'monthly_ee:industry': {'weight_null': 0, 'weight_zero': 0, 'not_employed_both': 2,
                            'code_not_in_universe': 0, 'guard_unusable': 1,
                            'no_change_reported': 0, 'coding_noise': 2, 'eligible': 2},
    'monthly_ee:occupation': {'weight_null': 0, 'weight_zero': 0, 'not_employed_both': 2,
                              'code_not_in_universe': 0, 'guard_unusable': 1,
                              'no_change_reported': 1, 'coding_noise': 0, 'eligible': 3},
    'monthly_ue:industry': UE_FUNNEL, 'monthly_ue:occupation': UE_FUNNEL,
    'asec_retro:industry': ASEC_FUNNEL, 'asec_retro:occupation': ASEC_FUNNEL,
}


def table(directory: Path, name: str) -> pl.DataFrame:
    return pl.read_parquet(directory / (name + '.parquet'))


def read(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text(encoding='utf-8'))


def directories(result: dict) -> tuple[Path, Path]:
    return Path(result['first']['directory']), Path(result['replay']['directory'])


def check_chain_is_genuine(result: dict) -> None:
    '''Raw triples in a temporary manifest, the unchanged converter, real upstream bundles.'''
    chain = result['chain']
    data_dir, request = chain.data_dir, chain.request
    manifest_file = paths.manifest_path(data_dir)
    assert manifest_file.is_relative_to(data_dir)
    conversions = result['conversions']
    assert [source for _, _, source in conversions] == ['acs', 'acs', 'acs', 'cps', 'cps']
    deliveries = read(chain.stage7, 'inputs.json')['deliveries']
    for set_name in ('monthly', 'asec'):
        record = deliveries[f'cps/{set_name}']
        name = record['delivery_id']
        raw = data_dir / 'raw/cps' / set_name / name
        triple = {raw / 'extract.json', raw / f'{name}.xml', raw / f'{name}.csv.gz'}
        assert set(raw.iterdir()) == triple
        for file in triple:
            assert manifest.entry_for(manifest_file, file).sha256 == manifest.sha256_file(file)
        assert (raw / f'{name}.csv.gz', data_dir / record['parquet'], 'cps') in conversions
    assert ipums_verification_run.verify_bundle(
        chain.stage7, data_dir, expected_outputs_sha256=request.stage7_outputs_sha256,
    )['status'] == 'verified'
    stage7_report = read(chain.stage7, 'report.json')
    assert stage7_report['status'] == 'unresolved'
    for profile in ('cps/monthly', 'cps/asec'):
        assert stage7_report['acceptance'][profile]['status'] == 'unresolved'
        assert stage7_report['acceptance'][profile]['definition_errors'] == []
    assert acs_mapping_bundle.verify_bundle(
        chain.mapping, data_dir, expected_outputs_sha256=request.stage8_mapping_outputs_sha256,
    )['status'] == 'verified'
    assert table(chain.codes, 'naics_nodes').height == 2125
    assert table(chain.codes, 'soc_nodes').height == 1447
    receipts = {
        'census_industry_2022.xlsx': data_dir / 'raw/references/ipums-verification'
        / request.stage7_receipt,
        'census_occupation_2018.xlsx': data_dir / 'raw/references/acs-mapping'
        / request.stage8_receipt}
    for name, directory in receipts.items():
        assert manifest.sha256_file(directory / name) == manifest.sha256_file(
            CLASSIFICATION / name)
    # Every row of the two full lists (266 industry codes, 570 occupation codes) and the two
    # specials is a unit.
    first, _ = directories(result)
    units = table(first, 'cps_category_units')
    assert dict(units.group_by('unit_type').len().iter_rows()) == {
        'cps_industry_category': 266 + 1, 'cps_occupation_category': 570 + 1}
    cps_flow_references.check_references(data_dir, request.cps_receipt)
    snapshot = data_dir / cps_flow_references.SNAPSHOT_ROOT / request.cps_receipt
    assert set(chain.originals) == set(cps_flow_references.REGISTRY)
    for kind, original in chain.originals.items():
        imported = snapshot / cps_flow_references.REGISTRY[kind].filename
        assert imported.read_bytes() == original.read_bytes()


def check_runs(result: dict) -> None:
    '''Both builds publish, verify against their detached pins and compare equal.'''
    data_dir = result['chain'].data_dir
    first, replay = directories(result)
    for key, directory in (('first', first), ('replay', replay)):
        response = result[key]
        assert directory == run_directory(data_dir, V12_RUNS[key])
        assert manifest.sha256_file(directory / 'outputs.json') == response['outputs_sha256']
        verified = result[key + '_verification']
        assert (verified['run_id'], verified['outputs_sha256']) == (
            V12_RUNS[key], response['outputs_sha256'])
        assert verified['rows'] == {name: table(directory, name).height for name in TABLES}
    assert result['first']['outputs_sha256'] != result['replay']['outputs_sha256']
    compared = result['compared']
    assert compared['equal'] is True
    assert compared['report_equal'] is True
    assert compared['trust_established'] is False
    assert list(compared['tables']) == list(TABLES)
    for name, comparison in compared['tables'].items():
        rows = table(first, name).height
        assert comparison == {'schema_equal': True, 'values_equal': True, 'first_rows': rows,
                              'second_rows': rows}


def check_no_external_access(result: dict) -> None:
    '''Zero attempts over the whole chain, and the counting guards are live at the end.'''
    counts = result['external_access_counts']
    assert counts == NO_ACCESS
    for category, probe in result['probes']:
        before = counts[category]
        with pytest.raises(AssertionError):
            probe()
        assert counts[category] == before + 1


def check_fixture_cases(result: dict) -> None:
    '''Each spec case of the fixture shows in the report and the aggregate tables.'''
    first, _ = directories(result)
    report = read(first, 'report.json')
    targets = table(first, 'cps_job_flows')
    diagnostics = table(first, 'cps_flow_diagnostics')
    pairs = {row['CPSIDV']: row for row in table(first, 'cps_linked_pairs').iter_rows(named=True)}
    people = cps_flow_case()['cpsidv']

    def pair(name: str) -> dict:
        return pairs[people[name]]

    def cells(universe: str, unit_a: str, unit_b: str) -> pl.DataFrame:
        return targets.filter((pl.col('universe') == universe) & (pl.col('unit_a') == unit_a)
                              & (pl.col('unit_b') == unit_b))

    def guard(reason: str) -> dict:
        rows = diagnostics.filter((pl.col('topic') == 'guard') & (pl.col('reason') == reason))
        return {row['dimension']: row['count'] for row in rows.iter_rows(named=True)}

    assert report['funnels'] == FUNNELS
    # P1: a guarded employer change, in both dimensions of monthly_ee.
    assert (pair('P1')['guard_industry'], pair('P1')['guard_occupation']) == (
        'changed', 'changed')
    assert pair('P1')['products'] == [*EE_IND, *EE_OCC]
    assert cells('monthly_ee:strict', IND + '0170', IND + '0180').height == 2
    assert cells('monthly_ee:strict', OCC + '0010', OCC + '0020').height == 2
    assert guard('changed') == {'industry': 2, 'occupation': 3}
    # P2: a duty change. Occupation is eligible, the industry difference is coding noise.
    assert (pair('P2')['guard_industry'], pair('P2')['guard_occupation']) == ('same', 'changed')
    assert pair('P2')['products'] == EE_OCC
    assert guard('noise_after_duty_change') == {'industry': 1}
    assert cells('monthly_ee:strict', OCC + '0010', OCC + '0040').height == 2
    # P3: a coding-noise pair. P4: an unusable guard.
    assert pair('P3')['products'] == pair('P4')['products'] == []
    assert (pair('P4')['guard_industry'], pair('P4')['guard_occupation']) == (
        'unusable', 'unusable')
    assert guard('unusable') == {'industry': 1, 'occupation': 1}
    assert cells('monthly_ee:sensitivity', IND + '0170', IND + '1190').is_empty()
    # P5: an unemployed-to-employed move.
    assert pair('P5')['products'] == UE_ALL
    assert cells('monthly_ue:strict', IND + '0170', IND + '0180').height == 2
    # P6: a 9890/9840 origin, in sensitivity only and flagged.
    assert pair('P6')['products'] == [UE_ALL[0], UE_ALL[2]]
    special = (pl.col('unit_a').is_in([IND + '9890', OCC + '9840'])
               | pl.col('unit_b').is_in([IND + '9890', OCC + '9840']))
    specials = targets.filter(special)
    assert set(specials.filter(pl.col('sample_set') == MONTHLY_SET)['unit_a']) == {
        IND + '9890', OCC + '9840'}
    assert set(specials['universe']) == {'monthly_ue:sensitivity', 'asec_retro:sensitivity'}
    assert all('special_military' in flags for flags in specials['flags'])
    assert not any('special_military' in flags for flags in targets.filter(~special)['flags'])
    assert report['specials'] == {'monthly/IND/2025': 1, 'monthly/OCC/2025': 1,
                                  'asec/INDLY/2025': 1, 'asec/OCCLY/2025': 1}
    # P7: the September-to-November 2025 link, counted in linkage.two_month and in no flow.
    # P9 matches on CPSIDV in the same month pair but fails the MISH rule.
    assert report['linkage'] == {
        'one_month': {'2025-01>2025-02': {'cpsidv': 7, 'cpsidp': 7, 'other_gap_matches': 0}},
        'two_month': {'2025-09>2025-11': {'cpsidv': 1, 'cpsidp': 1, 'other_gap_matches': 1}}}
    assert (pair('P7')['link_type'], pair('P7')['weight_status'], pair('P7')['products']) == (
        'two_month', 'not_linkable', [])
    assert targets.filter(pl.col('unit_a') == IND + '1190').is_empty()
    assert targets.filter(pl.col('unit_a') == OCC + '0040').is_empty()
    assert people['P9'] not in pairs
    # P8: an employer change with an allocated industry: industry in sensitivity only.
    assert pair('P8')['products'] == [EE_IND[0], *EE_OCC]
    assert cells('monthly_ee:sensitivity', IND + '0170', IND + '0180').height == 2
    assert report['weights'] == {'null': 0, 'zero': 0, 'positive': 7}
    # The ASEC difference carries unguarded_upper_bound, as every ASEC row does.
    asec = targets.filter(pl.col('sample_set') == ASEC_SET)
    assert cells('asec_retro:sensitivity', IND + '0170', IND + '0180').height == 2
    assert cells('asec_retro:sensitivity', OCC + '0010', OCC + '0020').height == 2
    assert set(asec['universe']) == {'asec_retro:sensitivity'}
    assert all('unguarded_upper_bound' in flags for flags in asec['flags'])
    assert not any('unguarded_upper_bound' in flags
                   for flags in targets.filter(pl.col('sample_set') == MONTHLY_SET)['flags'])


def check_privacy(result: dict) -> None:
    '''Only the linked pairs hold person identifiers; no JSON file holds a fixture one.'''
    case = cps_flow_case()
    identifiers = {str(row[name]) for row in (*case['monthly'], *case['asec'])
                   for name in ('CPSID', 'CPSIDV', 'CPSIDP')}
    for directory in directories(result):
        columns = {name: set(table(directory, name).columns) for name in TABLES}
        assert {name for name, found in columns.items() if 'CPSIDV' in found} == {
            'cps_linked_pairs'}
        assert not any({'CPSID', 'CPSIDP'} & found for name, found in columns.items()
                       if name != 'cps_linked_pairs')
        for name in ('report.json', 'inputs.json', 'outputs.json'):
            text = (directory / name).read_text(encoding='utf-8')
            assert not any(identifier in text for identifier in identifiers), name


def check_mutations(result: dict, tmp_path: Path) -> None:
    '''A wrong pin, and a changed software file, make `verify` raise.'''
    data_dir = result['chain'].data_dir
    first, _ = directories(result)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(first, data_dir, expected_outputs_sha256=result['replay']['outputs_sha256'])
    for changed in ('src/embedding_data/cps_flow_guards.py',
                    'src/embedding_data/ipums_conversion.py', 'uv.lock'):
        software = tmp_path / 'software' / Path(changed).name
        for name in SOFTWARE_FILES:
            (software / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(paths.PROJECT_ROOT / name, software / name)
        (software / changed).write_text((software / changed).read_text() + '\n# changed\n')
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(cps_flow_bundle, 'SOFTWARE_ROOT', software)
            with pytest.raises(ValueError, match='executing software differs from the build'):
                verify_bundle(first, data_dir,
                              expected_outputs_sha256=result['first']['outputs_sha256'])


@pytest.mark.slow
def test_raw_to_job_flows_is_offline_and_replayable(tmp_path, monkeypatch):
    result = run_cps_flow_v12(tmp_path / 'data', monkeypatch)
    assert result['chain'].request.cps_receipt == V12_IDS['cps_receipt']
    check_chain_is_genuine(result)
    check_runs(result)
    check_fixture_cases(result)
    check_privacy(result)
    check_mutations(result, tmp_path)
    check_no_external_access(result)
