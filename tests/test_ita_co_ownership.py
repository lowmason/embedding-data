import re
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import polars as pl
import pytest
from ita_establishment_fixtures import (
    canonical_frame,
    crosswalked,
    naics_reference,
    native,
    unresolved,
)

from embedding_data import target_contract
from embedding_data.classification_tables import NODE_SCHEMA
from embedding_data.ita_co_ownership import (
    CO_OWNERSHIP_VERSION,
    EXCLUSIONS,
    MARGINAL_SCHEMA,
    METADATA,
    PADDED_LABEL,
    RECORD_FLAGS,
    SAMPLE_SET,
    SIZE_LABEL,
    SUPPORT_SCHEMA,
    TOLERANCE,
    UNIVERSE,
    YEARS,
    CoOwnership,
    estimate,
    validate_co_ownership,
)
from embedding_data.ita_establishment_records import keyed_records, text_keys
from embedding_data.ita_index_references import INDEX_SCHEMA
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA

SPEC = Path(__file__).parents[1] / 'specs/ita-establishment-targets.md'
TITLES = pl.DataFrame(
    [(2022, '332312', 'Fabricated Structural Metal Manufacturing')],
    schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    orient='row',
)
INDEX = pl.DataFrame([(2022, '332312', 'Steel mill')], schema=INDEX_SCHEMA, orient='row')
KEYS = text_keys(TITLES, INDEX)

A, B, C, D, E = '238220', '722511', '332312', '541330', '561720'
NODES, _ = naics_reference([A, B, C, D, E])
# Decoys that carry a national-industry node ID but fail one membership condition each.
DECOYS = pl.DataFrame(
    [
        ('naics:2017:national_industry:238220', 'naics', 2017, 'national_industry', A, 'Decoy'),
        ('naics:2022:national_industry:999998', 'naics', 2022, 'industry', '999998', 'Decoy'),
        ('naics:2022:national_industry:999997', 'soc', 2022, 'national_industry', '999997', 'D'),
    ],
    schema=NODE_SCHEMA,
    orient='row',
)
NODES_WITH_DECOYS = pl.concat([NODES, DECOYS])

CROSSWALKED = crosswalked('517311', 2017, ['517111'])
AMBIGUOUS = crosswalked('517110', 2012, ['517111', '517112'])
UNKNOWN_VINTAGE = crosswalked('517311', None, ['517111'])
INVALID = unresolved('999999', 2022)
MISSING = unresolved(None, 2022)
REASONS = (*EXCLUSIONS, 'eligible')


def leaf(code):
    return f'naics:2022:national_industry:{code}'


def code_of(node_id):
    return node_id.rsplit(':', 1)[1]


def rec(code=A, year=2023, ein='100000001', mapping=None, **overrides):
    '''One canonical record of `code` (a native 2022 leaf unless `mapping` is given).'''
    return {
        **(native(code) if mapping is None else mapping),
        'year_filing_for': year,
        'ein': ein,
        **overrides,
    }


def keyed(rows):
    return keyed_records(canonical_frame(rows), KEYS)


def run(rows):
    return estimate(keyed(rows))


def tables(result):
    return tuple(frame.collect() for frame in (result.targets, result.marginals, result.support))


def cells(result):
    '''Target rows keyed by their (unit_a, unit_b) codes.'''
    rows = result.targets.collect().to_dicts()
    return {(code_of(row['unit_a']), code_of(row['unit_b'])): row for row in rows}


def support_of(result):
    rows = result.support.collect().to_dicts()
    return {(code_of(row['unit_a']), code_of(row['unit_b'])): row for row in rows}


def marginals_of(result):
    return {code_of(row['node_id']): row for row in result.marginals.collect().to_dicts()}


def reason_of(row):
    '''The partition reason of a single record.'''
    (entry,) = run([row]).report['partition_by_year']
    (reason,) = [name for name in REASONS if entry[name] == 1]
    return reason


# e1 {A,B}, e2 {A,B} and e3 {A,C} in 2023.
MIRROR = [
    rec(A, ein='100000001'),
    rec(B, ein='100000001'),
    rec(A, ein='100000002'),
    rec(B, ein='100000002'),
    rec(A, ein='100000003'),
    rec(C, ein='100000003'),
]
# MIRROR, then e4 in C whose padded spelling files A, and e5 alone in D.
VALID = [
    *MIRROR,
    rec(C, ein='023456789'),
    rec(A, ein='23456789'),
    rec(D, ein='100000005'),
]
# e1 {A,B}; e2 {A,C} with padded records in C and B; a padded-only EIN in A, D and E.
PADDED = [
    rec(A, ein='100000001'),
    rec(B, ein='100000001'),
    rec(A, ein='023456789'),
    rec(C, ein='023456789'),
    rec(C, ein='23456789'),
    rec(B, ein='23456789'),
    rec(A, ein='34567890'),
    rec(D, ein='34567890'),
    rec(E, ein='34567890'),
]
# EIN i owns the first i codes, and EIN 1 files a second record in A.
NESTED = [
    *[rec(code, ein=f'20000000{i}') for i in range(1, 6) for code in (A, B, C, D, E)[:i]],
    rec(A, ein='200000001'),
]


def test_contract_constants():
    assert CO_OWNERSHIP_VERSION == 'ita-co-ownership-v1'
    assert YEARS == (2023, 2024, 2025)
    assert SAMPLE_SET == 'ita_300a_2023_2025'
    assert TOLERANCE == 1e-12
    assert SIZE_LABEL == 'size_gate_pending'
    assert PADDED_LABEL == 'numerator:ein_padded_sensitivity:true'
    assert METADATA == {
        'source': 'osha_ita',
        'family': 'co_ownership',
        'unit_a_type': 'naics_national_industry',
        'unit_b_type': 'naics_national_industry',
        'measure': 'employer_share',
        'se_method': 'none',
        'sample_set': 'ita_300a_2023_2025',
        'vintage': 'naics=2022',
        'universe': UNIVERSE,
    }
    assert list(MARGINAL_SCHEMA.items()) == [
        ('node_id', pl.String),
        ('n_employers', pl.UInt64),
        ('n_multi_industry_employers', pl.UInt64),
        ('n_records', pl.UInt64),
        ('n_employers_including_padded', pl.UInt64),
        ('n_employers_partial', pl.UInt64),
    ]
    assert list(SUPPORT_SCHEMA.items()) == [
        ('unit_a', pl.String),
        ('unit_b', pl.String),
        ('j_employers', pl.UInt64),
        ('j_2023', pl.UInt64),
        ('j_2024', pl.UInt64),
        ('j_2025', pl.UInt64),
        ('j_including_padded', pl.UInt64),
    ]
    assert EXCLUSIONS == (
        'year_outside_window',
        'industry_ineligible',
        'ein_unusable',
        'ein_padded',
    )
    assert RECORD_FLAGS == (
        'flag_employment',
        'flag_hours_per_employee',
        'flag_below_filing_size',
        'flag_naics_year_unknown',
        'flag_outside_filing_industry',
        'flag_outside_filing_rule',
        'flag_filing_rule_label_bridged',
        'flag_filing_reference_ambiguous',
        'naics_year_from_dictionary',
    )


def test_universe_is_the_spec_statement():
    assert UNIVERSE == (
        'OSHA ITA Form 300A is a program-selected filing subset, not a frame representative '
        'of all establishments or firms. Voluntary and outside-rule filings are retained, and '
        'reported codes and employment are unvalidated. This target counts employers '
        'identified by a usable, unreconstructed EIN that filed 2023–2025 '
        'establishment-year records with valid native NAICS 2022 industries. An EIN is a '
        'tax-filing entity, not necessarily a whole firm. It is conditional on that '
        'eligibility population.'
    )
    text = SPEC.read_text()
    start = text.index('Universe statement: ') + len('Universe statement: ')
    assert ' '.join(text[start:text.index('\n\n', start)].split()) == UNIVERSE


def test_result_is_a_frozen_dataclass():
    assert [field.name for field in fields(CoOwnership)] == [
        'targets',
        'marginals',
        'support',
        'report',
    ]
    result = run(MIRROR)
    with pytest.raises(FrozenInstanceError):
        result.report = {}


def test_same_year_rule():
    cross_year = [rec(A, 2023), rec(B, 2024)]
    assert run(cross_year).targets.collect().is_empty()
    result = run([*cross_year, rec(A, 2025), rec(B, 2025)])
    assert {key: row['n_unweighted'] for key, row in cells(result).items()} == {
        (A, B): 1,
        (B, A): 1,
    }


def test_same_year_copresence_is_counted_once_per_year():
    result = run([rec(A, 2023), rec(B, 2023), rec(A, 2025), rec(B, 2025), rec(A, 2024),
                  rec(C, 2024)])
    support = support_of(result)
    assert support[A, B] == {
        'unit_a': leaf(A),
        'unit_b': leaf(B),
        'j_employers': 1,
        'j_2023': 1,
        'j_2024': 0,
        'j_2025': 1,
        'j_including_padded': 1,
    }
    assert [support[C, A][f'j_{year}'] for year in YEARS] == [0, 1, 0]
    assert cells(result)[A, B]['n_unweighted'] == 1
    assert cells(result)[A, B]['flags'] == [SIZE_LABEL]
    assert marginals_of(result)[A]['n_employers'] == 1


def test_each_ein_counts_once():
    result = run([rec(A, 2023), rec(A, 2024), rec(A, 2024, establishment_id=7),
                  rec(B, 2023), rec(B, 2024)])
    assert cells(result)[A, B]['n_unweighted'] == 1
    assert marginals_of(result)[A]['n_employers'] == 1
    assert marginals_of(result)[A]['n_records'] == 3


def test_repeated_records_and_years_add_no_employer_weight():
    result = run([rec(A, 2023), rec(A, 2024), rec(A, 2024, establishment_id=7),
                  rec(B, 2023), rec(B, 2024)])
    assert [support_of(result)[A, B][f'j_{year}'] for year in YEARS] == [1, 1, 0]
    assert support_of(result)[A, B]['j_including_padded'] == 1
    assert marginals_of(result) == {
        A: {
            'node_id': leaf(A),
            'n_employers': 1,
            'n_multi_industry_employers': 1,
            'n_records': 3,
            'n_employers_including_padded': 1,
            'n_employers_partial': 0,
        },
        B: {
            'node_id': leaf(B),
            'n_employers': 1,
            'n_multi_industry_employers': 1,
            'n_records': 2,
            'n_employers_including_padded': 1,
            'n_employers_partial': 0,
        },
    }
    assert result.report['N'] == 1


def test_exact_duplicate_records_add_no_weight():
    duplicate = rec(A, id=1, establishment_id=100)
    result = run([duplicate, duplicate, rec(B, establishment_id=100), rec(B, ein='100000002')])
    assert cells(result)[A, B]['n_unweighted'] == 1
    assert cells(result)[A, B]['value'] == 1.0
    assert cells(result)[B, A]['value'] == 0.5
    assert support_of(result)[A, B]['j_2023'] == 1
    assert marginals_of(result)[A]['n_employers'] == 1
    assert marginals_of(result)[A]['n_records'] == 2
    assert marginals_of(result)[B]['n_records'] == 2


def test_mirror_rows_and_values():
    rows = cells(run(MIRROR))
    assert set(rows) == {(A, B), (B, A), (A, C), (C, A)}
    assert rows[A, B]['value'] == pytest.approx(2 / 3, abs=TOLERANCE)
    assert rows[B, A]['value'] == 1.0
    assert rows[A, C]['value'] == pytest.approx(1 / 3, abs=TOLERANCE)
    assert rows[C, A]['value'] == 1.0
    assert all(a != b for a, b in rows)


def test_target_rows_follow_the_contract():
    targets = run(MIRROR).targets.collect()
    assert list(targets.schema.items()) == list(TARGET_SCHEMA.items())
    for row in targets.to_dicts():
        assert row['source'] == 'osha_ita'
        assert row['family'] == 'co_ownership'
        assert row['unit_a_type'] == 'naics_national_industry'
        assert row['unit_b_type'] == 'naics_national_industry'
        assert row['measure'] == 'employer_share'
        assert row['se'] is None
        assert row['se_method'] == 'none'
        assert row['sample_set'] == 'ita_300a_2023_2025'
        assert row['vintage'] == 'naics=2022'
        assert row['universe'] == UNIVERSE
        assert row['flags'] == ['size_gate_pending']
        assert row['n_weighted'] == float(row['n_unweighted'])
    assert targets.select('unit_a', 'unit_b', 'n_unweighted', 'n_weighted').rows() == [
        (leaf(A), leaf(C), 1, 1.0),
        (leaf(A), leaf(B), 2, 2.0),
        (leaf(C), leaf(A), 1, 1.0),
        (leaf(B), leaf(A), 2, 2.0),
    ]


def test_ein_spellings_count_once():
    result = run([
        rec(A, ein='12-3456789'),
        rec(B, ein='123456789'),
        rec(A, ein='023456789'),
        rec(B, ein='23456789'),
    ])
    assert cells(result)[A, B]['n_unweighted'] == 1
    assert support_of(result)[A, B]['j_including_padded'] == 2
    assert PADDED_LABEL in cells(result)[A, B]['flags']
    assert PADDED_LABEL in cells(result)[B, A]['flags']
    assert result.report['N'] == 2
    assert marginals_of(result)[A]['n_employers'] == 2
    assert marginals_of(result)[B]['n_employers'] == 1


def test_company_names_never_establish_co_ownership():
    result = run([
        rec(A, ein=None, company_name='Acme'),
        rec(B, ein='', company_name='Acme'),
        rec(C, ein='111111111', company_name='Acme'),
        rec(D, ein='100000001', company_name='Acme'),
    ])
    assert result.targets.collect().is_empty()
    assert result.support.collect().is_empty()
    assert set(marginals_of(result)) == {D}
    assert result.report['N'] == 1
    assert result.report['N_including_padded'] == 1
    assert result.report['n_sensitivity_only_cells'] == 0


def test_company_names_alone_give_no_employer():
    result = run([rec(A, ein=None, company_name='Acme'), rec(B, ein=None, company_name='Acme')])
    assert result.targets.collect().is_empty()
    assert result.marginals.collect().is_empty()
    assert result.report['N'] == 0


def test_spaced_ein_spelling_is_the_same_employer():
    result = run([rec(A, ein=' 123456789 '), rec(B, ein='12-3456789')])
    assert cells(result)[A, B]['n_unweighted'] == 1
    assert result.report['N'] == 1


def test_padded_sensitivity_flags_and_counts():
    result = run(PADDED)
    rows = cells(result)
    assert set(rows) == {(A, B), (B, A), (A, C), (C, A)}
    assert rows[A, B]['flags'] == [PADDED_LABEL, SIZE_LABEL]
    assert rows[B, A]['flags'] == [PADDED_LABEL, SIZE_LABEL]
    assert rows[A, C]['flags'] == [SIZE_LABEL]
    assert rows[C, A]['flags'] == [SIZE_LABEL]
    assert rows[A, B]['n_unweighted'] == 1
    assert [rows[key]['value'] for key in ((A, B), (B, A), (A, C), (C, A))] == [0.5, 1, 0.5, 1]
    assert {key: row['j_including_padded'] for key, row in support_of(result).items()} == {
        (A, B): 2,
        (B, A): 2,
        (A, C): 1,
        (C, A): 1,
    }
    marginals = marginals_of(result)
    assert set(marginals) == {A, B, C}
    assert [marginals[code]['n_employers'] for code in (A, B, C)] == [2, 1, 1]
    assert [marginals[code]['n_employers_including_padded'] for code in (A, B, C)] == [3, 2, 1]
    assert [marginals[code]['n_records'] for code in (A, B, C)] == [2, 1, 1]
    report = result.report
    assert report['N'] == 2
    assert report['N_including_padded'] == 3
    assert report['n_cells'] == 4
    assert report['n_cells_padded_label'] == 2
    assert report['n_sensitivity_only_cells'] == 8
    assert report['n_padded_only_nodes'] == 2


def test_cells_carry_no_partial_or_record_flag_label():
    result = run([
        rec(A, ein='100000001', flag_employment=True),
        rec(B, ein='100000001', flag_employment=True),
        rec(year=2023, ein='100000001', mapping=CROSSWALKED),
    ])
    assert marginals_of(result)[A]['n_employers_partial'] == 1
    assert [row['flags'] for row in cells(result).values()] == [[SIZE_LABEL], [SIZE_LABEL]]


def test_padded_records_outside_the_population_stay_out_of_the_sensitivity():
    result = run([
        rec(A, ein='023456789'),
        rec(mapping=CROSSWALKED, ein='23456789'),
        rec(A, 2022, ein='23456789'),
        rec(B, 2022, ein='23456789'),
        rec(B, ein='00000000'),
        rec(C, ein='00000000'),
    ])
    assert result.targets.collect().is_empty()
    assert result.support.collect().is_empty()
    report = result.report
    assert report['N'] == 1
    assert report['N_including_padded'] == 1
    assert report['n_sensitivity_only_cells'] == 0
    assert report['n_padded_only_nodes'] == 0
    assert marginals_of(result)[A]['n_employers_including_padded'] == 1


def test_a_null_padded_flag_is_not_eligible():
    records = keyed([rec(A), rec(B)]).with_columns(
        pl.when(pl.col('source_row').eq(1))
        .then(None)
        .otherwise(pl.col('flag_ein_padded'))
        .alias('flag_ein_padded')
    )
    result = estimate(records)
    (entry,) = result.report['partition_by_year']
    assert (entry['eligible'], entry['ein_padded']) == (1, 1)
    assert result.targets.collect().is_empty()
    assert set(marginals_of(result)) == {A}


def test_multi_industry_needs_the_industry_in_that_year():
    result = run([
        rec(A, 2023, ein='100000001'),
        rec(B, 2024, ein='100000001'),
        rec(C, 2024, ein='100000001'),
        rec(A, 2023, ein='100000002'),
        rec(D, 2023, ein='100000002'),
        rec(A, 2024, ein='100000002'),
        rec(D, 2024, ein='100000002'),
    ])
    multi = {code: row['n_multi_industry_employers'] for code, row in marginals_of(result).items()}
    assert multi == {A: 1, B: 1, C: 1, D: 1}
    assert marginals_of(result)[A]['n_employers'] == 2


def test_partial_industry_sets():
    result = run([
        rec(A, 2023, ein='100000001'),
        rec(year=2023, ein='100000001', mapping=CROSSWALKED),
        rec(A, 2023, ein='100000002'),
        rec(year=2024, ein='100000002', mapping=CROSSWALKED),
    ])
    assert marginals_of(result)[A]['n_employers'] == 2
    assert marginals_of(result)[A]['n_employers_partial'] == 1


def test_partial_needs_an_unpadded_same_key_record_in_a_year_of_the_industry():
    result = run([
        # Padded spelling of the same key: not partial.
        rec(A, 2023, ein='023456789'),
        rec(year=2023, ein='23456789', mapping=AMBIGUOUS),
        # Another spelling of the same key, in two years: partial once.
        rec(A, 2023, ein='98-7654321'),
        rec(A, 2024, ein='98-7654321'),
        rec(year=2023, ein='987654321', mapping=CROSSWALKED),
        rec(year=2024, ein='987654321', mapping=INVALID),
        # Ineligible only in the year of B: partial in B, not in A.
        rec(A, 2023, ein='100000003'),
        rec(B, 2024, ein='100000003'),
        rec(year=2024, ein='100000003', mapping=MISSING),
        # An ineligible record without a usable EIN is nobody's.
        rec(A, 2023, ein='100000004'),
        rec(year=2023, ein=None, mapping=CROSSWALKED),
        # A padded eligible-industry record of the same key is not ineligible.
        rec(A, 2023, ein='034567890'),
        rec(B, 2023, ein='34567890'),
    ])
    marginals = marginals_of(result)
    assert marginals[A]['n_employers'] == 5
    assert marginals[A]['n_employers_partial'] == 1
    assert marginals[B]['n_employers_partial'] == 1


@pytest.mark.parametrize(
    'row, reason',
    [
        pytest.param(rec(), 'eligible', id='plain-ein'),
        pytest.param(rec(ein='12-3456789'), 'eligible', id='hyphenated-ein'),
        pytest.param(rec(ein=' 123456789 '), 'eligible', id='spaced-ein'),
        pytest.param(rec(year=2023), 'eligible', id='year-2023'),
        pytest.param(rec(year=2024), 'eligible', id='year-2024'),
        pytest.param(rec(year=2025), 'eligible', id='year-2025'),
        pytest.param(rec(year=2022), 'year_outside_window', id='year-2022'),
        pytest.param(rec(year=2026), 'year_outside_window', id='year-2026'),
        pytest.param(rec(year=None), 'year_outside_window', id='year-null'),
        pytest.param(rec(mapping=CROSSWALKED), 'industry_ineligible', id='crosswalked-node'),
        pytest.param(rec(mapping=AMBIGUOUS), 'industry_ineligible', id='ambiguous'),
        pytest.param(rec(mapping=UNKNOWN_VINTAGE), 'industry_ineligible', id='unknown-vintage'),
        pytest.param(rec(mapping=INVALID), 'industry_ineligible', id='invalid-native'),
        pytest.param(rec(mapping=MISSING), 'industry_ineligible', id='missing-code'),
        pytest.param(rec(ein=None), 'ein_unusable', id='null-ein'),
        pytest.param(rec(ein=''), 'ein_unusable', id='blank-ein'),
        pytest.param(rec(ein='111111111'), 'ein_unusable', id='same-digit-ein'),
        pytest.param(rec(ein='12-34567AB'), 'ein_unusable', id='letters-ein'),
        pytest.param(rec(ein='23456789'), 'ein_padded', id='padded-ein'),
        pytest.param(rec(ein='2-3456789'), 'ein_padded', id='hyphenated-padded-ein'),
        pytest.param(rec(year=2022, mapping=CROSSWALKED), 'year_outside_window',
                     id='outside-and-ineligible'),
        pytest.param(rec(year=2026, ein=None), 'year_outside_window', id='outside-and-unusable'),
        pytest.param(rec(year=2022, ein='23456789'), 'year_outside_window',
                     id='outside-and-padded'),
        pytest.param(rec(mapping=CROSSWALKED, ein=None), 'industry_ineligible',
                     id='ineligible-and-unusable'),
        pytest.param(rec(mapping=CROSSWALKED, ein='23456789'), 'industry_ineligible',
                     id='ineligible-and-padded'),
        pytest.param(rec(ein='00000000'), 'ein_unusable', id='unusable-and-padded'),
    ],
)
def test_each_record_gets_its_first_reason(row, reason):
    assert reason_of(row) == reason


def test_exclusion_partition():
    rows = [
        rec(A, 2022),
        rec(year=2023, mapping=CROSSWALKED),
        rec(A, 2024, ein=None),
        rec(A, 2025, ein='23456789'),
        rec(A, 2023),
    ]
    partition = run(rows).report['partition_by_year']
    assert partition == [
        {'year_filing_for': 2022, 'year_outside_window': 1, 'industry_ineligible': 0,
         'ein_unusable': 0, 'ein_padded': 0, 'eligible': 0},
        {'year_filing_for': 2023, 'year_outside_window': 0, 'industry_ineligible': 1,
         'ein_unusable': 0, 'ein_padded': 0, 'eligible': 1},
        {'year_filing_for': 2024, 'year_outside_window': 0, 'industry_ineligible': 0,
         'ein_unusable': 1, 'ein_padded': 0, 'eligible': 0},
        {'year_filing_for': 2025, 'year_outside_window': 0, 'industry_ineligible': 0,
         'ein_unusable': 0, 'ein_padded': 1, 'eligible': 0},
    ]
    assert sum(entry[name] for entry in partition for name in REASONS) == len(rows)


def test_partition_lists_every_year_in_order_with_its_columns():
    rows = [rec(A, 2025), rec(A, 2016), rec(A, None), rec(A, 2016), rec(A, 2023)]
    partition = run(rows).report['partition_by_year']
    assert [entry['year_filing_for'] for entry in partition] == [None, 2016, 2023, 2025]
    assert all(list(entry) == ['year_filing_for', *REASONS] for entry in partition)
    assert [entry['year_outside_window'] for entry in partition] == [1, 2, 0, 0]
    assert [entry['eligible'] for entry in partition] == [0, 0, 1, 1]


def test_eligible_flags_by_year():
    flags = dict.fromkeys(RECORD_FLAGS, True)
    rows = [
        rec(A, 2023, **flags),
        rec(A, 2023, **dict.fromkeys(RECORD_FLAGS, None)),
        rec(A, 2023),
        rec(A, 2025, flag_employment=True, naics_year_from_dictionary=None),
        rec(A, 2022, **flags),
        rec(year=2024, mapping=CROSSWALKED, **flags),
        rec(A, 2024, ein='23456789', **flags),
    ]
    report = run(rows).report['eligible_flags_by_year']
    assert [(entry['year_filing_for'], entry['flag_name']) for entry in report] == [
        (year, flag) for year in YEARS for flag in RECORD_FLAGS
    ]
    assert all(list(entry) == ['year_filing_for', 'flag_name', 'n_true', 'n_null']
               for entry in report)
    counts = {(entry['year_filing_for'], entry['flag_name']): (entry['n_true'], entry['n_null'])
              for entry in report}
    assert all(counts[2023, flag] == (1, 1) for flag in RECORD_FLAGS)
    assert all(counts[2024, flag] == (0, 0) for flag in RECORD_FLAGS)
    assert counts[2025, 'flag_employment'] == (1, 0)
    assert counts[2025, 'naics_year_from_dictionary'] == (0, 1)
    assert counts[2025, 'flag_hours_per_employee'] == (0, 0)


def test_report_keys_and_distributions():
    result = run(NESTED)
    report = result.report
    assert list(report) == [
        'N',
        'N_including_padded',
        'partition_by_year',
        'eligible_flags_by_year',
        'n_cells',
        'n_cells_padded_label',
        'n_sensitivity_only_cells',
        'n_padded_only_nodes',
        'cell_count_distribution',
        'marginal_employer_distribution',
    ]
    assert report['N'] == 5
    assert report['N_including_padded'] == 5
    assert report['n_cells'] == 20
    assert report['n_cells_padded_label'] == 0
    assert report['n_sensitivity_only_cells'] == 0
    assert report['n_padded_only_nodes'] == 0
    assert report['cell_count_distribution'] == {
        'count': 20, 'min': 1, 'p25': 1, 'median': 2.0, 'p75': 3, 'p95': 4, 'max': 4,
    }
    assert report['marginal_employer_distribution'] == {
        'count': 5, 'min': 1, 'p25': 2, 'median': 3.0, 'p75': 4, 'p95': 5, 'max': 5,
    }
    marginals = marginals_of(result)
    assert [marginals[code]['n_employers'] for code in (A, B, C, D, E)] == [5, 4, 3, 2, 1]
    assert [marginals[code]['n_records'] for code in (A, B, C, D, E)] == [6, 4, 3, 2, 1]
    assert marginals[A]['n_multi_industry_employers'] == 4
    rows = cells(result)
    assert rows[A, E]['value'] == pytest.approx(1 / 5, abs=TOLERANCE)
    assert rows[E, A]['value'] == 1.0
    assert rows[B, C]['n_unweighted'] == 3
    assert rows[B, C]['value'] == pytest.approx(3 / 4, abs=TOLERANCE)


def test_no_eligible_records_give_empty_tables():
    for rows in ([], [rec(A, 2022), rec(B, 2023, ein=None)]):
        result = run(rows)
        targets, marginals, support = tables(result)
        assert list(targets.schema.items()) == list(TARGET_SCHEMA.items())
        assert list(marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
        assert list(support.schema.items()) == list(SUPPORT_SCHEMA.items())
        assert (targets.height, marginals.height, support.height) == (0, 0, 0)
        assert result.report['N'] == 0
        assert result.report['n_cells'] == 0
        assert result.report['cell_count_distribution'] == {
            'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p95': None,
            'max': None,
        }
        assert len(result.report['eligible_flags_by_year']) == len(YEARS) * len(RECORD_FLAGS)
        validate_co_ownership(result, NODES)
    assert run([]).report['partition_by_year'] == []


def test_tables_are_sorted_whatever_the_record_order():
    # Reverse eagerly: a lazy sort ahead of an unordered step can be dropped.
    records = keyed(NESTED).collect().reverse().lazy()
    targets, marginals, support = tables(estimate(records))
    assert targets.height == 20
    assert targets.equals(targets.sort(TARGET_KEY_COLUMNS))
    assert targets.select('unit_a', 'unit_b').equals(support.select('unit_a', 'unit_b'))
    assert support.equals(support.sort('unit_a', 'unit_b'))
    assert marginals['node_id'].to_list() == [leaf(code) for code in sorted((A, B, C, D, E))]


@pytest.mark.parametrize(
    'transform',
    [
        pytest.param(lambda lf: lf.drop('ein_key'), id='missing-ein-key'),
        pytest.param(lambda lf: lf.drop('naics_year_from_dictionary'), id='missing-record-flag'),
        pytest.param(lambda lf: lf.drop('flag_naics_unresolved'), id='missing-industry-flag'),
        pytest.param(lambda lf: lf.with_columns(pl.col('flag_ein_padded').cast(pl.String)),
                     id='padded-flag-type'),
        pytest.param(lambda lf: lf.with_columns(pl.col('year_filing_for').cast(pl.Int32)),
                     id='year-type'),
    ],
)
def test_estimate_refuses_records_without_the_keyed_columns(transform):
    with pytest.raises(ValueError, match='^co-ownership needs keyed records$'):
        estimate(transform(keyed(MIRROR)))


def test_targets_pass_shared_writer(tmp_path):
    result = run(VALID)
    record = target_contract.write_targets(result.targets, tmp_path / 'ita_co_ownership.parquet')
    assert record['rows'] == 4
    written = pl.read_parquet(tmp_path / 'ita_co_ownership.parquet')
    assert written.equals(result.targets.collect())


@pytest.mark.parametrize(
    'rows',
    [
        pytest.param(MIRROR, id='mirror'),
        pytest.param(VALID, id='valid'),
        pytest.param(PADDED, id='padded'),
        pytest.param(NESTED, id='nested'),
    ],
)
def test_validator_accepts_the_build(rows):
    validate_co_ownership(run(rows), NODES_WITH_DECOYS)


def message(text):
    return '^' + re.escape(text) + '$'


def edit(frame, where, **changes):
    '''A copy of `frame` with `changes` applied to the rows matching every `where` item.'''
    rows = frame.to_dicts()
    hits = [row for row in rows if all(row[key] == value for key, value in where.items())]
    assert hits
    for row in hits:
        row.update(changes)
    return pl.DataFrame(rows, schema=frame.schema, orient='row')


def cell(a, b):
    return {'unit_a': leaf(a), 'unit_b': leaf(b)}


def node(code):
    return {'node_id': leaf(code)}


def matching(where):
    condition = pl.lit(True)
    for key, value in where.items():
        condition = condition.and_(pl.col(key).eq(value))
    return condition


def only(frame, where):
    return frame.filter(matching(where))


def without(frame, where):
    return frame.filter(matching(where).not_())


def rebuilt(result, targets, marginals, support):
    return replace(result, targets=targets.lazy(), marginals=marginals.lazy(),
                   support=support.lazy())


def broken(change):
    result = run(VALID)
    return rebuilt(result, *change(*tables(result)))


def test_validator_rejects_broken_mirror():
    result = broken(lambda t, m, s: (without(t, cell(B, A)), m, without(s, cell(B, A))))
    with pytest.raises(ValueError, match=message('co-ownership cells lack an equal mirror')):
        validate_co_ownership(result, NODES_WITH_DECOYS)


def test_validator_rejects_value_mismatch():
    result = broken(lambda t, m, s: (edit(t, cell(A, B), value=0.5), m, s))
    with pytest.raises(ValueError, match=message('co-ownership values differ from the shares')):
        validate_co_ownership(result, NODES_WITH_DECOYS)


def test_validator_accepts_a_value_within_tolerance():
    result = run(VALID)
    targets, marginals, support = tables(result)
    nudged = edit(targets, cell(A, B), value=2 / 3 + 1e-13)
    assert nudged['value'].ne(targets['value']).sum() == 1
    validate_co_ownership(rebuilt(result, nudged, marginals, support), NODES_WITH_DECOYS)


def test_validator_refuses_nodes_with_another_schema():
    with pytest.raises(ValueError, match=message('nodes do not have the node schema')):
        validate_co_ownership(run(VALID), NODES.drop('level'))


TARGETS_SCHEMA = 'targets schema must match exact ordered targets-v1 types'
COMPANIONS = 'co-ownership companion schemas differ'
METADATA_DIFFERS = 'co-ownership rows differ from the metadata'
UNITS = 'co-ownership units are not two distinct NAICS 2022 national industries'
MIRRORS = 'co-ownership cells lack an equal mirror'
COUNTS = 'co-ownership counts are invalid'
VALUES = 'co-ownership values differ from the shares'
EXCEEDS = 'co-ownership counts exceed a marginal'
SUPPORT_KEYS = 'co-ownership support does not match the targets one to one'
SUPPORT_COUNTS = 'co-ownership support counts disagree with the targets'
PADDED_BELOW = 'co-ownership padded counts fall below J'
FLAGS = 'co-ownership flags disagree with the support'
MARGINAL_KEYS = 'co-ownership marginal nodes repeat'
NULL_NODES = 'co-ownership marginal nodes are null'
BOUNDS = 'co-ownership marginal counts are out of bounds'
MULTI = 'co-ownership multi-industry counts disagree with the targets'
AB, BA, AC, CA = cell(A, B), cell(B, A), cell(A, C), cell(C, A)
BROKEN = {
    'targets-schema': (lambda t, m, s: (t.drop('universe'), m, s), TARGETS_SCHEMA),
    'targets-se': (lambda t, m, s: (edit(t, AB, se=0.0), m, s),
                   'targets contain invalid standard error'),
    'marginals-column-order': (lambda t, m, s: (t, m.select(reversed(m.columns)), s),
                               COMPANIONS),
    'support-dtype': (lambda t, m, s: (t, m, s.with_columns(pl.col('j_2023').cast(pl.Int64))),
                      COMPANIONS),
    'metadata-source': (lambda t, m, s: (edit(t, AB, source='osha'), m, s), METADATA_DIFFERS),
    'metadata-family': (lambda t, m, s: (edit(t, AB, family='area_mix'), m, s),
                        METADATA_DIFFERS),
    'metadata-measure': (lambda t, m, s: (edit(t, AB, measure='establishment_share'), m, s),
                         METADATA_DIFFERS),
    'metadata-sample-set': (lambda t, m, s: (edit(t, AB, sample_set='ita_300a_2023'), m, s),
                            METADATA_DIFFERS),
    'metadata-vintage': (lambda t, m, s: (edit(t, AB, vintage='naics=2017'), m, s),
                         METADATA_DIFFERS),
    'metadata-universe': (lambda t, m, s: (edit(t, AB, universe='Another statement.'), m, s),
                          METADATA_DIFFERS),
    'metadata-se-method': (lambda t, m, s: (edit(t, AB, se_method='replicate', se=0.0), m, s),
                           METADATA_DIFFERS),
    'metadata-unit-a-type': (
        lambda t, m, s: (edit(t, AB, unit_a_type='naics_industry',
                              unit_a='naics:2022:industry:23822'), m, s),
        METADATA_DIFFERS,
    ),
    'metadata-unit-b-type': (
        lambda t, m, s: (edit(t, AB, unit_b_type='naics_industry',
                              unit_b='naics:2022:industry:72251'), m, s),
        METADATA_DIFFERS,
    ),
    'unit-absent': (lambda t, m, s: (edit(t, AB, unit_b='naics:2022:national_industry:999999'),
                                     m, s), UNITS),
    'unit-other-vintage': (
        lambda t, m, s: (edit(t, BA, unit_b='naics:2017:national_industry:238220'), m, s),
        UNITS,
    ),
    'unit-other-level': (
        lambda t, m, s: (edit(t, AB, unit_a='naics:2022:national_industry:999998'), m, s),
        UNITS,
    ),
    'unit-other-system': (
        lambda t, m, s: (edit(t, AB, unit_b='naics:2022:national_industry:999997'), m, s),
        UNITS,
    ),
    'diagonal': (lambda t, m, s: (edit(t, AB, unit_b=leaf(A)), m, s), UNITS),
    'mirror-unequal': (lambda t, m, s: (edit(t, BA, n_unweighted=1), m, s), MIRRORS),
    'count-zero': (
        lambda t, m, s: (edit(edit(t, AC, n_unweighted=0, n_weighted=0.0), CA,
                              n_unweighted=0, n_weighted=0.0), m, s),
        COUNTS,
    ),
    'weighted-count': (lambda t, m, s: (edit(t, AB, n_weighted=2.5), m, s), COUNTS),
    'value-beyond-tolerance': (lambda t, m, s: (edit(t, AB, value=2 / 3 + 1e-11), m, s),
                               VALUES),
    'marginal-missing': (lambda t, m, s: (t, without(m, node(C)), s), VALUES),
    'exceeds-marginal': (
        lambda t, m, s: (edit(t, BA, value=2.0), edit(m, node(B), n_employers=1), s),
        EXCEEDS,
    ),
    'support-missing': (lambda t, m, s: (t, m, without(s, AB)), SUPPORT_KEYS),
    'support-extra': (lambda t, m, s: (t, m, pl.concat([s, edit(only(s, AB), AB, **cell(B, C))])),
                      SUPPORT_KEYS),
    'support-repeated': (lambda t, m, s: (t, m, pl.concat([s, s.head(1)])), SUPPORT_KEYS),
    'support-j': (lambda t, m, s: (t, m, edit(s, AB, j_employers=1)), SUPPORT_COUNTS),
    'support-year-above': (lambda t, m, s: (t, m, edit(s, AB, j_2024=3)), SUPPORT_COUNTS),
    'support-years-below': (lambda t, m, s: (t, m, edit(s, AB, j_2023=1)), SUPPORT_COUNTS),
    'support-year-null': (lambda t, m, s: (t, m, edit(s, AB, j_2024=None)), SUPPORT_COUNTS),
    'support-years-null': (lambda t, m, s: (t, m, edit(s, AB, j_2024=None, j_2025=None)),
                           SUPPORT_COUNTS),
    'support-j-null': (lambda t, m, s: (t, m, edit(s, AB, j_employers=None)), SUPPORT_COUNTS),
    'support-padded-null': (lambda t, m, s: (t, m, edit(s, AB, j_including_padded=None)),
                            PADDED_BELOW),
    'padded-below': (lambda t, m, s: (t, m, edit(s, AB, j_including_padded=1)), PADDED_BELOW),
    'label-missing': (lambda t, m, s: (edit(t, AC, flags=[SIZE_LABEL]), m, s), FLAGS),
    'label-extra': (lambda t, m, s: (edit(t, AB, flags=[PADDED_LABEL, SIZE_LABEL]), m, s),
                    FLAGS),
    'size-missing': (lambda t, m, s: (edit(t, AB, flags=[]), m, s), FLAGS),
    'size-missing-padded': (lambda t, m, s: (edit(t, AC, flags=[PADDED_LABEL]), m, s), FLAGS),
    'unknown-label': (lambda t, m, s: (edit(t, AB, flags=['other_label', SIZE_LABEL]), m, s),
                      FLAGS),
    'marginal-repeated': (lambda t, m, s: (t, pl.concat([m, only(m, node(D))]), s),
                          MARGINAL_KEYS),
    'marginal-zero': (lambda t, m, s: (t, edit(m, node(D), n_employers=0), s), BOUNDS),
    'multi-above': (lambda t, m, s: (t, edit(m, node(A), n_multi_industry_employers=4), s),
                    BOUNDS),
    'partial-above': (lambda t, m, s: (t, edit(m, node(A), n_employers_partial=4), s), BOUNDS),
    'padded-marginal-below': (
        lambda t, m, s: (t, edit(m, node(A), n_employers_including_padded=2), s),
        BOUNDS,
    ),
    'marginal-null': (lambda t, m, s: (t, edit(m, node(A), n_employers_partial=None), s),
                      BOUNDS),
    'records-null': (lambda t, m, s: (t, edit(m, node(A), n_records=None), s), BOUNDS),
    'employers-null': (lambda t, m, s: (t, edit(m, node(D), n_employers=None), s), BOUNDS),
    'multi-null': (lambda t, m, s: (t, edit(m, node(D), n_multi_industry_employers=None), s),
                   BOUNDS),
    'padded-marginal-null': (
        lambda t, m, s: (t, edit(m, node(A), n_employers_including_padded=None), s),
        BOUNDS,
    ),
    'records-zero': (lambda t, m, s: (t, edit(m, node(A), n_records=0), s), BOUNDS),
    'records-below-employers': (lambda t, m, s: (t, edit(m, node(A), n_records=2), s), BOUNDS),
    'marginal-node-null': (
        lambda t, m, s: (t, pl.concat([m, edit(only(m, node(D)), node(D), node_id=None)]), s),
        NULL_NODES,
    ),
    'multi-below-cell': (lambda t, m, s: (t, edit(m, node(B), n_multi_industry_employers=1), s),
                         MULTI),
    'multi-without-cell': (
        lambda t, m, s: (t, edit(m, node(D), n_multi_industry_employers=1), s),
        MULTI,
    ),
}


@pytest.mark.parametrize('case', list(BROKEN))
def test_validator_rejects_a_broken_table(case):
    change, reason = BROKEN[case]
    with pytest.raises(ValueError, match=message(reason)):
        validate_co_ownership(broken(change), NODES_WITH_DECOYS)


def test_valid_fixture_is_the_one_the_broken_tables_assume():
    result = run(VALID)
    rows = cells(result)
    assert {key: (row['n_unweighted'], row['flags']) for key, row in rows.items()} == {
        (A, B): (2, [SIZE_LABEL]),
        (B, A): (2, [SIZE_LABEL]),
        (A, C): (1, [PADDED_LABEL, SIZE_LABEL]),
        (C, A): (1, [PADDED_LABEL, SIZE_LABEL]),
    }
    assert rows[C, A]['value'] == 0.5
    multi = {code: row['n_multi_industry_employers'] for code, row in marginals_of(result).items()}
    assert multi == {A: 3, B: 2, C: 1, D: 0}
    assert {key: row['j_including_padded'] for key, row in support_of(result).items()} == {
        (A, B): 2, (B, A): 2, (A, C): 2, (C, A): 2,
    }
    assert marginals_of(result)[A]['n_employers_including_padded'] == 4


def test_module_loads_no_ipums_or_dotenv_module():
    code = ('import sys; import embedding_data.ita_co_ownership as m; '
            'bad = [n for n in sys.modules if n.split(".")[0] in {"dotenv", "ipumspy"} '
            'or n.startswith(("embedding_data.ipums", "embedding_data.acs"))]; '
            'sys.exit(1 if bad else 0)')
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
