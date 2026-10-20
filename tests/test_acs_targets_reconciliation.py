'''Independent Stage9 scientific acceptance and immutable before-state tests.'''

import ast
import hashlib
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def guarded_external_access(monkeypatch):
    from acs_mapping_fixtures import forbid_external_access
    from acs_target_fixtures import install_counted_guards

    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    forbid_external_access(monkeypatch)
    install_counted_guards(monkeypatch, counts)
    yield counts
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}


def load_script(name):
    file = ROOT / 'scripts' / (name + '.py')
    assert file.is_file(), 'independent acceptance script is missing: ' + name
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_acceptance_scripts_import_no_production_package():
    for name in (
        'stage9_independent_io',
        'stage9_independent_estimates',
        'reconcile_stage9',
        'reconcile_stage8',
    ):
        file = ROOT / 'scripts' / (name + '.py')
        assert file.is_file(), 'independent acceptance script is missing: ' + name
        tree = ast.parse(file.read_text())
        modules = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        modules += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith('embedding_data') for m in modules)


def test_frozen_numerical_predicates():
    estimates = load_script('stage9_independent_estimates')
    assert estimates.close_share(0.5, 0.5)
    assert not estimates.close_share(0.5 + 1e-10, 0.5)
    assert estimates.close_allocated_or_se(1e8 + 0.00009, 1e8)
    assert not estimates.close_allocated_or_se(1e8 + 0.001, 1e8)
    for bad in (float('inf'), float('-inf'), float('nan')):
        assert not estimates.close_share(bad, bad)
        assert not estimates.close_allocated_or_se(bad, bad)


def test_genuine_before_build_freeze_independent_reconciliation_and_mutations(
    tmp_path, monkeypatch
):
    from acs_target_fixtures import run_acs_target_v12

    acceptance = load_script('reconcile_stage9')
    controls = tmp_path / 'independent-controls'
    captured = {}

    def freeze_before_build(fixture):
        assert not (fixture['data_dir'] / 'derived/acs/targets/first').exists()
        captured.update(
            acceptance.freeze(
                fixture['data_dir'],
                controls,
                mapping_run=fixture['mapping_run'],
                mapping_outputs_sha256=fixture['mapping_pin'],
                request=asdict(fixture['request']),
                first_run='first',
                replay_run='replay',
            )
        )
        assert (
            captured['freeze_sha256']
            == hashlib.sha256((controls / 'freeze.json').read_bytes()).hexdigest()
        )
        assert json.loads((controls / 'freeze-response.json').read_bytes()) == captured

    fixture = run_acs_target_v12(
        tmp_path / 'data', monkeypatch, before_targets=freeze_before_build
    )
    data = fixture['data_dir']
    pin = captured['freeze_sha256']
    for name in ('first', 'replay'):
        target_pin = hashlib.sha256((fixture[name] / 'outputs.json').read_bytes()).hexdigest()
        result = acceptance.reconcile(data, name, target_pin, controls, expected_freeze_sha256=pin)
        assert result['failure_count'] == 0, result
        assert set(result['gates']) == set(range(1, 7)) or set(result['gates']) == set('123456')
        assert all(g['failure_count'] == 0 for g in result['gates'].values())
    preserved = acceptance.preservation(data, controls, expected_freeze_sha256=pin)
    assert preserved['failure_count'] == 0
    assert preserved['stage9_raw_records_appended'] == 0
    assert fixture['external_access_counts'] == {
        'network': 0,
        'environment_file': 0,
        'live_client': 0,
    }

    # Production verification is deliberately unavailable for every mutation below.
    from embedding_data import acs_target_bundle

    def forbidden_verifier(*args, **kwargs):
        pytest.fail('independent acceptance called the production target verifier')

    monkeypatch.setattr(acs_target_bundle, 'verify_bundle', forbidden_verifier)
    bundle = fixture['first']
    mutations = [
        ('target_support', 'n_unweighted', lambda x: x + 1),
        ('target_support', 'denominator_n_unweighted', lambda x: x + 1),
        ('target_support', 'pool_divisor', lambda x: 1 if x == 2 else 2),
        ('target_support', 'cell_weight_sum_exact', lambda x: str(float(x) + 0.000001)),
        ('target_support', 'denominator_weight_sum_exact', lambda x: str(float(x) + 1)),
        ('replicate_estimates', 'numerator', lambda x: x + 1),
        ('replicate_estimates', 'denominator', lambda x: x + 1),
        ('replicate_estimates', 'estimate', lambda x: x + 0.01),
        ('targets_observed', 'se', lambda x: (x or 0) + 1),
        ('targets_observed', 'se_method', lambda x: 'none'),
        ('targets_canonical', 'unit_b', lambda x: 'naics:2022:sector:81'),
        ('eligibility_diagnostics', 'evidence_status', lambda x: 'allocated'),
        ('eligibility_diagnostics', 'partition_kind', lambda x: 'first_exclusion'),
        ('allocation_residuals', 'weighted_mass', lambda x: x + 1),
        ('target_support', 'fractional_support_mass', lambda x: x + 1),
        ('target_units', 'code_canonical_scalar_node_id', lambda x: 'naics:2022:sector:81'),
    ]
    for table, column, change in mutations:
        file = bundle / (table + '.parquet')
        original = file.read_bytes()
        outputs = (bundle / 'outputs.json').read_bytes()
        frame = pl.read_parquet(file)
        candidates = [
            i
            for i, value in enumerate(frame[column])
            if value is not None and change(value) != value
        ]
        if table == 'replicate_estimates':
            candidates = [
                i
                for i in candidates
                if frame['replicate'][i] == 37 and frame['view'][i] == 'observed'
            ]
            assert candidates and all(frame['replicate'][i] == 37 for i in candidates)
        if table == 'target_support' and column not in (
            'fractional_support_mass',
            'denominator_n_unweighted',
        ):
            candidates = [i for i in candidates if frame['view'][i] == 'observed']
        if table == 'target_support' and column in (
            'fractional_support_mass',
            'denominator_n_unweighted',
        ):
            candidates = [i for i in candidates if frame['view'][i] == 'allocated_msa']
        if table == 'eligibility_diagnostics':
            candidates = [i for i in candidates if frame['partition_kind'][i] == 'evidence']
        assert candidates, (table, column)
        index = candidates[len(candidates) // 2]
        values = frame[column].to_list()
        values[index] = change(values[index])
        frame.with_columns(pl.Series(column, values, dtype=frame.schema[column])).write_parquet(
            file
        )
        inventory = json.loads(outputs)
        inventory[file.name].update(
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(), size=file.stat().st_size
        )
        (bundle / 'outputs.json').write_text(json.dumps(inventory))
        mutated_pin = hashlib.sha256((bundle / 'outputs.json').read_bytes()).hexdigest()
        result = acceptance.reconcile(
            data, 'first', mutated_pin, controls, expected_freeze_sha256=pin
        )
        assert result['failure_count'] > 0, (table, column, result)
        group = {
            'target_units': 4,
            'targets_canonical': 4,
            'eligibility_diagnostics': 1,
            'allocation_residuals': 5,
        }.get(table, 3)
        if table == 'target_support' and column in (
            'fractional_support_mass',
            'denominator_n_unweighted',
        ):
            group = 5
        failures = result['gates'][group]['failures']
        assert any(
            f['check'] == table + ': field differs'
            and f.get('field') == column
            or f['check'] == table + ': key set differs'
            for f in failures
        ), (
            'source oracle did not reject corruption independently of exact replay',
            table,
            column,
            group,
            failures,
        )
        file.write_bytes(original)
        (bundle / 'outputs.json').write_bytes(outputs)

    with pytest.raises(ValueError, match='freeze.*pin'):
        acceptance.preservation(data, controls, expected_freeze_sha256='0' * 64)
    freeze_bytes = (controls / 'freeze.json').read_bytes()
    prefix_bytes = (controls / 'manifest-prefix.jsonl').read_bytes()
    forged = json.loads(freeze_bytes)
    forged_prefix = prefix_bytes + b'\n'
    forged['manifest_prefix'] = {
        'size': len(forged_prefix),
        'sha256': hashlib.sha256(forged_prefix).hexdigest(),
    }
    (controls / 'manifest-prefix.jsonl').write_bytes(forged_prefix)
    (controls / 'freeze.json').write_text(json.dumps(forged))
    with pytest.raises(ValueError, match='freeze.*pin'):
        acceptance.preservation(data, controls, expected_freeze_sha256=pin)
    (controls / 'freeze.json').write_bytes(freeze_bytes)
    (controls / 'manifest-prefix.jsonl').write_bytes(prefix_bytes)

    manifest = data / 'raw/manifest.jsonl'
    manifest_bytes = manifest.read_bytes()
    for changed in (manifest_bytes.replace(b'{', b'{ ', 1), manifest_bytes[:-1]):
        manifest.write_bytes(changed)
        with pytest.raises(ValueError, match='prefix'):
            acceptance.preservation(data, controls, expected_freeze_sha256=pin)
        manifest.write_bytes(manifest_bytes)
    frozen = json.loads(freeze_bytes)
    original = data / frozen['mapping_inputs']['sources']['acs/core']['parquet']
    saved = original.read_bytes()
    original.write_bytes(saved + b' ')
    with pytest.raises(ValueError, match='protected'):
        acceptance.preservation(data, controls, expected_freeze_sha256=pin)
    original.write_bytes(saved)
    assert (
        acceptance.preservation(data, controls, expected_freeze_sha256=pin)['failure_count'] == 0
    )


def test_annual_flags_are_separate_from_pooled_union():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    pair = ('a', 'A', 'b', 'B')
    annual = {
        (*pair, year): {'weights': [Decimal('1')] * 81, 'n': 1, 'fraction': 1.0, 'flags': {flag}}
        for year, flag in [(2023, 'first'), (2024, 'second')]
    }
    result = estimates.complete_components(annual, {'view': 'observed', 'years': [2023, 2024]})
    assert result[*pair, 2023]['flags'] == {'first'}
    assert result[*pair, 2024]['flags'] == {'second'}
    assert result[*pair, 0]['flags'] == {'first', 'second'}


def test_decimal_pooling_preserves_more_than_default_context_precision():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    large, small = Decimal('1234567890123456789012345678.12345'), Decimal('.00001')

    def cell(weight):
        return {'weights': [weight] * 81, 'n': 1, 'fraction': 1.0, 'flags': set()}

    result = estimates.add(cell(large), cell(small))
    assert result['weights'] == [Decimal('1234567890123456789012345678.12346')] * 81


def test_stream_alignment_accepts_unequal_physical_boundaries_and_rejects_order():
    estimates = load_script('stage9_independent_estimates')
    left = [pl.DataFrame({'v': [1]}), pl.DataFrame({'v': [2, 3, 4]})]
    right = [pl.DataFrame({'v': [1, 2]}), pl.DataFrame({'v': [3, 4]})]
    pieces = list(estimates.aligned_batches(iter(left), iter(right)))
    assert sum(a.height for a, _ in pieces) == 4
    assert all(a.equals(b) for a, b in pieces)
    with pytest.raises(ValueError, match='count'):
        list(estimates.aligned_batches(iter(left), iter(right[:1])))


def test_zero_denominator_status_and_interior_undefined_signed_replicates():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    product = next(
        p
        for p in estimates.products()
        if p['view'] == 'observed' and p['family'] == 'staffing_pattern'
    )
    pair = (
        'acs_industry_category',
        'feature:acs_industry_category:A',
        'acs_occupation_category',
        'feature:acs_occupation_category:B',
    )
    weights = [Decimal('0')] + [Decimal('1')] * 80
    weights[37] = Decimal('0')
    weights[38] = Decimal('-2.5')
    annual = {
        (*pair, year): {
            'weights': list(weights),
            'n': 1,
            'fraction': 1.0,
            'flags': {'size_gate_pending'},
        }
        for year in (2023, 2024)
    }
    cells = estimates.complete_components(annual, product)
    support, reps, targets = estimates.finalize(cells, {}, product)
    assert targets == []
    assert len(reps) == 160
    for row in support:
        if row['record_kind'] == 'denominator_status':
            assert row['cell_mass'] == 0.0
            assert row['cell_weight_sum_exact'] == '0'
            assert row['fractional_support_mass'] == 0.0
        if row['measure'] == 'forward_share':
            assert row['point_reason'] == 'nonpositive_denominator'
            assert row['se_reason'] == 'undefined_point'
    r37 = next(r for r in reps if r['measure'] == 'forward_share' and r['replicate'] == 37)
    assert r37['status'] == r37['reason'] == 'zero_denominator'
    assert r37['estimate'] is None
    r38 = next(r for r in reps if r['measure'] == 'forward_share' and r['replicate'] == 38)
    assert r38['numerator'] == -2.5 and r38['denominator'] == -2.5
    assert r38['estimate'] == 1.0 and r38['reason'] is None


@pytest.fixture
def byte_controls(tmp_path):
    '''Pure preservation fixture: never a selected-object mock or whole-acceptance oracle.'''
    acceptance = load_script('reconcile_stage9')
    io = acceptance.io
    data, control = tmp_path / 'data', tmp_path / 'control'
    (data / 'raw').mkdir(parents=True)
    (data / 'derived/history').mkdir(parents=True)
    original = data / 'raw/original.bin'
    original.write_bytes(b'immutable original\n')
    seal = data / 'derived/history/science-seal.json'
    seal.write_bytes(b'{"adoption": false}\n')
    manifest = (
        json.dumps(
            {
                'path': 'original.bin',
                **io.record(original),
                'collection': 'synthetic-byte-unit-test',
            }
        )
        + '\n'
    ).encode()
    (data / 'raw/manifest.jsonl').write_bytes(manifest)
    control.mkdir()
    frozen = {
        'version': 'stage9-independent-v1',
        'data_dir': str(data),
        'control_dir': str(control),
        'first_run': 'first',
        'replay_run': 'replay',
        'excluded_paths': [
            str(control),
            str(io.target_directory(data, 'first')),
            str(io.target_directory(data, 'replay')),
        ],
        'software': io.software(),
        'files': io.inventory(data, (control,)),
        'manifest_prefix': {'size': len(manifest), 'sha256': hashlib.sha256(manifest).hexdigest()},
    }
    io.write_exclusive(control / 'freeze.json', frozen)
    (control / 'manifest-prefix.jsonl').write_bytes(manifest)
    pin = io.digest(control / 'freeze.json')
    io.write_exclusive(
        control / 'freeze-response.json',
        {
            'freeze_sha256': pin,
            'protected_file_count': len(frozen['files']),
            'manifest_prefix': frozen['manifest_prefix'],
        },
    )
    return acceptance, data, control, pin, original, seal


@pytest.mark.parametrize('member', ['original', 'seal', 'prefix', 'freeze', 'response'])
def test_preservation_rejects_each_protected_byte_class(byte_controls, member):
    acceptance, data, control, pin, original, seal = byte_controls
    file = {
        'original': original,
        'seal': seal,
        'prefix': control / 'manifest-prefix.jsonl',
        'freeze': control / 'freeze.json',
        'response': control / 'freeze-response.json',
    }[member]
    file.write_bytes(file.read_bytes() + b' ')
    with pytest.raises(ValueError):
        acceptance.preservation(data, control, expected_freeze_sha256=pin)


def test_legitimate_manifest_append_is_accounted_separately_from_immutable_bytes(byte_controls):
    acceptance, data, control, pin, _, _ = byte_controls
    manifest = data / 'raw/manifest.jsonl'
    before = manifest.read_bytes()
    later = data / 'raw/later.bin'
    later.write_bytes(b'legitimate later immutable original\n')
    with manifest.open('ab') as stream:
        stream.write(
            (
                json.dumps(
                    {
                        'path': 'later.bin',
                        **acceptance.io.record(later),
                        'collection': 'another-stage-reference',
                    }
                )
                + '\n'
            ).encode()
        )
    result = acceptance.preservation(data, control, expected_freeze_sha256=pin)
    assert result['manifest_appends_accounted'] == 1
    assert result['stage9_raw_records_appended'] == 0
    assert manifest.read_bytes().startswith(before)
    later.write_bytes(b'mutated')
    with pytest.raises(ValueError, match='suffix'):
        acceptance.preservation(data, control, expected_freeze_sha256=pin)


def test_new_unmanifested_file_and_stage9_manifest_append_are_refused(byte_controls):
    acceptance, data, control, pin, _, _ = byte_controls
    later = data / 'raw/later.bin'
    later.write_bytes(b'unaccounted')
    with pytest.raises(ValueError, match='unaccounted'):
        acceptance.preservation(data, control, expected_freeze_sha256=pin)
    with (data / 'raw/manifest.jsonl').open('a') as stream:
        stream.write(
            json.dumps(
                {'path': 'later.bin', **acceptance.io.record(later), 'collection': 'acs-targets'}
            )
            + '\n'
        )
    with pytest.raises(ValueError, match='zero raw'):
        acceptance.preservation(data, control, expected_freeze_sha256=pin)


@pytest.mark.parametrize(
    'kind', ['control', 'control-part', 'first', 'first-part', 'unsafe', 'symlink']
)
def test_freeze_refuses_unsafe_symlink_and_occupied_paths_before_selection(tmp_path, kind):
    acceptance = load_script('reconcile_stage9')
    data, control = tmp_path / 'data', tmp_path / 'controls'
    (data / 'raw').mkdir(parents=True)
    (data / 'derived').mkdir()
    occupied = {
        'control': control,
        'control-part': control.with_suffix('.part'),
        'first': data / 'derived/acs/targets/first',
        'first-part': data / 'derived/acs/targets/first.part',
    }
    if kind in occupied:
        occupied[kind].mkdir(parents=True)
    if kind == 'symlink':
        control.symlink_to(data, target_is_directory=True)
    with pytest.raises(ValueError, match='unsafe|occupied|symlink'):
        acceptance.freeze(
            data,
            control,
            mapping_run='mapping',
            mapping_outputs_sha256='a' * 64,
            request={},
            first_run='../escape' if kind == 'unsafe' else 'first',
            replay_run='replay',
        )


def test_freeze_request_has_exactly_seven_explicit_fields(tmp_path):
    acceptance = load_script('reconcile_stage9')
    request = {
        name: 'run' if name.endswith('_run') else 'a' * 64 for name in acceptance.io.REQUEST_FIELDS
    }
    for invalid in (
        {k: v for k, v in request.items() if k != 'ipums_run'},
        dict(request, latest='forbidden'),
    ):
        with pytest.raises(ValueError, match='exactly seven'):
            acceptance.freeze(
                tmp_path / 'data',
                tmp_path / 'control',
                mapping_run='mapping',
                mapping_outputs_sha256='a' * 64,
                request=invalid,
                first_run='first',
                replay_run='replay',
            )


def test_cli_requires_explicit_inputs_and_failure_json_contains_all_gates(byte_controls):
    from typer.testing import CliRunner

    acceptance, data, control, _, _, _ = byte_controls
    runner = CliRunner()
    for command in ('freeze', 'preservation', 'reconcile'):
        assert runner.invoke(acceptance.app, [command]).exit_code == 2
    result = runner.invoke(
        acceptance.app,
        [
            'preservation',
            '--data-dir',
            str(data),
            '--control-dir',
            str(control),
            '--freeze-sha256',
            '0' * 64,
        ],
    )
    assert result.exit_code != 0
    output = json.loads(result.stdout)
    assert output['failure_count'] > 0
    assert set(output['gates']) == set('123456')


def test_county_first_allocation_zero_factors_typed_residuals_and_nonadditive_support():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    product = next(p for p in estimates.products() if p['view'] == 'allocated_msa')
    origins = [
        'geography:2020:work_migration_puma:0100100',
        'geography:2020:work_migration_puma:0200200',
    ]
    county_ids = [
        'geography:2025:county:' + value for value in ('00000', '01001', '02001', '01003', '02003')
    ]
    metro = 'geography:2023:cbsa:10000'
    counties = {
        identity: {'cbsa_type': kind, 'cbsa_id': cbsa}
        for identity, kind, cbsa in zip(
            county_ids,
            [None, 'metropolitan', 'metropolitan', 'micropolitan', None],
            [None, metro, metro, 'geography:2023:cbsa:20000', None],
            strict=True,
        )
    }
    factors = {
        origins[0]: list(zip(county_ids[:4], [0.0, 0.25, 0.5, 0.25], strict=True)),
        origins[1]: [(county_ids[4], 1.0)],
    }
    native = {}
    for origin, mass, n in [(origins[0], '100', 2), (origins[1], '60', 1)]:
        vector = [Decimal(mass)] * 81
        vector[37] = Decimal('-7')
        for year in (0, 2023, 2024):
            native[
                'work_migration_puma',
                origin,
                'acs_industry_category',
                'feature:acs_industry_category:A',
                year,
            ] = {'weights': vector, 'n': n, 'fraction': float(n), 'flags': {'size_gate_pending'}}
    cells, residuals = estimates.allocation(native, product, factors, counties)
    assert {key[1] for key in cells} == {metro}
    assert all(value['n'] == 2 and value['fraction'] == 1.5 for value in cells.values())
    assert all(
        value['weights'][0] == 75.0 and value['weights'][37] == -5.25 for value in cells.values()
    )
    assert len(residuals) == 2 * 3 * 81
    assert {r['residual_type'] for r in residuals} == {'micropolitan', 'no_cbsa'}
    for row in residuals:
        expected = (
            (-7 if row['replicate'] == 37 else 100) * 0.25
            if row['residual_type'] == 'micropolitan'
            else (-7 if row['replicate'] == 37 else 60)
        ) / 2
        assert row['weighted_mass'] == pytest.approx(expected, abs=1e-12, rel=0)
        assert row['n_input_support'] == (2 if row['residual_type'] == 'micropolitan' else 1)


def test_exact_counts_decimal_strings_and_logical_replay_ignore_no_float_gap():
    acceptance = load_script('reconcile_stage9')
    gates = {n: {'failures': []} for n in acceptance.GROUPS}
    expected = {
        'key': 'cell',
        'n_unweighted': 1,
        'cell_weight_sum_exact': '1.00000000000000000001',
    }
    actual = dict(expected, n_unweighted=2, cell_weight_sum_exact='1.00000000000000000002')
    acceptance.compare_rows(gates, 3, 'target_support', [actual], [expected], ['key'])
    assert len(gates[3]['failures']) == 2
    assert {r['field'] for r in gates[3]['failures']} == {'n_unweighted', 'cell_weight_sum_exact'}


def test_logical_replay_is_exact_inside_the_share_tolerance():
    acceptance = load_script('reconcile_stage9')
    expected = {'key': 'cell', 'measure': 'forward_share', 'value': 0.5}
    actual = dict(expected, value=0.5 + 1e-13)
    gates = {n: {'failures': []} for n in acceptance.GROUPS}
    acceptance.compare_rows(gates, 3, 'targets', [actual], [expected], ['key'])
    assert gates[3]['failures'] == []
    acceptance.compare_rows(gates, 6, 'replay', [actual], [expected], ['key'], exact=True)
    assert len(gates[6]['failures']) == 1


def test_freeze_accepts_the_public_build_upstream_option_spelling():
    from typer.testing import CliRunner

    acceptance = load_script('reconcile_stage9')
    result = CliRunner().invoke(acceptance.app, ['freeze', '--ipums-references-sha256', 'a' * 64])
    assert 'No such option' not in result.output
    assert 'Missing option' in result.output


def test_annual_zero_denominator_does_not_override_positive_pooled_status():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    product = next(
        p
        for p in estimates.products()
        if p['family'] == 'staffing_pattern' and p['view'] == 'observed'
    )
    pair = (
        'acs_industry_category',
        'feature:acs_industry_category:A',
        'acs_occupation_category',
        'feature:acs_occupation_category:B',
    )
    annual = {
        (*pair, year): {
            'weights': [Decimal(value)] * 81,
            'n': 1,
            'fraction': 1.0,
            'flags': {'size_gate_pending'},
        }
        for year, value in [(2023, '0'), (2024, '2')]
    }
    support, _, targets = estimates.finalize(
        estimates.complete_components(annual, product), {}, product
    )
    assert len(targets) == 2
    assert all(row['record_kind'] == 'cell' for row in support)
    assert all(row['point_status'] == 'defined' for row in support)


def test_positive_point_retains_undefined_interior_share_se_on_all_annual_rows():
    from decimal import Decimal

    estimates = load_script('stage9_independent_estimates')
    product = next(
        p
        for p in estimates.products()
        if p['family'] == 'staffing_pattern' and p['view'] == 'observed'
    )
    pair = (
        'acs_industry_category',
        'feature:acs_industry_category:A',
        'acs_occupation_category',
        'feature:acs_occupation_category:B',
    )
    weights = [Decimal('2')] * 81
    weights[37] = Decimal('0')
    weights[38] = Decimal('-2.5')
    annual = {
        (*pair, year): {
            'weights': list(weights),
            'n': 1,
            'fraction': 1.0,
            'flags': {'size_gate_pending'},
        }
        for year in (2023, 2024)
    }
    support, reps, targets = estimates.finalize(
        estimates.complete_components(annual, product), {}, product
    )
    share = next(r for r in targets if r['measure'] == 'forward_share')
    assert share['value'] == 1.0 and share['se'] is None and share['se_method'] == 'none'
    for row in support:
        assert row['point_status'] == 'defined'
        if row['measure'] == 'forward_share':
            assert row['se_status'] == row['se_reason'] == 'undefined_replicates'
            assert row['undefined_replicates'] == [37]
        else:
            assert row['se_status'] == 'defined' and row['undefined_replicates'] == []
    assert len(reps) == 160


def test_mapping_provenance_retains_complete_authenticated_parquet_records(tmp_path):
    acceptance = load_script('reconcile_stage9')
    # Pure inventory projection; authentication belongs to selected_mapping before this seam.
    record = {
        'sha256': 'a' * 64,
        'size': 17,
        'rows': 2,
        'columns': ['category'],
        'schema': {'category': 'String'},
    }
    inventory = {name + '.parquet': dict(record) for name in acceptance.io.stage8.TABLES}
    (tmp_path / 'outputs.json').write_text(json.dumps(inventory))
    expected = {name: dict(record) for name in acceptance.io.stage8.TABLES}
    assert acceptance.mapping_table_inventory(tmp_path) == expected
