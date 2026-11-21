'''Headline and node checks over the ACS wage microdata rows.'''

import polars as pl
import pytest
from acs_wage_fixtures import COMMON_NODE, DELIVERED_NODE, Q_COLUMNS, core_frame, core_row

from embedding_data import acs_wage_checks as checks
from embedding_data import acs_wage_rules as rules
from embedding_data.classification_tables import EDGE_SCHEMA, NODE_SCHEMA

# The spec names the nine headline fields: every Q column but QDEGFIELD.
HEADLINE_Q = Q_COLUMNS[:-1]

NODE_MESSAGE = 'industry node is not a Stage 4 NAICS 2022 node'
ANCESTOR_MESSAGE = 'delivered node is not an ancestor of the join node'
BRANCH_MESSAGE = 'delivered node chain branches'


# --- headline rows ---------------------------------------------------------------------------


def headline_persons() -> pl.LazyFrame:
    '''Return three derived rows that are all headline, with source_row 0, 1 and 2.'''
    persons = rules.wage_persons(core_frame([core_row(), core_row(), core_row()]))
    assert persons.select(pl.col('flag_headline').all()).collect().item()
    return persons


def forge(persons: pl.LazyFrame, **changes) -> pl.LazyFrame:
    '''Set each column on the middle row (source_row 1) and force flag_headline on every row.'''
    schema = persons.collect_schema()
    middle = pl.col('source_row') == 1
    return persons.with_columns(
        pl.when(middle)
        .then(pl.lit(value, dtype=schema[name]))
        .otherwise(pl.col(name))
        .alias(name)
        for name, value in changes.items()
    ).with_columns(flag_headline=pl.lit(True))


def shared_pair() -> list[dict]:
    '''Return two categories that share the common node 5614, so neither row is headline.'''
    node = 'naics:2022:industry_group:5614'
    return [
        core_row(
            INDNAICS=category,
            industry_canonical_common_node_id=node,
            industry_native_node_id=f'naics:2022:industry:{category}',
        )
        for category in ('56141', '56142')
    ]


def test_headline_rows_obey_every_rule():
    broken = [
        core_row(QINCWAGE=4),
        core_row(UHRSWORK=34),
        core_row(WKSWORK2=5),
        *(core_row(CLASSWKRD=code) for code in (13, 14, 29)),
        *(core_row(**{name: 1}) for name in HEADLINE_Q),
        *shared_pair(),
    ]
    headline = [
        *(core_row(CLASSWKRD=code) for code in rules.WAGE_SALARY_CLASSWKRD),
        core_row(YEAR=2024, acs_sample_id='us2024a'),
        core_row(QDEGFIELD=3),
    ]
    persons = rules.wage_persons(core_frame([*broken, *headline]))
    flagged = persons.select(pl.col('flag_headline').sum()).collect().item()
    assert flagged == len(headline)
    assert persons.pipe(checks.check_headline) is None


@pytest.mark.parametrize('change', [{'QINCWAGE': 4}, {'UHRSWORK': 34}, {'WKSWORK2': 5},
    {'flag_wage_salary': False}, {'flag_industry_shared_node': True}])
def test_a_forged_headline_row_is_refused(change):
    persons = headline_persons()
    checks.check_headline(persons)
    with pytest.raises(ValueError, match='headline rule'):
        checks.check_headline(forge(persons, **change))


@pytest.mark.parametrize('name', HEADLINE_Q)
def test_every_headline_q_column_is_checked(name):
    with pytest.raises(ValueError, match='headline rule'):
        checks.check_headline(forge(headline_persons(), **{name: 1}))


@pytest.mark.parametrize('weeks', [0, 1, 5, 7])
def test_a_headline_row_in_another_week_band_is_refused(weeks):
    with pytest.raises(ValueError, match='headline rule'):
        checks.check_headline(forge(headline_persons(), WKSWORK2=weeks))


@pytest.mark.parametrize('name', [*HEADLINE_Q, 'UHRSWORK', 'WKSWORK2', 'flag_wage_salary',
    'flag_industry_shared_node'])
def test_a_null_in_a_headline_field_is_refused(name):
    with pytest.raises(ValueError, match='headline rule'):
        checks.check_headline(forge(headline_persons(), **{name: None}))


@pytest.mark.parametrize('change', [{'UHRSWORK': 35}, {'UHRSWORK': 99}, {'QDEGFIELD': 3}])
def test_a_headline_row_at_the_limits_passes(change):
    checks.check_headline(forge(headline_persons(), **change))


# --- NAICS nodes -----------------------------------------------------------------------------

LEVELS = {
    2: 'sector',
    3: 'subsector',
    4: 'industry_group',
    5: 'industry',
    6: 'national_industry',
}
# Child code to parent code: 62 > 623 > 6231 > 62311 > 623110 has one child at each level, and
# 561 > 5614 > {56141, 56142} branches at 5614.
PARENTS = {
    '623': '62',
    '6231': '623',
    '62311': '6231',
    '623110': '62311',
    '5614': '561',
    '56141': '5614',
    '56142': '5614',
    '311': '31-33',
}
NODE_COLUMNS = (
    'industry_canonical_common_node_id',
    'industry_native_node_id',
    'industry_node_code',
    'industry_node_level',
    'industry_delivered_node_code',
)


def level_of(code: str) -> str:
    return 'sector' if '-' in code else LEVELS[len(code)]


def node_id(code: str) -> str:
    return f'naics:2022:{level_of(code)}:{code}'


def graph(parents: dict = PARENTS, noise: tuple = ()) -> tuple[pl.DataFrame, pl.DataFrame]:
    '''Return Stage 4 `naics_nodes` and `naics_edges` frames for the child-to-parent map.

    `noise` holds extra edge rows, such as an edge of another type.
    '''
    codes = sorted({*parents, *parents.values()})
    nodes = pl.DataFrame(
        [(node_id(code), 'naics', 2022, level_of(code), code, f'Title {code}')
         for code in codes],
        schema=NODE_SCHEMA,
        orient='row',
    )
    edges = pl.DataFrame(
        [(node_id(child), node_id(parent), 'hierarchy') for child, parent in parents.items()]
        + list(noise),
        schema=EDGE_SCHEMA,
        orient='row',
    )
    return nodes, edges


def altered(nodes: pl.DataFrame, code: str, **values) -> pl.DataFrame:
    '''Return the nodes with the given columns replaced on the row of the node with `code`.'''
    target = pl.col('node_id') == node_id(code)
    return nodes.with_columns(
        pl.when(target).then(pl.lit(value, dtype=nodes.schema[name])).otherwise(pl.col(name))
        .alias(name)
        for name, value in values.items()
    )


def node_row(join: str, delivered: str | None = None, **overrides) -> dict:
    '''Return the five node columns of a row. The level is the join node's level.'''
    delivered = delivered or join
    return {
        'industry_canonical_common_node_id': node_id(join),
        'industry_native_node_id': node_id(delivered),
        'industry_node_code': join,
        'industry_node_level': level_of(join),
        'industry_delivered_node_code': delivered,
    } | overrides


def persons(*rows: dict) -> pl.LazyFrame:
    return pl.LazyFrame(list(rows), schema=dict.fromkeys(NODE_COLUMNS, pl.String))


def run(*rows: dict, parents: dict = PARENTS, noise: tuple = (), tables=None) -> None:
    nodes, edges = tables or graph(parents, noise)
    checks.check_nodes(persons(*rows), nodes, edges)


def test_join_equal_to_delivered_passes():
    run(node_row('5614'))


def test_single_child_chain_passes():
    run(node_row('623110', '6231'))


@pytest.mark.parametrize('delivered', ['62', '623', '6231', '62311', '623110'])
def test_every_ancestor_on_a_single_child_chain_passes(delivered):
    run(node_row('623110', delivered))


def test_branching_chain_is_refused():
    with pytest.raises(ValueError, match=BRANCH_MESSAGE):
        run(node_row('56141', '561'))


@pytest.mark.parametrize('sibling', [('624', '62'), ('6232', '623'), ('62312', '6231'),
    ('623111', '62311')])
def test_a_branch_anywhere_on_the_chain_is_refused(sibling):
    child, parent = sibling
    with pytest.raises(ValueError, match=BRANCH_MESSAGE):
        run(node_row('623110', '62'), parents=PARENTS | {child: parent})


def test_children_of_the_join_node_do_not_count():
    run(node_row('5614', '561'))


def test_a_branch_above_the_delivered_node_does_not_count():
    run(node_row('623110', '623'), parents=PARENTS | {'624': '62'})


def test_edges_of_another_type_are_ignored():
    noise = (
        (node_id('623111'), node_id('62311'), 'crosswalk'),
        (node_id('623110'), node_id('561'), 'crosswalk'),
    )
    run(node_row('623110', '6231'), noise=noise)


def test_delivered_below_join_is_refused():
    with pytest.raises(ValueError, match=ANCESTOR_MESSAGE):
        run(node_row('6231', '62311'))


@pytest.mark.parametrize(('delivered', 'join'), [('56142', '56141'), ('561', '623110'),
    ('62', '56141'), ('623', '62')])
def test_a_delivered_node_off_the_join_path_is_refused(delivered, join):
    with pytest.raises(ValueError, match=ANCESTOR_MESSAGE):
        run(node_row(join, delivered))


def test_unknown_node_is_refused():
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('999999'))


def test_an_unknown_delivered_node_is_refused():
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('623110', '9999'))


def test_an_unknown_join_node_is_refused_beside_a_known_delivered_node():
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('999999', '62'))


@pytest.mark.parametrize('column', ['vintage', 'system'])
@pytest.mark.parametrize('role', ['join', 'delivered'])
def test_a_node_of_another_vintage_or_system_is_refused(column, role):
    nodes, edges = graph()
    other = {'vintage': 2017, 'system': 'soc'}[column]
    nodes = altered(nodes, '623110' if role == 'join' else '6231', **{column: other})
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('623110', '6231'), tables=(nodes, edges))


def test_split_parts_must_match_the_node_row():
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('6231', industry_node_code='6232'))


@pytest.mark.parametrize(('column', 'value'), [
    ('industry_node_code', '623111'),
    ('industry_node_level', 'industry'),
    ('industry_delivered_node_code', '6232'),
])
def test_every_split_part_must_match_its_node_row(column, value):
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('623110', '6231', **{column: value}))


@pytest.mark.parametrize('column', NODE_COLUMNS)
def test_a_null_node_part_is_refused(column):
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(node_row('623110', '6231', **{column: None}))


@pytest.mark.parametrize('position', [0, 1, 2, 3])
def test_a_bad_tuple_among_good_ones_is_refused(position):
    rows = [node_row('5614'), node_row('623110', '6231'), node_row('62311', '62')]
    rows.insert(position, node_row('999999'))
    with pytest.raises(ValueError, match=NODE_MESSAGE):
        run(*rows)


def test_derived_persons_pass_the_node_check():
    sibling = {
        'INDNAICS': '5614',
        'industry_canonical_common_node_id': node_id('5614'),
        'industry_native_node_id': node_id('5614'),
    }
    derived = rules.wage_persons(core_frame([core_row(), core_row(**sibling)]))
    assert derived.select('industry_canonical_common_node_id').unique().collect().height == 2
    assert COMMON_NODE == node_id('623110')
    assert DELIVERED_NODE == node_id('6231')
    nodes, edges = graph()
    checks.check_nodes(derived, nodes, edges)


def test_a_hyphenated_sector_passes_as_join_and_as_delivered_node():
    hyphenated = {
        'INDNAICS': '31M',
        'industry_canonical_common_node_id': node_id('31-33'),
        'industry_native_node_id': node_id('31-33'),
    }
    below = {
        'INDNAICS': '311',
        'industry_canonical_common_node_id': node_id('311'),
        'industry_native_node_id': node_id('31-33'),
    }
    derived = rules.wage_persons(core_frame([core_row(**hyphenated), core_row(**below)]))
    levels = derived.select('industry_node_level').collect()['industry_node_level']
    assert levels.to_list() == ['sector', 'subsector']
    nodes, edges = graph()
    checks.check_nodes(derived, nodes, edges)
