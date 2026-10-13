import polars as pl
import pytest
from code_fixtures import soc_sheet, titles

from embedding_data import classification_tables as ct

def test_naics_exact_graph_and_path():
    nodes, edges, paths = ct.naics_tables(titles(2022), 2022)
    assert nodes.schema == ct.NODE_SCHEMA
    assert edges.schema == ct.EDGE_SCHEMA
    assert paths.schema == ct.PATH_SCHEMA
    assert paths.filter(pl.col('node_id').str.ends_with(':111111'))['path'][0].to_list() == [
        'naics:2022:sector:11',
        'naics:2022:subsector:111',
        'naics:2022:industry_group:1111',
        'naics:2022:industry:11111',
        'naics:2022:national_industry:111111',
    ]


def test_soc_uses_workbook_parent_not_code_prefix():
    nodes, edges, paths = ct.soc_tables(soc_sheet())
    assert nodes.height == 4
    assert edges.filter(pl.col('child_id').str.ends_with(':29-1221'))['parent_id'][0] == (
        'soc:2018:broad:29-1210'
    )


@pytest.mark.parametrize(
    'sector,subsector', [('31-33', '311'), ('44-45', '441'), ('48-49', '491')]
)
def test_ranges_are_one_sector(sector, subsector):
    frame = pl.DataFrame(
        {
            'vintage': [2022, 2022],
            'code': [sector, subsector],
            'title': ['Fixture sector', 'Fixture subsector'],
        }
    )
    nodes, edges, paths = ct.naics_tables(frame, 2022)
    assert nodes.filter(pl.col('level').eq('sector'))['code'].to_list() == [sector]
    assert edges['parent_id'].to_list() == [f'naics:2022:sector:{sector}']


def test_duplicate_and_orphan_refused():
    frame = titles(2022)
    with pytest.raises(ValueError, match='duplicate'):
        ct.naics_tables(pl.concat([frame, frame.tail(1)]), 2022)
    with pytest.raises(ValueError, match='parent'):
        ct.naics_tables(frame.filter(pl.col('code').ne('11111')), 2022)


@pytest.mark.parametrize('code', [None, '', '1', '1111111', '１１', '11A', '30-33'])
def test_invalid_naics_codes(code):
    frame = pl.DataFrame(
        {'vintage': [2022], 'code': [code], 'title': ['Title']},
        schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    )
    with pytest.raises(ValueError, match='invalid'):
        ct.naics_tables(frame, 2022)


@pytest.mark.parametrize('title', [None, '', '  '])
def test_missing_naics_title(title):
    frame = titles(2022).with_columns(pl.lit(title, dtype=pl.String).alias('title'))
    with pytest.raises(ValueError, match='null|title'):
        ct.naics_tables(frame, 2022)


@pytest.mark.parametrize(
    'row,match',
    [
        ([None, '29-1200', '29-1210', None, 'Title'], 'multiple'),
        ([None, None, '29-1210', None, 'Title'], 'parent'),
        ([None, '31-1200', None, None, 'Title'], 'major'),
        ([None, '29-1210', None, None, 'Title'], 'level'),
        ([None, 'invalid', None, None, 'Title'], 'invalid'),
        (['29-0000', None, None, None, 'Duplicate'], 'duplicate'),
        ([None, '29-1200', None, None, None], 'null'),
    ],
)
def test_invalid_soc_rows(row, match):
    raw = pl.concat(
        [soc_sheet().head(2), pl.DataFrame([row], schema=soc_sheet().schema, orient='row')]
    )
    with pytest.raises(ValueError, match=match):
        ct.soc_tables(raw)


@pytest.mark.parametrize(
    'defect,match',
    [
        ('duplicate', 'duplicate'),
        ('unknown', 'endpoint'),
        ('level', 'level'),
        ('cycle', 'root|cycle|level'),
        ('kind', 'edge'),
        ('missing', 'parent'),
    ],
)
def test_invalid_forest_edges(defect, match):
    nodes, edges, _ = ct.naics_tables(titles(2022), 2022)
    rows = edges.rows()
    if defect == 'duplicate':
        rows.append(rows[0])
    elif defect == 'unknown':
        rows[0] = (rows[0][0], 'unknown', 'hierarchy')
    elif defect == 'level':
        rows[0] = (rows[0][0], 'naics:2022:sector:11', 'hierarchy')
    elif defect == 'cycle':
        rows.append(('naics:2022:sector:11', 'naics:2022:national_industry:111111', 'hierarchy'))
    elif defect == 'kind':
        rows[0] = (*rows[0][:2], 'other')
    else:
        rows = rows[1:]
    with pytest.raises(ValueError, match=match):
        ct.forest(nodes, pl.DataFrame(rows, schema=ct.EDGE_SCHEMA, orient='row'))


def test_header_and_column_ambiguity():
    raw = pl.DataFrame(
        [['2022 Code', '2022 Other Code', 'Title'], ['11', '11', 'Fixture']], orient='row'
    )
    body = ct.below_header(raw, ('2022', 'title'))
    with pytest.raises(ValueError, match='ambiguous'):
        ct.column(body, '2022', 'code')
    with pytest.raises(ValueError, match='header'):
        ct.below_header(raw, ('missing',))
    duplicate = pl.DataFrame([['Code', 'Code', 'Title']], orient='row')
    with pytest.raises(ValueError, match='duplicate header'):
        ct.below_header(duplicate, ('code', 'title'))


def test_original_soc_workbook_layout():
    from pathlib import Path

    raw = pl.read_excel(
        Path(__file__).parent / 'fixtures/codes/soc_2018_tiny.xlsx',
        has_header=False,
        read_options={'dtypes': 'string'},
    )
    actual = ct.soc_tables(raw)
    expected = ct.soc_tables(soc_sheet())
    assert all(left.equals(right) for left, right in zip(actual, expected, strict=True))

def test_original_naics_workbook_layout():
    from pathlib import Path

    from embedding_data.ita_references import parse_titles

    raw = pl.read_excel(Path(__file__).parent / 'fixtures/codes/naics_2022_tiny.xlsx',
                        has_header=False, read_options={'dtypes': 'string'})
    actual = ct.naics_tables(parse_titles(raw, 2022), 2022)
    expected = ct.naics_tables(titles(2022), 2022)
    assert all(left.equals(right) for left, right in zip(actual, expected, strict=True))
