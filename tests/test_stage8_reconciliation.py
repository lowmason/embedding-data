'''Independent acceptance controls against authenticated raw-to-bundle fixtures.'''
import importlib.util
import json
from pathlib import Path

import polars as pl
import pytest
from acs_mapping_fixtures import (
    build_fixture_mapping,
    forbid_external_access,
    seed_reconciliation_inputs,
)

@pytest.fixture
def reconciliation_module(monkeypatch):
    forbid_external_access(monkeypatch)
    script = Path(__file__).resolve().parents[1] / 'scripts/reconcile_stage8.py'
    assert script.is_file(), 'independent reconciler is missing'
    spec = importlib.util.spec_from_file_location('independent_stage8', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def accepted(reconciliation_module, tmp_path, monkeypatch):
    fixture = seed_reconciliation_inputs(tmp_path, monkeypatch)
    controls = tmp_path / 'controls'
    reconciliation_module.freeze(fixture.data_dir, controls)
    result = build_fixture_mapping(fixture, 'independent', monkeypatch)
    return fixture, controls, result

def test_independent_reconciliation_and_prefix_preservation(reconciliation_module, accepted):
    fixture, controls, result = accepted
    measured = reconciliation_module.reconcile(
        fixture.data_dir, 'independent', result['outputs_sha256'], controls
    )
    for key in (
        'code_frequencies_equal', 'population_reconciliation_equal', 'role_status_counts_equal'
    ):
        assert measured[key] is True
    assert measured['failure_count'] == 0
    assert measured['population']['scoped_puma_population'] == 600
    assert measured['population']['complete_puma_population'] == 610
    assert measured['population']['county_relations'] == 7
    assert measured['population']['msa_relations'] == 2
    assert len(measured['classification']['D4_rejected_constituents']) == 3
    prefix = (controls / 'manifest-prefix.jsonl').read_bytes()
    current = (fixture.data_dir / 'raw/manifest.jsonl').read_bytes()
    assert current.startswith(prefix) and len(current) > len(prefix)
    assert measured['population']['closure_max'] <= 1e-12
    preserved = reconciliation_module.preservation(fixture.data_dir, controls)
    assert preserved['manifest_prefix_equal'] is True
    assert preserved['protected_files_equal'] is True
    assert preserved['manifest_appends_accounted'] is True
    assert preserved['appended_record_count'] == len(current[len(prefix):].splitlines())

@pytest.mark.parametrize('damage', ['whitespace', 'truncate', 'unaccounted', 'raw'])
def test_preservation_rejects_damage(reconciliation_module, accepted, damage):
    fixture, controls, _ = accepted
    manifest = fixture.data_dir / 'raw/manifest.jsonl'
    original = manifest.read_bytes()
    if damage == 'whitespace':
        changed = bytearray(original)
        changed[original.index(b': ') + 1] = ord('\t')
        assert [json.loads(line) for line in changed.splitlines()] == [
            json.loads(line) for line in original.splitlines()
        ]
        manifest.write_bytes(changed)
    elif damage == 'truncate':
        manifest.write_bytes(original[:10])
    elif damage == 'unaccounted':
        manifest.write_bytes(original + b'{"path":"unaccounted","sha256":"x","size":1}\n')
    else:
        file = next((fixture.data_dir / 'raw/acs').rglob('*.xml'))
        file.write_bytes(file.read_bytes() + b' ')
    with pytest.raises(
        ValueError, match='manifest prefix' if damage in {'whitespace', 'truncate'} else None
    ):
        reconciliation_module.preservation(fixture.data_dir, controls)

def test_wrong_external_pin(reconciliation_module, accepted):
    fixture, controls, _ = accepted
    with pytest.raises(ValueError, match='pin|checksum'):
        reconciliation_module.reconcile(fixture.data_dir, 'independent', '0' * 64, controls)

def repin(directory):
    '''Independent physical inventory update makes semantic corruption self-consistent.'''
    import hashlib
    output = directory / 'outputs.json'
    record = json.loads(output.read_text())
    for name, item in record.items():
        file = directory / name
        item['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        item['size'] = file.stat().st_size
        if file.suffix == '.parquet':
            scan = pl.scan_parquet(file)
            item['rows'] = scan.select(pl.len()).collect().item()
            item['columns'] = scan.collect_schema().names()
            item['schema'] = {k: str(v) for k, v in scan.collect_schema().items()}
    output.write_text(json.dumps(record))
    return hashlib.sha256(output.read_bytes()).hexdigest()

@pytest.mark.parametrize(
    'damage', ['frequency', 'population', 'intersection', 'special', 'reason']
)
def test_independent_calculations_reject_rehashed_output(reconciliation_module, accepted, damage):
    fixture, controls, result = accepted
    directory = Path(result['directory'])
    if damage in {'frequency', 'special', 'reason'}:
        file = directory / 'acs_core_canonical.parquet'
        frame = pl.read_parquet(file)
        if damage == 'frequency':
            frame = frame.with_columns(pl.lit('999999').alias('INDNAICS'))
        elif damage == 'special':
            frame = frame.with_columns(pl.lit('mapped').alias('occupation_mapping_status'))
        else:
            frame = frame.with_columns(
                pl.lit('documented').alias('industry_aggregation_reason_status')
            )
    else:
        file = directory / 'puma_county_factors.parquet'
        frame = pl.read_parquet(file)
        if damage == 'population':
            frame = frame.with_columns(pl.col('intersection_population').add(1))
        else:
            frame = frame.slice(1)
    frame.write_parquet(file)
    pin = repin(directory)
    with pytest.raises(ValueError):
        reconciliation_module.reconcile(fixture.data_dir, 'independent', pin, controls)

def test_freeze_refuses_occupied_and_symlink(reconciliation_module, tmp_path):
    data = tmp_path / 'data'
    (data / 'raw').mkdir(parents=True)
    (data / 'derived').mkdir()
    (data / 'raw/manifest.jsonl').write_bytes(b'')
    control = tmp_path / 'controls'
    reconciliation_module.freeze(data, control)
    with pytest.raises(ValueError):
        reconciliation_module.freeze(data, control)
    (data / 'raw/unsafe').symlink_to(tmp_path)
    with pytest.raises(ValueError):
        reconciliation_module.freeze(data, tmp_path / 'other')

def test_reconciler_never_imports_production_mapping(reconciliation_module):
    import ast
    tree = ast.parse(Path(reconciliation_module.__file__).read_text())
    imported = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imported += [
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    ]
    assert not any(name.startswith('embedding_data') for name in imported)

def test_self_consistent_candidate_corruption_is_independently_rejected(
    reconciliation_module, accepted
):
    fixture, controls, result = accepted
    directory = Path(result['directory'])
    file = directory / 'acs_code_lookup.parquet'
    codes = pl.read_parquet(file)
    codes = codes.with_columns(
        *[
            pl.when(pl.col('system').eq('naics')).then(pl.lit(['111110'])).otherwise(pl.col(name)
                                                                                     ).alias(name)
            for name in ('native_finest_candidates', 'canonical_finest_candidates')
        ]
    )
    codes.write_parquet(file)
    for profile in ('core', 'five_year', 'vintage'):
        file = directory / ('acs_' + profile + '_canonical.parquet')
        pl.read_parquet(file).with_columns(
            *[
                pl.lit(['111110']).alias('industry_' + name)
                for name in ('native_finest_candidates', 'canonical_finest_candidates')
            ]
        ).write_parquet(file)
    with pytest.raises(ValueError, match='membership|candidate'):
        reconciliation_module.reconcile(
            fixture.data_dir, 'independent', repin(directory), controls
        )

@pytest.mark.parametrize(
    'defect', [None, 'family', 'file', 'old', 'new', 'run', 'pin', 'stage7', 'stage8']
)
def test_historical_cli_rule_is_exact(reconciliation_module, defect):
    module = reconciliation_module
    old = '68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742'
    new = '32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3'
    cli = 'src/embedding_data/cli.py'
    values = dict(
        family='geography',
        name=cli,
        recorded=old,
        actual=new,
        request={
            'geography_run': 'stage5_geography_20261014',
            'geography_outputs_sha256':
                '5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d'
        },
        stage7={'files': {
            cli: {
                'sha256': new
            }
        }},
        stage8={'files': {
            cli: {
                'sha256': new
            }
        }}
    )
    if defect in {'family', 'file', 'old', 'new'}:
        values[{'file': 'name', 'old': 'recorded', 'new': 'actual'}.get(defect, defect)] = 'wrong'
    elif defect in {'run', 'pin'}:
        values['request']['geography_run'
                          if defect == 'run' else 'geography_outputs_sha256'] = 'wrong'
    elif defect in {'stage7', 'stage8'}:
        values[defect]['files'][cli]['sha256'] = 'wrong'
    assert module.historical_cli_allowed(**values) is (defect is None)

def test_original_prefix_batches_ignore_physical_row_group_layout(reconciliation_module, tmp_path):
    import hashlib
    source = tmp_path / 'source.parquet'
    companion = tmp_path / 'companion.parquet'
    original = pl.DataFrame({'value': range(140001)})
    original.write_parquet(source, row_group_size=1000)
    original.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64),
        pl.lit(hashlib.sha256(source.read_bytes()).hexdigest()).alias('source_parquet_sha256')
    ).select('value', 'source_row', 'source_parquet_sha256').write_parquet(
        companion, row_group_size=8192)
    assert reconciliation_module.original_prefix(source, companion) == 140001
