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
