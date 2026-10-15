import polars as pl
import pytest

from embedding_data.ipums_industry import industry_frequencies

def lists():
    return {2017: pl.DataFrame({'code': ['1110', '2220'], 'title': ['Shared old', 'Old']}),
            2022: pl.DataFrame({'code': ['1110', '3330'], 'title': ['Shared new', 'New']})}


def test_year_field_membership_and_original_dictionary_meaning():
    frame = pl.DataFrame({'YEAR': [2025] * 7 + [2026],
                          'IND': ['1110', '2220', '3330', '0000', '9999', '110', None, '1110'],
                          'INDLY': ['1110'] * 8}).lazy()
    ddi = {'variables': [{'name': 'IND', 'categories': [
        {'value': '0000', 'label': 'NIU'}, {'value': '1110', 'label': 'Delivered meaning'}],
        'instructions': ['Source codes are harmonized; vintage unspecified.']}]}
    result = industry_frequencies(frame, ddi, lists())
    ind = {row['code']: row for row in result.filter(
        pl.col('variable').eq('IND').and_(pl.col('year').eq(2025))).to_dicts()}
    assert ind['1110']['membership'] == 'shared_ambiguous'
    assert ind['2220']['membership'] == '2017_only'
    assert ind['3330']['membership'] == '2022_only'
    assert ind['0000']['membership'] == 'documented_special'
    assert ind['9999']['membership'] == 'outside'
    assert ind['110']['membership'] == 'malformed'
    assert ind[None]['membership'] == 'missing'
    assert ind['1110']['ddi_label'] == 'Delivered meaning'
    assert ind['1110']['label_2017'] == 'Shared old'
    assert ind['1110']['label_2022'] == 'Shared new'
    assert ind['2220']['stage11_compatibility_required'] is True
    assert result['rows'].sum() == 16
    assert result['native_vintage'].null_count() == result.height
    assert result.filter(pl.col('variable').eq('INDLY'))['rows'].to_list() == [7, 1]


def test_shared_codes_alone_never_prove_native_vintage():
    result = industry_frequencies(pl.DataFrame({'YEAR': [2026], 'IND': ['1110'],
                                                'INDLY': ['1110']}).lazy(),
                                  {'variables': []}, lists())
    assert result['membership'].to_list() == ['shared_ambiguous'] * 2
    assert result['native_verdict'].to_list() == ['unresolved'] * 2


def test_duplicate_reference_codes_rejected():
    references = lists()
    references[2017] = pl.concat([references[2017], references[2017]])
    with pytest.raises(ValueError, match='unique'):
        industry_frequencies(pl.DataFrame({'YEAR': [2025], 'IND': ['1110'],
                                           'INDLY': ['1110']}).lazy(), {}, references)


def test_ddi_integer_category_meaning_without_reinterpreting_delivered_codes():
    frame = pl.DataFrame({'YEAR': [2025, 2025], 'IND': ['0000', '0'],
                          'INDLY': ['1110', '1110']}).lazy()
    ddi = {'variables': [{'name': 'IND', 'categories': [{'value': '0', 'label': 'NIU'}]}]}
    result = industry_frequencies(frame, ddi, lists())
    proper = result.filter(pl.col('code').eq('0000'))
    assert proper['membership'].item() == 'documented_special'
    assert proper['ddi_value'].item() == '0'
    assert result.filter(pl.col('code').eq('0'))['membership'].item() == 'malformed'


def test_empty_industry_result_has_stable_schema():
    frame = pl.DataFrame(schema={'YEAR': pl.Int64, 'IND': pl.String, 'INDLY': pl.String})
    result = industry_frequencies(frame.lazy(), {}, lists())
    assert result.height == 0
    assert result.schema == {
        'year': pl.Int64, 'variable': pl.String, 'code': pl.String, 'rows': pl.UInt64,
        'ddi_value': pl.String, 'ddi_label': pl.String, 'documented_special': pl.Boolean,
        'in_2017': pl.Boolean, 'label_2017': pl.String, 'in_2022': pl.Boolean,
        'label_2022': pl.String, 'membership': pl.String, 'ddi_instructions': pl.String,
        'source_scheme_evidence': pl.String, 'delivered_harmonization_evidence': pl.String,
        'native_vintage': pl.Int64, 'native_verdict': pl.String,
        'stage11_compatibility_required': pl.Boolean,
    }
