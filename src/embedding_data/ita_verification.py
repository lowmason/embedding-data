'''Offline measurements for ITA text content and establishment linkage.'''

import re
import unicodedata

import polars as pl

PLACEHOLDERS = frozenset(
    {'n/a', 'na', 'none', 'unknown', 'not applicable', 'not specified', '-', '--', '.'}
)

def normalize_key(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())

def key(column: str) -> pl.Expr:
    return pl.col(column).fill_null('').map_elements(normalize_key, return_dtype=pl.String)

def ein_key(value: str) -> str | None:
    compact = value.strip().replace('-', '')
    if not re.fullmatch(r'[0-9]{8,9}', compact):
        return None
    padded = compact.zfill(9)
    return None if len(set(padded)) == 1 else padded

def zip_key(value: str) -> str | None:
    value = value.strip()
    if re.fullmatch(r'[0-9]{4,5}', value):
        return value.zfill(5)
    if re.fullmatch(r'[0-9]{9}|[0-9]{5}-[0-9]{4}', value):
        return value[:5]
    return None

def zip_format(value: str) -> str:
    value = value.strip()
    if not value:
        return 'missing'
    if re.fullmatch(r'[0-9]{5}', value):
        return 'five_digit'
    if re.fullmatch(r'[0-9]{4}', value):
        return 'padded_four_digit'
    if re.fullmatch(r'[0-9]{9}|[0-9]{5}-[0-9]{4}', value):
        return 'zip_plus_four'
    return 'invalid'

def with_keys(lf: pl.LazyFrame) -> pl.LazyFrame:
    '''Append matching keys and flags while preserving every source column.'''
    return (
        lf.with_columns(
            description_key=key('industry_description'),
            company_key=key('company_name'),
            name_key=key('establishment_name'),
            street_key=key('street_address'),
            city_key=key('city'),
            state_key=key('state'),
            ein_key=pl.col('ein').fill_null('').map_elements(ein_key, return_dtype=pl.String),
            zip_key=pl.col('zip_code').fill_null('').map_elements(zip_key, return_dtype=pl.String),
            zip_format=pl.col('zip_code').fill_null('').map_elements(
                zip_format, return_dtype=pl.String
            ),
            flag_ein_padded=pl.col('ein').fill_null('').str.strip_chars().str.replace_all('-', '')
            .str.contains(r'^[0-9]{8}$'),
            flag_suspected_mojibake=pl.col('industry_description').fill_null('').str.contains(
                'Ã|Â|�'
            ),
        ).with_columns(
            employer_key=pl.when(pl.col('ein_key').is_not_null()).then(
                pl.concat_str(pl.lit('ein:'), pl.col('ein_key'))
            ).when(pl.col('company_key').ne('')).then(
                pl.concat_str(pl.lit('company:'), pl.col('company_key'))
            ).otherwise(None),
            flag_empty=pl.col('description_key').eq(''),
            flag_placeholder=pl.col('description_key').is_in(PLACEHOLDERS),
            address_key=pl.when(
                pl.col('street_key').ne('').and_(pl.col('city_key').ne('')).and_(
                    pl.col('state_key').ne('')
                ).and_(pl.col('zip_key').is_not_null())
            ).then(pl.concat_str('street_key', 'city_key', 'state_key', 'zip_key',
                                 separator='|')).otherwise(None),
        )
    )

def description_report(lf: pl.LazyFrame, titles: pl.DataFrame) -> pl.DataFrame:
    '''Measure overlapping text flags and employer repetition by filing year.'''
    normalized_titles = titles.with_columns(title_key=key('title'))
    any_keys = normalized_titles['title_key'].unique().to_list()
    native = normalized_titles.select('vintage', 'title_key').unique().lazy()
    annotated = (
        with_keys(lf).with_columns(flag_copied_any=pl.col('description_key').is_in(any_keys)).join(
            native.with_columns(native_match=pl.lit(True)),
            left_on=['naics_year', 'description_key'],
            right_on=['vintage', 'title_key'],
            how='left',
            validate='m:1'
        )
    )
    repeats = (
        annotated.filter(
            pl.col('employer_key').is_not_null().and_(pl.col('description_key').ne(''))
        ).group_by('year_filing_for', 'employer_key', 'description_key').agg(n=pl.len()).group_by(
            'year_filing_for'
        ).agg(
            n_repeat_rows=pl.col('n').filter(pl.col('n').gt(1)).sum(),
            n_repeat_excess=pl.col('n').sub(1).sum(),
        )
    )
    length = pl.col('industry_description').fill_null('').str.len_chars()
    return (
        annotated.group_by('year_filing_for').agg(
            n_rows=pl.len(),
            n_empty=pl.col('flag_empty').sum(),
            n_placeholder=pl.col('flag_placeholder').sum(),
            n_copied_any=pl.col('flag_copied_any').sum(),
            n_native_title_match=pl.col('native_match').fill_null(False).sum(),
            n_vintage_unknown=pl.col('naics_year').is_null().sum(),
            n_employer_unknown=pl.col('employer_key').is_null().sum(),
            n_employer_company=pl.col('employer_key').str.starts_with('company:'
                                                                      ).fill_null(False).sum(),
            n_ein_padded=pl.col('flag_ein_padded').sum(),
            n_mojibake=pl.col('flag_suspected_mojibake').sum(),
            length_min=length.min(),
            length_p25=length.quantile(0.25, interpolation='nearest'),
            length_p50=length.quantile(0.50, interpolation='nearest'),
            length_p75=length.quantile(0.75, interpolation='nearest'),
            length_p95=length.quantile(0.95, interpolation='nearest'),
            length_max=length.max(),
        ).join(repeats, on='year_filing_for', how='left', validate='1:1').with_columns(
            pl.col('n_repeat_rows', 'n_repeat_excess').fill_null(0)
        ).with_columns(
            share_empty=pl.col('n_empty').truediv(pl.col('n_rows')),
            share_placeholder=pl.col('n_placeholder').truediv(pl.col('n_rows')),
            share_copied_any=pl.col('n_copied_any').truediv(pl.col('n_rows')),
            share_repeat_rows=pl.col('n_repeat_rows').truediv(pl.col('n_rows')),
            share_repeat_excess=pl.col('n_repeat_excess').truediv(pl.col('n_rows')),
            share_employer_unknown=pl.col('n_employer_unknown').truediv(pl.col('n_rows')),
            share_native_title_match=pl.when(pl.col('n_rows').gt(pl.col('n_vintage_unknown'))).then(
                pl.col('n_native_title_match').truediv(
                    pl.col('n_rows').sub(pl.col('n_vintage_unknown'))
                )
            ).otherwise(None),
        ).sort('year_filing_for').collect()
    )

def quality_report(lf: pl.LazyFrame) -> pl.DataFrame:
    '''Compare all source rows with exact duplicates collapsed by filing year.'''
    columns = lf.collect_schema().names()
    raw_counts = lf.group_by('year_filing_for').agg(n_rows=pl.len())
    unique_counts = lf.unique(subset=columns).group_by('year_filing_for').agg(
        n_distinct_rows=pl.len()
    )
    return (
        with_keys(lf).group_by('year_filing_for').agg(
            n_company_empty=pl.col('company_key').eq('').sum(),
            n_ein_unusable=pl.col('ein_key').is_null().sum(),
            n_zip_unusable=pl.col('zip_key').is_null().sum(),
            n_distinct_record_ids=pl.col('id').n_unique(),
            n_distinct_establishment_ids=pl.col('establishment_id').n_unique(),
        ).join(raw_counts, on='year_filing_for', validate='1:1'
               ).join(unique_counts, on='year_filing_for', validate='1:1').with_columns(
                   n_exact_duplicate_excess=pl.col('n_rows').sub(pl.col('n_distinct_rows'))
               ).sort('year_filing_for').collect()
    )

def unique_ids(lf: pl.LazyFrame, year: int) -> pl.LazyFrame:
    '''Retain IDs with one distinct source row after exact duplicate collapse.'''
    return (
        with_keys(lf.filter(pl.col('year_filing_for').eq(year)).unique()).with_columns(
            n_id_rows=pl.len().over('establishment_id'),
            # Competing rows remain evidence of ambiguity even when their IDs are excluded.
            n_address=pl.len().over(['ein_key', 'name_key', 'address_key']),
        ).filter(pl.col('n_id_rows').eq(1).and_(pl.col('establishment_id').is_not_null()))
    )

def link_report(lf: pl.LazyFrame, base_year: int, later_year: int) -> dict:
    '''Measure raw ID recurrence and conservative unambiguous linkage.'''
    columns = [
        'establishment_id', 'ein', 'ein_key', 'flag_ein_padded', 'name_key', 'address_key',
        'n_address'
    ]
    cohort = unique_ids(lf, base_year).select(columns)
    later = unique_ids(lf, later_year).select(columns)
    later = later.with_columns(id_present=pl.lit(True))
    joined = cohort.join(later, on='establishment_id', how='left', suffix='_later', validate='1:1')
    present = pl.col('id_present').fill_null(False)
    known_ein = pl.col('ein_key').is_not_null().and_(pl.col('ein_key_later').is_not_null())
    same = known_ein.and_(pl.col('ein_key').eq(pl.col('ein_key_later')))
    unreconstructed = pl.col('flag_ein_padded').not_().and_(pl.col('flag_ein_padded_later').not_())
    same_address = pl.col('address_key').is_not_null().and_(
        pl.col('address_key').eq(pl.col('address_key_later'))
    )
    counts = joined.select(
        n_unique_cohort_ids=pl.len(),
        n_reappeared=present.sum(),
        n_same_ein_address=same.and_(same_address).and_(unreconstructed).fill_null(False).sum(),
        n_same_ein_address_including_padded=same.and_(same_address).fill_null(False).sum(),
        n_same_raw_ein_address=same.and_(same_address).and_(pl.col('ein').eq(pl.col('ein_later'))
                                                            ).fill_null(False).sum(),
        n_reappeared_ein_unknown=present.and_(known_ein.not_()).sum(),
        n_reappeared_ein_conflict=present.and_(known_ein).and_(
            pl.col('ein_key').ne(pl.col('ein_key_later'))
        ).sum(),
        n_reappeared_address_conflict=present.and_(same_address.not_()).fill_null(False).sum(),
    ).collect().row(0, named=True)
    address_columns = ['ein_key', 'name_key', 'address_key']

    def unique_addresses(frame):
        return (
            frame.filter(
                pl.col('ein_key').is_not_null().and_(pl.col('flag_ein_padded').not_()).and_(
                    pl.col('address_key').is_not_null()
                ).and_(pl.col('name_key').ne(''))
            ).filter(pl.col('n_address').eq(1))
        )

    addresses = unique_addresses(cohort).join(
        unique_addresses(later),
        on=address_columns,
        how='inner',
        suffix='_later',
        validate='1:1',
    ).select(
        n_unique_address_matches=pl.len(),
        n_address_matches_different_id=pl.col('establishment_id').ne(
            pl.col('establishment_id_later')
        ).sum(),
    ).collect().row(0, named=True)
    cohort_rows = lf.filter(pl.col('year_filing_for').eq(base_year))
    later_rows = lf.filter(pl.col('year_filing_for').eq(later_year))
    missing_counts = {
        'n_base_missing_id_rows': cohort_rows.select(pl.col('establishment_id').is_null().sum()
                                                     ).collect().item(),
        'n_later_missing_id_rows': later_rows.select(pl.col('establishment_id').is_null().sum()
                                                     ).collect().item(),
    }
    cohort_ids = cohort_rows.filter(pl.col('establishment_id').is_not_null()).select(
        'establishment_id'
    ).unique()
    later_ids = later_rows.filter(pl.col('establishment_id').is_not_null()).select(
        'establishment_id'
    ).unique()
    n_ids = cohort_ids.select(pl.len()).collect().item()
    n_raw_reappeared = cohort_ids.join(later_ids, on='establishment_id',
                                       how='inner').select(pl.len()).collect().item()
    output = {
        'base_year': base_year,
        'later_year': later_year,
        'n_cohort_ids': n_ids,
        'n_raw_reappeared': n_raw_reappeared,
        **counts,
        **missing_counts,
        **addresses
    }
    output['share_raw_reappeared'] = n_raw_reappeared / n_ids if n_ids else None
    output['share_same_ein_address'] = counts['n_same_ein_address'] / n_ids if n_ids else None
    address_n = addresses['n_unique_address_matches']
    output['share_address_matches_different_id'
           ] = addresses['n_address_matches_different_id'] / address_n if address_n else None
    return output
