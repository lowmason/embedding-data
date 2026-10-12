from hypothesis import example, given, settings, strategies as st

from embedding_data import cps_benchmark_extract as benchmark


YEAR_MONTHS = st.tuples(st.integers(min_value=2023, max_value=2035), st.integers(1, 12))
MONTHLY_VARIANTS = st.dictionaries(
    keys=YEAR_MONTHS,
    values=st.sampled_from(['b', 's', 'bs', 'sb']),
    max_size=24,
)


@settings(derandomize=True)
@given(year_month=YEAR_MONTHS)
@example(year_month=(2025, 1))
@example(year_month=(2024, 12))
def test_parse_month_preserves_valid_year_and_month(year_month):
    year, month = year_month

    assert benchmark.parse_month(f'{year:04d}-{month:02d}') == year_month


@settings(derandomize=True)
@given(variants=MONTHLY_VARIANTS, start=YEAR_MONTHS)
@example(variants={}, start=(2025, 1))
@example(variants={(2024, 12): 'b', (2025, 1): 's'}, start=(2025, 1))
@example(variants={(2026, 9): 'sb', (2025, 1): 'bs'}, start=(2025, 1))
def test_monthly_selection_has_one_sample_per_eligible_period_in_order(variants, start):
    catalog = {
        f'cps{year}_{month:02d}{suffix}': 'Basic Monthly' if suffix == 'b' else 'Supplement'
        for (year, month), suffixes in variants.items()
        for suffix in suffixes
    }
    catalog['not-a-cps-sample'] = 'Basic Monthly'
    catalog['cps2099_03s'] = 'March 2099 ASEC'

    samples = benchmark.select_samples(catalog, 'monthly', start)
    selected_periods = [(int(sample[3:7]), int(sample[8:10])) for sample in samples]
    expected_periods = sorted(period for period in variants if period >= start)
    reversed_catalog = dict(reversed(list(catalog.items())))

    assert selected_periods == expected_periods
    assert all(sample in catalog for sample in samples)
    assert samples == benchmark.select_samples(reversed_catalog, 'monthly', start)


@settings(derandomize=True)
@given(year_month=YEAR_MONTHS, basic_first=st.booleans())
def test_basic_sample_is_preferred_in_either_catalog_order(year_month, basic_first):
    year, month = year_month
    basic = f'cps{year}_{month:02d}b'
    supplement = f'cps{year}_{month:02d}s'
    entries = [(basic, 'Basic Monthly'), (supplement, 'Supplement')]
    catalog = dict(entries if basic_first else reversed(entries))

    assert benchmark.select_samples(catalog, 'monthly', year_month) == [basic]


@settings(derandomize=True)
@given(years=st.lists(st.integers(2023, 2035), unique=True, max_size=13), start=YEAR_MONTHS)
@example(years=[], start=(2025, 1))
@example(years=[2026, 2024, 2025], start=(2035, 12))
def test_asec_selection_starts_in_2025_independently_of_monthly_start(years, start):
    catalog = {f'cps{year}_03s': f'March {year} ASEC' for year in years}
    catalog['cps2035_01b'] = 'January 2035 Basic Monthly'
    catalog['not-a-cps-sample'] = 'ASEC'

    samples = benchmark.select_samples(catalog, 'asec', start)
    expected_samples = [f'cps{year}_03s' for year in sorted(years) if year >= 2025]

    assert samples == expected_samples
    assert samples == benchmark.select_samples(catalog, 'asec', (2023, 1))
