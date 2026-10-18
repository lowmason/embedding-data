'''Closed public-reference lifecycle, independent pins, and denied external access.'''

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import httpx
import polars as pl
import pytest
from acs_mapping_fixtures import seed_mapping_references
from target_fixtures import forbid_external_access

from embedding_data import acs_mapping_references as refs
from embedding_data import manifest, paths
from embedding_data.acs_mapping_references import (
    Reference,
    ReferenceSnapshot,
    acquire_references,
    check_references,
    import_reference,
)

@pytest.fixture(autouse=True)
def deny_external_access(monkeypatch):
    from embedding_data import ipums_census_access

    forbid_external_access(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError('reference test attempted real HTTP or credential access')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', forbidden)
    monkeypatch.setattr(ipums_census_access, 'read_credential', forbidden)


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    return seed_mapping_references(tmp_path, monkeypatch)


def test_registered_identity_and_public_fixture_metadata():
    assert pl.String is not None
    layouts = json.loads(
        (Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json').read_text()
    )
    assert {
        'ipums_ind_pairs',
        'pums_industry_2017',
        'pums_industry_2022',
        'ipums_occ_pairs',
        'pums_occupation_2018',
        'pums_annual_2024',
        'pums_five_year_2024',
        'county_composition_2022',
        'puma_composition_2020',
        'msa_puma_2023_2020',
        'geocorr_form',
        'geocorr_help',
    }.issubset(refs.REGISTRY)
    assert len(refs.REGISTRY) == len({r.filename for r in refs.REGISTRY.values()})
    for kind, reference in refs.REGISTRY.items():
        assert reference.kind == kind
        assert reference.edition and reference.parser_contract and reference.authority_role
        assert reference.authority_url.startswith('https://')
        if not kind.endswith('_request'):
            evidence = layouts['originals'][kind]
            assert len(evidence['sha256']) == 64 and evidence['transformation']
    reference = next(iter(refs.REGISTRY.values()))
    assert isinstance(reference, Reference)
    with pytest.raises(FrozenInstanceError):
        reference.filename = 'changed'


def test_full_import_snapshot_manifest_and_detached_pin(snapshot):
    verified = check_references(
        snapshot.data_dir, snapshot.reference_id, expected_receipt_sha256=snapshot.receipt_sha256
    )
    assert isinstance(verified, ReferenceSnapshot)
    assert set(verified.files) == set(refs.REGISTRY)
    receipt = verified.receipt
    assert receipt['reference_version'] == refs.REFERENCE_VERSION
    assert set(receipt['originals']) == set(refs.REGISTRY)
    assert len(receipt['files']) == len(refs.REGISTRY)
    entries = manifest.read_manifest(paths.manifest_path(snapshot.data_dir))
    assert len(entries) == len(refs.REGISTRY) + 1
    assert entries[-1].path.endswith('/receipt.json')
    assert {c['path'] for c in receipt['raw_citations']} == {e.path for e in entries[:-1]}
    assert all(r['retrieved_at_is_proxy'] for r in receipt['originals'].values())
    assert all(r['sha256'] == refs.REGISTRY[k].sha256 for k, r in receipt['originals'].items())
    with pytest.raises(ValueError):
        check_references(
            snapshot.data_dir, snapshot.reference_id, expected_receipt_sha256='0' * 64
        )


def test_cached_acquisition_never_constructs_an_http_client(snapshot, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('cached reference acquisition contacted HTTP')

    monkeypatch.setattr(refs, 'make_client', forbidden)
    again = acquire_references(snapshot.data_dir, snapshot.reference_id)
    assert again.receipt_sha256 == snapshot.receipt_sha256


@pytest.mark.parametrize(
    'damage', ['changed', 'missing', 'extra', 'partial', 'symlink', 'receipt']
)
def test_cached_damage_fails_before_transport(snapshot, monkeypatch, damage):
    directory = refs.reference_directory(snapshot.data_dir, snapshot.reference_id)
    first = directory / next(iter(refs.REGISTRY.values())).filename
    if damage == 'changed':
        first.write_bytes(b'changed original')
    elif damage == 'missing':
        first.unlink()
    elif damage == 'extra':
        (directory / 'unexpected.html').write_text('unexpected')
    elif damage == 'partial':
        first.with_name(first.name + '.part').write_bytes(b'occupied')
    elif damage == 'symlink':
        first.unlink()
        first.symlink_to(next(iter(snapshot.originals.values())))
    else:
        receipt = directory / 'receipt.json'
        value = json.loads(receipt.read_text())
        value['reference_id'] = 'tampered'
        receipt.write_text(json.dumps(value))
    monkeypatch.setattr(refs, 'make_client', lambda: pytest.fail('transport constructed'))
    with pytest.raises((ValueError, OSError, KeyError)):
        acquire_references(snapshot.data_dir, snapshot.reference_id)


@pytest.mark.parametrize(
    'damage', ['recorded_missing', 'unrecorded', 'partial', 'symlink', 'unexpected']
)
def test_full_set_preflight_before_any_http_or_import(snapshot, tmp_path, damage):
    root, run = tmp_path / 'new-data', 'new'
    directory = refs.reference_directory(root, run)
    directory.mkdir(parents=True)
    values = list(refs.REGISTRY.values())
    file = directory / values[-1].filename
    if damage == 'recorded_missing':
        file.write_bytes(b'evidence')
        from datetime import UTC, datetime

        entry = manifest.describe_file(
            file,
            paths.manifest_path(root).parent,
            retrieved_at=datetime.now(UTC),
            client='test',
            client_version='1',
        )
        manifest.append_entries(paths.manifest_path(root), [entry])
        file.unlink()
    elif damage == 'partial':
        file.with_name(file.name + '.part').write_text('occupied')
    elif damage == 'symlink':
        file.symlink_to(next(iter(snapshot.originals.values())))
    elif damage == 'unexpected':
        (directory / 'unknown').write_text('occupied')
    else:
        file.write_text('unrecorded')
    before = {p: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    calls = []
    with httpx.Client(transport=httpx.MockTransport(lambda req: calls.append(req))) as client:
        with pytest.raises((ValueError, OSError)):
            acquire_references(root, run, client=client)
    kind = next(iter(refs.REGISTRY))
    with pytest.raises((ValueError, OSError)):
        import_reference(root, run, kind, snapshot.originals[kind])
    assert not calls
    assert all(p.read_bytes() == body for p, body in before.items())


def test_incremental_import_conflict_and_complete_refusal(snapshot, tmp_path):
    root = tmp_path / 'incremental'
    kind, file = next(iter(snapshot.originals.items()))
    result = import_reference(root, 'partial', kind, file)
    assert result['complete'] is False
    with pytest.raises(ValueError):
        acquire_references(root, 'partial')
    with pytest.raises(ValueError):
        check_references(root, 'partial', expected_receipt_sha256='0' * 64)
    with pytest.raises(ValueError):
        import_reference(root, 'partial', kind, file)
    with pytest.raises(ValueError):
        import_reference(snapshot.data_dir, snapshot.reference_id, kind, file)


@pytest.mark.parametrize('run', ['../escape', 'bad.part', '/absolute', 'a/b', ''])
def test_unsafe_ids_fail_without_writes(tmp_path, monkeypatch, run):
    forbid_external_access(monkeypatch)
    with pytest.raises(ValueError):
        acquire_references(tmp_path, run)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    'kind,body',
    [
        ('pums_occupation_2018', b'not a workbook'),
        ('usa_pwpuma00', b'<html>application error</html>'),
        ('geocorr_intersections_response', b'<html>SAS Error: request failed</html>'),
    ],
)
def test_malformed_original_import_fails_before_publication(snapshot, tmp_path, kind, body):
    file = tmp_path / 'malformed'
    file.write_bytes(body)
    with pytest.raises(ValueError):
        import_reference(tmp_path / 'bad', 'bad', kind, file)
    assert not (
        refs.reference_directory(tmp_path / 'bad', 'bad') / refs.REGISTRY[kind].filename
    ).exists()


def mock_client(snapshot, calls, *, fail_kind=None, fail_body=None, fail_type=None):
    by_url = {
        r.authority_url: k
        for k, r in refs.REGISTRY.items()
        if not k.endswith('_request') and k not in refs.GEOCORR_QUERIES
    }

    def respond(request):
        calls.append(str(request.url))
        url = str(request.url)
        if '/temp/geocorr2022_' in url:
            response_kind = next(
                k
                for k in refs.REGISTRY
                if k.endswith('_response')
                and refs.generated_csv_url(snapshot.originals[k].read_text()) == url
            )
            kind = response_kind.removesuffix('_response')
        else:
            kind = by_url[url]
        body = snapshot.originals[kind].read_bytes()
        suffix = refs.REGISTRY[kind].filename.rsplit('.', 1)[-1]
        content_type = {
            'html': 'text/html',
            'csv': 'text/csv',
            'pdf': 'application/pdf',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }.get(suffix, 'text/plain')
        if kind == fail_kind:
            body = fail_body if fail_body is not None else body
            content_type = fail_type or content_type
        return httpx.Response(
            200,
            headers={'content-length': str(len(body)), 'content-type': content_type},
            stream=httpx.ByteStream(body),
        )

    return httpx.Client(transport=httpx.MockTransport(respond))


def test_acquisition_preserves_requests_padded_links_and_manifest_prefix(snapshot, tmp_path):
    root = tmp_path / 'acquired'
    calls = []
    with mock_client(snapshot, calls) as client:
        acquired = acquire_references(root, 'fresh', client=client)
        count = len(calls)
        cached = acquire_references(root, 'fresh', client=client)
    assert count == len(refs.REGISTRY) - len(refs.GEOCORR_QUERIES)
    assert len(calls) == count
    assert acquired.receipt_sha256 == cached.receipt_sha256
    for name in refs.GEOCORR_QUERIES:
        assert acquired.files[name + '_request'].read_bytes() == refs.request_bytes(name)
    assert len(acquired.receipt['request_files']) == 3
    assert not any(r['retrieved_at_is_proxy'] for r in acquired.receipt['originals'].values())


@pytest.mark.parametrize(
    'fail_kind,body,content_type',
    [
        ('geocorr_intersections_response', b'<html>ERROR: SAS failed</html>', 'text/html'),
        ('pums_industry_2017', b'<html>Access denied</html>', 'text/html'),
        ('usa_ind', b'<html>Application error</html>', 'text/html'),
    ],
)
def test_failed_acquisition_retains_manifested_evidence_and_refuses_recovery(
    snapshot, tmp_path, fail_kind, body, content_type
):
    root = tmp_path / 'failed'
    calls = []
    with mock_client(
        snapshot, calls, fail_kind=fail_kind, fail_body=body, fail_type=content_type
    ) as client:
        with pytest.raises(ValueError):
            acquire_references(root, 'failed', client=client)
        count = len(calls)
        with pytest.raises(ValueError):
            acquire_references(root, 'failed', client=client)
    assert len(calls) == count
    directory = refs.reference_directory(root, 'failed')
    assert not (directory / 'receipt.json').exists()
    for entry in manifest.read_manifest(paths.manifest_path(root)):
        assert (
            manifest.entry_for(
                paths.manifest_path(root), paths.manifest_path(root).parent / entry.path
            )
            == entry
        )
    assert not list(directory.glob('*.part'))


def test_manifest_failure_is_unrecorded_evidence(snapshot, tmp_path, monkeypatch):
    kind, file = next(iter(snapshot.originals.items()))
    root = tmp_path / 'append-failure'

    def fail(*args):
        raise OSError('manifest disk failure')

    monkeypatch.setattr(manifest, 'append_entries', fail)
    with pytest.raises(ValueError, match='unrecorded evidence'):
        import_reference(root, 'broken', kind, file)
    assert (refs.reference_directory(root, 'broken') / refs.REGISTRY[kind].filename).exists()
    with pytest.raises(ValueError):
        import_reference(root, 'broken', kind, file)


def test_geocorr_request_state_order_and_exact_empty_controls():
    from urllib.parse import parse_qsl

    for name in refs.GEOCORR_QUERIES:
        pairs = parse_qsl(refs.request_bytes(name).decode(), keep_blank_values=True)
        states = [v for k, v in pairs if k == 'state']
        assert len(states) == 52
        assert [v[-2:] for v in states] == sorted(v[-2:] for v in states)
        assert ('title', '') in pairs and ('counties', '') in pairs
        assert ('wtvar', 'pop20') in pairs and ('afacts2', 'on') in pairs


@pytest.mark.parametrize(
    'url',
    [
        'https://evil.invalid/temp/a.csv',
        '/temp/../../bad.csv',
        'javascript:alert(1)',
        '//evil.invalid/a.csv',
    ],
)
def test_generated_links_allow_only_documented_same_authority_csv(url):
    html = f'<h3>Processing completed</h3><a href="{url}">CSV</a>'
    with pytest.raises(ValueError):
        refs.generated_csv_url(html)


def test_import_source_partial_name_is_not_an_original(snapshot, tmp_path):
    kind, original = next(iter(snapshot.originals.items()))
    partial = tmp_path / 'browser-download.part'
    partial.write_bytes(original.read_bytes())
    with pytest.raises(ValueError, match='partial'):
        import_reference(tmp_path / 'partial-source', 'new', kind, partial)


def test_generated_link_does_not_normalize_traversal():
    html = (
        '<p>geocorr2022 version 1.9</p><h3>Processing completed</h3>'
        '<a href="/temp/ignored/../geocorr2022_123.csv ">CSV</a>'
    )
    with pytest.raises(ValueError, match='allowlisted'):
        refs.generated_csv_url(html)


@pytest.mark.parametrize(
    'kind,body',
    [
        ('pums_occupation_2018', b'not a workbook'),
        ('usa_pwpuma00', b'<title>IPUMS USA: descr: PWPUMA00</title><h1>PWPUMA00</h1>'),
        (
            'industry_tokens_html',
            b'<table class="condensed"><tr><td>INDNAICS Industry Title</td></tr></table>',
        ),
        ('geocorr_intersections', b'"state","pop20"\n"State","Population"\n"09",1\n'),
        (
            'geocorr_intersections_response',
            b'<p>geocorr2022 version 1.9</p><h3>Processing completed</h3>',
        ),
        ('pums_annual_guide', b'not a PDF'),
    ],
)
def test_layout_validation_is_independent_of_hash(snapshot, tmp_path, monkeypatch, kind, body):
    from dataclasses import replace

    file = tmp_path / 'changed-layout'
    file.write_bytes(body)
    monkeypatch.setitem(
        refs.REGISTRY, kind, replace(refs.REGISTRY[kind], sha256=manifest.sha256_file(file))
    )
    with pytest.raises(ValueError):
        import_reference(tmp_path / 'invalid-layout', 'new', kind, file)


def test_geocorr_csv_alone_cannot_complete_snapshot(snapshot, tmp_path):
    root = tmp_path / 'csv-only'
    for kind in refs.GEOCORR_QUERIES:
        result = import_reference(root, 'csv-only', kind, snapshot.originals[kind])
        assert not result['complete']
    assert not (refs.reference_directory(root, 'csv-only') / 'receipt.json').exists()
    with pytest.raises(ValueError):
        check_references(root, 'csv-only', expected_receipt_sha256='0' * 64)


def test_request_byte_tampering_fails_even_if_manifest_rewritten(snapshot, monkeypatch):
    from dataclasses import replace

    kind = next(iter(refs.GEOCORR_QUERIES)) + '_request'
    directory = refs.reference_directory(snapshot.data_dir, snapshot.reference_id)
    file = directory / refs.REGISTRY[kind].filename
    file.write_bytes(file.read_bytes().replace(b'title=', b'title=changed'))
    monkeypatch.setitem(
        refs.REGISTRY, kind, replace(refs.REGISTRY[kind], sha256=manifest.sha256_file(file))
    )
    manifest_file = paths.manifest_path(snapshot.data_dir)
    records = [json.loads(line) for line in manifest_file.read_text().splitlines()]
    for record in records:
        if record['path'] == file.relative_to(manifest_file.parent).as_posix():
            record.update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    manifest_file.write_text(''.join(json.dumps(r) + '\n' for r in records))
    with pytest.raises(ValueError, match='request bytes'):
        acquire_references(snapshot.data_dir, snapshot.reference_id)


def test_receipt_identity_tampering_fails_even_if_manifest_rewritten(snapshot):
    directory = refs.reference_directory(snapshot.data_dir, snapshot.reference_id)
    file = directory / 'receipt.json'
    receipt = json.loads(file.read_text())
    receipt['originals']['usa_puma']['authority_role'] = 'invented precedence'
    file.write_text(json.dumps(receipt))
    manifest_file = paths.manifest_path(snapshot.data_dir)
    records = [json.loads(line) for line in manifest_file.read_text().splitlines()]
    records[-1].update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    manifest_file.write_text(''.join(json.dumps(r) + '\n' for r in records))
    with pytest.raises(ValueError, match='receipt'):
        acquire_references(snapshot.data_dir, snapshot.reference_id)


def test_import_preserves_manifest_prefix_and_exact_delta(snapshot, tmp_path):
    from datetime import UTC, datetime

    root = tmp_path / 'prefix'
    prior = root / 'raw/other/evidence.txt'
    prior.parent.mkdir(parents=True)
    prior.write_bytes(b'earlier independent evidence')
    manifest_file = paths.manifest_path(root)
    manifest.append_entries(
        manifest_file,
        [
            manifest.describe_file(
                prior,
                manifest_file.parent,
                retrieved_at=datetime.now(UTC),
                client='fixture',
                client_version='1',
            )
        ],
    )
    prefix = manifest_file.read_bytes()
    for kind, file in snapshot.originals.items():
        import_reference(root, 'new', kind, file)
        assert manifest_file.read_bytes().startswith(prefix)
    entries = manifest.read_manifest(manifest_file)
    assert len(entries) == 1 + len(refs.REGISTRY) + 1
    assert prior.read_bytes() == b'earlier independent evidence'


def test_receipt_manifest_failure_never_enables_build(snapshot, tmp_path, monkeypatch):
    root = tmp_path / 'receipt-failure'
    real_append = manifest.append_entries

    def fail_receipt(file, entries):
        entries = list(entries)
        if any(e.path.endswith('/receipt.json') for e in entries):
            raise OSError('receipt manifest failure')
        return real_append(file, entries)

    monkeypatch.setattr(manifest, 'append_entries', fail_receipt)
    for kind, file in list(snapshot.originals.items())[:-1]:
        import_reference(root, 'new', kind, file)
    kind, file = list(snapshot.originals.items())[-1]
    with pytest.raises(ValueError, match='unrecorded evidence'):
        import_reference(root, 'new', kind, file)
    with pytest.raises(ValueError):
        check_references(root, 'new', expected_receipt_sha256='0' * 64)
    with pytest.raises(ValueError):
        acquire_references(root, 'new')


def test_transport_truncation_and_owned_partial_cleanup(snapshot, tmp_path):
    calls = []
    first = next(iter(refs.REGISTRY.values()))
    body = snapshot.originals[first.kind].read_bytes()

    def truncated(request):
        calls.append(str(request.url))
        return httpx.Response(
            200,
            headers={
                'content-type': 'application/vnd.ms-excel',
                'content-length': str(len(body) + 1),
            },
            stream=httpx.ByteStream(body),
        )

    root = tmp_path / 'truncated'
    with httpx.Client(transport=httpx.MockTransport(truncated)) as client:
        with pytest.raises(ValueError, match='completion'):
            acquire_references(root, 'new', client=client)
    directory = refs.reference_directory(root, 'new')
    assert len(calls) == 1
    assert list(directory.iterdir()) == []
    assert manifest.read_manifest(paths.manifest_path(root)) == []


def test_import_symlink_ancestor_fails_without_destination_write(snapshot, tmp_path):
    alias = tmp_path / 'source-alias'
    alias.symlink_to(next(iter(snapshot.originals.values())).parent, target_is_directory=True)
    kind, original = next(iter(snapshot.originals.items()))
    root = tmp_path / 'alias-import'
    with pytest.raises(ValueError, match='symlink'):
        import_reference(root, 'new', kind, alias / original.name)
    assert not root.exists()


def test_public_occupation_excerpt_preserves_style_fill_and_legend(snapshot):
    from xml.etree import ElementTree as ET
    from zipfile import ZipFile

    file = snapshot.originals['pums_occupation_2018']
    ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(file) as archive:
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        styles = ET.fromstring(archive.read('xl/styles.xml'))
        cell = sheet.find('.//x:c[@r="A17"]', ns)
        style = styles.find('x:cellXfs', ns)[int(cell.attrib['s'])]
        fill = styles.find('x:fills', ns)[int(style.attrib['fillId'])]
        color = fill.find('x:patternFill/x:fgColor', ns)
        assert color.attrib == {'theme': '7', 'tint': '0.79998168889431442'}
        row = sheet.find('.//x:row[@r="884"]', ns)
        assert 'highlight' in ''.join(row.itertext()).lower()


def test_geocorr_response_must_match_source_target_roles(snapshot, tmp_path, monkeypatch):
    from dataclasses import replace
    kind = 'geocorr_intersections_response'
    file = tmp_path / 'wrong-role.html'
    body = snapshot.originals[kind].read_text().replace(
        'Source geographies requested: <b>state puma22 </b>',
        'Source geographies requested: <b>county </b>').replace(
        'Target geographies requested: <b>county </b>',
        'Target geographies requested: <b>state puma22 </b>')
    file.write_text(body)
    monkeypatch.setitem(refs.REGISTRY, kind, replace(refs.REGISTRY[kind],
        sha256=manifest.sha256_file(file)))
    with pytest.raises(ValueError, match='query identity'):
        import_reference(tmp_path / 'wrong-role', 'new', kind, file)


def test_failure_does_not_clean_a_partial_owned_by_another_invocation(snapshot, tmp_path):
    root = tmp_path / 'other-owner'
    references = list(refs.REGISTRY.values())
    first, second = references[:2]
    other_partial = refs.reference_directory(root, 'new') / (second.filename + '.part')
    calls = []
    def insert_other_partial(request):
        calls.append(str(request.url))
        other_partial.write_bytes(b'evidence owned by another invocation')
        body = snapshot.originals[first.kind].read_bytes()
        return httpx.Response(200, headers={'content-type':'application/vnd.ms-excel',
            'content-length':str(len(body))}, stream=httpx.ByteStream(body))
    with httpx.Client(transport=httpx.MockTransport(insert_other_partial)) as client:
        with pytest.raises(FileExistsError):
            acquire_references(root, 'new', client=client)
    assert len(calls) == 1
    assert other_partial.read_bytes() == b'evidence owned by another invocation'
    assert len(manifest.read_manifest(paths.manifest_path(root))) == 1



def test_real_http_and_census_credentials_are_explicitly_denied():
    from embedding_data import ipums_census_access

    with httpx.Client() as client:
        with pytest.raises(AssertionError, match='real HTTP'):
            client.get('https://example.invalid/must-never-contact')
    with pytest.raises(AssertionError, match='credential access'):
        ipums_census_access.read_credential()


def test_unknown_import_kind_is_rejected_before_any_write(tmp_path):
    with pytest.raises(ValueError, match='unknown registered'):
        import_reference(tmp_path, 'new', 'unregistered-original', tmp_path / 'missing')
    assert list(tmp_path.iterdir()) == []


def test_reference_version_matches_frozen_contract():
    from embedding_data.acs_mapping_contract import REFERENCE_VERSION

    assert refs.REFERENCE_VERSION == REFERENCE_VERSION == 'acs-mapping-references-v1'


def test_documentary_excerpts_are_actual_source_sections():
    import hashlib

    originals = json.loads((Path(__file__).parent /
        'fixtures/acs_mapping/reference-layouts.json').read_text())['originals']
    for kind, pages in [('pums_annual_guide', [17, 19]),
                        ('pums_five_year_guide', [18, 19])]:
        record = originals[kind]
        text = record['public_section_text_excerpt']
        normalized = ' '.join(text.split())
        assert '559830 MIL-Military, Rank Not Specified' in normalized
        assert 'Pseudo-Codes Values for Select Variables' in normalized
        assert record['physical_pages'] == pages
        assert record['section_locators'] == ['VIII.I', 'VIII.J', 'VIII.K', 'VIII.L']
        assert record['section_text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
        assert 'pdftotext -layout -f' in record['extraction_command']


def test_public_excerpt_theme_preserved(snapshot):
    from zipfile import ZipFile

    originals = json.loads((Path(__file__).parent /
        'fixtures/acs_mapping/reference-layouts.json').read_text())['originals']
    with ZipFile(snapshot.originals['pums_occupation_2018']) as archive:
        assert 'xl/theme/theme1.xml' in archive.namelist()
        assert archive.read('xl/theme/theme1.xml').decode() == originals[
            'pums_occupation_2018']['theme_xml']


def test_geocorr_layout_evidence_records_generated_original_url():
    originals = json.loads((Path(__file__).parent /
        'fixtures/acs_mapping/reference-layouts.json').read_text())['originals']
    for kind in refs.GEOCORR_QUERIES:
        assert originals[kind]['retrieval_url'] == refs.generated_csv_url(
            originals[kind + '_response']['body'])
        assert originals[kind]['request_url'] == (
            'https://mcdc.missouri.edu/cgi-bin/broker?' +
            originals[kind + '_request']['body'])
