'''Official CT block populations and source-specific independent controls.'''
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from acs_mapping_fixtures import forbid_external_access

PUBLIC = Path(__file__).parent / 'fixtures/acs_mapping/ct'


@pytest.fixture
def ct_files(tmp_path, monkeypatch):
    forbid_external_access(monkeypatch)
    result = {}
    for kind, record in json.loads((PUBLIC / 'provenance.json').read_text()).items():
        if 'archive_parts' in record:
            chunks = []
            for part in record['archive_parts']:
                chunk = (PUBLIC / part['filename']).read_bytes()
                assert hashlib.sha256(chunk).hexdigest() == part['sha256']
                assert len(chunk) == part['size']
                chunks.append(chunk)
            archive = b''.join(chunks)
        else:
            archive = (PUBLIC / (record['filename'] + '.gz')).read_bytes()
        assert hashlib.sha256(archive).hexdigest() == record['archive_sha256']
        body = gzip.decompress(archive)
        assert hashlib.sha256(body).hexdigest() == record['fixture_sha256']
        assert len(body) == record['fixture_size']
        file = tmp_path / record['filename']
        file.write_bytes(body)
        result[kind] = file
    return result



@pytest.fixture(params=['runtime', 'independent'])
def ct_reader(request):
    if request.param == 'runtime':
        from embedding_data.acs_ct_population import read_ct_population
        return read_ct_population
    import importlib.util
    script = Path(__file__).resolve().parents[1] / 'scripts/reconcile_stage8.py'
    spec = importlib.util.spec_from_file_location('independent_ct_mutations', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ct_population


def test_official_block_route_closes_every_independent_control(ct_files):
    from embedding_data import acs_ct_population as ct
    result = ct.read_ct_population(ct_files)
    assert sum(r['population'] for r in result.relations) == 3605944
    assert len(result.relations) == 26
    assert not any(r['puma_code'] == '20702' and r['county_geoid'] == '09170'
                   for r in result.relations)
    assert len(result.puma_totals) == 25
    assert len(result.county_totals) == 9
    assert result.diagnostics['block_records'] == 49926
    assert len(result.diagnostics['zero_population_exclusions']) == 9
    assert result.diagnostics['mcd_controls'] == 173
    assert result.diagnostics['opm_towns'] == 169
    assert result.diagnostics['national_puma_keys'] == 2486
    assert result.diagnostics['excluded_puma_controls'] == [
        {'state_fips': '66', 'puma_code': '00100', 'population': 153836}]


def test_reference_versions_are_explicit_and_historical_registry_unchanged():
    from embedding_data import acs_mapping_references as refs
    v1 = refs.registry_for_version('acs-mapping-references-v1')
    v2 = refs.registry_for_version('acs-mapping-references-v2')
    assert len(v1) == len(refs.REGISTRY) == 39
    assert len(v2) == 46
    assert all(v2[k] == v for k, v in v1.items())
    with pytest.raises(ValueError, match='version'):
        refs.registry_for_version('latest')


def test_incomplete_shared_originals_bind_requested_version(tmp_path, monkeypatch):
    from dataclasses import replace

    from embedding_data import acs_mapping_references as refs
    from embedding_data import manifest

    source = tmp_path / 'help.html'
    from acs_mapping_fixtures import write_public_layout
    layouts = json.loads((PUBLIC.parent / 'reference-layouts.json').read_text())['originals']
    write_public_layout(source, layouts['geocorr_help'])
    # Fixture edition is explicitly pinned to fixture bytes, never a production hash.
    registry = dict(refs.REGISTRY)
    registry['geocorr_help'] = replace(registry['geocorr_help'],
                                      sha256=manifest.sha256_file(source))
    monkeypatch.setattr(refs, 'REGISTRY', registry)
    refs.import_reference(tmp_path / 'data', 'versioned', 'geocorr_help', source,
                          reference_version='acs-mapping-references-v2')
    with pytest.raises(ValueError, match='version|collection'):
        refs.preflight_destinations(tmp_path / 'data', 'versioned')
    refs.preflight_destinations(tmp_path / 'data', 'versioned',
                                reference_version='acs-mapping-references-v2')


def rewrite_member(file, name, change):
    import io
    from zipfile import ZipFile
    original = file.read_bytes()
    output = io.BytesIO()
    with ZipFile(io.BytesIO(original)) as source, ZipFile(output, 'w') as target:
        for member in source.infolist():
            data = source.read(member)
            if member.filename == name:
                data = change(data)
            target.writestr(member, data)
    file.write_bytes(output.getvalue())


@pytest.mark.parametrize('defect', ['header', 'descriptor', 'deletion', 'negative', 'noninteger',
                                   'duplicate', 'component', 'positive_ambiguity', 'terminator',
                                   'blank', 'tab'])
def test_ct_rejects_repinned_dbf_mutations(ct_files, defect, ct_reader):
    from embedding_data import acs_ct_population as ct

    result = ct.read_ct_population(ct_files)
    excluded = result.diagnostics['zero_population_exclusions'][0]['block']

    def mutate(body):
        data = bytearray(body)
        if defect == 'header':
            data[8] = 0
        elif defect == 'descriptor':
            data[32 + 16] = 3
        elif defect == 'deletion':
            data[577] = ord('*')
        elif defect == 'negative':
            data[577 + 125:577 + 137] = b'          -1'
        elif defect == 'noninteger':
            data[577 + 125:577 + 137] = b'         1.5'
        elif defect == 'blank':
            data[577 + 125:577 + 137] = b'            '
        elif defect == 'tab':
            assert data[577 + 125] == ord(' ')
            data[577 + 125] = ord('\t')
        elif defect == 'duplicate':
            data[577 + 137:577 + 274] = data[577:577 + 137]
        elif defect == 'component':
            data[577 + 1] = ord('1')
        elif defect == 'terminator':
            data[-1] = 0
        else:
            for start in range(577, len(data) - 1, 137):
                if bytes(data[start + 16:start + 31]).decode() == excluded:
                    data[start + 125:start + 137] = b'           1'
                    break
            else:
                raise AssertionError('authentic ambiguous block not found')
        return bytes(data)

    rewrite_member(ct_files['ct_tabblock2020'], 'tl_2020_09_tabblock20.dbf', mutate)
    with pytest.raises(ValueError):
        ct_reader(ct_files)


@pytest.mark.parametrize('kind,old,new', [
    ('ct_county_crosswalk', '0900104720', '0900104721'),
    ('census_puma_population2020', '>121054<', '>121055<'),
    ('census_ct_mcd_population2020', '>20358<', '>20359<'),
])
def test_ct_rejects_repinned_control_key_or_population_mutations(
    ct_files, kind, old, new, ct_reader
):
    body = ct_files[kind].read_text(encoding='utf-8-sig')
    assert old in body
    ct_files[kind].write_text(body.replace(old, new, 1), encoding='utf-8-sig')
    with pytest.raises(ValueError):
        ct_reader(ct_files)


def test_ct_rejects_duplicate_tract_in_complete_national_original(ct_files):
    from embedding_data import acs_ct_population as ct
    file = ct_files['tract_puma2020']
    body = file.read_text(encoding='utf-8-sig')
    first = body.splitlines()[1]
    file.write_text(body + '\n' + first + '\n', encoding='utf-8-sig')
    with pytest.raises(ValueError, match='duplicate tract'):
        ct.tract_pumas(file)


def test_ct_replacement_preserves_nonct_and_rejects_old_absent_relation(ct_files):
    import csv
    import io
    from collections import defaultdict

    from acs_mapping_fixtures import genuine_geocorr_bytes

    from embedding_data import acs_ct_population as ct

    reader = csv.DictReader(io.StringIO(genuine_geocorr_bytes().decode('cp1252')))
    next(reader)
    intersections, pumas, counties = [], defaultdict(int), defaultdict(int)
    for n, row in enumerate(reader, 3):
        st, puma, county = row['state'], row['puma22'], row['county']
        population = int(row['pop20'])
        pumas[st, puma] += population
        counties[st, county] += population
        intersections.append(dict(state_fips=st, puma_code=puma, county_geoid=county,
                                  intersection_population=population,
                                  published_area_factor=float(row['afact']),
                                  published_county_factor=float(row['afact2']),
                                  reference_ids=['fixture:geocorr_intersections'],
                                  reference_locators=[f'geocorr_intersections:csv:row:{n}']))
    puma_rows = [dict(state_fips=s, puma_code=p, population=n, reference_ids=[],
                      reference_locators=[]) for (s, p), n in pumas.items()]
    county_rows = [dict(state_fips=s, county_geoid=c, population=n, reference_ids=[],
                        reference_locators=[]) for (s, c), n in counties.items()]
    relations, puma_totals, county_totals, diagnostics = ct.replace_geocorr_basis(
        ct.read_ct_population(ct_files), intersections, puma_rows, county_rows, 'fixture')
    assert [r for r in relations if r['state_fips'] != '09'] == [
        r for r in intersections if r['state_fips'] != '09']
    assert len(diagnostics['geocorr_assertions']) == 27
    absent = [r for r in diagnostics['geocorr_assertions'] if r['puma_code'] == '20702'
              and r['county_geoid'] == '09170']
    assert len(absent) == 1 and absent[0]['accepted_population'] is None
    assert absent[0]['intersection_population'] == 1452
    assert not any(r['puma_code'] == '20702' and r['county_geoid'] == '09170' for r in relations)
    assert sum(r['population'] for r in puma_totals if r['state_fips'] == '09') == 3605944
    assert sum(r['population'] for r in county_totals if r['state_fips'] == '09') == 3605944
    from copy import deepcopy
    for changed_controls, axis in [(puma_rows, 'puma'), (county_rows, 'county')]:
        changed = deepcopy(changed_controls)
        next(r for r in changed if r['state_fips'] == '09')['population'] += 1
        with pytest.raises(ValueError, match='original Geocorr'):
            ct.replace_geocorr_basis(ct.read_ct_population(ct_files), intersections,
                                      changed if axis == 'puma' else puma_rows,
                                      changed if axis == 'county' else county_rows, 'fixture')


def test_independent_ct_reconstructs_originals_without_runtime_import(ct_files):
    import importlib.util
    script = Path(__file__).resolve().parents[1] / 'scripts/reconcile_stage8.py'
    spec = importlib.util.spec_from_file_location('independent_ct', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.ct_population(ct_files)
    assert result['state_population'] == 3605944
    assert len(result['relations']) == 26
    assert len(result['zero_population_exclusions']) == 9
    assert len(result['national_pumas']) == 2486
    assert result['pumas']['20702'] == 177009


def test_v2_national_raw_to_bundle_replay_and_independent_reconciliation(
    ct_files, tmp_path, monkeypatch
):
    import importlib.util

    from acs_mapping_fixtures import (
        build_v2_fixture_mapping,
        national_mapping_originals,
        seed_national_reconciliation_inputs,
    )

    from embedding_data import acs_mapping_bundle as bundle
    from embedding_data import acs_mapping_references as refs

    originals = national_mapping_originals(tmp_path / 'national-originals')
    fixture = seed_national_reconciliation_inputs(tmp_path, monkeypatch, originals)
    script = Path(__file__).resolve().parents[1] / 'scripts/reconcile_stage8.py'
    spec = importlib.util.spec_from_file_location('independent_v2', script)
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    controls = tmp_path / 'controls'
    independent.freeze(fixture.data_dir, controls)
    from acs_mapping_fixtures import seed_mapping_references
    history_dir = tmp_path / 'historical-v1'
    history_dir.mkdir()
    with pytest.MonkeyPatch.context() as legacy_patch:
        legacy = seed_mapping_references(history_dir, legacy_patch, data_dir=fixture.data_dir,
                                         reference_id='historical_v1')
        historical = refs.check_cached_snapshot(fixture.data_dir, legacy.reference_id)
        historical_bytes = (historical.directory / 'receipt.json').read_bytes()
        assert len(historical.files) == 39
    first = build_v2_fixture_mapping(fixture, 'national_v2', monkeypatch, originals, ct_files)
    import polars as pl
    msa = pl.read_parquet(Path(first['directory']) / 'puma_msa_factors.parquet')
    partial = msa.filter(pl.col('state_fips').eq('09').and_(
        pl.col('puma_code').eq('20301'))).row(0, named=True)
    assert (partial['intersection_population'], partial['puma_population']) == (11472, 106820)
    assert partial['puma_to_msa_factor'] == 11472 / 106820
    snapshot = refs.check_cached_snapshot(fixture.data_dir, 'national_v2_references')
    before = (snapshot.directory / 'receipt.json').read_bytes()
    with pytest.raises(ValueError, match='version'):
        refs.acquire_references(fixture.data_dir, snapshot.reference_id)
    refs.acquire_references(fixture.data_dir, snapshot.reference_id,
                             reference_version='acs-mapping-references-v2')
    assert (snapshot.directory / 'receipt.json').read_bytes() == before
    bundle.verify_bundle(Path(first['directory']), fixture.data_dir,
                         expected_outputs_sha256=first['outputs_sha256'])
    replay = bundle.build(fixture.data_dir, 'national_v2_replay', fixture.request,
                          snapshot.reference_id,
                          expected_reference_receipt_sha256=snapshot.receipt_sha256)
    bundle.verify_bundle(Path(replay['directory']), fixture.data_dir,
                         expected_outputs_sha256=replay['outputs_sha256'])
    assert bundle.compare_runs(Path(first['directory']), Path(replay['directory']))['equal']
    measured = independent.reconcile(fixture.data_dir, 'national_v2', first['outputs_sha256'],
                                      controls)
    assert measured['population_reconciliation_equal']
    assert independent.preservation(fixture.data_dir, controls)['appended_record_count'] == 87
    assert (historical.directory / 'receipt.json').read_bytes() == historical_bytes

    # A newly pinned old-basis control must not be hidden by official CT replacement.
    import csv
    import io
    inputs = json.loads((Path(first['directory']) / 'inputs.json').read_text())
    files = independent.reference_files(fixture.data_dir, inputs['references'])
    county_inventory = {r['county'] for r in
                        independent.csv_rows(files['geocorr_county_totals'])}
    for kind, field, key in [('geocorr_puma_totals', 'puma22', '20201'),
                             ('geocorr_county_totals', 'county', '09160')]:
        file = files[kind]
        before_control = file.read_bytes()
        rows = list(csv.reader(io.StringIO(before_control.decode('cp1252'), newline='')))
        index, population = rows[0].index(field), rows[0].index('pop20')
        state_index = rows[0].index('state')
        target = next(row for row in rows[2:] if row[state_index] == '09' and row[index] == key)
        target[population] = str(int(target[population]) + 1)
        output = io.StringIO(newline='')
        csv.writer(output).writerows(rows)
        changed = output.getvalue().encode('cp1252')
        assert hashlib.sha256(changed).digest() != hashlib.sha256(before_control).digest()
        file.write_bytes(changed)
        try:
            with pytest.raises(ValueError, match='original Geocorr'):
                independent.populations(Path(first['directory']), files, county_inventory)
        finally:
            file.write_bytes(before_control)

    # Replace a genuine member-row target consistently wherever outputs cite it.

    from embedding_data import manifest, target_io
    directory = Path(first['directory'])
    factors = pl.read_parquet(directory / 'puma_county_factors.parquet')
    ct_rows = factors.filter(pl.col('area_type').eq('residence').and_(
        pl.col('state_fips').eq('09'))).to_dicts()
    old = next(v for v in ct_rows[0]['reference_locators']
               if v.startswith('ct_tabblock2020:') and 'record-ranges=' in v)
    new = next(v for row in ct_rows[1:] for v in row['reference_locators']
               if v.startswith('ct_tabblock2020:') and 'record-ranges=' in v and v != old)
    for file in directory.glob('*.parquet'):
        frame = pl.read_parquet(file)
        expressions = [pl.col(name).list.eval(
            pl.when(pl.element().eq(old)).then(pl.lit(new)).otherwise(pl.element())
        ).list.unique().list.sort().alias(name) for name, dtype in frame.schema.items()
                       if dtype == pl.List(pl.String) and name.endswith('reference_locators')]
        if expressions:
            frame.with_columns(expressions).write_parquet(file)
    inventory = json.loads((directory / 'outputs.json').read_text())
    for name in inventory:
        inventory[name] = target_io.file_record(directory / name)
    (directory / 'outputs.json').write_text(json.dumps(inventory, sort_keys=True) + '\n')
    pin = manifest.sha256_file(directory / 'outputs.json')
    with pytest.raises(ValueError, match='factor|reference|table'):
        bundle.verify_bundle(directory, fixture.data_dir, expected_outputs_sha256=pin)
    with pytest.raises(ValueError, match='locator|reference'):
        independent.reconcile(fixture.data_dir, 'national_v2', pin, controls)

    manifest_file = fixture.data_dir / 'raw/manifest.jsonl'
    manifest_before = manifest_file.read_bytes()
    lines = manifest_before.splitlines(keepends=True)
    records = [json.loads(line) for line in lines]
    receipt_path = str((snapshot.directory / 'receipt.json').relative_to(fixture.data_dir / 'raw'))
    next(r for r in records if r['path'] == receipt_path)['collection'] = None
    manifest_file.write_bytes(b''.join(
        (json.dumps(record).encode() + b'\n' if record['path'] == receipt_path else line)
        for record, line in zip(records, lines, strict=True)))
    with pytest.raises(ValueError, match='collection|version'):
        refs.check_cached_snapshot(fixture.data_dir, snapshot.reference_id)
    with pytest.raises(ValueError, match='collection|version'):
        independent.preservation(fixture.data_dir, controls)


@pytest.mark.parametrize('defect', ['traversal', 'duplicate', 'symlink', 'compression',
                                   'encryption', 'oversized', 'encoding', 'not_zip'])
def test_ct_archive_directory_and_encoding_fail_closed(ct_files, ct_reader, defect):
    import io
    import stat
    import struct
    from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

    file = ct_files['ct_tabblock2020']
    if defect == 'not_zip':
        file.write_bytes(b'not a zip original')
    elif defect == 'encoding':
        rewrite_member(file, 'tl_2020_09_tabblock20.cpg', lambda body: b'CP1252')
    elif defect in ('encryption', 'oversized'):
        data = bytearray(file.read_bytes())
        position = data.index(b'PK\x01\x02')
        if defect == 'encryption':
            struct.pack_into('<H', data, position + 8, 1)
        else:
            struct.pack_into('<I', data, position + 24, 100 * 1024 * 1024)
        file.write_bytes(data)
    else:
        output = io.BytesIO()
        with ZipFile(file) as original, ZipFile(output, 'w') as changed:
            for i, member in enumerate(original.infolist()):
                data = original.read(member)
                if i == 0:
                    if defect == 'traversal':
                        member.filename = '../' + member.filename
                    elif defect == 'symlink':
                        member.external_attr = (stat.S_IFLNK | 0o777) << 16
                    elif defect == 'compression':
                        member.compress_type = ZIP_DEFLATED
                changed.writestr(member, data)
            if defect == 'duplicate':
                # ZipInfo's duplicate-name warning is expected for this malformed fixture.
                member = ZipInfo('tl_2020_09_tabblock20.cpg')
                with pytest.warns(UserWarning, match='Duplicate name'):
                    changed.writestr(member, b'UTF-8')
        file.write_bytes(output.getvalue())
    with pytest.raises(ValueError):
        ct_reader(ct_files)
