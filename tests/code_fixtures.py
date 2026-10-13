import polars as pl

def titles(vintage: int, leaves=('111111', '111112')) -> pl.DataFrame:
    codes = ['11', '111', '1111', '11111', *leaves]
    return pl.DataFrame(
        {
            'vintage': [vintage] * len(codes),
            'code': codes,
            'title': [f'Fixture {code}' for code in codes],
        },
        schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    )


def soc_sheet() -> pl.DataFrame:
    return pl.DataFrame(
        [
            ['Major Group', 'Minor Group', 'Broad Group', 'Detailed Occupation', None],
            ['29-0000', None, None, None, 'Healthcare Practitioners'],
            [None, '29-1200', None, None, 'Health Diagnosing Practitioners'],
            [None, None, '29-1210', None, 'Physicians'],
            [None, None, None, '29-1221', 'Pediatricians'],
        ],
        orient='row',
        schema={f'c{i}': pl.String for i in range(5)},
    )


def pair_sheet(source, target, pairs):
    rows = [
        [
            f'{source} NAICS Code',
            f'{source} NAICS Title\n(piece in {target})',
            f'{target} NAICS Code',
            f'{target} NAICS Title',
        ]
    ]
    rows += [[a, 'Fixture source', b, 'Fixture target'] for a, b in pairs]
    return pl.DataFrame(rows, orient='row', schema={f'c{i}': pl.String for i in range(4)})


def toy_reference_tables():
    from embedding_data.classification_tables import naics_tables
    from embedding_data.naics_relationships import parse_concordance, validate_relationships

    native = []
    for v in (2002, 2007, 2012, 2017, 2022):
        leaves = ('111111', '111112', '111113') if v == 2022 else ('111111', '111112')
        nodes, edges, paths = naics_tables(titles(v, leaves), v)
        native.append(nodes)
        if v == 2022:
            canonical_paths = paths
    structures = pl.concat(native)
    frames = [
        parse_concordance(pair_sheet(a, b, pairs), a, b, f'fixture_{a}_{b}.xlsx')
        for a, b, pairs in [
            (2002, 2007, [('111111', '111111'), ('111112', '111112')]),
            (2007, 2012, [('111111', '111111'), ('111112', '111112')]),
            (2012, 2017, [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]),
            (2017, 2022, [('111111', '111111'), ('111112', '111112'), ('111112', '111113')]),
        ]
    ]
    relations = pl.concat(frames)
    validate_relationships(relations, structures)
    return structures, relations, canonical_paths
