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
    core = measured['sources']['acs/core']
    occupation = {
        r['occupation_mapping_status']: r['len']
        for r in core['codes']['occupation']['status']
    }
    assert occupation == {'documented_special': 2, 'mapped': 2}
    industry = {
        r['industry_mapping_status']: r['len']
        for r in core['codes']['industry']['status']
    }
    assert industry == {'mapped': 3, 'missing': 1}
    allocation = {
        r['industry_source_allocation_status']: r['len']
        for r in core['allocation']['QIND']['status']
    }
    assert allocation == {'allocated': 1, 'not_allocated_or_niu': 2, 'unavailable': 1}
    workplace = {r['workplace_area_status']: r['len'] for r in core['roles']['workplace']}
    assert workplace == {'foreign': 1, 'niu_or_unidentifiable': 2, 'territory': 1}
    five = measured['sources']['acs/five_year']['role_allocation_flags']
    territory = [r for r in five['workplace'] if r['workplace_area_status'] == 'territory']
    assert territory == [
        {
            'workplace_area_status': 'territory',
            'workplace_flag_source_geography_recoded': True,
            'workplace_flag_geographic_allocation': False,
            'workplace_flag_fractional_split': False,
            'len': 1
        }
    ]
    prior_pr = [r for r in five['migration'] if r['migration_area_status'] == 'territory']
    assert prior_pr[0]['migration_flag_source_geography_recoded'] is False

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
    ).select('value', 'source_row',
             'source_parquet_sha256').write_parquet(companion, row_group_size=8192)
    assert reconciliation_module.original_prefix(source, companion) == 140001

@pytest.mark.parametrize(
    'defect', ['factor_key', 'role_flags', 'scalar', 'published_county', 'published_msa']
)
def test_independent_annotation_controls_reject_consistent_mutations(
    reconciliation_module, accepted, defect
):
    fixture, controls, result = accepted
    directory = Path(result['directory'])
    if defect == 'factor_key':
        for name in ('acs_area_lookup', 'puma_county_factors'):
            file = directory / (name + '.parquet')
            frame = pl.read_parquet(file)
            frame.with_columns(pl.lit('wrong').alias('factor_key')).write_parquet(file)
        for profile in ('core', 'five_year', 'vintage'):
            file = directory / ('acs_' + profile + '_canonical.parquet')
            pl.read_parquet(file).with_columns(
                *[
                    pl.lit('wrong').alias(role + '_factor_key')
                    for role in ('residence', 'workplace', 'migration')
                ]
            ).write_parquet(file)
    elif defect == 'role_flags':
        file = directory / 'acs_core_canonical.parquet'
        pl.read_parquet(file).with_columns(
            pl.lit(False).alias('residence_flag_geographic_allocation')
        ).write_parquet(file)
    elif defect == 'scalar':
        file = directory / 'acs_code_lookup.parquet'
        pl.read_parquet(file).with_columns(
            pl.when(pl.col('system').eq('naics')).then(pl.lit('111110')).otherwise(
                pl.col('canonical_scalar_code')
            ).alias('canonical_scalar_code')
        ).write_parquet(file)
        for profile in ('core', 'five_year', 'vintage'):
            file = directory / ('acs_' + profile + '_canonical.parquet')
            pl.read_parquet(file).with_columns(
                pl.lit('111110').alias('industry_canonical_scalar_code')
            ).write_parquet(file)
    else:
        name, field = (
            'puma_county_factors', 'published_area_factor'
        ) if defect == 'published_county' else ('puma_msa_factors', 'published_percent_msa')
        file = directory / (name + '.parquet')
        pl.read_parquet(file).with_columns(pl.col(field).add(0.01)).write_parquet(file)
    with pytest.raises(ValueError):
        reconciliation_module.reconcile(
            fixture.data_dir, 'independent', repin(directory), controls
        )

def test_cli_failure_is_aggregate_json_and_explicit_paths_are_required(
    reconciliation_module, tmp_path
):
    from typer.testing import CliRunner
    runner = CliRunner()
    assert runner.invoke(reconciliation_module.app, ['freeze']).exit_code == 2
    result = runner.invoke(
        reconciliation_module.app, [
            'preservation', '--data-dir',
            str(tmp_path), '--control-dir',
            str(tmp_path / 'absent')
        ]
    )
    assert result.exit_code == 1
    assert json.loads(result.output)['status'] == 'failed'
    assert 'Traceback' not in result.output

def test_strict_constructors_survive_authenticated_fixture_setup(accepted):
    import dotenv
    import httpx
    import ipumspy

    from embedding_data import acs_mapping_references, ipums_census_access
    for function in (
        httpx.Client, httpx.AsyncClient, dotenv.dotenv_values, dotenv.load_dotenv, ipumspy
        .IpumsApiClient, acs_mapping_references.make_client, ipums_census_access.read_credential
    ):
        with pytest.raises(AssertionError):
            function()

def test_receipt_request_inventory_cannot_be_omitted(reconciliation_module, accepted):
    import hashlib
    fixture, controls, _ = accepted
    receipt = fixture.data_dir / 'raw/references/acs-mapping/independent_references/receipt.json'
    contents = json.loads(receipt.read_text())
    contents['request_files'].pop('geocorr_puma_totals_request')
    receipt.write_text(json.dumps(contents))
    manifest = fixture.data_dir / 'raw/manifest.jsonl'
    entries = [json.loads(line) for line in manifest.read_bytes().splitlines()]
    path = receipt.relative_to(fixture.data_dir / 'raw').as_posix()
    entries[-1]['sha256'] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    entries[-1]['size'] = receipt.stat().st_size
    assert entries[-1]['path'] == path
    prefix = (controls / 'manifest-prefix.jsonl').read_bytes()
    old_count = len(prefix.splitlines())
    manifest.write_bytes(
        prefix + b''.join((json.dumps(entry) + '\n').encode() for entry in entries[old_count:])
    )
    with pytest.raises(ValueError, match='request'):
        reconciliation_module.preservation(fixture.data_dir, controls)


@pytest.mark.parametrize('value,expected', [('001', '01'), ('072', '72'), ('110', None),
                                          ('1', None), ('099', None), (None, None)])
def test_composition_state_keeps_its_own_namespace(reconciliation_module, value, expected):
    if expected is None:
        with pytest.raises(ValueError):
            reconciliation_module.composition_state(value)
    else:
        assert reconciliation_module.composition_state(value) == expected


def test_malformed_preservation_evidence_raises_value_error(reconciliation_module, tmp_path):
    data = tmp_path / 'data'
    (data / 'raw').mkdir(parents=True)
    (data / 'derived').mkdir()
    manifest = data / 'raw/manifest.jsonl'
    manifest.write_bytes(b'')
    controls = tmp_path / 'controls'
    reconciliation_module.freeze(data, controls)
    manifest.write_bytes(b'{}\n')
    with pytest.raises(ValueError):
        reconciliation_module.preservation(data, controls)

@pytest.mark.parametrize(
    'defect', [
        'native_id', 'native_vintage', 'county_id', 'msa_id', 'reference_id', 'code_locator',
        'county_locator', 'area_reference_id'
    ]
)
def test_review_semantic_bindings_reject_consistent_repin(reconciliation_module, accepted, defect):
    fixture, controls, result = accepted
    directory = Path(result['directory'])
    if defect in {'native_id', 'native_vintage', 'reference_id', 'code_locator'}:
        field, value = {
            'native_id': ('native_node_id', 'wrong-native-node'),
            'native_vintage': ('native_vintage', 2022),
            'reference_id': ('reference_ids', ['wrong-original']),
            'code_locator': ('reference_locators', ['pums_industry_2017:ACS!C:E:row=999999'])
        }[defect]
        file = directory / 'acs_code_lookup.parquet'
        codes = pl.read_parquet(file)
        chosen = codes.filter(pl.col('source_scheme').eq('naics2017')).row(0, named=True)
        # The fixture's 113M category has unchanged finest memberships across vintages.
        if defect == 'native_vintage':
            other = codes.filter(
                pl.col('source_scheme').eq('naics2022').and_(
                    pl.col('source_token').eq(chosen['source_token'])
                )
            ).row(0, named=True)
            assert chosen['native_finest_candidates'] == other['native_finest_candidates']
        key = chosen['code_lookup_id']
        codes.with_columns(
            pl.when(pl.col('code_lookup_id').eq(key)).then(pl.lit(value)).otherwise(pl.col(field)
                                                                                    ).alias(field)
        ).write_parquet(file)
        for profile in ('core', 'five_year', 'vintage'):
            file = directory / ('acs_' + profile + '_canonical.parquet')
            pl.read_parquet(file).with_columns(
                pl.when(pl.col('industry_code_lookup_id').eq(key)).then(pl.lit(value)).otherwise(
                    pl.col('industry_' + field)
                ).alias('industry_' + field)
            ).write_parquet(file)
    elif defect == 'area_reference_id':
        file = directory / 'acs_area_lookup.parquet'
        frame = pl.read_parquet(file)
        frame.with_columns(pl.lit(['wrong:usa_puma']).alias('reference_ids')).write_parquet(file)
        for profile in ('core', 'five_year', 'vintage'):
            file = directory / ('acs_' + profile + '_canonical.parquet')
            pl.read_parquet(file).with_columns(
                *[
                    pl.lit(['wrong:usa_puma']).alias(role + '_reference_ids')
                    for role in ('residence', 'workplace', 'migration')
                ]
            ).write_parquet(file)
    else:
        name, field, value = {
            'county_id': ('puma_county_factors', 'county_node_id', 'wrong-county'),
            'msa_id': ('puma_msa_factors', 'msa_node_id', 'wrong-msa'),
            'county_locator': (
                'puma_county_factors', 'reference_locators', [
                    'geocorr_intersections:csv:row:999999'
                ]
            )
        }[defect]
        file = directory / (name + '.parquet')
        pl.read_parquet(file).with_columns(pl.lit(value).alias(field)).write_parquet(file)
    with pytest.raises(ValueError, match='native|node|reference|locator|provenance'):
        reconciliation_module.reconcile(
            fixture.data_dir, 'independent', repin(directory), controls
        )

def test_review_swapped_receipt_originals_rejected(reconciliation_module, accepted):
    import hashlib
    fixture, controls, _ = accepted
    receipt = fixture.data_dir / 'raw/references/acs-mapping/independent_references/receipt.json'
    contents = json.loads(receipt.read_text())
    originals = contents['originals']
    left, right = 'pums_industry_2017', 'pums_industry_2022'
    originals[left], originals[right] = originals[right], originals[left]
    receipt.write_text(json.dumps(contents))
    manifest = fixture.data_dir / 'raw/manifest.jsonl'
    prefix = (controls / 'manifest-prefix.jsonl').read_bytes()
    entries = [json.loads(line) for line in manifest.read_bytes()[len(prefix):].splitlines()]
    path = receipt.relative_to(fixture.data_dir / 'raw').as_posix()
    target = next(r for r in entries if r['path'] == path)
    target.update(
        sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(), size=receipt.stat().st_size
    )
    manifest.write_bytes(prefix + b''.join((json.dumps(r) + '\n').encode() for r in entries))
    with pytest.raises(ValueError, match='original|registered|citation'):
        reconciliation_module.preservation(fixture.data_dir, controls)

def test_review_freeze_failure_preserves_unowned_collision(
    reconciliation_module, tmp_path, monkeypatch
):
    data = tmp_path / 'data'
    (data / 'raw').mkdir(parents=True)
    (data / 'derived').mkdir()
    (data / 'raw/manifest.jsonl').write_bytes(b'')
    controls = tmp_path / 'controls'
    original_open = Path.open

    def collide(path, mode='r', *args, **kwargs):
        if path == controls / 'freeze.json' and mode == 'x':
            with original_open(controls / 'sentinel', 'w') as stream:
                stream.write('unowned')
            with original_open(path, 'w') as stream:
                stream.write('unowned collision')
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', collide)
    with pytest.raises(FileExistsError):
        reconciliation_module.freeze(data, controls)
    assert (controls / 'sentinel').read_text() == 'unowned'
    assert (controls / 'freeze.json').read_text() == 'unowned collision'
    assert not (controls / 'manifest-prefix.jsonl').exists()

@pytest.mark.parametrize('kind', ['code', 'county', 'code_columns'])
def test_review_existing_but_unrelated_locator_is_rejected(reconciliation_module, accepted, kind):
    import re
    fixture, controls, result = accepted
    directory = Path(result['directory'])
    if kind.startswith('code'):
        file = directory / 'acs_code_lookup.parquet'
        frame = pl.read_parquet(file)
        row = frame.filter(pl.col('source_scheme').eq('naics2017')).row(0, named=True)
        old = next(t for t in row['reference_locators'] if t.startswith('pums_industry_2017:'))
        original = fixture.data_dir / (
            'raw/references/acs-mapping/independent_references/'
            'pums_industry_2017.xlsx'
        )
        rows = reconciliation_module.workbook(original, 'ACS')
        number = next(
            n for n, r in enumerate(rows, 1) if len(r) >= 5 and r[2] and re.fullmatch(
                '[0-9]{4}', r[2]
            ) and r[2] != row['paired_census_code']
        )
        new = (old.replace('!C:E:', '!A:B:') if kind == 'code_columns' else
               re.sub(r'row=[0-9]+', f'row={number}', old))
        changed = sorted(new if t == old else t for t in row['reference_locators'])
        key = row['code_lookup_id']
        frame.with_columns(
            pl.when(pl.col('code_lookup_id').eq(key)).then(pl.lit(changed)).otherwise(
                pl.col('reference_locators')
            ).alias('reference_locators')
        ).write_parquet(file)
        for profile in ('core', 'five_year', 'vintage'):
            file = directory / ('acs_' + profile + '_canonical.parquet')
            pl.read_parquet(file).with_columns(
                pl.when(pl.col('industry_code_lookup_id').eq(key)).then(pl.lit(changed)).otherwise(
                    pl.col('industry_reference_locators')
                ).alias('industry_reference_locators')
            ).write_parquet(file)
    else:
        file = directory / 'puma_county_factors.parquet'
        frame = pl.read_parquet(file)
        row = frame.filter(pl.col('area_type').eq('residence')).row(0, named=True)
        old = next(t for t in row['reference_locators'] if t.startswith('geocorr_intersections:'))
        other = next(
            r for r in frame.filter(pl.col('area_type').eq('residence')).to_dicts()
            if r['county_geoid'] != row['county_geoid']
        )
        new = next(
            t for t in other['reference_locators'] if t.startswith('geocorr_intersections:')
        )
        changed = sorted(new if t == old else t for t in row['reference_locators'])
        frame.with_columns(
            pl.when(
                pl.col('factor_key').eq(row['factor_key']).and_(
                    pl.col('county_geoid').eq(row['county_geoid'])
                )
            ).then(pl.lit(changed)).otherwise(pl.col('reference_locators')).alias(
                'reference_locators'
            )
        ).write_parquet(file)
    with pytest.raises(ValueError, match='locator|reference'):
        reconciliation_module.reconcile(
            fixture.data_dir, 'independent', repin(directory), controls
        )


def test_independent_actual_geocorr_csv_decoding(reconciliation_module, tmp_path):
    from acs_mapping_fixtures import genuine_geocorr_bytes
    body = genuine_geocorr_bytes()
    file = tmp_path / 'geocorr_intersections.csv'
    file.write_bytes(body)
    rows = reconciliation_module.csv_rows(file)
    assert len(rows) == 4690 and len({r['state'] for r in rows}) == 52
    assert any('ó' in r['PUMA22name'] or 'ó' in r['CountyName'] for r in rows)
    assert reconciliation_module.geocorr_text(file)[1] == 'cp1252'
    assert file.read_bytes() == body

@pytest.mark.parametrize('body', [b'\x81', b'\xff\xfea\x00b\x00'])
def test_independent_geocorr_rejects_unsupported_encoding(reconciliation_module, tmp_path, body):
    file = tmp_path / 'geocorr_intersections.csv'
    file.write_bytes(body)
    with pytest.raises(ValueError, match='encoding'):
        reconciliation_module.geocorr_text(file)


def test_independent_geocorr_decoder_is_reference_scoped(reconciliation_module, tmp_path):
    file = tmp_path / 'source.csv'
    file.write_bytes(b'\xf3')
    with pytest.raises(ValueError, match='registered Geocorr'):
        reconciliation_module.geocorr_text(file)


@pytest.fixture
def accepted_source_roles(reconciliation_module, tmp_path, monkeypatch):
    from acs_mapping_fixtures import _reconciliation_delivery

    def source_roles(profile, ddi, frame):
        ddi, frame = _reconciliation_delivery(profile, ddi, frame)
        variable = next(v for v in ddi['variables'] if v['name'] == 'MIGPLAC1')
        variable['categories'].extend([
            {'value': '413', 'label': 'United Kingdom (excluding England: 2005ACS)'},
            {'value': '465', 'label': 'USSR'}])
        next(c for c in variable['categories'] if c['value'] == '988')['label'] = (
            'Suppressed for data year 2022 for select cases')
        if profile == 'core':
            frame = frame.with_columns(pl.Series('MIGPLAC1', [413, 465, 1]),
                                       pl.Series('MIGPUMA1', [1, 1, 100]))
        elif profile == 'five_year':
            frame = frame.with_columns(pl.Series('MIGPLAC1', [110, 1, 988, 413, 465]),
                                       pl.Series('MIGPUMA1', [2, 100, 88888, 1, 1]))
        return ddi, frame

    fixture = seed_reconciliation_inputs(tmp_path, monkeypatch, prepare_acs=source_roles)
    controls = tmp_path / 'controls'
    reconciliation_module.freeze(fixture.data_dir, controls)
    result = build_fixture_mapping(fixture, 'source_roles', monkeypatch)
    return fixture, controls, result


def test_source_roles_genuine_build_verify_replay_and_independent(
        reconciliation_module, accepted_source_roles, monkeypatch):
    from embedding_data import acs_mapping_bundle

    fixture, controls, result = accepted_source_roles
    directory = Path(result['directory'])
    acs_mapping_bundle.verify_bundle(directory, fixture.data_dir,
                                    expected_outputs_sha256=result['outputs_sha256'])
    measured = reconciliation_module.reconcile(
        fixture.data_dir, 'source_roles', result['outputs_sha256'], controls)
    assert measured['failure_count'] == 0
    companion = pl.read_parquet(directory / 'acs_five_year_canonical.parquet')
    suppressed = companion.filter(pl.col('MIGPLAC1').eq(988))
    assert suppressed.height == 1
    row = suppressed.row(0, named=True)
    assert row['MULTYEAR'] == 2022 and row['STATEFIP'] == 1
    assert row['migration_area_status'] == 'documented_unavailable'
    assert row['migration_factor_key'] is None and row['migration_state_fips'] is None
    for flag in ('geographic_allocation', 'fractional_split', 'source_geography_recoded'):
        assert row['migration_flag_' + flag] is False
    assert row['migration_source_allocation_evidence_status'] == 'unavailable'
    for field in ('PWSTATE2', 'MIGPLAC1', 'MIGPUMA1'):
        source = pl.read_parquet(fixture.data_dir / fixture.sources['acs/five_year']['parquet'])
        assert companion[field].equals(source[field])
    replay = acs_mapping_bundle.build(
        fixture.data_dir, 'source_roles_replay', fixture.request,
        'source_roles_references', expected_reference_receipt_sha256=json.loads(
            (directory / 'inputs.json').read_text())['references']['receipt_sha256'])
    replay_dir = Path(replay['directory'])
    for file in directory.glob('*.parquet'):
        assert pl.read_parquet(file).equals(pl.read_parquet(replay_dir / file.name))


@pytest.mark.parametrize('damage', ['locator', 'status', 'reason', 'component', 'raw_pair',
                                    'ddi_label', 'guide', 'ipums'])
def test_independent_source_role_semantics_reject_mutations(
        reconciliation_module, accepted_source_roles, damage):
    fixture, _, result = accepted_source_roles
    directory = Path(result['directory'])
    inputs = json.loads((directory / 'inputs.json').read_text())
    files = reconciliation_module.reference_files(fixture.data_dir, inputs['references'])
    if damage in {'guide', 'ipums'}:
        kind = 'pums_five_year_guide' if damage == 'guide' else 'usa_migplac1'
        files[kind].write_bytes(files[kind].read_bytes() + b' changed')
    elif damage == 'ddi_label':
        variable = next(v for v in inputs['sources']['acs/five_year']['ddi']['variables']
                        if v['name'] == 'MIGPLAC1')
        next(c for c in variable['categories'] if c['value'] == '988')['label'] += ' changed'
    else:
        file = directory / 'acs_area_lookup.parquet'
        frame = pl.read_parquet(file)
        field, value = {
            'locator': ('reference_locators', ['pums_five_year_guide:physical-page=19:X.M']),
            'status': ('area_status', 'foreign'), 'reason': ('status_reason', 'No migration'),
            'component': ('component_year', 2021), 'raw_pair': ('source_area_code', '00001')
        }[damage]
        frame = frame.with_columns(pl.when(pl.col('area_status').eq('documented_unavailable'))
                                   .then(pl.lit(value, dtype=frame.schema[field]))
                                   .otherwise(pl.col(field)).alias(field))
        frame.write_parquet(file)
    expected = ('reference locator targets' if damage == 'locator' else 'suppression')
    with pytest.raises(ValueError, match=expected):
        reconciliation_module.geographic_provenance(directory, files, inputs)


@pytest.fixture
def accepted_industry_pairs(reconciliation_module, tmp_path, monkeypatch):
    from acs_mapping_fixtures import _reconciliation_delivery

    def duplicate_pairs(profile, ddi, frame):
        ddi, frame = _reconciliation_delivery(profile, ddi, frame)
        if profile == 'vintage':
            frame = pl.concat([frame] * 4)
        row_count = frame.select(pl.len()).collect().item()
        pairs = [[770, 7570, 2970, 2980][n % 4] for n in range(row_count)]
        tokens = [{770: '23', 7570: '55', 2970: '33299M', 2980: '332MZ'}[pair]
                  for pair in pairs]
        return ddi, frame.with_columns(pl.Series('IND', pairs), pl.Series('INDNAICS', tokens))

    fixture = seed_reconciliation_inputs(tmp_path, monkeypatch, prepare_acs=duplicate_pairs)
    controls = tmp_path / 'controls'
    reconciliation_module.freeze(fixture.data_dir, controls)
    result = build_fixture_mapping(fixture, 'industry_pairs', monkeypatch)
    return fixture, controls, result


def industry_pair_cases():
    for year in (2017, 2022):
        editions = [(f'pums_industry_{year}', 'ACS')]
        if year == 2022:
            editions += [('pums_annual_2024', 'Industry'), ('pums_five_year_2024', 'Industry')]
        for kind, sheet in editions:
            management_rows = (265, 267) if year == 2017 else (259, 261)
            for pair, token, numbers in [('0770', '23', (40, 42)),
                                         ('7570', '55', management_rows)]:
                yield year, kind, sheet, pair, token, numbers


def canonical_industry_pair_cases():
    for year in (2017, 2022):
        sheet = '2017 Census Industry Code List' if year == 2017 else '2022 Census Ind Code List '
        for pair, token, numbers in [('0770', '23', (28, 30)),
                                     ('7570', '55', (253, 255) if year == 2017 else (249, 251))]:
            yield year, f'census_industry_{year}', sheet, pair, token, numbers


def industry_provenance_inputs(module, fixture, result):
    directory = Path(result['directory'])
    inputs = json.loads((directory / 'inputs.json').read_text())
    selected, _ = module.upstreams(fixture.data_dir, inputs)
    files = module.reference_files(fixture.data_dir, inputs['references'])
    code_directory = fixture.data_dir / 'derived/codes' / fixture.request.codes_run
    codes = pl.read_parquet(directory / 'acs_code_lookup.parquet')
    return codes, files, inputs, selected, fixture.data_dir, code_directory


def test_industry_agreeing_duplicate_rows_build_verify_replay_and_independent(
        reconciliation_module, accepted_industry_pairs):
    from embedding_data import acs_mapping_bundle

    fixture, controls, result = accepted_industry_pairs
    module = reconciliation_module
    directory = Path(result['directory'])
    arguments = industry_provenance_inputs(module, fixture, result)
    codes, files = arguments[:2]
    for year, kind, sheet, pair, _, numbers in canonical_industry_pair_cases():
        row = codes.filter(pl.col('native_vintage').eq(year)
                           .and_(pl.col('paired_census_code').eq(pair))).row(0, named=True)
        assert {module.locator_target(v) for v in row['reference_locators']
                if v.startswith(kind + ':')} == {
                    f'{kind}:{sheet}!D:E:row:{n}' for n in numbers}
    for year, kind, sheet, pair, token, numbers in industry_pair_cases():
        row = codes.filter(pl.col('native_vintage').eq(year)
                           .and_(pl.col('paired_census_code').eq(pair))).row(0, named=True)
        assert row['source_token'] == token
        original = module.workbook(files[kind], sheet)
        assert [n for n, r in enumerate(original, 1) if r[2:5] == (pair, token, token)] == list(
            numbers)
        targets = [module.locator_target(v) for v in row['reference_locators']]
        assert {v for v in targets if v.startswith(kind + ':')} == {
            f'{kind}:{sheet}!C:E:row:{n}' for n in numbers}
        assert row['reference_locators'] == sorted(set(row['reference_locators']))
    rejected = module.code_provenance(*arguments)
    report = json.loads((directory / 'report.json').read_text())
    assert report['classifications']['reference_diagnostics'][
        'rejected_industry_membership_assertions'] == rejected
    assert len(rejected) == 2
    for pair, count_ in [('2970', 4), ('2980', 9)]:
        row = codes.filter(pl.col('native_vintage').eq(2017)
                           .and_(pl.col('paired_census_code').eq(pair))).row(0, named=True)
        assert len(row['native_finest_candidates']) == count_
        assert row['flag_vintage_crosswalk'] is True
    acs_mapping_bundle.verify_bundle(directory, fixture.data_dir,
                                    expected_outputs_sha256=result['outputs_sha256'])
    measured = module.reconcile(fixture.data_dir, 'industry_pairs', result['outputs_sha256'],
                               controls)
    assert measured['failure_count'] == 0
    replay = acs_mapping_bundle.build(
        fixture.data_dir, 'industry_pairs_replay', fixture.request, 'industry_pairs_references',
        expected_reference_receipt_sha256=arguments[2]['references']['receipt_sha256'])
    replay_dir = Path(replay['directory'])
    acs_mapping_bundle.verify_bundle(replay_dir, fixture.data_dir,
                                    expected_outputs_sha256=replay['outputs_sha256'])
    for file in directory.glob('*.parquet'):
        assert pl.read_parquet(file).equals(pl.read_parquet(replay_dir / file.name))
    compared = acs_mapping_bundle.compare_runs(directory, replay_dir)
    assert compared['equal'] is True and compared['substantive_report_equal'] is True
    assert module.reconcile(fixture.data_dir, 'industry_pairs_replay',
                            replay['outputs_sha256'], controls)['failure_count'] == 0


def test_industry_duplicate_provenance_rejects_incomplete_or_unrelated_locators(
        reconciliation_module, accepted_industry_pairs):
    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    codes, *arguments = industry_provenance_inputs(module, fixture, result)
    for year, kind, sheet, pair, _, numbers in [*industry_pair_cases(),
                                                *canonical_industry_pair_cases()]:
        columns = 'D:E' if kind.startswith('census_') else 'C:E'
        chosen = codes.filter(pl.col('native_vintage').eq(year)
                              .and_(pl.col('paired_census_code').eq(pair)))
        row = chosen.row(0, named=True)
        for number in numbers:
            target = f'{kind}:{sheet}!{columns}:row:{number}'
            changed = [v for v in row['reference_locators'] if module.locator_target(v) != target]
            assert len(changed) == len(row['reference_locators']) - 1
            damaged = chosen.with_columns(pl.lit(changed).alias('reference_locators'))
            with pytest.raises(ValueError, match='reference locator targets'):
                module.code_provenance(damaged, *arguments)
        other_number = 12 if kind.startswith('census_') else 25
        original = module.workbook(arguments[0][kind], sheet)
        assert original[other_number - 1][3 if kind.startswith('census_') else 2] == '0170'
        for extra in (f'{kind}:{sheet}!{columns}:row:999999',
                      f'{kind}:{sheet}!{columns}:row:{other_number}',
                      f'{kind}:{sheet}!A:E:row:{numbers[0]}',
                      f'{kind}:unrelated!{columns}:row:{numbers[0]}'):
            changed = sorted([*row['reference_locators'], extra])
            damaged = chosen.with_columns(pl.lit(changed).alias('reference_locators'))
            with pytest.raises(ValueError, match='reference locator targets'):
                module.code_provenance(damaged, *arguments)


def test_industry_duplicate_provenance_rejects_absent_or_conflicting_source_assertions(
        reconciliation_module, accepted_industry_pairs, tmp_path):
    from acs_mapping_fixtures import write_public_layout

    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    codes, files, *arguments = industry_provenance_inputs(module, fixture, result)
    for year, kind, sheet, pair, _, numbers in industry_pair_cases():
        chosen = codes.filter(pl.col('native_vintage').eq(year)
                              .and_(pl.col('paired_census_code').eq(pair)))
        original = module.workbook(files[kind], sheet)
        for damage in ('absent', 'token', 'expression', 'additional_assertion'):
            rows = {str(n): list(r) for n, r in enumerate(original, 1)}
            if damage == 'absent':
                for n in numbers:
                    rows[str(n)][2] = None
            elif damage == 'additional_assertion':
                rows['25'][2:5] = [pair, '111', '111']
            else:
                rows[str(numbers[1])][4 if damage == 'token' else 3] = '111'
            changed = tmp_path / f'{kind}-{pair}-{damage}.xlsx'
            write_public_layout(changed, {'sheets': {sheet: {'width': 5, 'rows': rows}}})
            with pytest.raises(ValueError, match='industry|D10'):
                module.code_provenance(chosen, {**files, kind: changed}, *arguments)


def test_canonical_census_industry_rejects_absent_or_conflicting_assertions(
        reconciliation_module, accepted_industry_pairs, tmp_path):
    from copy import deepcopy

    from acs_mapping_fixtures import write_public_layout

    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    codes, files, inputs, selected, data_dir, code_directory = industry_provenance_inputs(
        module, fixture, result)
    for year, kind, sheet, pair, _, numbers in canonical_industry_pair_cases():
        chosen = codes.filter(pl.col('native_vintage').eq(year)
                              .and_(pl.col('paired_census_code').eq(pair)))
        citation = selected['ipums']['references']['receipt']['originals'][kind]['citation']
        original = module.workbook(data_dir / 'raw' / citation['path'], sheet)
        for damage in ('absent', 'expression', 'additional_assertion'):
            rows = {str(n): list(r) for n, r in enumerate(original, 1)}
            if damage == 'absent':
                for n in numbers:
                    rows[str(n)][3] = None
            elif damage == 'expression':
                rows[str(numbers[1])][4] = '111'
            else:
                rows['12'][3:5] = [pair, '111']
            changed = data_dir / 'raw' / f'{kind}-{pair}-{damage}.xlsx'
            write_public_layout(changed, {'sheets': {sheet: {'width': len(original[0]),
                                                            'rows': rows}}})
            # Re-pin test bytes to reach the independent semantic check.
            mutated = deepcopy(selected)
            mutated['ipums']['references']['receipt']['originals'][kind]['citation'] = {
                **citation, 'path': changed.relative_to(data_dir / 'raw').as_posix(),
                **module.record(changed)}
            with pytest.raises(ValueError, match='Census|D10'):
                module.code_provenance(chosen, files, inputs, mutated, data_dir, code_directory)


def test_d10_independent_rejection_diagnostics_cannot_be_rehashed(
        reconciliation_module, accepted_industry_pairs):
    from copy import deepcopy

    fixture, controls, result = accepted_industry_pairs
    directory = Path(result['directory'])
    file = directory / 'report.json'
    original = json.loads(file.read_text())
    for damage in ('omit_all', 'null_container', 'omit_container', 'omit', 'cause', 'expression',
                   'members', 'hash', 'locator', 'support',
                   'vintage', 'tuple', 'token', 'omit_rejected', 'omit_support',
                   'invent_rejected', 'positive_member', 'positive_hash', 'column', 'sheet',
                   'positive_row', 'rejected_row'):
        report = deepcopy(original)
        rows = report['classifications']['reference_diagnostics'][
            'rejected_industry_membership_assertions']
        if damage == 'omit_all':
            report['classifications']['reference_diagnostics'].pop(
                'rejected_industry_membership_assertions')
        elif damage == 'null_container':
            report['classifications']['reference_diagnostics'] = None
        elif damage == 'omit_container':
            report.pop('classifications')
        elif damage == 'omit':
            rows.pop()
        elif damage == 'cause':
            rows[0]['cause'] = 'confidentiality'
        elif damage in {'vintage', 'tuple', 'token'}:
            field, value = {'vintage': ('native_vintage', 2022),
                            'tuple': ('paired_census_code', '2980'),
                            'token': ('source_token', '332MZ')}[damage]
            rows[0][field] = value
        elif damage == 'omit_rejected':
            rows[0].pop('rejected_assertion')
        elif damage == 'omit_support':
            rows[0]['supporting_assertions'].pop()
        elif damage == 'invent_rejected':
            rows.append(deepcopy(rows[0]))
        else:
            positive = damage in {'support', 'positive_member', 'positive_hash', 'column',
                                   'sheet', 'positive_row'}
            assertion = rows[0]['supporting_assertions'][1] if positive else rows[0][
                'rejected_assertion']
            field, value = {
                'expression': ('expression', '332996'),
                'members': ('native_finest_candidates', ['332996']),
                'hash': ('original_sha256', '0' * 64),
                'locator': ('reference_locator', 'census_industry_2017:wrong!D:E:row=83'),
                'support': ('reference_locator',
                            'census_industry_2017:2017 Census Industry Code List!D:E:row=83'),
                'positive_member': ('native_finest_candidates', ['332992']),
                'positive_hash': ('original_sha256', '0' * 64),
                'column': ('reference_locator',
                           'census_industry_2017:2007 - 2017 Industry Crosswalk!H:J:row=79'),
                'sheet': ('reference_locator', 'census_industry_2017:wrong!I:K:row=79'),
                'positive_row': ('reference_locator',
                                 'census_industry_2017:2007 - 2017 Industry Crosswalk!I:K:row=80'),
                'rejected_row': ('reference_locator',
                                 'census_industry_2017:2017 Census Industry Code List!D:E:row=84'),
            }[damage]
            assertion[field] = value
        file.write_text(json.dumps(report))
        with pytest.raises(ValueError, match='D10 industry rejection diagnostics'):
            reconciliation_module.reconcile(fixture.data_dir, 'industry_pairs', repin(directory),
                                            controls)


def test_d10_independent_pair_candidate_and_positive_support_bounds(
        reconciliation_module, accepted_industry_pairs):
    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    codes, *arguments = industry_provenance_inputs(module, fixture, result)
    chosen = codes.filter(pl.col('native_vintage').eq(2017)
                          .and_(pl.col('paired_census_code').eq('2970')))
    mutations = {
        'source_token': '332MZ', 'paired_census_code': '2980', 'native_vintage': 2022,
        'native_finest_candidates': ['332992'],
        'reference_locators': ['census_industry_2017:2017 Census Industry Code List!D:E:row=83']}
    for field, value in mutations.items():
        damaged = chosen.with_columns(pl.lit(value, dtype=chosen.schema[field]).alias(field))
        with pytest.raises(ValueError):
            module.candidate_memberships(damaged, arguments[0], arguments[-1])
            module.code_provenance(damaged, *arguments)

    for pair in ('2970', '2980'):
        chosen = codes.filter(pl.col('native_vintage').eq(2017)
                              .and_(pl.col('paired_census_code').eq(pair)))
        original = chosen['reference_locators'][0].to_list()
        for kind in ('pums_industry_2017', 'census_industry_2017'):
            removed = [v for v in original if v.startswith(kind + ':')]
            assert len(removed) == 1
            changed = [v for v in original if v not in removed]
            damaged = chosen.with_columns(pl.lit(changed).alias('reference_locators'))
            with pytest.raises(ValueError, match='reference locator targets'):
                module.code_provenance(damaged, *arguments)


def test_d10_independent_source_and_unrelated_membership_mutations(
        reconciliation_module, accepted_industry_pairs, tmp_path):
    from copy import deepcopy

    from test_acs_code_references import rewrite_public_cell

    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    _, files, _, selected, data_dir, code_directory = industry_provenance_inputs(
        module, fixture, result)
    module.industry_membership_authorities(files, selected, data_dir, code_directory)
    mutations = [
        ('pums_industry_2017', 'ACS', (95, 3), '332992'),
        ('pums_industry_2017', 'ACS', (96, 4), '33299M'),
        ('census_industry_2017', '2017 Census Industry Code List', (83, 4), '332996'),
        ('census_industry_2017', '2017 Census Industry Code List', (84, 3), '2981'),
        ('census_industry_2017', '2007 - 2017 Industry Crosswalk', (79, 8), '2971'),
        ('census_industry_2017', '2007 - 2017 Industry Crosswalk', (79, 8), ''),
        ('census_industry_2017', '2007 - 2017 Industry Crosswalk', (80, 9), '3325'),
        ('census_industry_2017', '2007 - 2017 Industry Crosswalk', (9, 8), '2022 Census Code'),
        ('census_industry_2022', '2022 Census Ind Code List ', (12, 4), '112'),
        ('census_industry_2022', '2022 Census Ind Code List ', (4, 3), '2017 Census Code')]
    for index, (kind, sheet, address, value) in enumerate(mutations):
        changed = data_dir / 'raw' / f'd10-variant-{index}.xlsx'
        rewrite_public_cell(files[kind], changed, sheet, address, value)
        altered = deepcopy(selected)
        if kind.startswith('census_'):
            citation = altered['ipums']['references']['receipt']['originals'][kind]['citation']
            citation.update(path=changed.relative_to(data_dir / 'raw').as_posix(),
                            **module.record(changed))
        with pytest.raises(ValueError, match='D10|industry|Census'):
            module.industry_membership_authorities({**files, kind: changed}, altered,
                                                   data_dir, code_directory)

    for kind in ('pums_industry_2017', 'census_industry_2017'):
        changed = data_dir / 'raw' / f'{kind}-repackaged.xlsx'
        changed.write_bytes(files[kind].read_bytes() + b' ')
        altered = deepcopy(selected)
        if kind.startswith('census_'):
            altered['ipums']['references']['receipt']['originals'][kind]['citation'].update(
                path=changed.relative_to(data_dir / 'raw').as_posix(), **module.record(changed))
        with pytest.raises(ValueError, match='D10 industry original pin'):
            module.industry_membership_authorities({**files, kind: changed}, altered,
                                                   data_dir, code_directory)


def test_all_admitted_public_classification_keys_have_independent_support(
        reconciliation_module, accepted_industry_pairs, tmp_path, monkeypatch):
    '''Synthetic reference-only keys cover every admitted category and full D8 originals.'''
    from acs_mapping_fixtures import seed_mapping_references
    from test_acs_source_rules import public_files

    from embedding_data.acs_code_mapping import build_code_lookup
    from embedding_data.acs_code_references import read_code_evidence
    from embedding_data.acs_mapping_inputs import select_inputs
    from embedding_data.acs_mapping_references import check_cached_snapshot

    fixture, _, result = accepted_industry_pairs
    module = reconciliation_module
    _, files, inputs, selected, data_dir, code_directory = industry_provenance_inputs(
        module, fixture, result)
    originals = tmp_path / 'all-public-originals'
    originals.mkdir()
    overrides = {**files, **public_files.__wrapped__(originals)}
    snapshot_dir = tmp_path / 'all-public-snapshot'
    snapshot_dir.mkdir()
    seeded = seed_mapping_references(snapshot_dir, monkeypatch, original_overrides=overrides,
                                     data_dir=data_dir, reference_id='all_public_support')
    snapshot = check_cached_snapshot(data_dir, seeded.reference_id)
    forbid_external_access(monkeypatch)
    authenticated = select_inputs(data_dir, fixture.request)
    evidence = read_code_evidence(snapshot, authenticated)
    keys = evidence.metadata.select(
        'system', 'source_scheme', 'paired_census_code', 'source_token')
    codes = build_code_lookup(keys, evidence, authenticated)
    counts = codes.group_by('system', 'source_scheme').len().sort('system', 'source_scheme')
    print(json.dumps({'public_reference_key_scope': counts.to_dicts(), 'total_keys': codes.height},
                     sort_keys=True))
    assert codes.height == keys.height
    assert set(codes['source_scheme']) == {'naics2017', 'naics2022', 'soc2018'}
    module.independent_lookup(codes, snapshot.files)
    candidates = module.candidate_memberships(codes, snapshot.files, code_directory)
    rejected = module.code_provenance(codes, dict(snapshot.files), inputs, selected,
                                      data_dir, code_directory)
    assert rejected == evidence.diagnostics['rejected_industry_membership_assertions']
    assert candidates['D8_rejected_occupation_html_assertions'] == evidence.diagnostics[
        'rejected_occupation_html_assertions']
    assert len(rejected) == 2
    assert len(candidates['D8_rejected_occupation_html_assertions']) == 3
