'''Tests for the SOC candidates, X residuals, PUMS cross-check and the unit registry.'''

import polars as pl
import pytest
from cps_flow_fixtures import tree_frames

from embedding_data import cps_flow_references, cps_flow_units
from embedding_data.cps_flow_lists import ListRow

UNIT_SCHEMA = {
    'unit': pl.String, 'unit_type': pl.String, 'code': pl.String, 'vintage': pl.String,
    'label': pl.String, 'status': pl.String, 'source_expression': pl.String,
    'membership_types': pl.List(pl.String), 'candidates': pl.List(pl.String),
    'candidate_node_ids': pl.List(pl.String), 'x_token': pl.String,
    'x_cross_check': pl.String, 'evidence_monthly': pl.String,
    'evidence_asec_current': pl.String, 'evidence_asec_last_year': pl.String,
    'bls_evidence': pl.String, 'list_locator': pl.String, 'pums_locator': pl.String,
    'reference_id': pl.String}
REFERENCES = {'industry': 'ref-ind', 'occupation': 'ref-occ', 'special': 'ref-special'}


@pytest.fixture
def tree():
    return tree_frames()


@pytest.fixture
def detailed(tree):
    return sorted(tree[1].filter(pl.col('level') == 'detailed')['code'])


def occupation_row(code: str, token: str, number: int = 1) -> ListRow:
    return ListRow(code, f'Title {code}', token,
                   f'census_occupation_2018:2018 Census Occ Code List!B:D:row={number}')


def industry_row(code: str, expression: str | None, number: int = 1) -> ListRow:
    return ListRow(code, f'Title {code}', expression,
                   f'census_industry_2022:2022 Census Ind Code List !B:E:row={number}')


def receipt() -> dict:
    return {'parser_version': cps_flow_references.PARSER_VERSION,
            'originals': {kind: {} for kind in cps_flow_references.REGISTRY}}


def sample_rows():
    industry = [
        industry_row('0170', '211120', 10),
        industry_row('1370', '311811, 311812', 11),
        industry_row('1380', '3118 exc. 311813', 12),
        industry_row('9920', None, 13)]
    occupation = [
        occupation_row('0010', '13-2051', 20),
        occupation_row('0020', '13-2050', 21),
        occupation_row('0030', '13-2000', 22),
        occupation_row('7000', '51-4040', 23),
        occupation_row('8225', '51-4XXX', 24),
        occupation_row('8025', '51-403X', 25),
        occupation_row('8865', '25-10XX', 26),
        occupation_row('9830', 'none', 27),
        occupation_row('9920', 'none', 28)]
    return industry, occupation


PUMS = {'8025': (['51-4031', '51-4032'], 'pums_occupation_2018:ACS!A:B:row=7'),
        '8225': (['51-4041', '51-4099'], 'pums_occupation_2018:ACS!A:B:row=9')}


def build(tree, industry=None, occupation=None, *, pums=None, delivered=None, evidence=None):
    naics_nodes, soc_nodes, paths = tree
    default_industry, default_occupation = sample_rows()
    return cps_flow_units.build_units(
        default_industry if industry is None else industry,
        default_occupation if occupation is None else occupation,
        naics_nodes=naics_nodes, soc_nodes=soc_nodes, paths=paths,
        pums=PUMS if pums is None else pums,
        delivered=delivered or {'industry': {'0170'},
                                'occupation': {'0010', '8025', '8225'}},
        evidence=evidence or cps_flow_references.special_evidence(receipt()),
        references=REFERENCES)


def test_soc_candidates_are_detailed_descendants_at_any_level(tree):
    _, soc_nodes, paths = tree
    assert cps_flow_units.soc_candidates('13-2051', soc_nodes, paths) == ['13-2051']
    assert cps_flow_units.soc_candidates('13-2050', soc_nodes, paths) == [
        '13-2051', '13-2052', '13-2054']
    assert cps_flow_units.soc_candidates('25-1000', soc_nodes, paths) == [
        '25-1011', '25-1021']
    assert cps_flow_units.soc_candidates('13-0000', soc_nodes, paths) == [
        '13-2051', '13-2052', '13-2054', '13-2099']


def test_soc_candidates_reject_an_unknown_code(tree):
    _, soc_nodes, paths = tree
    with pytest.raises(ValueError, match='unknown SOC code'):
        cps_flow_units.soc_candidates('99-9999', soc_nodes, paths)


def test_soc_candidates_reject_a_node_with_no_detailed_member(tree):
    _, soc_nodes, paths = tree
    trimmed = soc_nodes.filter(~pl.col('code').is_in(['13-2051', '13-2052', '13-2054']))
    with pytest.raises(ValueError, match='no detailed members'):
        cps_flow_units.soc_candidates('13-2050', trimmed, paths)


def test_x_matches_use_detailed_nodes_only(detailed):
    assert cps_flow_units.x_matches('51-403X', detailed) == ['51-4031', '51-4032']
    assert cps_flow_units.x_matches('51-4XXX', detailed) == [
        '51-4031', '51-4032', '51-4041', '51-4099']
    assert cps_flow_units.x_matches('51-4XXX', ['51-4099', '51-4031', '13-2051']) == [
        '51-4031', '51-4099']


def test_x_matches_never_match_a_shorter_or_other_major_group(detailed):
    assert cps_flow_units.x_matches('13-20XX', detailed) == [
        '13-2051', '13-2052', '13-2054', '13-2099']
    assert cps_flow_units.x_matches('51-405X', detailed) == []
    with pytest.raises(ValueError, match='unsupported X token'):
        cps_flow_units.x_matches('51-40X', detailed)
    with pytest.raises(ValueError, match='unsupported X token'):
        cps_flow_units.x_matches('51-4xxx', detailed)


def test_residuals_order_narrow_before_wide_and_subtract_claims(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('8225', '51-4XXX'), occupation_row('7000', '51-4040'),
            occupation_row('8025', '51-403X')]
    residuals = cps_flow_units.x_residuals(rows, soc_nodes, paths)
    assert residuals == {'8025': ['51-4031', '51-4032'], '8225': ['51-4099']}
    claim = set(cps_flow_units.soc_candidates('51-4040', soc_nodes, paths))
    assert not set(residuals['8025']) & set(residuals['8225'])
    assert not claim & (set(residuals['8025']) | set(residuals['8225']))


def test_residuals_do_not_depend_on_the_input_row_order(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('8025', '51-403X'), occupation_row('8225', '51-4XXX'),
            occupation_row('7000', '51-4040')]
    forward = cps_flow_units.x_residuals(rows, soc_nodes, paths)
    backward = cps_flow_units.x_residuals(rows[::-1], soc_nodes, paths)
    assert forward == backward == {'8025': ['51-4031', '51-4032'], '8225': ['51-4099']}


def test_a_detailed_non_x_claim_is_subtracted(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('8225', '51-4XXX'), occupation_row('7000', '51-4041')]
    assert cps_flow_units.x_residuals(rows, soc_nodes, paths) == {
        '8225': ['51-4031', '51-4032', '51-4099']}


def test_rows_with_no_soc_or_no_claim_leave_the_residual_alone(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('8225', '51-4XXX'), occupation_row('9830', 'none')]
    assert cps_flow_units.x_residuals(rows, soc_nodes, paths) == {
        '8225': ['51-4031', '51-4032', '51-4041', '51-4099']}


def test_x_residuals_of_a_list_with_no_x_row_are_empty(tree):
    _, soc_nodes, paths = tree
    assert cps_flow_units.x_residuals(
        [occupation_row('0010', '13-2051')], soc_nodes, paths) == {}


def test_broad_and_minor_tokens_claim_all_detailed_descendants(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('7001', '25-1000'), occupation_row('8865', '25-10XX')]
    residuals = cps_flow_units.x_residuals(rows, soc_nodes, paths)
    assert residuals == {'8865': []}
    with pytest.raises(ValueError, match='^x residual is empty$'):
        cps_flow_units.cross_check(residuals, {'8865': ['25-1011']}, {}, {'8865'})


def test_broad_claim_leaves_the_other_detailed_codes(tree):
    _, soc_nodes, paths = tree
    rows = [occupation_row('7001', '25-1010'), occupation_row('8865', '25-10XX')]
    assert cps_flow_units.x_residuals(rows, soc_nodes, paths) == {'8865': ['25-1021']}


def test_cross_check_outcomes():
    residuals = {'8025': ['51-4031', '51-4032'], '8225': ['51-4099'], '8865': ['25-1011']}
    pums = {'8025': ['51-4031', '51-4032'], '8225': ['51-4041', '51-4099']}
    claimed = {'8025': set(), '8225': {'51-4041', '51-4040'}, '8865': set()}
    assert cps_flow_units.cross_check(residuals, pums, claimed, {'8025', '8225'}) == {
        '8025': 'equal', '8225': 'strict_subset', '8865': 'not_delivered_no_pums_list'}


def test_cross_check_failures_have_fixed_reasons():
    def fail(residuals, pums, claimed, delivered, reason):
        with pytest.raises(ValueError) as caught:
            cps_flow_units.cross_check(residuals, pums, claimed, delivered)
        assert str(caught.value) == reason

    fail({'8225': []}, {'8225': ['51-4099']}, {}, {'8225'}, 'x residual is empty')
    fail({'8225': ['51-4099', '51-4031']}, {'8225': ['51-4099']}, {}, {'8225'},
         'x residual is not within the PUMS list')
    fail({'8225': ['51-4099']}, {'8225': ['51-4099', '51-4041']}, {'8225': set()},
         {'8225'}, 'x PUMS extra member is not claimed by another row')
    fail({'8225': ['51-4099']}, {'8225': ['51-4099', '51-4041', '51-4032']},
         {'8225': {'51-4041'}}, {'8225'}, 'x PUMS extra member is not claimed by another row')
    fail({'8225': ['51-4099']}, {}, {}, {'8225'}, 'x category has no PUMS list')


def test_cross_check_fails_an_undelivered_category_whose_list_disagrees():
    with pytest.raises(ValueError, match='x residual is not within the PUMS list'):
        cps_flow_units.cross_check(
            {'8225': ['51-4099']}, {'8225': ['51-4031']}, {'8225': set()}, set())
    with pytest.raises(ValueError, match='x residual is empty'):
        cps_flow_units.cross_check({'8225': []}, {}, {}, set())


def test_read_pums_lists_reads_only_soc_rows(tmp_path):
    lookup = tmp_path / 'acs_code_lookup.parquet'
    frame = pl.DataFrame({
        'system': ['naics', 'soc', 'soc'],
        'paired_census_code': ['0170', '8025', '8225'],
        'canonical_finest_candidates': [['111120'], ['51-4031', '51-4032'], ['51-4099']],
        'reference_locators': [['a:1'], ['pums:ACS!A:B:row=7', 'pums:ACS!A:B:row=8'],
                               ['pums:ACS!A:B:row=9']]})
    frame.write_parquet(lookup)
    assert cps_flow_units.read_pums_lists(lookup) == {
        '8025': (['51-4031', '51-4032'], 'pums:ACS!A:B:row=7|pums:ACS!A:B:row=8'),
        '8225': (['51-4099'], 'pums:ACS!A:B:row=9')}


def test_read_pums_lists_refuses_a_repeated_code(tmp_path):
    lookup = tmp_path / 'acs_code_lookup.parquet'
    pl.DataFrame({
        'system': ['soc', 'soc'], 'paired_census_code': ['8025', '8025'],
        'canonical_finest_candidates': [['51-4031'], ['51-4032']],
        'reference_locators': [['a'], ['b']]}).write_parquet(lookup)
    with pytest.raises(ValueError, match='repeats Census code'):
        cps_flow_units.read_pums_lists(lookup)


def test_a_naics_row_does_not_repeat_a_soc_code(tmp_path):
    lookup = tmp_path / 'acs_code_lookup.parquet'
    pl.DataFrame({
        'system': ['naics', 'soc'], 'paired_census_code': ['8025', '8025'],
        'canonical_finest_candidates': [['111120'], ['51-4031']],
        'reference_locators': [['a'], ['b']]}).write_parquet(lookup)
    assert cps_flow_units.read_pums_lists(lookup) == {'8025': (['51-4031'], 'b')}


def test_registry_statuses_and_specials(tree):
    units = build(tree)
    rows = {(r['unit_type'], r['code']): r for r in units.iter_rows(named=True)}
    for key in (('cps_occupation_category', '9830'), ('cps_occupation_category', '9920')):
        assert rows[key]['status'] == 'no_soc_equivalent'
        assert rows[key]['candidates'] == [] and rows[key]['candidate_node_ids'] == []
        assert rows[key]['membership_types'] == []
    gap = rows[('cps_industry_category', '9920')]
    assert gap['status'] == 'no_naics_equivalent'
    assert gap['candidates'] == [] and gap['source_expression'] is None
    industry = rows[('cps_industry_category', '9890')]
    assert (industry['status'], industry['label']) == ('special_military', 'Armed Forces')
    assert industry['candidates'] == [] and industry['candidate_node_ids'] == []
    assert industry['membership_types'] == [] and industry['source_expression'] is None
    assert (industry['evidence_monthly'], industry['evidence_asec_current'],
            industry['evidence_asec_last_year']) == (
        'settled', 'unresolved_owner_decision', 'unresolved_owner_decision')
    assert industry['bls_evidence'] == 'pt. 92811'
    assert industry['reference_id'] == 'ref-special'
    assert industry['vintage'] == 'census-industry-2022'
    military = rows[('cps_occupation_category', '9840')]
    assert (military['status'], military['label']) == ('special_military', 'Armed Forces')
    assert military['candidates'] == [] and military['candidate_node_ids'] == []
    assert (military['evidence_monthly'], military['evidence_asec_current'],
            military['evidence_asec_last_year']) == ('settled', 'settled', 'settled')
    assert military['bls_evidence'] == '55-0000'
    assert military['vintage'] == 'census-occupation-2018'
    assert military['reference_id'] == 'ref-special'
    assert military['x_token'] is None and military['x_cross_check'] is None
    assert military['pums_locator'] is None
    mapped = rows[('cps_occupation_category', '0010')]
    assert mapped['status'] == 'mapped'
    for column in ('evidence_monthly', 'evidence_asec_current', 'evidence_asec_last_year',
                   'bls_evidence'):
        assert mapped[column] is None and gap[column] is None
    assert units.height == 4 + 1 + 9 + 1


def test_specials_carry_a_list_locator_for_the_basic_code_lists(tree):
    rows = {(r['unit_type'], r['code']): r for r in build(tree).iter_rows(named=True)}
    assert rows[('cps_industry_category', '9890')]['list_locator'] == (
        'cps_basic_2026_industry_codes:9890')
    assert rows[('cps_occupation_category', '9840')]['list_locator'] == (
        'cps_basic_2026_occupation_codes:9840')


def test_registry_schema_order_and_unit_strings(tree):
    units = build(tree)
    assert units.schema == pl.Schema(UNIT_SCHEMA)
    assert units.columns == list(UNIT_SCHEMA)
    keys = list(zip(units['unit_type'], units['code']))
    assert keys == sorted(keys)
    assert keys[0] == ('cps_industry_category', '0170')
    assert keys[-1] == ('cps_occupation_category', '9920')
    for row in units.iter_rows(named=True):
        assert row['unit'] == f'feature:{row["unit_type"]}:{row["code"]}'
    assert units['unit'][0] == 'feature:cps_industry_category:0170'


def test_registry_industry_rows(tree):
    naics_nodes = tree[0]
    ids = dict(zip(naics_nodes['code'], naics_nodes['node_id']))
    rows = {r['code']: r for r in build(tree).filter(
        pl.col('unit_type') == 'cps_industry_category').iter_rows(named=True)}
    whole = rows['0170']
    assert whole['status'] == 'mapped' and whole['membership_types'] == ['whole']
    assert whole['candidates'] == ['211120'] and whole['candidate_node_ids'] == [ids['211120']]
    assert whole['source_expression'] == '211120' and whole['label'] == 'Title 0170'
    assert whole['vintage'] == 'census-industry-2022' and whole['reference_id'] == 'ref-ind'
    assert whole['list_locator'].endswith('row=10')
    assert whole['x_token'] is None and whole['pums_locator'] is None
    several = rows['1370']
    assert several['membership_types'] == ['several']
    assert several['candidates'] == ['311811', '311812']
    assert several['candidate_node_ids'] == [ids['311811'], ids['311812']]
    group = rows['1380']
    assert group['membership_types'] == ['group']
    assert group['candidates'] == ['311811', '311812', '311830']
    assert group['source_expression'] == '3118 exc. 311813'


def test_registry_occupation_membership_types_and_x_rows(tree):
    soc_nodes = tree[1]
    ids = dict(zip(soc_nodes['code'], soc_nodes['node_id']))
    rows = {r['code']: r for r in build(tree).filter(
        pl.col('unit_type') == 'cps_occupation_category').iter_rows(named=True)}
    detailed = rows['0010']
    assert detailed['membership_types'] == ['whole']
    assert detailed['candidates'] == ['13-2051']
    assert detailed['candidate_node_ids'] == [ids['13-2051']]
    assert detailed['vintage'] == 'census-occupation-2018'
    assert detailed['reference_id'] == 'ref-occ' and detailed['x_token'] is None
    broad = rows['0020']
    assert broad['membership_types'] == ['group']
    assert broad['candidates'] == ['13-2051', '13-2052', '13-2054']
    assert rows['0030']['membership_types'] == ['group']
    assert rows['7000']['candidates'] == ['51-4041']
    narrow = rows['8025']
    assert narrow['membership_types'] == ['x_residual'] and narrow['x_token'] == '51-403X'
    assert narrow['candidates'] == ['51-4031', '51-4032']
    assert narrow['candidate_node_ids'] == [ids['51-4031'], ids['51-4032']]
    assert narrow['x_cross_check'] == 'equal'
    assert narrow['pums_locator'] == 'pums_occupation_2018:ACS!A:B:row=7'
    assert narrow['source_expression'] == '51-403X'
    wide = rows['8225']
    assert wide['candidates'] == ['51-4099'] and wide['x_token'] == '51-4XXX'
    assert wide['x_cross_check'] == 'strict_subset'
    assert wide['pums_locator'] == 'pums_occupation_2018:ACS!A:B:row=9'
    absent = rows['8865']
    assert absent['candidates'] == ['25-1011', '25-1021']
    assert absent['x_cross_check'] == 'not_delivered_no_pums_list'
    assert absent['pums_locator'] is None
    assert rows['0010']['x_cross_check'] is None


def test_a_delivered_x_category_without_a_pums_list_fails(tree):
    delivered = {'industry': set(), 'occupation': {'8865'}}
    with pytest.raises(ValueError, match='^x category has no PUMS list$'):
        build(tree, delivered=delivered)


def test_a_failed_cross_check_stops_the_build(tree):
    pums = {**PUMS, '8225': (['51-4031'], 'pums:row=9')}
    with pytest.raises(ValueError, match='x residual is not within the PUMS list'):
        build(tree, pums=pums)
    pums = {**PUMS, '8225': (['51-4099', '25-1011'], 'pums:row=9')}
    with pytest.raises(ValueError, match='x PUMS extra member is not claimed'):
        build(tree, occupation=[row for row in sample_rows()[1] if row.code != '8865'],
              pums=pums)


def test_an_extra_member_claimed_by_a_narrower_x_row_passes(tree):
    pums = {**PUMS, '8225': (['51-4031', '51-4099'], 'pums:row=9')}
    units = build(tree, pums=pums)
    row = units.filter(pl.col('code') == '8225').row(0, named=True)
    assert row['x_cross_check'] == 'strict_subset'


def test_an_extra_member_claimed_by_an_x_row_with_the_wider_token_passes(tree):
    industry, occupation = sample_rows()
    pums = {**PUMS, '8025': (['51-4031', '51-4032', '51-4099'], 'pums:row=7')}
    units = build(tree, industry, occupation, pums=pums)
    row = units.filter(pl.col('code') == '8025').row(0, named=True)
    assert row['x_cross_check'] == 'strict_subset'


def test_a_delivered_code_with_no_equivalent_fails(tree):
    with pytest.raises(ValueError, match='^delivered code has no equivalent$'):
        build(tree, delivered={'industry': set(), 'occupation': {'9830'}})
    with pytest.raises(ValueError, match='^delivered code has no equivalent$'):
        build(tree, delivered={'industry': {'9920'}, 'occupation': set()})
    with pytest.raises(ValueError, match='^delivered code has no equivalent$'):
        build(tree, delivered={'industry': set(), 'occupation': {'9920'}})


def test_a_duplicate_code_or_a_list_special_fails(tree):
    industry, occupation = sample_rows()
    with pytest.raises(ValueError, match='repeats a code'):
        build(tree, industry=[*industry, industry_row('0170', '211120', 40)])
    with pytest.raises(ValueError, match='repeats a code'):
        build(tree, occupation=[*occupation, occupation_row('0010', '13-2051', 41)])
    with pytest.raises(ValueError, match='repeats a code'):
        build(tree, industry=[*industry, industry_row('9890', '211120', 40)])
    with pytest.raises(ValueError, match='repeats a code'):
        build(tree, occupation=[*occupation, occupation_row('9840', '13-2051', 41)])


def test_candidates_must_be_stage4_nodes(tree, monkeypatch):
    with pytest.raises(ValueError):
        build(tree, industry=[industry_row('0170', '999999')])
    with pytest.raises(ValueError):
        build(tree, occupation=[occupation_row('0010', '99-9999')], pums={})
    monkeypatch.setattr(cps_flow_units, 'naics_candidates', lambda *args: ['999999'])
    with pytest.raises(ValueError, match='candidate is not a Stage 4 node'):
        build(tree, industry=[industry_row('0170', '211120')])
    monkeypatch.setattr(cps_flow_units, 'soc_candidates', lambda *args: ['99-9999'])
    with pytest.raises(ValueError, match='candidate is not a Stage 4 node'):
        build(tree, occupation=[occupation_row('0010', '13-2051')], pums={})


def test_a_candidate_must_sit_at_the_finest_level(tree, monkeypatch):
    monkeypatch.setattr(cps_flow_units, 'naics_candidates', lambda *args: ['21112'])
    with pytest.raises(ValueError, match='candidate is not a Stage 4 node'):
        build(tree, industry=[industry_row('0170', '211120')])
    monkeypatch.setattr(cps_flow_units, 'soc_candidates', lambda *args: ['13-2050'])
    with pytest.raises(ValueError, match='candidate is not a Stage 4 node'):
        build(tree, occupation=[occupation_row('0010', '13-2051')], pums={})


def test_the_sample_registry_keeps_the_list_order_out_of_the_result(tree):
    industry, occupation = sample_rows()
    first = build(tree)
    second = build(tree, industry[::-1], occupation[::-1])
    assert first.equals(second)


def test_soc_candidates_reject_an_ambiguous_code(tree):
    _, soc_nodes, paths = tree
    doubled = pl.concat([soc_nodes, soc_nodes.filter(pl.col('code') == '13-2051')])
    with pytest.raises(ValueError, match='unknown SOC code'):
        cps_flow_units.soc_candidates('13-2051', doubled, paths)


def test_soc_candidates_are_sorted_whatever_the_node_order(tree):
    _, soc_nodes, paths = tree
    assert cps_flow_units.soc_candidates('13-0000', soc_nodes.reverse(), paths) == [
        '13-2051', '13-2052', '13-2054', '13-2099']


def test_x_matches_refuse_an_x_that_is_not_trailing(detailed):
    with pytest.raises(ValueError, match='unsupported X token'):
        cps_flow_units.x_matches('51-X031', detailed)
    with pytest.raises(ValueError, match='unsupported X token'):
        cps_flow_units.x_matches('51-4031', detailed)


def test_cross_check_equal_needs_no_claim_entry():
    assert cps_flow_units.cross_check(
        {'8025': ['51-4031']}, {'8025': ['51-4031']}, {}, {'8025'}) == {'8025': 'equal'}


def test_special_fields_come_from_the_evidence(tree):
    evidence = {
        '9890': {'label': 'L-ind', 'monthly': 'm-ind', 'asec_current': 'c-ind',
                 'asec_last_year': 'y-ind', 'bls': 'b-ind'},
        '9840': {'label': 'L-occ', 'monthly': 'm-occ', 'asec_current': 'c-occ',
                 'asec_last_year': 'y-occ', 'bls': 'b-occ'}}
    rows = {r['unit']: r for r in build(tree, evidence=evidence).iter_rows(named=True)}
    industry = rows['feature:cps_industry_category:9890']
    occupation = rows['feature:cps_occupation_category:9840']
    assert [industry[c] for c in ('label', 'evidence_monthly', 'evidence_asec_current',
                                  'evidence_asec_last_year', 'bls_evidence')] == [
        'L-ind', 'm-ind', 'c-ind', 'y-ind', 'b-ind']
    assert [occupation[c] for c in ('label', 'evidence_monthly', 'evidence_asec_current',
                                    'evidence_asec_last_year', 'bls_evidence')] == [
        'L-occ', 'm-occ', 'c-occ', 'y-occ', 'b-occ']
