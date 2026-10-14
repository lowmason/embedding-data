import polars as pl
from geography_fixtures import source_frames
from polars.testing import assert_frame_equal

from embedding_data import geography_hud as gh
from embedding_data import geography_tables as gt

def test_hud_inventory_ratios_and_all_statuses(tmp_path):
    sources = source_frames(tmp_path)
    counties = gt.assemble(sources)['county_reference']
    candidates = gh.annotate(sources['hud'], counties)
    table = gh.lookup(candidates)
    assert candidates.schema == gh.HUD_SCHEMA
    assert table.schema == gh.LOOKUP_SCHEMA
    assert_frame_equal(candidates.select(sources['hud'].columns), sources['hud'])
    assert table['zip_key'].to_list() == [f'{i:05}' for i in range(1, 10)]
    assert table['eligibility_status'].to_list() == [
        'eligible', 'zero_business', 'multiple_counties', 'multiple_counties',
        'out_of_scope', 'incompatible_county', 'incompatible_county',
        'zero_business', 'eligible']
    assert table.filter(pl.col('zip_key').eq('99999')).is_empty()
    rows = {r['zip_key']: r for r in table.iter_rows(named=True)}
    assert rows['00002']['business_counties'] == []
    assert rows['00002']['dominant_candidates'] == []
    assert rows['00002']['max_business_ratio'] is None
    assert rows['00003']['business_counties'] == ['01001', '72001']
    assert rows['00003']['zip_dominant_county'] == '01001'
    assert rows['00003']['zip_single_candidate'] is None
    assert rows['00003']['zip_fallback_county'] is None
    assert rows['00003']['flag_zip_has_out_of_scope'] is True
    assert rows['00004']['dominant_candidates'] == ['01001', '51510']
    assert rows['00004']['zip_dominant_county'] is None
    assert rows['00005']['zip_single_candidate'] == '72001'
    assert rows['00007']['zip_single_candidate'] == '09001'
    assert rows['00007']['flag_zip_legacy_ct'] is True
    assert rows['00007']['flag_zip_has_incompatible'] is True
    assert rows['00008']['n_hud_rows'] == 1
    assert rows['00008']['flag_zip_has_out_of_scope'] is False
    assert candidates.filter(pl.col('county_geoid').eq('60')).item(
        0, 'flag_county_out_of_scope') is True
    assert rows['00009']['n_hud_rows'] == 2
    assert rows['00009']['n_business_counties'] == 1
    assert rows['00009']['zip_fallback_county'] == '01001'
    assert rows['00009']['flag_zip_has_out_of_scope'] is False
    assert all(r['zip_fallback_county'] is None for r in rows.values()
               if r['eligibility_status'] != 'eligible')


def test_reordered_candidates_produce_identical_sorted_lookup(tmp_path):
    sources = source_frames(tmp_path)
    counties = gt.assemble(sources)['county_reference']
    one = gh.annotate(sources['hud'], counties)
    two = gh.annotate(sources['hud'].reverse(), counties)
    assert_frame_equal(one, two)
    assert_frame_equal(gh.lookup(one), gh.lookup(two))
