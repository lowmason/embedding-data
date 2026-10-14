from collections import defaultdict

import polars as pl

from embedding_data.geography_parsers import EXCLUDED

NORMALIZED_SCHEMA = {'zip_key': pl.String, 'county_geoid': pl.String,
                     'bus_ratio': pl.Float64, 'noncounty_geography': pl.Boolean}
HUD_SCHEMA = {**NORMALIZED_SCHEMA, **{c: pl.Boolean for c in [
    'county_in_frame', 'flag_county_out_of_scope', 'flag_county_incompatible',
    'flag_county_legacy_ct']}}
LOOKUP_SCHEMA = {'zip_key': pl.String, 'n_hud_rows': pl.Int64,
                 'n_business_counties': pl.Int64, 'business_counties': pl.List(pl.String),
                 'max_business_ratio': pl.Float64, 'dominant_candidates': pl.List(pl.String),
                 'zip_dominant_county': pl.String, 'zip_single_candidate': pl.String,
                 'zip_fallback_county': pl.String, 'eligibility_status': pl.String}
LOOKUP_SCHEMA.update({c: pl.Boolean for c in ['flag_zip_zero_business',
    'flag_zip_multiple_counties', 'flag_zip_has_out_of_scope',
    'flag_zip_has_incompatible', 'flag_zip_legacy_ct']})
SCHEMAS = {'hud_zip_county': HUD_SCHEMA, 'hud_zip_lookup': LOOKUP_SCHEMA}


def annotate(hud: pl.DataFrame, counties: pl.DataFrame) -> pl.DataFrame:
    if hud.schema != NORMALIZED_SCHEMA:
        raise ValueError('incompatible normalized read_hud schema')
    inventory = counties['county_geoid'].to_list()
    output = hud.with_columns(
        county_in_frame=pl.col('county_geoid').is_in(inventory),
        flag_county_out_of_scope=pl.col('county_geoid').str.slice(0, 2).is_in(sorted(EXCLUDED)),
        flag_county_legacy_ct=pl.col('county_geoid').str.contains(r'^090[0-9]{2}$'),
    ).with_columns(flag_county_incompatible=pl.col('county_in_frame').not_().and_(
        pl.col('flag_county_out_of_scope').not_()).and_(pl.col('noncounty_geography').not_()))
    return output.select(list(HUD_SCHEMA)).sort('zip_key', 'county_geoid')


def lookup(candidates: pl.DataFrame) -> pl.DataFrame:
    if candidates.schema != HUD_SCHEMA:
        raise ValueError('incompatible geography HUD candidate schema')
    groups = defaultdict(list)
    for row in candidates.iter_rows(named=True):
        groups[row['zip_key']].append(row)
    result = []
    for zip_key, items in sorted(groups.items()):
        positive = [r for r in items if r['bus_ratio'] > 0]
        n = len(positive)
        business = sorted(r['county_geoid'] for r in positive)
        maximum = max((r['bus_ratio'] for r in positive), default=None)
        dominant = sorted(r['county_geoid'] for r in positive if r['bus_ratio'] == maximum)
        single = positive[0] if n == 1 else None
        if n == 0:
            status = 'zero_business'
        elif n > 1:
            status = 'multiple_counties'
        elif single['flag_county_out_of_scope']:
            status = 'out_of_scope'
        elif not single['county_in_frame']:
            status = 'incompatible_county'
        else:
            status = 'eligible'
        result.append((zip_key, len(items), n, business, maximum, dominant,
                       dominant[0] if len(dominant) == 1 else None,
                       single['county_geoid'] if single else None,
                       single['county_geoid'] if status == 'eligible' else None, status,
                       n == 0, n > 1,
                       any(r['flag_county_out_of_scope'] for r in positive),
                       any(r['flag_county_incompatible'] for r in positive),
                       any(r['flag_county_legacy_ct'] for r in positive)))
    return pl.DataFrame(result, schema=LOOKUP_SCHEMA, orient='row').sort('zip_key')
