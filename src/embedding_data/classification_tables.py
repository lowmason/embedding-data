import re

import polars as pl

NODE_SCHEMA = {name: pl.String for name in ['node_id', 'system']}
NODE_SCHEMA.update(vintage=pl.Int64, level=pl.String, code=pl.String, title=pl.String)
EDGE_SCHEMA = {name: pl.String for name in ['child_id', 'parent_id', 'edge_type']}
PATH_SCHEMA = {'node_id': pl.String, 'path': pl.List(pl.String)}
NAICS_LEVELS = {
    2: 'sector',
    3: 'subsector',
    4: 'industry_group',
    5: 'industry',
    6: 'national_industry',
}
SOC_LEVELS = ('major', 'minor', 'broad', 'detailed')


def below_header(raw: pl.DataFrame, needles: tuple[str, ...]) -> pl.DataFrame:
    for i, row in enumerate(raw.rows()):
        cells = [str(x).strip() for x in row if x is not None and str(x).strip()]
        if len(cells) >= 2 and all(x.lower() in ' | '.join(cells).lower() for x in needles):
            names = [
                str(x).strip() if x is not None and str(x).strip() else f'c{j}'
                for j, x in enumerate(row)
            ]
            if len(set(names)) != len(names):
                raise ValueError('ambiguous duplicate header')
            body = raw.slice(i + 1)
            body.columns = names
            return body
    raise ValueError('required workbook header missing')


def column(body: pl.DataFrame, *needles: str) -> str:
    matches = [
        name
        for name in body.columns
        if all(token.lower() in name.split('\n', 1)[0].lower() for token in needles)
    ]
    if len(matches) != 1:
        raise ValueError(f'ambiguous or missing column: {needles}')
    return matches[0]


def forest(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    if nodes.schema != NODE_SCHEMA or edges.schema != EDGE_SCHEMA or nodes.is_empty():
        raise ValueError('incompatible or empty graph schema')
    if any(nodes[c].null_count() for c in nodes.columns):
        raise ValueError('null node field')
    if (
        nodes['node_id'].n_unique() != nodes.height
        or nodes.select('system', 'vintage', 'code').is_duplicated().any()
    ):
        raise ValueError('duplicate node')
    if nodes.filter(pl.col('title').str.strip_chars().eq('')).height:
        raise ValueError('missing title')
    records = {r['node_id']: r for r in nodes.iter_rows(named=True)}
    parents = {}
    for child, parent, kind in edges.iter_rows():
        if (
            child in parents
            or child not in records
            or parent not in records
            or kind != 'hierarchy'
        ):
            raise ValueError('duplicate child or missing parent/edge endpoint')
        parents[child] = parent
    for identifier, node in records.items():
        levels = tuple(NAICS_LEVELS.values()) if node['system'] == 'naics' else SOC_LEVELS
        if node['system'] not in ('naics', 'soc') or node['level'] not in levels:
            raise ValueError('unsupported classification level')
        depth = levels.index(node['level'])
        if (identifier in parents) != (depth > 0):
            raise ValueError('missing parent or parent on root')
        if depth:
            parent = records[parents[identifier]]
            if (parent['system'], parent['vintage'], parent['level']) != (
                node['system'],
                node['vintage'],
                levels[depth - 1],
            ):
                raise ValueError('contradictory immediate parent level')
        if identifier != f"{node['system']}:{node['vintage']}:{node['level']}:{node['code']}":
            raise ValueError('incompatible node_id')
    paths = []
    for identifier in sorted(records):
        chain, cursor = [], identifier
        while cursor is not None:
            if cursor in chain:
                raise ValueError('cycle in hierarchy')
            chain.append(cursor)
            cursor = parents.get(cursor)
        paths.append((identifier, list(reversed(chain))))
    return pl.DataFrame(paths, schema=PATH_SCHEMA, orient='row').sort('node_id')


def naics_tables(titles: pl.DataFrame, vintage: int):
    rows, edges = [], []
    selected = titles.filter(pl.col('vintage').eq(vintage))
    for code, title in selected.select('code', 'title').iter_rows():
        if code is None or not re.fullmatch(r'(?:[0-9]{2,6}|31-33|44-45|48-49)', code):
            raise ValueError('invalid NAICS structure code')
        width = 2 if '-' in code else len(code)
        level = NAICS_LEVELS[width]
        identifier = f'naics:{vintage}:{level}:{code}'
        rows.append((identifier, 'naics', vintage, level, code, title))
        if width > 2:
            prefix = code[:2]
            sector = next(
                (
                    r
                    for r in ('31-33', '44-45', '48-49')
                    if int(r[:2]) <= int(prefix) <= int(r[-2:])
                ),
                prefix,
            )
            parent_code = sector if width == 3 else code[:-1]
            parent_level = NAICS_LEVELS[width - 1]
            edges.append(
                (identifier, f'naics:{vintage}:{parent_level}:{parent_code}', 'hierarchy')
            )
    nodes = pl.DataFrame(rows, schema=NODE_SCHEMA, orient='row').sort('node_id')
    edge_frame = pl.DataFrame(edges, schema=EDGE_SCHEMA, orient='row').sort(
        'child_id', 'parent_id'
    )
    return nodes, edge_frame, forest(nodes, edge_frame)


def soc_tables(raw: pl.DataFrame):
    body = below_header(raw, ('major group', 'minor group', 'broad group', 'detailed occupation'))
    code_cols = [column(body, word) for word in ('major', 'minor', 'broad', 'detailed')]
    other = [c for c in body.columns if c not in code_cols]
    if len(other) != 1:
        raise ValueError('ambiguous SOC title column')
    rows, edges, current = [], [], {}
    for row in body.iter_rows(named=True):
        present = [
            (i, str(row[c]).strip())
            for i, c in enumerate(code_cols)
            if row[c] is not None and str(row[c]).strip()
        ]
        if not present:
            continue
        if len(present) != 1:
            raise ValueError('multiple SOC codes in one row')
        depth, code = present[0]
        if re.fullmatch(r'[0-9]{6}', code):
            code = code[:2] + '-' + code[2:]
        if not re.fullmatch(r'[0-9]{2}-[0-9]{4}', code):
            raise ValueError('invalid SOC code')
        pattern_depth = (
            0
            if code.endswith('0000')
            else 1
            if code.endswith('00')
            else (2 if code.endswith('0') else 3)
        )
        if pattern_depth != depth:
            raise ValueError('contradictory SOC column/level')
        level = SOC_LEVELS[depth]
        identifier = f'soc:2018:{level}:{code}'
        title = None if row[other[0]] is None else str(row[other[0]]).strip()
        rows.append((identifier, 'soc', 2018, level, code, title))
        if depth:
            if depth - 1 not in current:
                raise ValueError('missing SOC workbook parent')
            parent_id = current[depth - 1]
            if parent_id.rsplit(':', 1)[1][:2] != code[:2]:
                raise ValueError('contradictory SOC major group')
            edges.append((identifier, parent_id, 'hierarchy'))
        current[depth] = identifier
        for deeper in range(depth + 1, 4):
            current.pop(deeper, None)
    nodes = pl.DataFrame(rows, schema=NODE_SCHEMA, orient='row').sort('node_id')
    edge_frame = pl.DataFrame(edges, schema=EDGE_SCHEMA, orient='row').sort(
        'child_id', 'parent_id'
    )
    return nodes, edge_frame, forest(nodes, edge_frame)
