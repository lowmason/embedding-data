'''Check the headline rows and the NAICS nodes of the ACS wage microdata rows.

Both checks run lazy aggregates over the person rows and collect only the distinct node tuples
or one count. Every refusal has a fixed message that holds no data value.
'''

from collections import Counter

import polars as pl

from embedding_data.acs_wage_rules import (
    FULL_TIME_HOURS,
    FULL_YEAR_WKSWORK2,
    HEADLINE_ALLOCATION,
)

SYSTEM = 'naics'
VINTAGE = 2022
# A national industry has four ancestors, from industry to sector. The bound ends a walk up
# the hierarchy even when forged edges form a cycle.
MAX_ANCESTORS = 4

NODE_COLUMNS = (
    'industry_canonical_common_node_id',
    'industry_native_node_id',
    'industry_node_code',
    'industry_node_level',
    'industry_delivered_node_code',
)


def check_headline(persons: pl.LazyFrame) -> None:
    '''Refuse a headline row that breaks a headline rule.

    A headline row has no allocated value in the nine headline fields, is full time and full
    year, has `flag_wage_salary` true and has no shared node. A null in one of those fields
    counts as a break, because the row cannot be shown to obey the rule.
    '''
    obeys = pl.all_horizontal(
        *(pl.col(name) == 0 for name in HEADLINE_ALLOCATION),
        pl.col('UHRSWORK') >= FULL_TIME_HOURS,
        pl.col('WKSWORK2') == FULL_YEAR_WKSWORK2,
        pl.col('flag_wage_salary'),
        ~pl.col('flag_industry_shared_node'),
    )
    broken = (
        persons.filter(pl.col('flag_headline'))
        .filter(~obeys.fill_null(False))
        .select(pl.len())
        .collect()
        .item()
    )
    if broken:
        raise ValueError('headline row breaks a headline rule')


def check_nodes(persons: pl.LazyFrame, nodes: pl.DataFrame, edges: pl.DataFrame) -> None:
    '''Refuse a join node or a delivered node that the Stage 4 NAICS 2022 tables do not support.

    `nodes` and `edges` are the Stage 4 `naics_nodes` and `naics_edges` frames. Each distinct
    node tuple must name two NAICS 2022 nodes that carry the row's code parts. The delivered
    node must be the join node or an ancestor of it, and each node on the chain from the
    delivered node down to the parent of the join node must have one child.
    '''
    tuples = persons.select(NODE_COLUMNS).unique(maintain_order=True).collect().to_dicts()
    known = {
        row['node_id']: (row['code'], row['level'])
        for row in nodes.filter(
            pl.col('system') == SYSTEM, pl.col('vintage') == VINTAGE
        ).iter_rows(named=True)
    }
    if not all(_names_nodes(row, known) for row in tuples):
        raise ValueError('industry node is not a Stage 4 NAICS 2022 node')
    hierarchy = edges.filter(pl.col('edge_type') == 'hierarchy')
    parents = dict(hierarchy.select('child_id', 'parent_id').iter_rows())
    children = Counter(hierarchy['parent_id'])
    for row in tuples:
        chain = _chain(
            parents, row['industry_canonical_common_node_id'], row['industry_native_node_id']
        )
        if chain is None:
            raise ValueError('delivered node is not an ancestor of the join node')
        if any(children[node] > 1 for node in chain):
            raise ValueError('delivered node chain branches')


def _names_nodes(row: dict, known: dict) -> bool:
    '''Return True when both node IDs name a known node that has the row's code parts.

    The join node must match the code and the level. The delivered node has no level part.
    '''
    join = known.get(row['industry_canonical_common_node_id'])
    delivered = known.get(row['industry_native_node_id'])
    return (
        join == (row['industry_node_code'], row['industry_node_level'])
        and delivered is not None
        and delivered[0] == row['industry_delivered_node_code']
    )


def _chain(parents: dict, join: str, delivered: str) -> list[str] | None:
    '''Return the nodes from the delivered node down to the parent of the join node.

    The chain is empty when the two nodes are the same node. It is None when the delivered node
    is not an ancestor of the join node.
    '''
    if delivered == join:
        return []
    chain, cursor = [], parents.get(join)
    for _ in range(MAX_ANCESTORS):
        if cursor is None:
            return None
        chain.append(cursor)
        if cursor == delivered:
            return chain
        cursor = parents.get(cursor)
    return None
