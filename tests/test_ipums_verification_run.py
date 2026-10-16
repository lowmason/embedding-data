'''Complete synthetic deliveries exercise offline publication and detached replay.'''

import gzip
import importlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import httpx
import polars as pl
import pytest
from ipums_fixtures import bls_response, reference_originals
from test_ipums_acceptance import PROFILES, delivery

from embedding_data import ipums_references as refs
from embedding_data import manifest, paths, target_io

def runner():
    return importlib.import_module('embedding_data.ipums_verification_run')


def forbidden(*args, **kwargs):
    raise AssertionError('offline operation constructed a client or loaded dotenv')


@pytest.fixture
def complete_inputs(tmp_path, monkeypatch):
    root = tmp_path / 'data'
    originals = reference_originals(tmp_path / 'originals', refs.REGISTRY)
    originals['cps_employment'].write_text(json.dumps(bls_response()))
    originals['usa_samples'].write_text(
        '<table><tr><th>Sample ID</th><th>Description</th></tr>'
        + ''.join(f'<tr><td>{key}</td><td>{label}</td></tr>' for key, label in
                  delivery()[-1].items()) + '</table>')
    for year in (2023, 2024):
        file = originals[f'acs_{year}_b23025_metadata']
        file.write_text(file.read_text().replace(
            '<td>B23025_004E</td>', '<td>B23025_004E</td>'
            '<td>Estimate!!Civilian labor force:!!Employed</td>')
            + '<p>Population 16 years and over</p>')
    monkeypatch.setattr(refs, 'REGISTRY', {
        kind: replace(reference, sha256=manifest.sha256_file(originals[kind]))
        if reference.sha256 else reference for kind, reference in refs.REGISTRY.items()})
    for kind, original in originals.items():
        refs.import_reference(root, 'references', kind, original)
    selections = {}
    for index, (source, set_name) in enumerate(PROFILES, 1):
        definition, ddi, frame, _, _, _ = delivery(source, set_name)
        frame = frame.with_columns(pl.lit(30).alias('AGE'))
        if source == 'acs':
            frame = frame.with_columns(pl.lit(10).alias('EMPSTATD'),
                                       pl.lit('31M').alias('INDNAICS'),
                                       pl.lit('1110XX').alias('OCCSOC'),
                                       pl.lit('100.25').alias('PERWT'))
        else:
            frame = frame.with_columns(pl.lit(10).alias('EMPSTAT'),
                                       pl.lit('0170').alias('IND'),
                                       pl.lit('0010').alias('OCC'))
            if set_name == 'monthly':
                frame = frame.with_columns(pl.lit('123.5').alias('WTFINL'))
            else:
                frame = frame.with_columns(pl.lit('0180').alias('INDLY'),
                                           pl.lit('0010').alias('OCCLY'))
        collection = 'usa' if source == 'acs' else 'cps'
        name = f'{collection}_{index}'
        directory = root / 'raw' / source / set_name / name
        directory.mkdir(parents=True)
        (directory / 'extract.json').write_text(json.dumps(definition))
        xml = ET.Element('codeBook', version='2.5')
        study = ET.SubElement(xml, 'stdyDscr')
        info = ET.SubElement(study, 'stdyInfo')
        for note in ddi['study_notes']:
            ET.SubElement(info, 'notes').text = note
        summary = ET.SubElement(info, 'sumDscr')
        for note in ddi['time_notes']:
            ET.SubElement(summary, 'timePrd', date=note['date']).text = note['text']
        data = ET.SubElement(xml, 'dataDscr')
        for variable in ddi['variables']:
            element = ET.SubElement(data, 'var', name=variable['name'], dcml='2')
            ET.SubElement(element, 'labl').text = variable['label']
            for category in variable['categories']:
                item = ET.SubElement(element, 'catgry')
                ET.SubElement(item, 'catValu').text = category['value']
                ET.SubElement(item, 'labl').text = category['label']
        ET.ElementTree(xml).write(directory / f'{name}.xml')
        csv = frame.collect().write_csv()
        with gzip.open(directory / f'{name}.csv.gz', 'wt') as stream:
            stream.write(csv)
        for file in directory.iterdir():
            entry = manifest.describe_file(file, root / 'raw', retrieved_at=datetime.now(UTC),
                                           client='fixture', client_version='1',
                                           collection=collection, extract_number=index,
                                           samples=list(definition['samples']))
            manifest.append_entries(paths.manifest_path(root), [entry])
        # Independent CSV import states the historical storage contract explicitly.
        overrides = {'INCWAGE_CPIU_2010': pl.Float64}
        if source == 'acs':
            overrides.update(INDNAICS=pl.String, OCCSOC=pl.String)
        converted = pl.read_csv(csv.encode(), schema_overrides=overrides)
        if source == 'cps':
            codes = [c for c in ['IND', 'OCC', 'INDLY', 'OCCLY'] if c in converted.columns]
            converted = converted.with_columns(pl.col(codes).cast(pl.String).str.zfill(4))
        relative = f'derived/{source}/{set_name}/{name}.parquet'
        parquet = root / relative
        parquet.parent.mkdir(parents=True)
        converted.write_parquet(parquet)
        selections[f'{source}/{set_name}'] = {'delivery': name, 'parquet': relative}
    selection = tmp_path / 'selection.json'
    selection.write_text(json.dumps(selections))
    import dotenv

    from embedding_data import acs_benchmark_extract, cps_benchmark_extract
    for module in (acs_benchmark_extract, cps_benchmark_extract):
        monkeypatch.setattr(module, 'IpumsApiClient', forbidden)
        monkeypatch.setattr(module, 'load_dotenv', forbidden)
    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    from embedding_data import ipums_census_access
    monkeypatch.setattr(ipums_census_access, 'dotenv_values', forbidden)
    monkeypatch.setattr(ipums_census_access, 'read_credential', forbidden)
    monkeypatch.setattr(httpx, 'Client', forbidden)
    monkeypatch.setattr(refs, 'make_client', forbidden)
    return root, selection


def test_complete_five_profile_raw_to_report_and_replay(complete_inputs):
    root, selection = complete_inputs
    run = runner().measure(root, 'first', 'references', selection)
    pin = manifest.sha256_file(run / 'outputs.json')
    assert runner().verify_bundle(run, root, expected_outputs_sha256=pin)['status'] == 'verified'
    assert len(list(run.iterdir())) == 12
    samples = pl.read_parquet(run / 'sample_counts.parquet')
    counts = samples.group_by('extract_key').agg(pl.col('rows').sum()).sort('extract_key')
    assert counts.rows() == [
        ('acs/core', 3), ('acs/five_year', 5), ('acs/vintage', 1),
        ('cps/asec', 2), ('cps/monthly', 2)]
    weights = pl.read_parquet(run / 'weight_diagnostics.parquet')
    assert weights.filter((pl.col('set_name') == 'core') & (pl.col('variable') == 'PERWT'))[
        'sum_exact'].item() == '300.75'
    industry = pl.read_parquet(run / 'industry_frequencies.parquet')
    assert industry.select('variable', 'code', 'rows', 'membership').rows() == [
        ('IND', '0170', 2, 'shared_ambiguous'), ('INDLY', '0180', 2, 'shared_ambiguous')]
    comparisons = pl.read_parquet(run / 'employment_comparisons.parquet')
    assert comparisons.filter((pl.col('source') == 'acs') & (pl.col('state_fips') == '01'))[
        'measured'].to_list() == [200.5, 100.25, 150.375]
    monthly = comparisons.filter((pl.col('source') == 'cps')
                                 & pl.col('month').is_in([1, 2]) & (pl.col('year') == 2025))
    assert monthly.select('measured', 'published', 'gap', 'comparison_status').rows() == [
        (123.5, 100500.0, -100376.5, 'matched'),
        (123.5, 100500.0, -100376.5, 'matched')]
    assert weights.height == 407
    inventory = pl.read_parquet(run / 'variable_inventory.parquet')
    replicates = inventory.filter(pl.col('replicate'))
    assert replicates.filter(pl.col('extract_key') == 'acs/core').height == 80
    assert replicates.filter(pl.col('extract_key') == 'cps/asec').height == 160
    assert inventory.filter(pl.col('variable') == 'EMPSTATD')['detailed'].to_list() == [True] * 3
    flags = pl.read_parquet(run / 'flag_coverage.parquet')
    assert flags.filter(pl.col('extract_key') == 'acs/core').select(
        'year', 'value', 'rows', 'dtype').rows() == [
            (2023, '1', 1, 'Int64'), (2023, '10', 1, 'Int64'), (2024, None, 1, 'Int64')]
    parity = pl.read_parquet(run / 'conversion_parity.parquet')
    assert parity['values_equal'].to_list() == [True] * 5
    assert parity['expected_rows'].to_list() == [3, 5, 1, 2, 2]
    report = json.loads((run / 'report.json').read_text())
    assert report['status'] == 'unresolved'
    assert report['acceptance']['acs/core']['raw_header_parity'] == 'pass'
    second = runner().measure(root, 'replay', 'references', selection)
    assert runner().compare_runs(run, second)['equal'] is True
    assert not list(run.rglob('*.csv'))


@pytest.mark.parametrize('mutation', ['raw', 'parquet', 'reference', 'software', 'schema',
                                      'count', 'byte', 'pin', 'extra', 'missing'])
def test_detached_verification_rejects_mutations(complete_inputs, mutation):
    root, selection = complete_inputs
    run = runner().measure(root, 'first', 'references', selection)
    pin = manifest.sha256_file(run / 'outputs.json')
    if mutation in {'raw', 'parquet', 'reference'}:
        pattern = {'raw': 'raw/acs/core/*/*.csv.gz', 'parquet': 'derived/acs/core/*.parquet',
                   'reference': 'raw/references/ipums-verification/references/usa_samples.html'}
        file = next(root.glob(pattern[mutation]))
        file.write_bytes(file.read_bytes() + b'changed')
    elif mutation == 'pin':
        pin = '0' * 64
    elif mutation == 'extra':
        (run / 'extra').write_text('unexpected')
    elif mutation == 'missing':
        (run / 'report.json').unlink()
    elif mutation == 'software':
        file = run / 'inputs.json'
        data = json.loads(file.read_text())
        data['software']['files']['pyproject.toml']['sha256'] = '0' * 64
        target_io.write_json(file, data)
    elif mutation in {'schema', 'count'}:
        file = run / 'sample_counts.parquet'
        frame = pl.read_parquet(file)
        (frame.drop('rows') if mutation == 'schema' else frame.head(1)).write_parquet(file)
    else:
        file = run / 'report.json'
        file.write_bytes(file.read_bytes() + b' ')
    # A forged, repinned inventory cannot bypass semantic schema/software validation.
    if mutation in {'schema', 'count', 'software'}:
        target_io.write_json(run / 'outputs.json', target_io.inventory(
            run, [p.name for p in run.iterdir() if p.name != 'outputs.json']))
        pin = manifest.sha256_file(run / 'outputs.json')
    with pytest.raises((ValueError, OSError, pl.exceptions.PolarsError)):
        runner().verify_bundle(run, root, expected_outputs_sha256=pin)


def test_unrelated_manifest_append_is_allowed(complete_inputs):
    root, selection = complete_inputs
    run = runner().measure(root, 'first', 'references', selection)
    file = root / 'raw/unrelated.txt'
    file.write_text('legitimate unrelated original')
    manifest.append_entries(paths.manifest_path(root), [manifest.describe_file(
        file, root / 'raw', retrieved_at=datetime.now(UTC), client='fixture', client_version='1')])
    assert runner().verify_bundle(run, root, expected_outputs_sha256=manifest.sha256_file(
        run / 'outputs.json'))['status'] == 'verified'


def test_fidelity_failure_preserves_diagnostic_staging(complete_inputs):
    root, selection = complete_inputs
    file = next(root.glob('derived/acs/core/*.parquet'))
    pl.read_parquet(file).head(1).write_parquet(file)
    before = manifest.sha256_file(file)
    with pytest.raises(ValueError, match='usa_1'):
        runner().measure(root, 'bad', 'references', selection)
    assert not (root / 'derived/ipums/verification/bad').exists()
    staging = root / 'derived/ipums/verification/bad.part'
    assert json.loads((staging / 'failure.json').read_text())['delivery_id'] == 'usa_1'
    assert manifest.sha256_file(file) == before


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'traversal', 'part',
                                      'wrong_delivery', 'raw_symlink', 'parquet_symlink'])
def test_selection_rejects_unsafe_or_incomplete_profiles(complete_inputs, mutation):
    root, selection = complete_inputs
    values = json.loads(selection.read_text())
    if mutation == 'missing':
        values.pop('acs/vintage')
    elif mutation == 'extra':
        values['acs/other'] = values['acs/core']
    elif mutation == 'traversal':
        values['acs/core']['parquet'] = '../outside.parquet'
    elif mutation == 'part':
        values['acs/core']['delivery'] += '.part'
    elif mutation == 'wrong_delivery':
        values['acs/core']['parquet'] = values['acs/vintage']['parquet']
    elif mutation.endswith('symlink'):
        file = (root / values['acs/core']['parquet'] if mutation == 'parquet_symlink'
                else next(root.glob('raw/acs/core/*/*.csv.gz')))
        destination = file.with_name('original-copy')
        file.rename(destination)
        file.symlink_to(destination)
    selection.write_text(json.dumps(values))
    if mutation == 'duplicate':
        text = selection.read_text()
        selection.write_text(text[:-1] + ', "acs/core": ' + json.dumps(values['acs/core']) + '}')
    with pytest.raises((ValueError, OSError)):
        runner().measure(root, 'bad', 'references', selection)


@pytest.mark.parametrize('name', ['occupied', 'occupied.part'])
def test_occupied_run_or_staging_is_preserved(complete_inputs, name):
    root, selection = complete_inputs
    occupied = root / 'derived/ipums/verification' / name
    occupied.mkdir(parents=True)
    (occupied / 'sentinel').write_text('keep')
    with pytest.raises(ValueError, match='exists'):
        runner().measure(root, 'occupied', 'references', selection)
    assert (occupied / 'sentinel').read_text() == 'keep'


def test_final_revalidation_detects_concurrent_input_mutation(complete_inputs, monkeypatch):
    root, selection = complete_inputs
    original = runner()._measure_profile
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        file = next(root.glob('derived/acs/core/*.parquet'))
        file.write_bytes(file.read_bytes() + b'changed')
        return result
    monkeypatch.setattr(runner(), '_measure_profile', mutate)
    with pytest.raises((ValueError, pl.exceptions.PolarsError)):
        runner().measure(root, 'concurrent', 'references', selection)
    assert not (root / 'derived/ipums/verification/concurrent').exists()


def test_b23025_context_requires_the_exact_employment_field(tmp_path):
    directory = tmp_path / 'raw/references/ipums-verification/references'
    directory.mkdir(parents=True)
    from ipums_fixtures import acs_levels
    for year in (2023, 2024):
        (directory / f'acs_{year}_employment.json').write_text(json.dumps(acs_levels()))
        (directory / f'acs_{year}_b23025_metadata.html').write_text(
            '<h1>Population 16 years and over</h1><table><tr><td>B23025_005E</td>'
            '<td>Estimate!!Civilian labor force:!!Unemployed</td></tr>'
            '<tr><td>B23025_004E</td><td>Unknown metadata</td></tr></table>')
    published, evidence = runner()._acs_references(tmp_path, 'references')
    assert published['universe'].null_count() == published.height
    assert evidence['2023']['universe_status'] == 'unresolved'


def test_extra_empty_output_directory_is_rejected(complete_inputs):
    root, selection = complete_inputs
    run = runner().measure(root, 'first', 'references', selection)
    pin = manifest.sha256_file(run / 'outputs.json')
    (run / 'extra-directory').mkdir()
    with pytest.raises(ValueError):
        runner().verify_bundle(run, root, expected_outputs_sha256=pin)


def test_compare_runs_detects_logical_value_changes(complete_inputs):
    root, selection = complete_inputs
    first = runner().measure(root, 'first', 'references', selection)
    second = runner().measure(root, 'second', 'references', selection)
    file = second / 'sample_counts.parquet'
    pl.read_parquet(file).with_columns((pl.col('rows') + 1).alias('rows')).write_parquet(file)
    target_io.write_json(second / 'outputs.json', target_io.inventory(
        second, [p.name for p in second.iterdir() if p.name != 'outputs.json']))
    result = runner().compare_runs(first, second)
    assert result['equal'] is False
    assert result['tables']['sample_counts']['values_equal'] is False


def test_dependency_identity_change_fails_detached_verification(complete_inputs, monkeypatch):
    root, selection = complete_inputs
    run = runner().measure(root, 'first', 'references', selection)
    pin = manifest.sha256_file(run / 'outputs.json')
    original = runner()._software
    def changed_dependencies():
        result = original()
        result['dependencies']['polars'] = 'changed'
        return result
    monkeypatch.setattr(runner(), '_software', changed_dependencies)
    with pytest.raises(ValueError, match='software or dependency'):
        runner().verify_bundle(run, root, expected_outputs_sha256=pin)
