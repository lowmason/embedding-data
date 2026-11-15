import hashlib
import subprocess
import sys
from dataclasses import replace

import polars as pl
import pytest
from ita_establishment_fixtures import (
    canonical_frame,
    crosswalked,
    naics_reference,
    native,
    unresolved,
)
from polars.testing import assert_frame_equal

from embedding_data import classification_tables, ita_text_pairs
from embedding_data.classification_tables import NODE_SCHEMA
from embedding_data.ita_establishment_records import COPY_FLAGS, keyed_records, text_keys
from embedding_data.ita_index_references import INDEX_SCHEMA
from embedding_data.ita_naics_mapping import MAPPING_SCHEMA
from embedding_data.ita_text_pairs import (
    MEMBER_SCHEMA,
    PAIR_CODE_SCHEMA,
    PAIR_SCHEMA,
    PAIRS_VERSION,
    PATH_SCHEMA,
    TextPairs,
    build_pairs,
    pair_id,
    require_single_mapping_state,
    validate_pairs,
)

TITLES = pl.DataFrame(
    [
        (2022, '332312', 'Fabricated Structural Metal Manufacturing'),
        (2017, '517311', 'Wired Telecommunications Carriers'),
    ],
    schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    orient='row',
)
INDEX = pl.DataFrame([(2022, '332312', 'Steel mill')], schema=INDEX_SCHEMA, orient='row')
KEYS = text_keys(TITLES, INDEX)
NODES, CODE_PATHS = naics_reference(['332312', '238210', '238220', '517111', '517112'])

STEEL = native('332312')
CONCORDED = crosswalked('517311', 2017, ['517111'])
AMBIGUOUS = crosswalked('517110', 2012, ['517111', '517112'])
UNKNOWN_VINTAGE = crosswalked('517311', None, ['517111'])
INVALID = unresolved('999999', 2022)
MISSING = unresolved(None, 2022)
UNKNOWN = {'ein': None, 'company_name': None}
COMPANY = {'ein': None, 'company_name': 'Acme'}


def leaf(code):
    return f'naics:2022:national_industry:{code}'


def record(description='Steel', year=2023, mapping=STEEL, **overrides):
    return {**mapping, 'year_filing_for': year, 'industry_description': description, **overrides}


def keyed(rows):
    return keyed_records(canonical_frame(rows), KEYS)


def build(rows, nodes=NODES, code_paths=CODE_PATHS):
    return build_pairs(keyed(rows), nodes, code_paths)


def tables(result):
    return tuple(
        frame.collect()
        for frame in (result.pairs, result.pair_codes, result.members, result.paths)
    )


def by_row(result):
    '''The pair of each source row, as a dict.'''
    joined = result.members.collect().join(result.pairs.collect(), on='pair_id', how='left')
    return {row['source_row']: row for row in joined.to_dicts()}


def codes_by_row(result):
    '''The pair-code rows of each source row's pair, in table order.'''
    codes = result.pair_codes.collect()
    return {
        row: codes.filter(pl.col('pair_id').eq(pair)).to_dicts()
        for row, pair in result.members.collect().iter_rows()
    }


def test_versions_and_schemas_are_the_spec_tables():
    assert PAIRS_VERSION == 'ita-text-pairs-v1'
    assert list(PAIR_SCHEMA.items()) == [
        ('pair_id', pl.String),
        ('pair_kind', pl.String),
        ('employer_key', pl.String),
        ('employer_basis', pl.String),
        ('description_key', pl.String),
        ('original_strings', pl.List(pl.String)),
        ('representative_string', pl.String),
        ('n_records', pl.UInt64),
        ('n_headline_records', pl.UInt64),
        ('first_year', pl.Int64),
        ('last_year', pl.Int64),
        ('n_years', pl.UInt64),
        ('flag_headline', pl.Boolean),
        ('flag_headline_codes_conflict', pl.Boolean),
        ('flag_empty', pl.Boolean),
        ('flag_placeholder', pl.Boolean),
        ('flag_copied_title_any', pl.Boolean),
        ('flag_copied_index_any', pl.Boolean),
        ('flag_suspected_mojibake', pl.Boolean),
        ('flag_employer_unknown', pl.Boolean),
        ('flag_employer_company_fallback', pl.Boolean),
        ('n_records_ein_padded', pl.UInt64),
    ]
    assert list(PAIR_CODE_SCHEMA.items()) == [
        ('pair_id', pl.String),
        ('naics_code', pl.String),
        ('naics_year', pl.Int64),
        ('naics_mapping_status', pl.String),
        ('naics_2022_candidates', pl.List(pl.String)),
        ('naics_2022_candidate_node_ids', pl.List(pl.String)),
        ('naics_2022_node_id', pl.String),
        ('naics_deepest_common_node_id', pl.String),
        ('flag_naics_crosswalked', pl.Boolean),
        ('flag_naics_ambiguous', pl.Boolean),
        ('flag_naics_unresolved', pl.Boolean),
        ('flag_headline_basis', pl.Boolean),
        ('flag_copied_title_native', pl.Boolean),
        ('flag_copied_index_native', pl.Boolean),
        ('n_records', pl.UInt64),
        ('n_records_year_from_dictionary', pl.UInt64),
        ('years', pl.List(pl.Int64)),
    ]
    assert list(MEMBER_SCHEMA.items()) == [('source_row', pl.UInt64), ('pair_id', pl.String)]
    assert PATH_SCHEMA is classification_tables.PATH_SCHEMA


# --- pair identity ---


def test_pair_id_encoding():
    assert pair_id('employer', ('ein:123456789', 'steel mill')) == (
        '7a0f1cef9cf5bc5d79af3a2993a46c15767dd0f3d208a8233fca9a07aac0d6f1'
    )
    assert pair_id('unknown_employer', ('17',)) == (
        'ac9816baa66533d9e4744c9321d083fae0633e0c70c6735c2a0af22d73064587'
    )


def test_pair_id_prefixes_each_utf8_part_with_its_byte_length():
    fields = ('company:café', 'crème brûlée')
    parts = [b'ita-text-pairs-v1', b'employer', *(field.encode() for field in fields)]
    body = b''.join(len(part).to_bytes(8, 'big') + part for part in parts)
    assert pair_id('employer', fields) == hashlib.sha256(body).hexdigest()
    assert pair_id('employer', ('ab', 'c')) != pair_id('employer', ('a', 'bc'))


def test_built_pair_ids_follow_the_encoding():
    rows = [record('Steel Mill') for _ in range(17)] + [record('Steel Mill', **UNKNOWN)]
    members = build(rows).members.collect()
    assert members['pair_id'][0] == (
        '7a0f1cef9cf5bc5d79af3a2993a46c15767dd0f3d208a8233fca9a07aac0d6f1'
    )
    assert members['pair_id'][17] == (
        'ac9816baa66533d9e4744c9321d083fae0633e0c70c6735c2a0af22d73064587'
    )


def test_pair_id_is_computed_once_per_pair(monkeypatch):
    calls = []

    def counting(kind, fields):
        calls.append((kind, fields))
        return pair_id(kind, fields)

    monkeypatch.setattr(ita_text_pairs, 'pair_id', counting)
    build(
        [
            record('Steel'),
            record('STEEL', year=2024),
            record('Steel', year=2025),
            record('Steel', **UNKNOWN),
            record('Steel', **UNKNOWN),
        ]
    )
    assert sorted(calls) == [
        ('employer', ('ein:123456789', 'steel')),
        ('unknown_employer', ('3',)),
        ('unknown_employer', ('4',)),
    ]


MIXED = [
    record('Steel'),
    record('STEEL', year=2024),
    record('Steel', ein='987654321'),
    record(''),
    record('N/A', year=2019, mapping=CONCORDED),
    record('Steel', **UNKNOWN),
    record('Steel', **UNKNOWN),
    record('Weld', **COMPANY),
    record(None, year=2018, mapping=CONCORDED),
]


def test_every_record_in_exactly_one_pair():
    records = keyed(MIXED)
    pairs, _, members, _ = tables(build_pairs(records, NODES, CODE_PATHS))
    assert members['source_row'].to_list() == list(range(len(MIXED)))
    assert pairs.height == 7
    assert pairs['n_records'].sum() == len(MIXED)
    counts = members.group_by('pair_id').agg(n=pl.len().cast(pl.UInt64))
    joined = pairs.join(counts, on='pair_id', how='full', coalesce=True)
    assert joined['n_records'].to_list() == joined['n'].to_list()
    keys = records.select('source_row', 'employer_key', 'description_key').collect()
    expected = [
        pair_id('unknown_employer', (str(row),))
        if employer is None
        else pair_id('employer', (employer, description))
        for row, employer, description in keys.iter_rows()
    ]
    assert members['pair_id'].to_list() == expected


def test_unknown_employers_never_group():
    rows = [
        record('Steel', ein='', company_name=''),
        record('Steel', ein=None, company_name='  '),
    ]
    pairs = build(rows).pairs.collect()
    assert pairs.height == 2
    assert set(pairs['pair_id']) == {
        pair_id('unknown_employer', ('0',)),
        pair_id('unknown_employer', ('1',)),
    }
    for pair in pairs.to_dicts():
        assert pair['pair_kind'] == 'unknown_employer'
        assert pair['employer_key'] is None
        assert pair['employer_basis'] == 'unknown'
        assert pair['flag_employer_unknown'] is True
        assert pair['flag_employer_company_fallback'] is False
        assert pair['n_records'] == 1
        assert pair['flag_headline'] is False


# --- delivered strings ---


def test_variant_spellings_share_one_pair():
    variants = ['Steel Mill', 'steel  mill', 'STEEL MILL', 'Ｓｔｅｅｌ Mill']
    pairs = build([record(text) for text in variants]).pairs.collect()
    assert pairs.height == 1
    pair = pairs.row(0, named=True)
    assert pair['description_key'] == 'steel mill'
    assert pair['original_strings'] == [
        'STEEL MILL',
        'Steel Mill',
        'steel  mill',
        'Ｓｔｅｅｌ Mill',
    ]
    assert pair['original_strings'] == sorted(variants)
    assert pair['n_records'] == 4
    assert pair['representative_string'] == 'STEEL MILL'


@pytest.mark.parametrize(
    ('texts', 'originals', 'representative'),
    [
        pytest.param(['STEEL', 'Steel', 'Steel'], ['STEEL', 'Steel'], 'Steel', id='most-frequent'),
        pytest.param(
            ['steel', 'Steel'], ['Steel', 'steel'], 'Steel', id='tie-first-by-code-point'
        ),
        pytest.param([None, None, ''], [None, ''], None, id='null-counted'),
        pytest.param(['', None], [None, ''], None, id='null-wins-a-tie'),
        pytest.param([None, '', ''], [None, ''], '', id='null-loses-on-count'),
        pytest.param([' ', None, ''], [None, '', ' '], None, id='nulls-first'),
    ],
)
def test_representative_string(texts, originals, representative):
    pairs = build([record(text) for text in texts]).pairs.collect()
    assert pairs.height == 1
    pair = pairs.row(0, named=True)
    assert pair['original_strings'] == originals
    assert pair['representative_string'] == representative


def test_null_description_pair():
    pair = build([record(None)]).pairs.collect().row(0, named=True)
    assert pair['original_strings'] == [None]
    assert pair['representative_string'] is None
    assert pair['flag_empty'] is True
    assert pair['description_key'] == ''
    assert pair['flag_headline'] is False


def test_pair_columns_pool_every_year_of_the_pair():
    rows = [
        record('Stã©el', year=2019, mapping=CONCORDED, ein='023456789'),
        record('StÃ©el', year=2025, ein='23456789'),
        record('stã©el', year=2023, ein='02-3456789'),
        record('Stã©el', year=2023, ein='023456789'),
    ]
    pair = build(rows).pairs.collect().row(0, named=True)
    assert pair == {
        'pair_id': pair_id('employer', ('ein:023456789', 'stã©el')),
        'pair_kind': 'employer',
        'employer_key': 'ein:023456789',
        'employer_basis': 'ein',
        'description_key': 'stã©el',
        'original_strings': ['StÃ©el', 'Stã©el', 'stã©el'],
        'representative_string': 'Stã©el',
        'n_records': 4,
        'n_headline_records': 3,
        'first_year': 2019,
        'last_year': 2025,
        'n_years': 3,
        'flag_headline': True,
        'flag_headline_codes_conflict': False,
        'flag_empty': False,
        'flag_placeholder': False,
        'flag_copied_title_any': False,
        'flag_copied_index_any': False,
        'flag_suspected_mojibake': True,
        'flag_employer_unknown': False,
        'flag_employer_company_fallback': False,
        'n_records_ein_padded': 1,
    }


# --- headline rule ---


def test_headline_rule():
    rows = [
        record('Steel'),
        record('Steel', year=2019, mapping=CONCORDED),
        record('', ein='987654321'),
        record('N/A', ein='987654321'),
        record('Steel', **UNKNOWN),
        record('Steel', **COMPANY),
    ]
    result = build(rows)
    pairs, codes = by_row(result), codes_by_row(result)
    assert pairs[0]['flag_headline'] is True
    assert pairs[0]['n_headline_records'] == 1
    assert pairs[0]['employer_basis'] == 'ein'
    assert pairs[0]['flag_employer_company_fallback'] is False
    assert [(c['naics_code'], c['naics_year'], c['flag_headline_basis']) for c in codes[0]] == [
        ('332312', 2022, True),
        ('517311', 2017, False),
    ]
    assert pairs[2]['flag_empty'] is True
    assert pairs[3]['flag_placeholder'] is True
    assert pairs[4]['flag_employer_unknown'] is True
    for row in (2, 3, 4):
        assert pairs[row]['flag_headline'] is False
        assert pairs[row]['n_headline_records'] == 1
    assert pairs[5]['flag_headline'] is True
    assert pairs[5]['flag_employer_company_fallback'] is True
    assert pairs[5]['employer_basis'] == 'company'
    assert pairs[5]['employer_key'] == 'company:acme'
    assert pairs[5]['flag_employer_unknown'] is False


@pytest.mark.parametrize(
    'mapping',
    [CONCORDED, AMBIGUOUS, UNKNOWN_VINTAGE, INVALID, MISSING],
    ids=['concorded', 'ambiguous', 'unknown-vintage', 'invalid-native', 'missing-code'],
)
def test_headline_needs_an_eligible_record(mapping):
    result = build([record('Steel', mapping=mapping)])
    pair = by_row(result)[0]
    assert pair['flag_headline'] is False
    assert pair['n_headline_records'] == 0
    assert [code['flag_headline_basis'] for code in codes_by_row(result)[0]] == [False]


def test_headline_records_are_counted_in_every_pair():
    rows = [record(''), record('', year=2024), record('N/A'), record('Steel', **UNKNOWN)]
    pairs = by_row(build(rows))
    assert [pairs[row]['n_headline_records'] for row in (0, 2, 3)] == [2, 1, 1]
    assert [pairs[row]['flag_headline'] for row in (0, 2, 3)] == [False, False, False]


def test_headline_ignores_quality_flags():
    rows = [
        record('Wired Telecommunications Carriers', **COMPANY),
        record('Stã©el', ein='23456789'),
        record('StÃ©el', ein='023456789'),
        record('Steel mill'),
    ]
    pairs = by_row(build(rows))
    assert pairs[0]['flag_copied_title_any'] is True
    assert pairs[0]['flag_employer_company_fallback'] is True
    assert pairs[1]['flag_suspected_mojibake'] is True
    assert pairs[1]['n_records_ein_padded'] == 1
    assert pairs[3]['flag_copied_index_any'] is True
    assert pairs[3]['flag_copied_title_any'] is False
    assert [pairs[row]['flag_headline'] for row in (0, 1, 3)] == [True, True, True]


def test_headline_code_conflict_keeps_both_nodes():
    rows = [
        record('Steel', mapping=native('238220')),
        record('Steel', year=2024, mapping=native('238210')),
    ]
    result = build(rows)
    pair = by_row(result)[0]
    assert pair['flag_headline'] is True
    assert pair['flag_headline_codes_conflict'] is True
    assert pair['n_headline_records'] == 2
    codes = codes_by_row(result)[0]
    assert [(c['naics_2022_node_id'], c['flag_headline_basis']) for c in codes] == [
        (leaf('238210'), True),
        (leaf('238220'), True),
    ]


def test_conflict_counts_distinct_basis_nodes_of_headline_pairs():
    rows = [
        record('Steel', mapping=native('238220')),
        record('Steel', year=2024, mapping=native('238220')),
        record('Steel', year=2019, mapping=CONCORDED),
        record('', ein='987654321', mapping=native('238220')),
        record('', ein='987654321', year=2024, mapping=native('238210')),
    ]
    pairs = by_row(build(rows))
    assert pairs[0]['flag_headline'] is True
    assert pairs[0]['flag_headline_codes_conflict'] is False
    assert pairs[3]['flag_headline'] is False
    assert pairs[3]['flag_headline_codes_conflict'] is False


@pytest.mark.parametrize('year', [2016, 2022, 2026])
def test_an_eligible_record_outside_2023_to_2025_fails(year):
    with pytest.raises(ValueError, match='^an eligible record falls outside 2023 to 2025$'):
        build([record(year=2023), record(year=year)])


def test_eligible_records_at_the_window_edges_pass():
    rows = [record(year=2023), record(year=2025), record('Weld', year=2016, mapping=CONCORDED)]
    result = build(rows)
    assert by_row(result)[0]['n_headline_records'] == 2


# --- pair codes ---


def code_row(pair, mapping, basis, title, index, n, dictionary, years, node_ids):
    return {
        'pair_id': pair,
        **{name: mapping[name] for name in ('naics_code', 'naics_year', 'naics_mapping_status')},
        'naics_2022_candidates': mapping['naics_2022_candidates'],
        'naics_2022_candidate_node_ids': node_ids,
        **{
            name: mapping[name]
            for name in (
                'naics_2022_node_id',
                'naics_deepest_common_node_id',
                'flag_naics_crosswalked',
                'flag_naics_ambiguous',
                'flag_naics_unresolved',
            )
        },
        'flag_headline_basis': basis,
        'flag_copied_title_native': title,
        'flag_copied_index_native': index,
        'n_records': n,
        'n_records_year_from_dictionary': dictionary,
        'years': years,
    }


def test_pair_code_columns():
    title = 'Wired Telecommunications Carriers'
    rows = [
        record(title, year=2019, mapping=CONCORDED, naics_year_from_dictionary=True),
        record(title, year=2020, mapping=CONCORDED, naics_year_from_dictionary=True),
        record(title, year=2019, mapping=CONCORDED, naics_year_from_dictionary=False),
        record(title, year=2020, mapping=CONCORDED, naics_year_from_dictionary=None),
        record(title, year=2021, mapping=UNKNOWN_VINTAGE),
        record(title, year=2024, mapping=native('517111')),
    ]
    codes = build(rows).pair_codes.collect()
    pair = pair_id('employer', ('ein:123456789', 'wired telecommunications carriers'))
    expected = pl.DataFrame(
        [
            code_row(pair, native('517111'), True, False, False, 1, 0, [2024], [leaf('517111')]),
            code_row(pair, UNKNOWN_VINTAGE, False, None, None, 1, 0, [2021], [leaf('517111')]),
            code_row(pair, CONCORDED, False, True, False, 4, 2, [2019, 2020], [leaf('517111')]),
        ],
        schema=PAIR_CODE_SCHEMA,
    )
    assert_frame_equal(codes, expected)


def test_copied_native_flags_follow_each_code_vintage():
    result = build([record('Steel mill'), record('Steel mill', year=2019, mapping=CONCORDED)])
    codes = codes_by_row(result)[0]
    assert [
        (c['naics_code'], c['flag_copied_title_native'], c['flag_copied_index_native'])
        for c in codes
    ] == [('332312', False, True), ('517311', False, False)]


# --- mapping state ---


def test_contradictory_mapping_state_fails():
    rows = [
        record('Steel', year=2019, mapping=CONCORDED),
        record(
            'Weld',
            year=2020,
            mapping={**CONCORDED, 'naics_2022_candidates': ['517111', '517112']},
        ),
    ]
    with pytest.raises(ValueError, match='^contradictory mapping states$'):
        build(rows)


CHANGES = {
    'naics_mapping_status': 'invalid_native_code',
    'naics_matching_vintages': [2012, 2017],
    'naics_2022_candidates': ['517111', '517112'],
    'naics_2022_code': None,
    'naics_2022_node_id': None,
    'naics_deepest_common_node_id': None,
    'flag_naics_crosswalked': False,
    'flag_naics_ambiguous': True,
    'flag_naics_unresolved': True,
}


@pytest.mark.parametrize('column', list(MAPPING_SCHEMA))
def test_require_single_mapping_state_compares_every_mapping_field(column):
    assert set(CHANGES) == set(MAPPING_SCHEMA)
    assert CHANGES[column] != CONCORDED[column]
    frame = canonical_frame(
        [
            record(year=2019, mapping=CONCORDED),
            record(year=2019, mapping={**CONCORDED, column: CHANGES[column]}),
        ]
    )
    with pytest.raises(ValueError, match='^contradictory mapping states$'):
        require_single_mapping_state(frame)


def test_a_null_key_with_two_states_is_contradictory():
    missing = unresolved(None, None)
    frame = canonical_frame(
        [
            record(mapping=missing),
            record(mapping={**missing, 'naics_mapping_status': 'invalid_native_code'}),
        ]
    )
    with pytest.raises(ValueError, match='^contradictory mapping states$'):
        require_single_mapping_state(frame)


def test_single_mapping_state_allows_repeats_and_other_vintages():
    frame = canonical_frame(
        [
            record(year=2019, mapping=CONCORDED),
            record(year=2020, mapping=CONCORDED),
            record(year=2021, mapping=UNKNOWN_VINTAGE),
            record(year=2021, mapping=crosswalked('517311', 2012, ['517112'])),
            record(mapping=STEEL),
            record(mapping=native('238220')),
            record(mapping=unresolved(None, None)),
            record(mapping=unresolved(None, None)),
        ]
    )
    assert require_single_mapping_state(frame) is None


def test_mapping_state_is_checked_first():
    canonical = canonical_frame(
        [
            record(year=2022),
            record('Weld', year=2019, mapping=CONCORDED),
            record('Weld', year=2019, mapping={**CONCORDED, 'flag_naics_ambiguous': True}),
        ]
    )
    with pytest.raises(ValueError, match='^contradictory mapping states$'):
        build_pairs(canonical, NODES, CODE_PATHS)


@pytest.mark.parametrize('column', ['naics_code', 'naics_year', *MAPPING_SCHEMA])
def test_require_single_mapping_state_needs_the_mapping_columns(column):
    frame = canonical_frame([record()]).drop(column)
    with pytest.raises(ValueError, match='^records lack the NAICS mapping columns$'):
        require_single_mapping_state(frame)


def test_require_single_mapping_state_needs_the_mapping_types():
    frame = canonical_frame([record()]).with_columns(pl.col('naics_year').cast(pl.String))
    with pytest.raises(ValueError, match='^records lack the NAICS mapping columns$'):
        require_single_mapping_state(frame)


# --- candidate nodes and paths ---


def test_paths_cover_candidates_and_scalars():
    result = build(
        [record('Line', year=2018, mapping=AMBIGUOUS), record('Bolt', mapping=INVALID), record()]
    )
    expected = [leaf('332312'), leaf('517111'), leaf('517112')]
    stage4 = CODE_PATHS.filter(pl.col('node_id').is_in(expected)).sort('node_id')
    assert_frame_equal(result.paths.collect(), stage4)
    codes = codes_by_row(result)
    assert codes[0][0]['naics_2022_candidate_node_ids'] == [leaf('517111'), leaf('517112')]
    assert codes[1][0]['naics_2022_candidate_node_ids'] == []
    assert codes[2][0]['naics_2022_candidate_node_ids'] == [leaf('332312')]
    paths = build([record('Bolt', mapping=INVALID)]).paths.collect()
    assert paths.is_empty()
    assert list(paths.schema.items()) == list(PATH_SCHEMA.items())


def test_paths_cover_a_scalar_node_outside_the_candidates():
    mapping = {**STEEL, 'naics_2022_candidates': [], 'naics_deepest_common_node_id': None}
    paths = build([record(mapping=mapping)]).paths.collect()
    assert_frame_equal(paths, CODE_PATHS.filter(pl.col('node_id').eq(leaf('332312'))))


def test_paths_are_the_sorted_stage4_rows():
    rows = [record('Line', year=2018, mapping=AMBIGUOUS), record()]
    paths = build(rows, code_paths=CODE_PATHS.reverse()).paths.collect()
    assert paths['node_id'].to_list() == [leaf('332312'), leaf('517111'), leaf('517112')]
    stage4 = CODE_PATHS.filter(pl.col('node_id').is_in(paths['node_id'].implode()))
    assert_frame_equal(paths, stage4)


@pytest.mark.parametrize(
    ('mapping', 'missing'),
    [
        pytest.param(AMBIGUOUS, leaf('517112'), id='candidate'),
        pytest.param(STEEL, leaf('332312'), id='candidate-and-scalar'),
        pytest.param(
            {**STEEL, 'naics_2022_candidates': [], 'naics_deepest_common_node_id': None},
            leaf('332312'),
            id='scalar-only',
        ),
    ],
)
def test_a_referenced_node_without_a_path_fails(mapping, missing):
    code_paths = CODE_PATHS.filter(pl.col('node_id').ne(missing))
    with pytest.raises(ValueError, match='^a referenced node has no path$'):
        build([record(year=2023, mapping=mapping)], code_paths=code_paths)


DECOYS = pl.DataFrame(
    [
        ('naics:2017:national_industry:517111', 'naics', 2017, 'national_industry', '517111', 'X'),
        ('naics:2022:industry:517112', 'naics', 2022, 'industry', '517112', 'Wrong level'),
    ],
    schema=NODE_SCHEMA,
    orient='row',
)


def test_candidate_node_ids_name_the_2022_leaves():
    nodes = pl.concat([NODES, DECOYS])
    codes = build([record('Line', year=2018, mapping=AMBIGUOUS)], nodes=nodes).pair_codes.collect()
    assert codes.height == 1
    assert codes['naics_2022_candidate_node_ids'].to_list() == [[leaf('517111'), leaf('517112')]]


@pytest.mark.parametrize(
    'decoy',
    [None, DECOYS.head(1), DECOYS.tail(1)],
    ids=['absent', 'other-vintage', 'other-level'],
)
def test_a_candidate_without_a_2022_leaf_node_fails(decoy):
    code = '517111' if decoy is not None and decoy['vintage'][0] == 2017 else '517112'
    nodes = NODES.filter(pl.col('node_id').ne(leaf(code)))
    if decoy is not None:
        nodes = pl.concat([nodes, decoy])
    with pytest.raises(ValueError, match='^a candidate has no NAICS 2022 national industry node$'):
        build([record('Line', year=2018, mapping=AMBIGUOUS)], nodes=nodes)


# --- sort orders ---


def test_tables_are_sorted_whatever_the_record_order():
    names = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta']
    rows = [
        record('Steel', mapping=unresolved(None, None)),
        record('Steel'),
        record('Steel', year=2021, mapping=UNKNOWN_VINTAGE),
        record('Steel', year=2019, mapping=CONCORDED),
        *[record(name, year=2019, mapping=CONCORDED) for name in names],
        record('Steel', **UNKNOWN),
        record('Steel', **UNKNOWN),
    ]
    # Reverse eagerly: a lazy sort that only feeds an unordered join can be optimized away.
    records = keyed(rows).collect().reverse().lazy()
    result = build_pairs(records, NODES, CODE_PATHS)
    pairs, codes, members, _ = tables(result)
    assert pairs.height == 10
    assert pairs['pair_id'].to_list() == sorted(pairs['pair_id'].to_list())
    assert members['source_row'].to_list() == list(range(len(rows)))
    steel = pair_id('employer', ('ein:123456789', 'steel'))
    assert codes.filter(pl.col('pair_id').eq(steel)).select('naics_code', 'naics_year').rows() == [
        (None, None),
        ('332312', 2022),
        ('517311', None),
        ('517311', 2017),
    ]
    assert_frame_equal(codes, codes.sort('pair_id', 'naics_code', 'naics_year', nulls_last=False))


# --- report ---


REPORT_ROWS = [
    record('Steel'),
    record('Steel', year=2024),
    record('Steel', ein='987654321', mapping=native('238220')),
    record('Steel', ein='987654321', year=2024, mapping=native('238210')),
    record('Steel', ein='987654321', year=2019, mapping=CONCORDED),
    record('Weld', year=2025, **COMPANY),
    record('Rivet'),
    record('Nail'),
    record(''),
    record('N/A', year=2019, mapping=CONCORDED),
    record('Steel', **UNKNOWN),
    record('Bolt', year=2019, mapping=CONCORDED),
    record('Bolt', mapping=INVALID),
]


def test_report_reconciles_pairs_to_records():
    assert build(REPORT_ROWS).report == {
        'n_pairs': 9,
        'n_records': 13,
        'records_by_year_status_basis': [
            {'year_filing_for': 2019, 'naics_mapping_status': 'concorded',
             'flag_headline_basis': False, 'n': 3},
            {'year_filing_for': 2023, 'naics_mapping_status': 'invalid_native_code',
             'flag_headline_basis': False, 'n': 1},
            {'year_filing_for': 2023, 'naics_mapping_status': 'native_2022',
             'flag_headline_basis': True, 'n': 6},
            {'year_filing_for': 2024, 'naics_mapping_status': 'native_2022',
             'flag_headline_basis': True, 'n': 2},
            {'year_filing_for': 2025, 'naics_mapping_status': 'native_2022',
             'flag_headline_basis': True, 'n': 1},
        ],
        'pairs_by_kind_headline_text': [
            {'pair_kind': 'employer', 'flag_headline': False, 'text_state': 'empty', 'n': 1},
            {'pair_kind': 'employer', 'flag_headline': False, 'text_state': 'placeholder', 'n': 1},
            {'pair_kind': 'employer', 'flag_headline': False, 'text_state': 'text', 'n': 1},
            {'pair_kind': 'employer', 'flag_headline': True, 'text_state': 'text', 'n': 5},
            {'pair_kind': 'unknown_employer', 'flag_headline': False, 'text_state': 'text',
             'n': 1},
        ],
        'headline_pairs_by_node_count': [
            {'n_headline_nodes': 1, 'n': 4},
            {'n_headline_nodes': 2, 'n': 1},
        ],
        'headline_pair_record_distribution': {
            'count': 5, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 2.0, 'p95': 3.0, 'max': 3,
        },
    }


def test_report_keeps_empty_and_placeholder_pairs_apart():
    rows = [record(''), record('', ein='987654321'), record('N/A')]
    assert build(rows).report['pairs_by_kind_headline_text'] == [
        {'pair_kind': 'employer', 'flag_headline': False, 'text_state': 'empty', 'n': 2},
        {'pair_kind': 'employer', 'flag_headline': False, 'text_state': 'placeholder', 'n': 1},
    ]


def test_headline_pair_record_distribution():
    sizes = [1, 1, 2, 2, 3, 9]
    rows = [record(f'Text {i}') for i, size in enumerate(sizes) for _ in range(size)]
    rows += [record('') for _ in range(4)]
    assert build(rows).report['headline_pair_record_distribution'] == {
        'count': 6, 'min': 1, 'p25': 1.0, 'median': 2.0, 'p75': 3.0, 'p95': 9.0, 'max': 9,
    }


def test_report_of_no_headline_pairs():
    report = build([record('')]).report
    assert report['headline_pairs_by_node_count'] == []
    assert report['headline_pair_record_distribution'] == {
        'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p95': None,
        'max': None,
    }


# --- input refusals ---


KEYED_COLUMNS = [
    'source_row',
    'description_key',
    'employer_key',
    'flag_empty',
    'flag_placeholder',
    'flag_ein_padded',
    'flag_suspected_mojibake',
    *COPY_FLAGS,
    'year_filing_for',
    'industry_description',
    'naics_year_from_dictionary',
]


@pytest.mark.parametrize('column', KEYED_COLUMNS)
def test_build_refuses_records_without_a_keyed_column(column):
    records = keyed([record()]).drop(column)
    with pytest.raises(ValueError, match='^pairs need keyed records$'):
        build_pairs(records, NODES, CODE_PATHS)


@pytest.mark.parametrize(
    ('column', 'dtype'),
    [
        ('source_row', pl.Int64),
        ('year_filing_for', pl.Int32),
        ('flag_copied_title_native', pl.String),
    ],
)
def test_build_refuses_records_with_another_column_type(column, dtype):
    records = keyed([record()]).with_columns(pl.col(column).cast(dtype))
    with pytest.raises(ValueError, match='^pairs need keyed records$'):
        build_pairs(records, NODES, CODE_PATHS)


@pytest.mark.parametrize(
    ('nodes', 'code_paths'),
    [
        pytest.param(NODES.drop('title'), CODE_PATHS, id='nodes-missing-column'),
        pytest.param(NODES.select(NODES.columns[::-1]), CODE_PATHS, id='nodes-column-order'),
        pytest.param(NODES, CODE_PATHS.rename({'path': 'ancestors'}), id='paths-renamed'),
        pytest.param(NODES, CODE_PATHS.select('path', 'node_id'), id='paths-column-order'),
    ],
)
def test_build_refuses_reference_frames_with_other_schemas(nodes, code_paths):
    with pytest.raises(ValueError, match='^nodes or code paths do not have the Stage 4 schemas$'):
        build_pairs(keyed([record()]), nodes, code_paths)


def test_build_refuses_an_employer_key_without_a_known_basis():
    records = keyed([record()]).with_columns(employer_key=pl.lit('duns:123'))
    with pytest.raises(ValueError, match='^an employer key has no known basis$'):
        build_pairs(records, NODES, CODE_PATHS)


def test_no_records_give_empty_tables():
    records = keyed([])
    result = build_pairs(records, NODES, CODE_PATHS)
    schemas = (PAIR_SCHEMA, PAIR_CODE_SCHEMA, MEMBER_SCHEMA, PATH_SCHEMA)
    for frame, schema in zip(tables(result), schemas):
        assert frame.is_empty()
        assert list(frame.schema.items()) == list(schema.items())
    assert result.report == {
        'n_pairs': 0,
        'n_records': 0,
        'records_by_year_status_basis': [],
        'pairs_by_kind_headline_text': [],
        'headline_pairs_by_node_count': [],
        'headline_pair_record_distribution': {
            'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p95': None,
            'max': None,
        },
    }
    validate_pairs(result, records, CODE_PATHS)


# --- validator ---


VALID_ROWS = [
    record('Steel'),
    record('Steel', year=2024),
    record('Steel', ein='987654321', mapping=native('238220')),
    record('Steel', ein='987654321', year=2024, mapping=native('238210')),
    record('N/A'),
    record('', mapping=native('238220')),
    record('', year=2024, mapping=native('238210')),
    record('Steel', **UNKNOWN),
    record('Weld', year=2019, mapping=CONCORDED, **UNKNOWN),
    record('Bolt', year=2019, mapping=CONCORDED),
    record('Bolt', mapping=INVALID),
    record('Line', year=2018, mapping=AMBIGUOUS),
    record('Weld', year=2025, **COMPANY),
]


@pytest.fixture(scope='module')
def valid():
    records = keyed(VALID_ROWS)
    return build_pairs(records, NODES, CODE_PATHS), records


class Tables:
    '''Collected copies of a result's tables, and the pair ID of each source row.'''

    def __init__(self, result):
        self.pairs, self.codes, self.members, self.paths = tables(result)
        self.pid = dict(self.members.iter_rows())


def set_pair(frame, pair, **values):
    return frame.with_columns(
        **{
            name: pl.when(pl.col('pair_id').eq(pair))
            .then(pl.lit(value, dtype=PAIR_SCHEMA[name]))
            .otherwise(pl.col(name))
            for name, value in values.items()
        }
    )


def set_code(frame, pair, code, **values):
    chosen = pl.col('pair_id').eq(pair).and_(pl.col('naics_code').eq(code))
    return frame.with_columns(
        **{
            name: pl.when(chosen).then(pl.lit(value, dtype=PAIR_CODE_SCHEMA[name]))
            .otherwise(pl.col(name))
            for name, value in values.items()
        }
    )


def set_member(frame, row, pair):
    chosen = pl.col('source_row').eq(row)
    return frame.with_columns(pair_id=pl.when(chosen).then(pl.lit(pair)).otherwise('pair_id'))


TAMPERS = {
    'pairs-column-order': (
        lambda t: {'pairs': t.pairs.select('pair_kind', pl.exclude('pair_kind'))},
        'pair tables do not have their schemas',
    ),
    'pairs-dtype': (
        lambda t: {'pairs': t.pairs.with_columns(pl.col('n_years').cast(pl.Int64))},
        'pair tables do not have their schemas',
    ),
    'codes-missing-column': (
        lambda t: {'pair_codes': t.codes.drop('years')},
        'pair tables do not have their schemas',
    ),
    'members-extra-column': (
        lambda t: {'members': t.members.with_columns(extra=pl.lit(1))},
        'pair tables do not have their schemas',
    ),
    'paths-renamed': (
        lambda t: {'paths': t.paths.rename({'path': 'ancestors'})},
        'pair tables do not have their schemas',
    ),
    'duplicate-pair-id': (
        lambda t: {'pairs': pl.concat([t.pairs, t.pairs.head(1)])},
        'pair IDs repeat',
    ),
    'member-row-repeated': (
        lambda t: {
            'members': t.members.with_columns(
                source_row=pl.when(pl.col('source_row').eq(12)).then(pl.lit(0, pl.UInt64))
                .otherwise('source_row')
            )
        },
        'members do not hold each source row once',
    ),
    'members-shifted': (
        lambda t: {'members': t.members.with_columns(pl.col('source_row').add(1))},
        'members do not hold each source row once',
    ),
    'member-extra': (
        lambda t: {
            'members': pl.concat(
                [t.members, pl.DataFrame([(13, t.pid[0])], schema=MEMBER_SCHEMA, orient='row')]
            )
        },
        'members do not hold each source row once',
    ),
    'member-unknown-pair': (
        lambda t: {'members': set_member(t.members, 0, '0' * 64)},
        'a member names no pair',
    ),
    'pair-records-sum': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[0], n_records=3)},
        'pair record counts do not sum to the record count',
    ),
    'member-moved': (
        lambda t: {'members': set_member(t.members, 1, t.pid[4])},
        'pair member counts differ from n_records',
    ),
    'pair-without-codes': (
        lambda t: {'pair_codes': t.codes.filter(pl.col('pair_id').ne(t.pid[9]))},
        'pairs and pair codes disagree on pair IDs',
    ),
    'orphan-code-row': (
        lambda t: {
            'pair_codes': pl.concat(
                [
                    t.codes,
                    t.codes.filter(pl.col('pair_id').eq(t.pid[0])).with_columns(
                        pair_id=pl.lit('f' * 64)
                    ),
                ]
            )
        },
        'pairs and pair codes disagree on pair IDs',
    ),
    'code-key-repeated': (
        lambda t: {
            'pair_codes': pl.concat([t.codes, t.codes.filter(pl.col('pair_id').eq(t.pid[11]))])
        },
        'pair code keys repeat',
    ),
    'code-records': (
        lambda t: {'pair_codes': set_code(t.codes, t.pid[9], '517311', n_records=2)},
        'pair code counts differ from n_records',
    ),
    'headline-records': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[0], n_headline_records=3)},
        'headline invariants fail',
    ),
    'headline-on-placeholder': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[4], flag_headline=True)},
        'headline invariants fail',
    ),
    'headline-on-empty': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[5], flag_headline=True)},
        'headline invariants fail',
    ),
    'headline-on-unknown': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[7], flag_headline=True)},
        'headline invariants fail',
    ),
    'headline-without-eligible': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[9], flag_headline=True)},
        'headline invariants fail',
    ),
    'headline-cleared': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[12], flag_headline=False)},
        'headline invariants fail',
    ),
    'headline-null': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[9], flag_headline=None)},
        'headline invariants fail',
    ),
    'conflict-cleared': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[2], flag_headline_codes_conflict=False)},
        'headline conflict flags differ from the basis nodes',
    ),
    'conflict-set': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[0], flag_headline_codes_conflict=True)},
        'headline conflict flags differ from the basis nodes',
    ),
    'conflict-on-non-headline': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[5], flag_headline_codes_conflict=True)},
        'headline conflict flags differ from the basis nodes',
    ),
    'basis-node-merged': (
        lambda t: {
            'pair_codes': set_code(t.codes, t.pid[2], '238210', naics_2022_node_id=leaf('238220'))
        },
        'headline conflict flags differ from the basis nodes',
    ),
    'unknown-employer-key': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[7], employer_key='ein:123456789')},
        'unknown-employer pairs are malformed',
    ),
    'unknown-flag': (
        lambda t: {'pairs': set_pair(t.pairs, t.pid[7], flag_employer_unknown=False)},
        'unknown-employer pairs are malformed',
    ),
    'unknown-records': (
        lambda t: {
            'pairs': set_pair(
                t.pairs,
                t.pid[9],
                pair_kind='unknown_employer',
                employer_key=None,
                employer_basis='unknown',
                flag_employer_unknown=True,
            )
        },
        'unknown-employer pairs are malformed',
    ),
    'path-changed': (
        lambda t: {
            'paths': t.paths.with_columns(
                path=pl.when(pl.col('node_id').eq(leaf('517111')))
                .then(pl.col('path').list.reverse())
                .otherwise('path')
            )
        },
        'paths differ from the Stage 4 rows',
    ),
    'path-fabricated': (
        lambda t: {
            'paths': pl.concat(
                [
                    t.paths,
                    pl.DataFrame(
                        [(leaf('999999'), [leaf('999999')])], schema=PATH_SCHEMA, orient='row'
                    ),
                ]
            )
        },
        'paths differ from the Stage 4 rows',
    ),
    'path-dropped': (
        lambda t: {'paths': t.paths.filter(pl.col('node_id').ne(leaf('517112')))},
        'referenced nodes differ from the path nodes',
    ),
    'path-extra': (
        lambda t: {
            'paths': pl.concat(
                [t.paths, CODE_PATHS.filter(pl.col('node_id').eq('naics:2022:sector:31-33'))]
            )
        },
        'referenced nodes differ from the path nodes',
    ),
    'path-repeated': (
        lambda t: {'paths': pl.concat([t.paths, t.paths.head(1)])},
        'referenced nodes differ from the path nodes',
    ),
}


def test_validator_accepts_the_build(valid):
    result, records = valid
    validate_pairs(result, records, CODE_PATHS)
    pairs = by_row(result)
    assert pairs[2]['flag_headline_codes_conflict'] is True
    assert pairs[5]['n_headline_records'] == 2
    assert pairs[9]['n_records'] == 2


def test_validator_rejects_row_loss(valid):
    result, records = valid
    members = result.members.filter(pl.col('source_row').ne(5))
    with pytest.raises(ValueError, match='^members do not hold each source row once$'):
        validate_pairs(replace(result, members=members), records, CODE_PATHS)


@pytest.mark.parametrize('case', list(TAMPERS))
def test_validator_rejects_a_broken_table(valid, case):
    result, records = valid
    tamper, message = TAMPERS[case]
    frames = tamper(Tables(result))
    broken = replace(result, **{name: frame.lazy() for name, frame in frames.items()})
    with pytest.raises(ValueError, match=f'^{message}$'):
        validate_pairs(broken, records, CODE_PATHS)


def test_validator_counts_the_given_records(valid):
    result, _ = valid
    with pytest.raises(ValueError, match='^members do not hold each source row once$'):
        validate_pairs(result, keyed([*VALID_ROWS, record()]), CODE_PATHS)


def test_validator_refuses_code_paths_with_another_schema(valid):
    result, records = valid
    with pytest.raises(ValueError, match='^code paths do not have the path schema$'):
        validate_pairs(result, records, CODE_PATHS.rename({'path': 'ancestors'}))


def test_result_is_a_frozen_dataclass(valid):
    result, _ = valid
    assert isinstance(result, TextPairs)
    with pytest.raises(AttributeError):
        result.report = {}


def test_pairs_module_loads_no_ipums_or_dotenv_module():
    code = ('import sys; import embedding_data.ita_text_pairs as m; '
            'bad = [n for n in sys.modules if n.split(".")[0] in {"dotenv", "ipumspy"} '
            'or n.startswith(("embedding_data.ipums", "embedding_data.acs"))]; '
            'sys.exit(1 if bad else 0)')
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
