import polars as pl
import pytest
from code_fixtures import toy_reference_tables
from ita_establishment_fixtures import (
    canonical_frame,
    crosswalked,
    naics_reference,
    native,
    unresolved,
)
from polars.testing import assert_frame_equal

from embedding_data import ita_naics_mapping, ita_summary
from embedding_data.classification_tables import NODE_SCHEMA, PATH_SCHEMA, naics_tables
from embedding_data.ita_establishment_expected import V1_COLUMNS
from embedding_data.ita_establishment_records import (
    COPY_FLAGS,
    SOURCE_COLUMNS,
    index_counts,
    keyed_records,
    text_keys,
    v1_counts,
)
from embedding_data.ita_index_references import CROSS_REFERENCE, INDEX_SCHEMA
from embedding_data.ita_verification import description_report, with_keys
from embedding_data.target_inputs import CANONICAL_SCHEMA

TITLE_SCHEMA = {'vintage': pl.Int64, 'code': pl.String, 'title': pl.String}
TITLES = pl.DataFrame(
    {
        'vintage': [2022, 2012, 2017, 2022, 2022],
        'code': ['332312', '321113', '517311', '31-33', '111110'],
        'title': [
            'Fabricated Structural Metal Manufacturing',
            'Sawmills',
            'Wired Telecommunications Carriers',
            'Manufacturing',
            'Soybean Farming',
        ],
    },
    schema=TITLE_SCHEMA,
)
# One entry sits under two vintages, one text is a title and an index entry, and one
# cross-reference entry ends with a space, as the official files deliver it.
INDEX = pl.DataFrame(
    [
        (2012, '517110', 'Telephone carriers, wired'),
        (2017, '517311', 'Telephone carriers, wired'),
        (2012, '111110', 'Soybean farming'),
        (2017, '111110', 'Soybean farming'),
        (2022, '111120', 'Oilseed (except soybean) farming'),
        (2012, CROSS_REFERENCE, 'Wholesale -- see type of product '),
        (2017, CROSS_REFERENCE, 'Wholesale -- see type of product '),
    ],
    schema=INDEX_SCHEMA,
    orient='row',
)
MAPPINGS = {
    2022: native('332312'),
    2017: crosswalked('517311', 2017, ['517111']),
    2012: crosswalked('517110', 2012, ['517111']),
    None: unresolved('332312', None),
}


def record(description, year=2022, **overrides):
    return {**MAPPINGS[year], 'industry_description': description, **overrides}


@pytest.fixture(scope='module')
def keys():
    return text_keys(TITLES, INDEX)


def flags_of(keys, description, year=2022):
    frame = canonical_frame([record(description, year)])
    return keyed_records(frame, keys).collect().select(*COPY_FLAGS).row(0)


def test_constants_name_the_source_and_flag_columns():
    assert SOURCE_COLUMNS == tuple(ita_summary.COLUMNS)
    assert len(SOURCE_COLUMNS) == 24
    assert COPY_FLAGS == (
        'flag_copied_title_any',
        'flag_copied_title_native',
        'flag_copied_index_any',
        'flag_copied_index_native',
    )


# --- text_keys ---


def test_text_keys_are_normalized_unique_and_sorted():
    titles = pl.DataFrame(
        [
            (2022, '310000', 'Manufacturing'),
            (2017, '310001', 'Ｍanufacturing'),
            (2022, '310002', ' manufacturing  '),
            (2012, '310003', 'Sawmills'),
        ],
        schema=TITLE_SCHEMA,
        orient='row',
    )
    index = pl.DataFrame(
        [
            (2022, '111120', 'Zinc mining'),
            (2012, '111110', 'Soybean farming'),
            (2012, '111120', 'Soybean  FARMING'),
            (2012, CROSS_REFERENCE, 'Wholesale -- see type of product '),
            (2012, '111130', 'Manufacturing'),
            (2012, '111140', 'Alpha'),
            (2017, '111150', 'Alpha'),
        ],
        schema=INDEX_SCHEMA,
        orient='row',
    )
    result = text_keys(titles, index)
    assert result.schema == {'kind': pl.String, 'vintage': pl.Int64, 'key': pl.String}
    assert result.rows() == [
        ('index', 2012, 'alpha'),
        ('index', 2012, 'manufacturing'),
        ('index', 2012, 'soybean farming'),
        ('index', 2012, 'wholesale -- see type of product'),
        ('index', 2017, 'alpha'),
        ('index', 2022, 'zinc mining'),
        ('title', 2012, 'sawmills'),
        ('title', 2017, 'manufacturing'),
        ('title', 2022, 'manufacturing'),
    ]
    assert not result.is_duplicated().any()
    assert text_keys(titles.reverse(), index.reverse()).equals(result)


def test_text_keys_of_the_fixture_cover_every_title_and_entry(keys):
    kinds = keys.group_by('kind').agg(n=pl.len()).sort('kind').rows()
    assert kinds == [('index', 7), ('title', 5)]
    assert ('index', 2012, 'wholesale -- see type of product') in keys.rows()
    assert ('title', 2022, 'manufacturing') in keys.rows()
    assert ('title', 2022, 'soybean farming') in keys.rows()


def test_text_keys_with_no_index_rows_hold_titles_only():
    result = text_keys(TITLES, INDEX.clear())
    assert result.schema == {'kind': pl.String, 'vintage': pl.Int64, 'key': pl.String}
    assert set(result['kind']) == {'title'}
    assert result.height == TITLES.height


@pytest.mark.parametrize(
    'kind,vintage,value',
    [
        pytest.param('title', 2022, '', id='title-blank'),
        pytest.param('title', 2012, '   \t', id='title-only-whitespace'),
        pytest.param('title', 2017, None, id='title-null'),
        pytest.param('index', 2022, '   ', id='index-blank'),
        pytest.param('index', 2012, None, id='index-null'),
    ],
)
def test_text_keys_refuse_empty_key(kind, vintage, value):
    titles = TITLES
    index = INDEX
    if kind == 'title':
        titles = pl.concat(
            [titles, pl.DataFrame([(vintage, '999999', value)], schema=TITLE_SCHEMA, orient='row')]
        )
    else:
        index = pl.concat(
            [index, pl.DataFrame([(vintage, '111110', value)], schema=INDEX_SCHEMA, orient='row')]
        )
    with pytest.raises(ValueError, match='empty key'):
        text_keys(titles, index)


@pytest.mark.parametrize(
    'defect',
    [
        'titles-missing-title',
        'titles-vintage-string',
        'titles-null-vintage',
        'index-extra-column',
        'index-column-order',
        'index-entry-length',
        'index-null-vintage',
    ],
)
def test_text_keys_refuse_wrong_inputs(defect):
    titles, index = TITLES, INDEX
    if defect == 'titles-missing-title':
        titles = titles.drop('title')
    elif defect == 'titles-vintage-string':
        titles = titles.with_columns(pl.col('vintage').cast(pl.String))
    elif defect == 'titles-null-vintage':
        titles = titles.with_columns(vintage=pl.lit(None, dtype=pl.Int64))
    elif defect == 'index-extra-column':
        index = index.with_columns(extra=pl.lit(1))
    elif defect == 'index-column-order':
        index = index.select('entry', 'code', 'vintage')
    elif defect == 'index-entry-length':
        index = index.with_columns(entry=pl.col('entry').str.len_chars())
    else:
        index = index.with_columns(vintage=pl.lit(None, dtype=pl.Int64))
    with pytest.raises(ValueError, match='^(titles|index|text sources)'):
        text_keys(titles, index)


# --- keyed_records ---


def test_keys_match_stage3_semantics(keys):
    rows = [
        record('Steel', year_filing_for=2025, ein='12345678'),
        record('  ＳＴＥＥＬ   Mill', year_filing_for=2016, ein='', company_name=' Acme  Co '),
        record('N/A', ein='111111111', company_name=''),
        record('SteÃ¨l', ein='bad', zip_code='2134'),
        record('', zip_code='021341234', street_address=''),
        record(None, zip_code=None, ein=None, company_name=None),
        record('Manufacturing', year=None),
    ]
    frame = canonical_frame(rows)
    keyed = keyed_records(frame, keys).collect()
    expected = with_keys(frame.select(SOURCE_COLUMNS)).collect()
    added = expected.columns[len(SOURCE_COLUMNS):]
    assert len(added) == 15
    assert_frame_equal(keyed.select(added), expected.select(added))
    assert keyed.columns == ['source_row', *CANONICAL_SCHEMA, *added, *COPY_FLAGS]
    assert keyed.select(*CANONICAL_SCHEMA).equals(frame.collect())
    assert keyed.select(*COPY_FLAGS).schema == {name: pl.Boolean for name in COPY_FLAGS}


def test_source_row_is_the_zero_based_physical_position(keys):
    rows = [
        record('b', year_filing_for=2025, id=30),
        record('a', year_filing_for=2016, id=10),
        record('c', year_filing_for=2020, id=20),
        record('d', year_filing_for=2016, id=10),
    ]
    keyed = keyed_records(canonical_frame(rows), keys).collect()
    assert keyed.columns[0] == 'source_row'
    assert keyed.schema['source_row'] == pl.UInt64
    assert keyed['source_row'].to_list() == [0, 1, 2, 3]
    assert keyed['industry_description'].to_list() == ['b', 'a', 'c', 'd']


COPY_CASES = [
    pytest.param('Manufacturing', 2022, (True, True, False, False), id='own-vintage-title'),
    pytest.param('Sawmills', 2022, (True, False, False, False), id='other-vintage-title'),
    pytest.param('Manufacturing', None, (True, None, False, None), id='title-unknown-vintage'),
    pytest.param(
        'Telephone carriers, wired', 2017, (False, False, True, True), id='own-vintage-index'
    ),
    pytest.param(
        'Telephone carriers, wired', 2022, (False, False, True, False), id='other-vintage-index'
    ),
    pytest.param(
        'Telephone carriers, wired', None, (False, None, True, None), id='index-unknown-vintage'
    ),
    pytest.param(
        'wholesale -- see type of product', 2012, (False, False, True, True), id='cross-reference'
    ),
    pytest.param('Soybean Farming', 2022, (True, True, True, False), id='title-and-index'),
    pytest.param(
        'ＭＡＮＵＦＡＣＴＵＲＩＮＧ  ', 2022, (True, True, False, False), id='compatibility-form'
    ),
    pytest.param('', 2022, (False, False, False, False), id='empty-description'),
    pytest.param('   ', None, (False, None, False, None), id='blank-description-unknown-vintage'),
    pytest.param('N/A', 2022, (False, False, False, False), id='placeholder'),
    pytest.param('Plumbing contractors', 2022, (False, False, False, False), id='neither'),
]


@pytest.mark.parametrize('description,year,expected', COPY_CASES)
def test_copy_flags(keys, description, year, expected):
    assert flags_of(keys, description, year) == expected


def test_copy_flags_of_a_null_description(keys):
    frame = canonical_frame([record(None), record(None, None)])
    keyed = keyed_records(frame, keys).collect()
    assert keyed.select(*COPY_FLAGS).rows() == [
        (False, False, False, False),
        (False, None, False, None),
    ]


def test_index_whitespace_still_flags_copy():
    index = pl.DataFrame(
        [(2012, CROSS_REFERENCE, 'Wholesale -- see type of product ')],
        schema=INDEX_SCHEMA,
        orient='row',
    )
    keys = text_keys(TITLES, index)
    frame = canonical_frame([record('  wholesale -- SEE type of product', 2012)])
    keyed = keyed_records(frame, keys).collect()
    assert keyed['flag_copied_index_any'].to_list() == [True]
    assert keyed['flag_copied_index_native'].to_list() == [True]


def test_flags_with_titles_only_keys_leave_the_index_flags_false():
    keys = text_keys(TITLES, INDEX.clear())
    frame = canonical_frame([record('Manufacturing'), record('Manufacturing', None)])
    keyed = keyed_records(frame, keys).collect()
    assert keyed.select(*COPY_FLAGS).rows() == [
        (True, True, False, False),
        (True, None, False, None),
    ]


def test_flags_with_no_keys_are_false_or_unknown():
    keys = text_keys(TITLES.clear(), INDEX.clear())
    assert keys.is_empty()
    frame = canonical_frame([record('Manufacturing'), record('Manufacturing', None)])
    keyed = keyed_records(frame, keys).collect()
    assert keyed.select(*COPY_FLAGS).rows() == [
        (False, False, False, False),
        (False, None, False, None),
    ]


@pytest.mark.parametrize('defect', ['missing-column', 'column-order', 'column-type'])
def test_keyed_records_refuse_a_non_canonical_frame(keys, defect):
    frame = canonical_frame([record('Steel')])
    if defect == 'missing-column':
        frame = frame.drop('city')
    elif defect == 'column-order':
        frame = frame.select(*reversed(list(CANONICAL_SCHEMA)))
    else:
        frame = frame.with_columns(pl.col('id').cast(pl.String))
    with pytest.raises(ValueError, match='canonical schema'):
        keyed_records(frame, keys)


@pytest.mark.parametrize(
    'defect',
    ['extra-column', 'column-order', 'vintage-string', 'empty-key', 'null-key', 'unknown-kind'],
)
def test_keyed_records_refuse_defective_keys(keys, defect):
    frame = canonical_frame([record('Steel')])
    if defect == 'extra-column':
        bad = keys.with_columns(extra=pl.lit(1))
    elif defect == 'column-order':
        bad = keys.select('key', 'kind', 'vintage')
    elif defect == 'vintage-string':
        bad = keys.with_columns(pl.col('vintage').cast(pl.String))
    elif defect == 'empty-key':
        extra = pl.DataFrame([('title', 2022, '')], schema=keys.schema, orient='row')
        bad = pl.concat([keys, extra])
    elif defect == 'null-key':
        extra = pl.DataFrame([('index', 2022, None)], schema=keys.schema, orient='row')
        bad = pl.concat([keys, extra])
    else:
        bad = keys.with_columns(kind=pl.lit('titles'))
    with pytest.raises(ValueError, match='text keys'):
        keyed_records(frame, bad)


def test_keyed_records_of_no_rows(keys):
    keyed = keyed_records(canonical_frame([]), keys)
    schema = keyed.collect_schema()
    assert schema['source_row'] == pl.UInt64
    assert list(schema)[0] == 'source_row'
    assert list(schema)[-4:] == list(COPY_FLAGS)
    assert keyed.collect().is_empty()
    assert v1_counts(keyed).is_empty()
    assert index_counts(keyed).is_empty()


# --- v1_counts ---


def v1_rows():
    steel = {'ein': '123456789'}
    return [
        # 2024, written first: two unknown employers with one description, a company
        # fallback behind an EIN of one repeated digit, and a title of the 2022 vintage.
        record('Unknown thing', year_filing_for=2024, ein='', company_name=''),
        record('Unknown thing', year_filing_for=2024, ein='', company_name=''),
        record('X', year_filing_for=2024, ein='111111111', company_name='Delta'),
        record('Soybean farming', 2022, year_filing_for=2024, ein='123456789'),
        # 2025: no employer is known, so the year has no repeat groups at all.
        record('Z', year_filing_for=2025, ein='', company_name=''),
        record('Z', year_filing_for=2025, ein=None, company_name=None),
        # 2023: a repeat group of three through case, spacing and fullwidth forms.
        record('Steel Mill', **steel),
        record('steel  mill', **steel),
        record('ＳＴＥＥＬ MILL', **steel),
        # Titles: own vintage, another vintage, own vintage under 2012, unknown vintage.
        record('Manufacturing', ein='234567891'),
        record('Sawmills', ein='234567891'),
        record('Sawmills', 2012, ein='234567891'),
        record('Steel', None, ein='345678912'),
        record('Manufacturing', None, ein='345678912'),
        record(
            'Fabricated Structural Metal Manufacturing', ein='789123456', company_name='Plant Co'
        ),
        record('Fabricated Structural Metal Manufacturing', ein='789123456'),
        # Company fallback, a repeat through the normalized name, and an unknown employer.
        record('Widgets', ein='', company_name='Globex Inc'),
        record('widgets', ein='', company_name='globex  inc'),
        record('Widgets', ein='', company_name=''),
        # A padded EIN is a different employer from the unpadded one.
        record('Steel Mill', ein='12345678'),
        # Suspected mojibake, empty descriptions (never a repeat), placeholders (repeat).
        record('SteÃ¨l', ein='456789123'),
        record('Café Â', ein='456789124'),
        record('   ', ein='456789125'),
        record('', ein='456789125'),
        record('N/A', ein='678912345'),
        record('n/a', ein='678912345'),
        record('None', ein='678912345'),
    ]


# Counts by hand. 2023 holds 21 rows. A group repeats when an employer repeats a nonempty
# description: steel mill (3), sawmills (2, one per vintage), the long title (2), widgets by
# company (2) and n/a (2), so 11 rows and 6 excess rows. Empty descriptions and unknown
# employers never repeat.
V1_EXPECTED = {
    2023: {
        'n_rows': 21,
        'n_empty': 2,
        'n_placeholder': 3,
        'n_copied_any': 6,
        'n_native_title_match': 4,
        'n_vintage_unknown': 2,
        'n_employer_unknown': 1,
        'n_employer_company': 2,
        'n_ein_padded': 1,
        'n_mojibake': 2,
        'n_repeat_rows': 11,
        'n_repeat_excess': 6,
    },
    2024: {
        'n_rows': 4,
        'n_empty': 0,
        'n_placeholder': 0,
        'n_copied_any': 1,
        'n_native_title_match': 1,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 2,
        'n_employer_company': 1,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 0,
        'n_repeat_excess': 0,
    },
    2025: {
        'n_rows': 2,
        'n_empty': 0,
        'n_placeholder': 0,
        'n_copied_any': 0,
        'n_native_title_match': 0,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 2,
        'n_employer_company': 0,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 0,
        'n_repeat_excess': 0,
    },
}


def test_v1_counts_equal_stage3_description_report(keys):
    frame = canonical_frame(v1_rows())
    counts = v1_counts(keyed_records(frame, keys))
    report = description_report(frame.select(SOURCE_COLUMNS), TITLES)
    expected = report.select('year_filing_for', *V1_COLUMNS).cast(pl.Int64)
    assert counts.columns == ['year_filing_for', *V1_COLUMNS]
    assert set(counts.schema.values()) == {pl.Int64}
    assert_frame_equal(counts, expected)
    assert {row['year_filing_for']: {c: row[c] for c in V1_COLUMNS} for row in counts.to_dicts()
            } == V1_EXPECTED


def test_v1_counts_are_sorted_by_year_whatever_the_record_order(keys):
    frame = canonical_frame(v1_rows())
    counts = v1_counts(keyed_records(frame, keys))
    assert counts['year_filing_for'].to_list() == [2023, 2024, 2025]
    reversed_counts = v1_counts(keyed_records(canonical_frame(v1_rows()[::-1]), keys))
    assert_frame_equal(counts, reversed_counts)


# --- index_counts ---


def index_rows():
    return [
        # 2022: three title-only, two index-only, one both, one neither.
        record('Manufacturing', year_filing_for=2022),
        record('Manufacturing', year_filing_for=2022),
        record('manufacturing', year_filing_for=2022),
        record('Telephone carriers, wired', 2017, year_filing_for=2022),
        record('Telephone carriers, wired', 2022, year_filing_for=2022),
        record('Soybean Farming', year_filing_for=2022),
        record('Plumbing contractors', year_filing_for=2022),
        # 2023: two both (one with an unknown vintage), one cross-reference, no title-only.
        record('soybean farming', year_filing_for=2023),
        record('Soybean farming', None, year_filing_for=2023),
        record('Wholesale -- see type of product', 2012, year_filing_for=2023),
    ]


INDEX_EXPECTED = [
    (2022, 3, 1, 1, 3, 2),
    (2023, 3, 1, 2, 0, 1),
]
INDEX_COLUMNS = [
    'year_filing_for',
    'n_copied_index_any',
    'n_copied_index_native',
    'n_copied_title_and_index_any',
    'n_copied_title_only_any',
    'n_copied_index_only_any',
]


def test_index_counts_partition_overlap(keys):
    keyed = keyed_records(canonical_frame(index_rows()), keys)
    counts = index_counts(keyed)
    assert counts.columns == INDEX_COLUMNS
    assert set(counts.schema.values()) == {pl.Int64}
    assert counts.rows() == INDEX_EXPECTED
    # Title-only, index-only and both are disjoint. The title count of Stage 3 is title-only
    # plus both, and the index count is index-only plus both.
    for year, index_any, _, both, title_only, index_only in counts.rows():
        assert index_any == both + index_only
        stage3 = v1_counts(keyed).filter(pl.col('year_filing_for').eq(year)).row(0, named=True)
        assert stage3['n_copied_any'] == both + title_only


def test_index_counts_are_sorted_by_year(keys):
    counts = index_counts(keyed_records(canonical_frame(index_rows()[::-1]), keys))
    assert counts['year_filing_for'].to_list() == [2022, 2023]
    assert counts.rows() == INDEX_EXPECTED


@pytest.mark.parametrize('function', [v1_counts, index_counts])
def test_counts_refuse_records_that_are_not_keyed(function):
    frame = canonical_frame([record('Steel')])
    with pytest.raises(ValueError, match='keyed records'):
        function(frame)


V1_INPUTS = [
    'year_filing_for',
    'naics_year',
    'description_key',
    'employer_key',
    'flag_empty',
    'flag_placeholder',
    'flag_ein_padded',
    'flag_suspected_mojibake',
    'flag_copied_title_any',
    'flag_copied_title_native',
]


@pytest.mark.parametrize(
    'function,column',
    [pytest.param(v1_counts, name, id=f'v1-{name}') for name in V1_INPUTS]
    + [
        pytest.param(index_counts, name, id=f'index-{name}')
        for name in ['year_filing_for', *COPY_FLAGS]
    ],
)
def test_counts_name_the_missing_keyed_column(keys, function, column):
    keyed = keyed_records(canonical_frame([record('Steel')]), keys)
    with pytest.raises(ValueError, match='keyed records'):
        function(keyed.drop(column))


# --- frame builders ---


def test_canonical_frame_defaults_are_canonical_and_usable():
    frame = canonical_frame([{}, {}, {'year_filing_for': 2019}])
    assert list(frame.collect_schema().items()) == list(CANONICAL_SCHEMA.items())
    rows = frame.collect().to_dicts()
    assert [row['year_filing_for'] for row in rows] == [2023, 2023, 2019]
    assert [row['id'] for row in rows] == [1, 2, 3]
    assert len({row['establishment_id'] for row in rows}) == 3
    keyed = with_keys(frame.select(SOURCE_COLUMNS)).collect()
    assert keyed['ein_key'].to_list() == ['123456789'] * 3
    assert keyed['address_key'].null_count() == 0
    assert keyed['employer_key'].to_list() == ['ein:123456789'] * 3
    assert all(row['naics_code'] == '332312' for row in rows)
    for row in rows:
        mapping = {name: row[name] for name in ita_naics_mapping.MAPPING_SCHEMA}
        assert mapping == {k: v for k, v in native('332312').items() if k in mapping}
        assert not [name for name, value in row.items() if name.startswith('flag_') and value]


def test_canonical_frame_applies_overrides_and_refuses_unknown_columns():
    frame = canonical_frame([{'ein': '', 'id': 77, **crosswalked('517110', 2012, ['517111'])}])
    row = frame.collect().row(0, named=True)
    assert (row['ein'], row['id'], row['naics_year']) == ('', 77, 2012)
    assert row['flag_naics_crosswalked'] is True
    with pytest.raises(ValueError, match='unknown canonical columns'):
        canonical_frame([{'not_a_column': 1}])
    with pytest.raises(ValueError, match='older or unknown vintage'):
        crosswalked('332312', 2022, ['332312'])
    with pytest.raises(ValueError, match='older or unknown vintage'):
        crosswalked('517110', 2012, [])


def test_naics_reference_holds_every_code_and_ancestor():
    nodes, code_paths = naics_reference(['332312', '238220', '488999', '441110'])
    assert nodes.schema == NODE_SCHEMA and code_paths.schema == PATH_SCHEMA
    assert set(nodes['level']) == {
        'sector',
        'subsector',
        'industry_group',
        'industry',
        'national_industry',
    }
    assert set(nodes.filter(pl.col('level').eq('sector'))['code']) == {
        '31-33',
        '23',
        '48-49',
        '44-45',
    }
    assert nodes['vintage'].unique().to_list() == [2022]
    paths = dict(code_paths.iter_rows())
    assert paths['naics:2022:national_industry:332312'] == [
        'naics:2022:sector:31-33',
        'naics:2022:subsector:332',
        'naics:2022:industry_group:3323',
        'naics:2022:industry:33231',
        'naics:2022:national_industry:332312',
    ]
    assert paths['naics:2022:sector:44-45'] == ['naics:2022:sector:44-45']
    rebuilt = naics_tables(nodes.select('vintage', 'code', 'title'), 2022)
    assert rebuilt[0].equals(nodes) and rebuilt[2].equals(code_paths)


MAPPING_CASES = [
    pytest.param(native('111113'), ('111113', 2022), True, id='native'),
    pytest.param(
        crosswalked('111112', 2012, ['111112', '111113']),
        ('111112', 2012),
        False,
        id='ambiguous-concorded',
    ),
    pytest.param(crosswalked('111111', 2017, ['111111']), ('111111', 2017), False, id='singleton'),
    pytest.param(
        crosswalked('111112', None, ['111112', '111113']),
        ('111112', None),
        False,
        id='unknown-vintage-candidates',
    ),
    pytest.param(unresolved('999999', None), ('999999', None), True, id='unmapped'),
    pytest.param(unresolved(None, None), (None, None), True, id='missing-code'),
    pytest.param(unresolved(None, 2012), (None, 2012), True, id='missing-code-known-vintage'),
    pytest.param(unresolved('111113', 2012), ('111113', 2012), False, id='invalid-native-code'),
]


@pytest.fixture(scope='module')
def lookup():
    keys = pl.DataFrame(
        [case.values[1] for case in MAPPING_CASES],
        schema=ita_naics_mapping.KEY_SCHEMA,
        orient='row',
    ).unique()
    result = ita_naics_mapping.build_lookup(keys, *toy_reference_tables())
    return {(row['naics_code'], row['naics_year']): row for row in result.to_dicts()}


@pytest.mark.parametrize('built,key,same_vintages', MAPPING_CASES)
def test_mapping_builders_agree_with_build_lookup(lookup, built, key, same_vintages):
    expected = dict(lookup[key])
    if not same_vintages:
        # The toy structures list these codes under other vintages too. The builders
        # assume each code belongs to the vintage that names it.
        expected['naics_matching_vintages'] = built['naics_matching_vintages']
    assert built == expected
