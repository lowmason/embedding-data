'''Sample and compare ITA county methods offline from manifested references/responses.'''

import csv
import hashlib
import io
import json
import re

import polars as pl

from embedding_data.ita_references import read_hud  # noqa: F401 - county input interface
from embedding_data.ita_verification import with_keys

SAMPLE_SALT = 'embedding-data:V3:2026-10-13:v1'
OUT_OF_SCOPE_STATES = ('PR', 'VI', 'GU', 'AS', 'MP', 'UM')

def zip_candidates(frame: pl.DataFrame) -> pl.DataFrame:
    positive = frame.lazy().filter(pl.col('bus_ratio').gt(0))
    maxima = pl.col('bus_ratio').eq(pl.col('bus_ratio').max())
    return (
        positive.group_by('zip_key').agg(
            n_business_counties=pl.len(),
            business_counties=pl.col('county_geoid').sort(),
            max_business_ratio=pl.col('bus_ratio').max(),
            dominant_candidates=pl.col('county_geoid').filter(maxima).sort(),
            flag_zip_legacy_ct=pl.col('county_geoid').str.starts_with('090').any(),
        ).with_columns(
            zip_dominant_county=pl.when(pl.col('dominant_candidates').list.len().eq(1)).then(
                pl.col('dominant_candidates').list.first()
            ).otherwise(None),
            zip_single_county=pl.when(
                pl.col('n_business_counties').eq(1).and_(pl.col('flag_zip_legacy_ct').not_())
            ).then(pl.col('business_counties').list.first()).otherwise(None),
        ).sort('zip_key').collect()
    )

def content_key(row: dict) -> str:
    text = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def stratified_sample(
    lf: pl.LazyFrame, candidates: pl.DataFrame, per_stratum: int = 8
) -> pl.DataFrame:
    if per_stratum < 1:
        raise ValueError('per_stratum must be positive')
    columns = sorted(lf.collect_schema().names())
    population = (
        with_keys(lf.unique()).with_columns(
            row_key=pl.struct(columns).map_elements(content_key, return_dtype=pl.String)
        ).join(candidates.lazy(), on='zip_key', how='left', validate='m:1').with_columns(
            n_business_counties=pl.col('n_business_counties').fill_null(0),
            flag_zip_legacy_ct=pl.col('flag_zip_legacy_ct').fill_null(False)
        ).with_columns(
            county_count_class=pl.when(pl.col('n_business_counties').eq(0)
                                       ).then(pl.lit('none')).when(
                                           pl.col('n_business_counties').eq(1)
                                       ).then(pl.lit('single')).otherwise(pl.lit('multiple')),
            rank_key=pl.col('row_key').map_elements(
                lambda value: hashlib.sha256((SAMPLE_SALT + value).encode()).hexdigest(),
                return_dtype=pl.String,
            ),
        ).with_columns(
            stratum=pl.concat_str(
                pl.col('year_filing_for').cast(pl.String),
                'state',
                'zip_format',
                'county_count_class',
                separator='|',
            )
        ).with_columns(population_n=pl.len().over('stratum')).sort(
            'stratum', 'rank_key', 'row_key'
        ).group_by('stratum', maintain_order=True).head(per_stratum).with_columns(
            sample_n=pl.len().over('stratum')
        ).with_columns(
            inclusion_probability=pl.col('sample_n').truediv(pl.col('population_n')),
            sample_weight=pl.col('population_n').truediv(pl.col('sample_n'))
        )
    )
    return population.sort('stratum', 'row_key').collect()

def parse_geocodes(text: str) -> pl.DataFrame:
    records = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) < 3 or row[2] not in ('Match', 'No_Match', 'Tie'):
            raise ValueError('unrecognized Census batch response')
        status = row[2]
        match_type = row[3] if status == 'Match' and len(row) >= 4 else None
        geoid = None
        if status == 'Match':
            if len(row) < 12 or not re.fullmatch(r'[0-9]{2}', row[8]) or not re.fullmatch(
                r'[0-9]{3}', row[9]
            ):
                raise ValueError('Census geography match lacks valid state/county codes')
            geoid = row[8] + row[9]
        records.append((row[0], status, match_type, geoid))
    result = pl.DataFrame(
        records,
        schema={
            'row_key': pl.String,
            'geocode_status': pl.String,
            'match_type': pl.String,
            'county_geoid': pl.String,
        },
        orient='row'
    )
    if result['row_key'].n_unique() != result.height:
        raise ValueError('duplicate Census response ID')
    return result

def county_report(sample: pl.DataFrame, geocodes: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    sample_ids = set(sample['row_key'].to_list())
    if sample_ids != set(geocodes['row_key'].to_list()) or geocodes.height != sample.height:
        raise ValueError('sample/response IDs do not match exactly')
    compared = (
        sample.lazy().join(geocodes.lazy(), on='row_key', validate='1:1').with_columns(
            flag_out_of_scope=pl.col('state').is_in(OUT_OF_SCOPE_STATES),
            flag_geocode_legacy_ct=pl.col('county_geoid').str.starts_with('090').fill_null(False),
            geocode_non_exact=pl.col('geocode_status').eq('Match').and_(
                pl.col('match_type').ne('Exact')
            ).fill_null(False),
            geocode_no_match=pl.col('geocode_status').eq('No_Match'),
            geocode_tie=pl.col('geocode_status').eq('Tie'),
            zip_covered=pl.col('n_business_counties').gt(0),
            zip_single_compatible=pl.col('zip_single_county').is_not_null(),
        ).with_columns(
            geocode_exact=pl.col('geocode_status').eq('Match').and_(
                pl.col('match_type').eq('Exact')
            ).and_(pl.col('county_geoid').is_not_null()).and_(
                pl.col('flag_geocode_legacy_ct').not_()
            ).fill_null(False),
        ).with_columns(
            joint_dominant_comparable=pl.col('geocode_exact').and_(
                pl.col('zip_dominant_county').is_not_null()
            ).and_(pl.col('flag_zip_legacy_ct').not_()).and_(pl.col('flag_out_of_scope').not_()),
            joint_single_comparable=pl.col('geocode_exact').and_(pl.col('zip_single_compatible'))
            .and_(pl.col('flag_out_of_scope').not_()),
            proposed_assignable=pl.col('geocode_exact').or_(pl.col('zip_single_compatible')).and_(
                pl.col('flag_out_of_scope').not_()
            ),
        ).with_columns(
            joint_dominant_agree=pl.col('joint_dominant_comparable').and_(
                pl.col('county_geoid').eq(pl.col('zip_dominant_county'))
            ).fill_null(False),
            joint_single_agree=pl.col('joint_single_comparable').and_(
                pl.col('county_geoid').eq(pl.col('zip_single_county'))
            ).fill_null(False),
        )
    )
    flags = {
        'n_geocode_exact': 'geocode_exact',
        'n_zip_covered': 'zip_covered',
        'n_zip_single_compatible': 'zip_single_compatible',
        'n_joint_dominant_comparable': 'joint_dominant_comparable',
        'n_joint_dominant_agree': 'joint_dominant_agree',
        'n_joint_single_comparable': 'joint_single_comparable',
        'n_joint_single_agree': 'joint_single_agree',
        'n_proposed_assignable': 'proposed_assignable',
        'n_geocode_non_exact': 'geocode_non_exact',
        'n_geocode_no_match': 'geocode_no_match',
        'n_geocode_tie': 'geocode_tie',
        'n_geocode_legacy_ct': 'flag_geocode_legacy_ct',
        'n_ct_incomparable': 'flag_zip_legacy_ct',
        'n_out_of_scope': 'flag_out_of_scope',
    }
    strata = (
        compared.group_by('stratum').agg(
            population_n=pl.col('population_n').first(),
            n_sample=pl.len(),
            **{
                name: pl.col(column).sum()
                for name, column in flags.items()
            },
        ).sort('stratum').collect()
    )
    overall = compared.select(
        n_sample=pl.len(),
        n_population=pl.col('sample_weight').sum(),
        **{
            name: pl.col(column).sum()
            for name, column in flags.items()
        },
        **{
            'weighted_' + name: pl.col(column).cast(pl.Float64).mul(pl.col('sample_weight')).sum()
            for name, column in flags.items()
        },
    ).collect().row(0, named=True)
    denominators = {name: 'n_sample' for name in flags}
    denominators.update(
        n_joint_dominant_agree='n_joint_dominant_comparable',
        n_joint_single_agree='n_joint_single_comparable'
    )
    for name, denominator in denominators.items():
        total = overall[denominator]
        overall['share_' + name[2:]] = overall[name] / total if total else None
        weighted_total = (
            overall['n_population']
            if denominator == 'n_sample' else overall['weighted_' + denominator]
        )
        overall['weighted_share_' + name[2:]] = (
            overall['weighted_' + name] / weighted_total if weighted_total else None
        )
    return strata, overall
