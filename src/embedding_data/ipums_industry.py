'''ASEC delivered-code frequencies and evidence, without guessing native vintages.'''

import json
import re

import polars as pl

SCHEMA = {
    'year': pl.Int64, 'variable': pl.String, 'code': pl.String, 'rows': pl.UInt64,
    'ddi_value': pl.String, 'ddi_label': pl.String, 'documented_special': pl.Boolean,
    'in_2017': pl.Boolean, 'label_2017': pl.String, 'in_2022': pl.Boolean,
    'label_2022': pl.String, 'membership': pl.String, 'ddi_instructions': pl.String,
    'source_scheme_evidence': pl.String, 'delivered_harmonization_evidence': pl.String,
    'native_vintage': pl.Int64, 'native_verdict': pl.String,
    'stage11_compatibility_required': pl.Boolean,
}
SPECIAL_LABEL = re.compile(
    r'\bNIU\b|not in universe|not applicable|unknown|unemployed|never worked',
                           re.IGNORECASE)


def industry_frequencies(frame: pl.LazyFrame, ddi: dict,
                         lists: dict[int, pl.DataFrame]) -> pl.DataFrame:
    '''Return year/field/code aggregates joined to exact official membership and DDI labels.

    Requires lists[2017/2022] with unique String code/title columns from Task3.
    Special status derives only from explicit DDI category meanings, never code magnitude.
    Source-document scheme and harmonization review remain external; membership alone
    cannot establish a delivered native vintage, including for a discriminating code.
    '''
    for vintage in (2017, 2022):
        reference = lists[vintage]
        if (reference.schema != {'code': pl.String, 'title': pl.String}
                or reference['code'].null_count() or reference['title'].null_count()
                or reference['code'].n_unique() != reference.height):
            raise ValueError('industry lists require unique String code/title records')
    metadata = {variable['name']: variable for variable in ddi.get('variables', [])}
    results = []
    for name in ('IND', 'INDLY'):
        if frame.collect_schema()[name] != pl.String:
            raise ValueError('industry values must retain delivered String codes')
        variable = metadata.get(name, {})
        categories = variable.get('categories', [])
        meanings = pl.DataFrame([
            {'code': (category['value'].zfill(4)
                      if re.fullmatch(r'[0-9]{1,4}', category['value']) else category['value']),
             'ddi_value': category['value'], 'ddi_label': category['label'],
             'documented_special': (bool(SPECIAL_LABEL.search(category['label']))
                                    if category['label'] is not None else None)}
            for category in categories
        ], schema={'code': pl.String, 'ddi_value': pl.String, 'ddi_label': pl.String,
                   'documented_special': pl.Boolean})
        if meanings['code'].n_unique() != meanings.height:
            raise ValueError('DDI industry categories must be unique')
        grouped = frame.group_by('YEAR', name).agg(pl.len().cast(pl.UInt64).alias('rows')).select(
            pl.col('YEAR').cast(pl.Int64).alias('year'), pl.lit(name).alias('variable'),
            pl.col(name).alias('code'), 'rows').join(meanings.lazy(), on='code', how='left')
        for vintage in (2017, 2022):
            grouped = grouped.join(lists[vintage].lazy().rename({'title': f'label_{vintage}'}),
                                   on='code', how='left').with_columns(
                pl.col(f'label_{vintage}').is_not_null().alias(f'in_{vintage}'))
        valid = pl.col('code').str.contains(r'^[0-9]{4}$')
        grouped = grouped.with_columns(
            pl.when(pl.col('code').is_null()).then(pl.lit('missing'))
            .when(valid.not_()).then(pl.lit('malformed'))
            .when(pl.col('documented_special')).then(pl.lit('documented_special'))
            .when(pl.col('in_2017').and_(pl.col('in_2022'))).then(pl.lit('shared_ambiguous'))
            .when(pl.col('in_2017')).then(pl.lit('2017_only'))
            .when(pl.col('in_2022')).then(pl.lit('2022_only'))
            .otherwise(pl.lit('outside')).alias('membership'),
            pl.lit(json.dumps(variable.get('instructions', []), ensure_ascii=False))
                .alias('ddi_instructions'),
            pl.lit('external_required').alias('source_scheme_evidence'),
            pl.lit('external_required').alias('delivered_harmonization_evidence'),
            pl.lit(None, dtype=pl.Int64).alias('native_vintage'),
            pl.lit('unresolved').alias('native_verdict'),
            valid.and_(pl.col('in_2022').not_())
                .and_(pl.col('documented_special').fill_null(False).not_())
                .alias('stage11_compatibility_required'),
        ).select(list(SCHEMA)).cast(SCHEMA)
        results.append(grouped)
    return pl.concat(results).sort('year', 'variable', 'code', nulls_last=False).collect()
