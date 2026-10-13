from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from embedding_data import code_references as cr
from embedding_data import manifest, paths

FIXTURES = Path(__file__).parent / 'fixtures/codes'


@pytest.fixture
def registry():
    reference = replace(cr.REGISTRY['naics_2022'], relative='naics/fixture.xlsx', expected=(6, 2))
    return {reference.kind: reference}


def original(tmp_path):
    file = tmp_path / 'original.xlsx'
    file.write_bytes((FIXTURES / 'naics_2022_tiny.xlsx').read_bytes())
    return file


def test_import_is_original_bytes_and_verified_idempotent(tmp_path, registry):
    file = original(tmp_path)
    destination = cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)
    assert destination.read_bytes() == file.read_bytes()
    assert manifest.entry_for(paths.manifest_path(tmp_path), destination).proxies == (
        'retrieved_at',
    )
    before = paths.manifest_path(tmp_path).read_bytes()
    assert cr.import_reference(tmp_path, 'naics_2022', file, registry=registry) == destination
    assert paths.manifest_path(tmp_path).read_bytes() == before
    destination.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA-256'):
        cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)


def install_transport(monkeypatch, body):
    requests = []
    client_type = httpx.Client

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, stream=httpx.ByteStream(body), headers={'Content-Length': str(len(body))}
        )

    monkeypatch.setattr(
        cr.httpx,
        'Client',
        lambda **kwargs: client_type(**kwargs, transport=httpx.MockTransport(respond)),
    )
    return requests


def test_acquisition_replays_without_requests_or_changes(tmp_path, registry, monkeypatch):
    requests = install_transport(monkeypatch, original(tmp_path).read_bytes())
    destinations = cr.acquire(tmp_path, registry=registry)
    before = paths.manifest_path(tmp_path).read_bytes()
    raw = destinations[0].read_bytes()
    assert cr.acquire(tmp_path, registry=registry) == destinations
    assert len(requests) == 1
    assert paths.manifest_path(tmp_path).read_bytes() == before
    assert destinations[0].read_bytes() == raw


@pytest.mark.parametrize('state', ['missing', 'unrecorded', 'part', 'symlink'])
def test_batch_preflight_refuses_before_http(tmp_path, registry, monkeypatch, state):
    reference = replace(registry['naics_2022'], kind='second', relative='naics/second.xlsx')
    second = cr.reference_path(tmp_path, reference)
    second.parent.mkdir(parents=True)
    file = original(tmp_path)
    if state == 'missing':
        cr.import_reference(tmp_path, 'second', file, registry={'second': reference})
        second.unlink()
    elif state == 'unrecorded':
        second.write_bytes(file.read_bytes())
    elif state == 'part':
        second.with_name(second.name + '.part').write_bytes(b'interrupted')
    else:
        second.symlink_to(file)
    requests = install_transport(monkeypatch, file.read_bytes())
    with pytest.raises((ValueError, FileNotFoundError)):
        cr.acquire(tmp_path, registry={**registry, 'second': reference})
    assert requests == []


def test_different_valid_original_is_refused(tmp_path, registry):
    file = original(tmp_path)
    cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)
    file.write_bytes(file.read_bytes() + b'additional zip trailing bytes')
    cr.parse_reference(file, registry['naics_2022'])
    with pytest.raises(ValueError, match='different bytes'):
        cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)


@pytest.mark.parametrize(
    'kind,body',
    [
        ('naics_2022', b'<html>not a workbook</html>'),
        ('designated_2017', b'<html>Access Denied challenge</html>'),
    ],
)
def test_invalid_download_never_publishes(tmp_path, monkeypatch, kind, body):
    reference = replace(cr.REGISTRY[kind], expected=(6, 2) if kind == 'naics_2022' else 1)
    install_transport(monkeypatch, body)
    with pytest.raises(Exception):
        cr.acquire(tmp_path, registry={kind: reference})
    assert not cr.reference_path(tmp_path, reference).exists()
    assert not paths.manifest_path(tmp_path).exists()


def test_missing_soc_requires_manual_import_before_request(tmp_path, monkeypatch):
    monkeypatch.delenv('BLS_CONTACT_EMAIL', raising=False)
    requests = install_transport(monkeypatch, b'')
    with pytest.raises(ValueError, match='import-reference soc_2018'):
        cr.acquire(tmp_path, registry={'soc_2018': cr.REGISTRY['soc_2018']})
    assert requests == []


def test_imported_soc_parses_offline_without_contact(tmp_path, monkeypatch):
    monkeypatch.delenv('BLS_CONTACT_EMAIL', raising=False)
    reference = replace(cr.REGISTRY['soc_2018'], expected=(4, 1))
    registry = {'soc_2018': reference}
    destination = cr.import_reference(
        tmp_path, 'soc_2018', FIXTURES / 'soc_2018_tiny.xlsx', registry=registry
    )
    assert cr.parse_reference(destination, reference).height == 4
    requests = install_transport(monkeypatch, b'')
    assert cr.acquire(tmp_path, registry=registry) == [destination]
    assert requests == []


def test_naics_text_header_and_rows():
    frame = cr.parse_naics_text('Code    2002 NAICS Title\n31-33 Manufacturing\n311 Food\n', 2002)
    assert frame['code'].to_list() == ['31-33', '311']
    for text in ['wrong header', 'Code    2002 NAICS Title\nABC Bad']:
        with pytest.raises(ValueError):
            cr.parse_naics_text(text, 2002)


def write_workbook(file, rows):
    from html import escape
    from zipfile import ZipFile

    cells = []
    for index, row in enumerate(rows, 1):
        values = ''.join(
            f'<c r="{chr(65 + column)}{index}" t="inlineStr"><is><t>'
            f'{escape(str(value))}</t></is></c>'
            for column, value in enumerate(row)
            if value is not None
        )
        cells.append(f'<row r="{index}">{values}</row>')
    with ZipFile(file, 'w') as workbook:
        workbook.writestr(
            '[Content_Types].xml',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"'
            '><Default Extension="rels" ContentType="application/vnd.openxmlformats-pack'
            'age.relationships+xml"/><Default Extension="xml" ContentType="application/x'
            'ml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.ope'
            'nxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartNam'
            'e="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-o'
            'fficedocument.spreadsheetml.worksheet+xml"/></Types>',
        )
        workbook.writestr(
            '_rels/.rels',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relati'
            'onships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/of'
            'ficeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><'
            '/Relationships>',
        )
        workbook.writestr(
            'xl/workbook.xml',
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationshi'
            'ps"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbo'
            'ok>',
        )
        workbook.writestr(
            'xl/_rels/workbook.xml.rels',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relati'
            'onships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/of'
            'ficeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        workbook.writestr(
            'xl/worksheets/sheet1.xml',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + ''.join(cells)
            + '</sheetData></worksheet>',
        )


@pytest.fixture
def full_registry(tmp_path):
    from code_fixtures import pair_sheet, titles

    registry = {}
    for vintage in (2002, 2007, 2012, 2017, 2022):
        kind = f'naics_{vintage}'
        reference = replace(
            cr.REGISTRY[kind], family='naics', relative=f'naics/{vintage}.xlsx', expected=(6, 2)
        )
        registry[kind] = reference
        file = tmp_path / f'{vintage}.xlsx'
        frame = titles(vintage)
        write_workbook(
            file,
            [
                [f'{vintage} NAICS Code', f'{vintage} NAICS Title'],
                *frame.select('code', 'title').rows(),
            ],
        )
        cr.import_reference(tmp_path, kind, file, registry=registry)
    for source, target in ((2002, 2007), (2007, 2012), (2012, 2017), (2017, 2022)):
        kind = f'concordance_{source}_{target}'
        reference = replace(cr.REGISTRY[kind], relative=f'naics/{kind}.xlsx')
        registry[kind] = reference
        file = tmp_path / f'{kind}.xlsx'
        write_workbook(
            file, pair_sheet(source, target, [('111111', '111111'), ('111112', '111112')]).rows()
        )
        cr.import_reference(tmp_path, kind, file, registry=registry)
    reference = replace(cr.REGISTRY['soc_2018'], expected=(4, 1))
    registry['soc_2018'] = reference
    cr.import_reference(tmp_path, 'soc_2018', FIXTURES / 'soc_2018_tiny.xlsx', registry=registry)
    for kind in ('designated_2012', 'designated_2017', 'partially_exempt_2007'):
        reference = replace(cr.REGISTRY[kind], expected=1)
        registry[kind] = reference
        file = tmp_path / f'{kind}.htm'
        subpart = 'B' if kind.startswith('partially') else 'E'
        file.write_text(
            f'<pre>Appendix A to Subpart {subpart} of Part 1904\n'
            '111111...... Fixture industry</pre>'
        )
        cr.import_reference(tmp_path, kind, file, registry=registry)
    return registry


def test_complete_reader_is_offline_and_preserves_rule_outputs(
    tmp_path, full_registry, monkeypatch
):
    monkeypatch.delenv('BLS_CONTACT_EMAIL', raising=False)
    requests = install_transport(monkeypatch, b'')
    tables = cr.read_references(tmp_path, registry=full_registry)
    assert set(tables) == {
        'structures',
        'soc_nodes',
        'relations',
        'rule_groups',
        'rules',
        'rule_labels',
        'rule_membership',
    }
    assert tables['structures'].height == 30
    assert tables['relations'].height == 8
    assert tables['rule_groups']['listed_groups'].to_list() == [1, 1, 1]
    assert tables['rule_membership'].height > 0
    assert requests == []


@pytest.mark.parametrize('state', ['missing', 'changed'])
def test_reader_refuses_every_missing_or_changed_original(tmp_path, full_registry, state):
    for reference in full_registry.values():
        file = cr.reference_path(tmp_path, reference)
        body = file.read_bytes()
        if state == 'missing':
            file.unlink()
        else:
            file.write_bytes(b'changed')
        with pytest.raises((ValueError, FileNotFoundError)):
            cr.read_references(tmp_path, registry=full_registry)
        file.write_bytes(body)


def test_reader_refuses_incomplete_full_bridge(tmp_path, full_registry):
    from code_fixtures import pair_sheet

    kind = 'concordance_2002_2007'
    # Build a fresh validly recorded but incomplete bridge, not a hash-corrupted original.
    alternate = tmp_path / 'alternate'
    for key, entry in full_registry.items():
        file = cr.reference_path(tmp_path, entry)
        if key == kind:
            file = tmp_path / 'incomplete.xlsx'
            write_workbook(file, pair_sheet(2002, 2007, [('111111', '111111')]).rows())
        cr.import_reference(alternate, key, file, registry=full_registry)
    with pytest.raises(ValueError, match='coverage'):
        cr.read_references(alternate, registry=full_registry)


def test_original_naics_text_is_validated_and_preserved(tmp_path):
    reference = replace(cr.REGISTRY['naics_2002'], expected=(6, 2))
    file = tmp_path / 'original.txt'
    file.write_text(
        'Code    2002 NAICS Title\n'
        + '\n'.join(
            f'{code} Fixture {code}' for code in ['11', '111', '1111', '11111', '111111', '111112']
        )
    )
    destination = cr.import_reference(
        tmp_path, reference.kind, file, registry={reference.kind: reference}
    )
    assert destination.read_bytes() == file.read_bytes()
    assert cr.parse_reference(destination, reference).height == 6


@pytest.mark.parametrize(
    'kind,body',
    [
        ('naics_2022', b'<html>not workbook</html>'),
        ('designated_2017', b'<html>Access Denied</html>'),
    ],
)
def test_invalid_import_never_publishes(tmp_path, kind, body):
    reference = replace(cr.REGISTRY[kind], expected=(6, 2) if kind == 'naics_2022' else 1)
    file = tmp_path / Path(reference.relative).name
    file.write_bytes(body)
    with pytest.raises(Exception):
        cr.import_reference(tmp_path, kind, file, registry={kind: reference})
    assert not cr.reference_path(tmp_path, reference).exists()
    assert not paths.manifest_path(tmp_path).exists()


def test_changed_bytes_during_import_copy_are_not_published(tmp_path, registry, monkeypatch):
    file = original(tmp_path)

    def changed_copy(source, output):
        output.write(b'changed while copying')

    monkeypatch.setattr(cr.shutil, 'copyfileobj', changed_copy)
    with pytest.raises(ValueError, match='SHA-256'):
        cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)
    destination = cr.reference_path(tmp_path, registry['naics_2022'])
    assert not destination.exists()
    assert not destination.with_name(destination.name + '.part').exists()
    assert not paths.manifest_path(tmp_path).exists()


def test_destination_appearing_at_publication_is_never_overwritten(
    tmp_path, registry, monkeypatch
):
    file = original(tmp_path)
    destination = cr.reference_path(tmp_path, registry['naics_2022'])
    partial = destination.with_name(destination.name + '.part')
    original_is_symlink = Path.is_symlink

    def competing_writer(path):
        if path == destination and partial.exists():
            destination.write_bytes(b'concurrent original')
            return False
        return original_is_symlink(path)

    monkeypatch.setattr(Path, 'is_symlink', competing_writer)
    with pytest.raises((ValueError, FileExistsError)):
        cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)
    assert destination.read_bytes() == b'concurrent original'
    assert not paths.manifest_path(tmp_path).exists()
    assert not partial.exists()


def test_competing_staging_file_survives_exclusive_creation_refusal(
    tmp_path, registry, monkeypatch
):
    file = original(tmp_path)
    destination = cr.reference_path(tmp_path, registry['naics_2022'])
    partial = destination.with_name(destination.name + '.part')
    original_open = Path.open
    competing_bytes = b'other importer owns this staging file'

    def competing_open(path, mode='r', *args, **kwargs):
        if path == partial and mode == 'xb':
            with original_open(path, 'wb') as competitor:
                competitor.write(competing_bytes)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', competing_open)
    with pytest.raises(FileExistsError):
        cr.import_reference(tmp_path, 'naics_2022', file, registry=registry)
    assert partial.read_bytes() == competing_bytes
    assert not destination.exists()
    assert not paths.manifest_path(tmp_path).exists()
