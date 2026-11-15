import shutil
from dataclasses import asdict, fields, replace
from functools import partial
from importlib.metadata import version
from urllib.parse import urlparse
from zipfile import ZipFile

import httpx
import polars as pl
import pytest
from code_fixtures import write_xlsx
from ita_establishment_fixtures import (
    INDEX_ROWS,
    fixture_index_registry,
    seed_structure_titles,
    write_index_workbook,
)

from embedding_data import ita_index_references as iir
from embedding_data import ita_references, manifest, osha_benchmark_download, paths

CROSS = iir.CROSS_REFERENCE
SHEET = '2022NAICS'
HEADER = ('NAICS22', 'INDEX ITEM DESCRIPTION')
LEAVES = frozenset({'111110', '111120', '111130'})
GOOD_ROWS = [
    ('111110', 'Soybean farming '),
    ('111120', 'Oilseed farming'),
    ('111130', 'Soybean farming'),
    (CROSS, 'Laboratories (see specific type)'),
    (CROSS, 'Wholesale -- see type of product '),
]
INDEX_PATHS = {
    2012: 'references/naics/2012_fixture_index.xlsx',
    2017: 'references/naics/2017_fixture_index.xlsx',
    2022: 'references/naics/2022_fixture_index.xlsx',
}


def parse(tmp_path, rows=GOOD_ROWS, *, sheet=SHEET, header=HEADER, extra=None, **changes):
    '''Write rows as a workbook, and parse it under the reference that GOOD_ROWS registers.'''
    reference = fixture_index_registry(tmp_path, {2022: GOOD_ROWS})['naics_index_2022']
    file = tmp_path / reference.relative
    if extra == 'column':
        write_xlsx(file, [[*header, 'x'], *[[*row, 'x'] for row in rows]], sheet=sheet)
    else:
        write_index_workbook(file, sheet, header, rows)
    if extra == 'sheet':
        add_second_sheet(file)
    return iir.parse_index(file, replace(reference, **changes), LEAVES)


def add_second_sheet(file):
    '''Rewrite a one-sheet workbook so that it also holds a copy of its sheet, named Extra.'''
    with ZipFile(file) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    relationships = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    worksheet = 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'
    parts['xl/worksheets/sheet2.xml'] = parts['xl/worksheets/sheet1.xml']
    parts['xl/workbook.xml'] = parts['xl/workbook.xml'].replace(
        b'</sheets>', b'<sheet name="Extra" sheetId="2" r:id="rId2"/></sheets>'
    )
    parts['xl/_rels/workbook.xml.rels'] = parts['xl/_rels/workbook.xml.rels'].replace(
        b'</Relationships>',
        f'<Relationship Id="rId2" Type="{relationships}/worksheet" '
        'Target="worksheets/sheet2.xml"/></Relationships>'.encode(),
    )
    parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace(
        b'</Types>',
        f'<Override PartName="/xl/worksheets/sheet2.xml" ContentType="{worksheet}"/></Types>'
        .encode(),
    )
    with ZipFile(file, 'w') as archive:
        for name, body in parts.items():
            archive.writestr(name, body)


def with_row(index, row):
    rows = list(GOOD_ROWS)
    rows[index] = row
    return rows


def test_parse_keeps_cross_references_and_delivered_entries(tmp_path):
    result = parse(tmp_path)
    assert result.schema == iir.INDEX_SCHEMA
    assert result.rows() == [(2022, code, entry) for code, entry in GOOD_ROWS]
    assert result['entry'][0] == 'Soybean farming '
    assert result['entry'][4] == 'Wholesale -- see type of product '
    assert result['code'].to_list()[3:] == [CROSS, CROSS]


@pytest.mark.parametrize(
    ('options', 'message'),
    [
        pytest.param({'sheet': 'Sheet1'}, 'expected one sheet', id='wrong-sheet-name'),
        pytest.param({'extra': 'sheet'}, 'expected one sheet', id='extra-sheet'),
        pytest.param({'extra': 'column'}, 'expected one sheet', id='three-columns'),
        pytest.param(
            {'header': ('NAICS 22', HEADER[1])}, 'unexpected index header', id='first-header'
        ),
        pytest.param(
            {'header': (HEADER[0], 'ITEM DESCRIPTION')}, 'unexpected index header',
            id='second-header',
        ),
        pytest.param(
            {'header': (HEADER[1], HEADER[0])}, 'unexpected index header', id='swapped-header'
        ),
        pytest.param(
            {'rows': with_row(1, (None, 'Oilseed farming'))}, 'blank index code', id='null-code'
        ),
        pytest.param(
            {'rows': with_row(1, ('   ', 'Oilseed farming'))}, 'blank index code',
            id='blank-code',
        ),
        pytest.param(
            {'rows': with_row(1, ('111120', None))}, 'blank index entry', id='null-entry'
        ),
        pytest.param(
            {'rows': with_row(1, ('111120', '   '))}, 'blank index entry', id='blank-entry'
        ),
        pytest.param(
            {'rows': with_row(1, ('111120', '  '))}, 'blank index entry',
            id='nonbreaking-space-entry',
        ),
        pytest.param(
            {'rows': with_row(1, ('111111', 'Oilseed farming'))}, 'neither a leaf',
            id='non-leaf-six-digit',
        ),
        pytest.param(
            {'rows': with_row(1, ('11111', 'Oilseed farming'))}, 'neither a leaf',
            id='five-digit',
        ),
        pytest.param(
            {'rows': with_row(1, ('517110', 'Oilseed farming'))}, 'neither a leaf',
            id='other-vintage-leaf',
        ),
        pytest.param(
            {'rows': with_row(3, ('*****', 'Laboratories (see specific type)'))},
            'neither a leaf', id='short-marker',
        ),
        pytest.param({'expected_rows': 6}, 'row count changed', id='one-row-short'),
        pytest.param({'expected_rows': 4}, 'row count changed', id='one-row-extra'),
        pytest.param(
            {'expected_cross_references': 3}, 'cross-reference count changed',
            id='one-cross-reference-short',
        ),
        pytest.param(
            {'expected_cross_references': 1}, 'cross-reference count changed',
            id='one-cross-reference-extra',
        ),
    ],
)
def test_parse_refuses(tmp_path, options, message):
    with pytest.raises(ValueError, match=message):
        parse(tmp_path, **options)


def test_parse_strips_the_code_and_the_header_but_not_the_entry(tmp_path):
    rows = [(' 111110 ', ' Soybean farming '), (f' {CROSS} ', ' Wholesale -- see ')]
    result = parse(
        tmp_path, rows, header=(' NAICS22 ', ' INDEX ITEM DESCRIPTION '),
        expected_rows=2, expected_cross_references=1,
    )
    assert result.rows() == [
        (2022, '111110', ' Soybean farming '), (2022, CROSS, ' Wholesale -- see ')
    ]


def test_entries_sharing_text_across_codes_are_kept(tmp_path):
    result = parse(tmp_path, with_row(2, ('111130', 'Oilseed farming')))
    assert result.filter(pl.col('entry').eq('Oilseed farming'))['code'].to_list() == [
        '111120', '111130'
    ]
    assert result.height == 5


def test_repeated_rows_are_kept_in_file_order(tmp_path):
    rows = [
        ('111130', 'Zebra'), ('111110', 'Alpha'), ('111130', 'Zebra'), (CROSS, 'Alpha'),
        (CROSS, 'Alpha'),
    ]
    result = parse(tmp_path, rows)
    assert result.rows() == [(2022, code, entry) for code, entry in rows]


def test_leaves_by_vintage_keeps_six_digit_codes_of_each_vintage():
    codes = {2012: ['11', '1111', '111110', '111120'], 2017: ['11', '111110', '517311']}
    titles = pl.DataFrame(
        [(v, c, 'Fixture') for v, items in codes.items() for c in items],
        schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
        orient='row',
    )
    assert iir.leaves_by_vintage(titles) == {
        2012: frozenset({'111110', '111120'}), 2017: frozenset({'111110', '517311'})
    }


def test_production_registry_records_inspected_originals():
    header = 'INDEX ITEM DESCRIPTION'
    expected = {
        'naics_index_2012': iir.IndexReference(
            'naics_index_2012', 2012,
            'https://www.census.gov/naics/2012NAICS/2012_NAICS_Index_File.xls',
            'naics/2012_NAICS_Index_File.xls', '2012NAICS', ('NAICS12', header),
            'c688f221987497db897bbc0e641156997d4e2f528e4fd390a3ad983b13462a23',
            2177024, 19280, 25,
        ),
        'naics_index_2017': iir.IndexReference(
            'naics_index_2017', 2017,
            'https://www.census.gov/naics/2017NAICS/2017_NAICS_Index_File.xlsx',
            'naics/2017_NAICS_Index_File.xlsx', '2017NAICS', ('NAICS17', header),
            'fb3b428300f698aa3d623e1a0edc50aaa3b729e930b7cdc22851825f487fb1ac',
            509235, 20082, 25,
        ),
        'naics_index_2022': iir.IndexReference(
            'naics_index_2022', 2022,
            'https://www.census.gov/naics/2022NAICS/2022_NAICS_Index_File.xlsx',
            'naics/2022_NAICS_Index_File.xlsx', '2022NAICS', ('NAICS22', header),
            '6506b37b9546dd9cec1f8b79e0b38b68e547a5cce5fd6f8332d35024dbd6cd63',
            499358, 20398, 25,
        ),
    }
    assert list(iir.REGISTRY) == list(expected)
    for kind, reference in iir.REGISTRY.items():
        for field in fields(reference):
            assert getattr(reference, field.name) == getattr(expected[kind], field.name)
    assert iir.INDEX_VERSION == 'naics-index-v1'
    assert iir.CROSS_REFERENCE == '******'
    assert iir.INDEX_SCHEMA == {'vintage': pl.Int64, 'code': pl.String, 'entry': pl.String}


@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    root = tmp_path_factory.mktemp('seeded')
    seed_structure_titles(root / 'data', root / 'originals')
    return root / 'data', ita_references.read_titles(root / 'data')


@pytest.fixture
def data_dir(tmp_path, seeded):
    shutil.copytree(seeded[0], tmp_path / 'data')
    return tmp_path / 'data'


@pytest.fixture
def titles(seeded):
    return seeded[1]


class Mirror:
    '''Fixture workbooks served by URL path through a mock transport; requests are recorded.'''

    def __init__(self, monkeypatch, directory, rows=INDEX_ROWS):
        self.directory = directory
        self.registry = fixture_index_registry(directory, rows)
        self.bodies = {
            urlparse(reference.url).path: (directory / reference.relative).read_bytes()
            for reference in self.registry.values()
        }
        self.requests = []
        transport = httpx.MockTransport(self.respond)
        monkeypatch.setattr(
            iir, 'make_client', partial(osha_benchmark_download.make_client, transport=transport)
        )

    def respond(self, request):
        self.requests.append(str(request.url))
        body = self.bodies.get(request.url.path)
        if body is None:
            return httpx.Response(404, stream=httpx.ByteStream(b''))
        return httpx.Response(200, stream=httpx.ByteStream(body))

    def original(self, vintage):
        return self.directory / self.registry[f'naics_index_{vintage}'].relative

    def serve(self, vintage, body):
        self.bodies[urlparse(self.registry[f'naics_index_{vintage}'].url).path] = body


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    return Mirror(monkeypatch, tmp_path / 'served')


def index_entries(data_dir):
    return [
        entry for entry in manifest.read_manifest(paths.manifest_path(data_dir))
        if entry.path in INDEX_PATHS.values()
    ]


def published(data_dir, vintage):
    relative = INDEX_PATHS[vintage].removeprefix('references/')
    return ita_references.reference_path(data_dir, relative)


def test_acquire_downloads_missing_and_records_once(data_dir, mirror):
    destinations = iir.acquire(data_dir, registry=mirror.registry)
    assert [path.name for path in destinations] == [
        '2012_fixture_index.xlsx', '2017_fixture_index.xlsx', '2022_fixture_index.xlsx'
    ]
    assert mirror.requests == [reference.url for reference in mirror.registry.values()]
    for reference, destination in zip(mirror.registry.values(), destinations, strict=True):
        assert destination == iir.reference_path(data_dir, reference)
        assert destination.read_bytes() == mirror.original(reference.vintage).read_bytes()
        assert not destination.with_name(destination.name + '.part').exists()
    entries = index_entries(data_dir)
    assert [entry.path for entry in entries] == list(INDEX_PATHS.values())
    for entry, reference in zip(entries, mirror.registry.values(), strict=True):
        assert entry.client == 'httpx'
        assert entry.client_version == version('httpx')
        assert entry.proxies == ()
        assert entry.source_url == reference.url
        assert (entry.sha256, entry.size) == (reference.sha256, reference.size)
    before = paths.manifest_path(data_dir).read_bytes()
    assert iir.acquire(data_dir, registry=mirror.registry) == destinations
    assert len(mirror.requests) == 3
    assert paths.manifest_path(data_dir).read_bytes() == before


def test_acquire_skips_recorded_originals_and_downloads_the_rest(data_dir, mirror):
    only_2012 = {'naics_index_2012': mirror.registry['naics_index_2012']}
    iir.acquire(data_dir, registry=only_2012)
    assert len(mirror.requests) == 1
    iir.acquire(data_dir, registry=mirror.registry)
    assert mirror.requests[1:] == [
        mirror.registry['naics_index_2017'].url, mirror.registry['naics_index_2022'].url
    ]
    assert [entry.path for entry in index_entries(data_dir)] == list(INDEX_PATHS.values())


@pytest.mark.parametrize('state', ['unrecorded', 'part', 'symlink'])
def test_acquire_refuses_unsafe_state_before_any_request(data_dir, mirror, state):
    before = paths.manifest_path(data_dir).read_bytes()
    last = published(data_dir, 2022)
    last.parent.mkdir(parents=True, exist_ok=True)
    if state == 'unrecorded':
        last.write_bytes(mirror.original(2022).read_bytes())
        message = 'without recorded provenance'
    elif state == 'part':
        last.with_name(last.name + '.part').write_bytes(b'interrupted')
        message = 'symlink or interrupted'
    else:
        last.symlink_to(mirror.original(2022))
        message = 'symlink or interrupted'
    with pytest.raises(ValueError, match=message):
        iir.acquire(data_dir, registry=mirror.registry)
    assert mirror.requests == []
    assert not published(data_dir, 2012).exists()
    assert paths.manifest_path(data_dir).read_bytes() == before


@pytest.mark.parametrize(
    ('mutate', 'message'),
    [
        pytest.param(lambda body: body + b'x', 'size differs', id='size'),
        pytest.param(lambda body: body[:-1] + bytes([body[-1] ^ 1]), 'SHA-256 differs', id='hash'),
    ],
)
def test_acquire_refuses_changed_bytes(data_dir, mirror, mutate, message):
    before = paths.manifest_path(data_dir).read_bytes()
    mirror.serve(2012, mutate(mirror.bodies['/naics/2012_fixture_index.xlsx']))
    with pytest.raises(ValueError, match=message):
        iir.acquire(data_dir, registry=mirror.registry)
    assert not published(data_dir, 2012).exists()
    assert not published(data_dir, 2012).with_name('2012_fixture_index.xlsx.part').exists()
    assert paths.manifest_path(data_dir).read_bytes() == before


@pytest.mark.parametrize(
    ('change', 'message'),
    [
        pytest.param({'size': 1}, 'size differs', id='size'),
        pytest.param({'sha256': '0' * 64}, 'SHA-256 differs', id='hash'),
    ],
)
def test_acquire_checks_each_pin_field_of_the_served_bytes(data_dir, mirror, change, message):
    registry = {
        kind: replace(reference, **change) if reference.vintage == 2017 else reference
        for kind, reference in mirror.registry.items()
    }
    with pytest.raises(ValueError, match=message):
        iir.acquire(data_dir, registry=registry)
    assert not published(data_dir, 2017).exists()


def test_acquire_parses_before_publishing(data_dir, tmp_path, monkeypatch):
    rows = {**INDEX_ROWS, 2012: [('111111', 'Not a leaf'), *INDEX_ROWS[2012][1:]]}
    mirror = Mirror(monkeypatch, tmp_path / 'bad', rows)
    before = paths.manifest_path(data_dir).read_bytes()
    with pytest.raises(ValueError, match='neither a leaf'):
        iir.acquire(data_dir, registry=mirror.registry)
    assert not published(data_dir, 2012).exists()
    assert paths.manifest_path(data_dir).read_bytes() == before


def test_acquire_checks_codes_against_the_leaves_of_their_own_vintage(
    data_dir, tmp_path, monkeypatch
):
    # 517110 is a 2012 leaf only. Under 2017 it is a leaf of no 2017 structure.
    rows = {**INDEX_ROWS, 2017: [('517110', 'Telephone'), *INDEX_ROWS[2017][1:]]}
    mirror = Mirror(monkeypatch, tmp_path / 'bad', rows)
    with pytest.raises(ValueError, match='neither a leaf'):
        iir.acquire(data_dir, registry=mirror.registry)
    assert not published(data_dir, 2017).exists()


@pytest.mark.parametrize(
    ('change', 'message'),
    [
        pytest.param({'size': 1}, 'size differs', id='size'),
        pytest.param({'sha256': '0' * 64}, 'SHA-256 differs', id='hash'),
    ],
)
def test_acquire_checks_the_pin_of_a_recorded_original(data_dir, mirror, change, message):
    iir.acquire(data_dir, registry=mirror.registry)
    requests = len(mirror.requests)
    registry = {
        kind: replace(reference, **change) if reference.vintage == 2022 else reference
        for kind, reference in mirror.registry.items()
    }
    with pytest.raises(ValueError, match=message):
        iir.acquire(data_dir, registry=registry)
    assert len(mirror.requests) == requests


def test_acquire_verifies_the_manifest_hash_of_a_recorded_original(data_dir, mirror):
    iir.acquire(data_dir, registry=mirror.registry)
    original = published(data_dir, 2012)
    original.write_bytes(original.read_bytes()[:-1] + b'x')
    with pytest.raises(ValueError, match='SHA-256'):
        iir.acquire(data_dir, registry=mirror.registry)
    assert len(mirror.requests) == 3


def test_import_records_proxy_time(data_dir, mirror):
    original = mirror.original(2012)
    destination = iir.import_reference(
        data_dir, 'naics_index_2012', original, registry=mirror.registry
    )
    assert destination == published(data_dir, 2012)
    assert destination.read_bytes() == original.read_bytes()
    [entry] = index_entries(data_dir)
    assert entry.client == 'manual-import'
    assert entry.client_version == version('embedding-data')
    assert entry.proxies == ('retrieved_at',)
    assert entry.source_url == mirror.registry['naics_index_2012'].url
    assert entry == manifest.entry_for(paths.manifest_path(data_dir), destination)
    before = paths.manifest_path(data_dir).read_bytes()
    assert iir.import_reference(
        data_dir, 'naics_index_2012', original, registry=mirror.registry
    ) == destination
    assert paths.manifest_path(data_dir).read_bytes() == before
    other = mirror.directory / 'other.xlsx'
    write_index_workbook(other, '2012NAICS', ('NAICS12', 'INDEX ITEM DESCRIPTION'), [
        ('517110', 'Other entry'), *INDEX_ROWS[2012][1:]
    ])
    with pytest.raises(ValueError, match='different bytes'):
        iir.import_reference(data_dir, 'naics_index_2012', other, registry=mirror.registry)
    assert paths.manifest_path(data_dir).read_bytes() == before
    assert mirror.requests == []


def test_publish_refuses_bytes_that_change_while_copying(data_dir, mirror, monkeypatch):
    copy = shutil.copyfileobj

    def corrupt(source, output, *arguments):
        copy(source, output, *arguments)
        output.write(b'x')

    monkeypatch.setattr(iir.shutil, 'copyfileobj', corrupt)
    with pytest.raises(ValueError, match='changed while copying'):
        iir.import_reference(
            data_dir, 'naics_index_2012', mirror.original(2012), registry=mirror.registry
        )
    destination = published(data_dir, 2012)
    assert not destination.exists()
    assert not destination.with_name(destination.name + '.part').exists()
    assert index_entries(data_dir) == []


def test_publish_never_replaces_a_destination_that_appears(data_dir, mirror, monkeypatch):
    copy = shutil.copyfileobj
    destination = published(data_dir, 2012)

    def compete(source, output, *arguments):
        copy(source, output, *arguments)
        destination.write_bytes(b'competitor')

    monkeypatch.setattr(iir.shutil, 'copyfileobj', compete)
    with pytest.raises(ValueError, match='appeared'):
        iir.import_reference(
            data_dir, 'naics_index_2012', mirror.original(2012), registry=mirror.registry
        )
    assert destination.read_bytes() == b'competitor'
    assert not destination.with_name(destination.name + '.part').exists()
    assert index_entries(data_dir) == []


def test_import_refuses_an_unknown_kind(data_dir, mirror):
    with pytest.raises(ValueError, match='unknown registered reference'):
        iir.import_reference(
            data_dir, 'naics_index_2007', mirror.original(2012), registry=mirror.registry
        )


@pytest.mark.parametrize('state', ['unrecorded', 'part'])
def test_import_refuses_unsafe_state(data_dir, mirror, state):
    destination = published(data_dir, 2012)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if state == 'unrecorded':
        destination.write_bytes(mirror.original(2012).read_bytes())
        message = 'without recorded provenance'
    else:
        destination.with_name(destination.name + '.part').write_bytes(b'interrupted')
        message = 'symlink or interrupted'
    with pytest.raises(ValueError, match=message):
        iir.import_reference(
            data_dir, 'naics_index_2012', mirror.original(2012), registry=mirror.registry
        )
    assert index_entries(data_dir) == []


def test_import_refuses_bytes_that_differ_from_the_pin_or_do_not_parse(
    data_dir, mirror, tmp_path
):
    changed = tmp_path / 'changed.xlsx'
    changed.write_bytes(mirror.original(2012).read_bytes() + b'x')
    with pytest.raises(ValueError, match='size differs'):
        iir.import_reference(data_dir, 'naics_index_2012', changed, registry=mirror.registry)
    rows = [('111111', 'Not a leaf'), *INDEX_ROWS[2012][1:]]
    bad = fixture_index_registry(tmp_path / 'bad', {2012: rows})
    with pytest.raises(ValueError, match='neither a leaf'):
        iir.import_reference(
            data_dir, 'naics_index_2012', tmp_path / 'bad' / bad['naics_index_2012'].relative,
            registry=bad,
        )
    assert not published(data_dir, 2012).exists()
    assert index_entries(data_dir) == []


def published_registry(data_dir, mirror):
    iir.acquire(data_dir, registry=mirror.registry)
    return mirror.registry


def test_read_index_returns_every_row_with_vintages_ascending(data_dir, mirror, titles):
    registry = published_registry(data_dir, mirror)
    result = iir.read_index(data_dir, titles, registry=dict(reversed(registry.items())))
    assert result.schema == iir.INDEX_SCHEMA
    assert result.rows() == [
        (vintage, code, entry) for vintage, rows in INDEX_ROWS.items() for code, entry in rows
    ]
    assert result['vintage'].unique(maintain_order=True).to_list() == [2012, 2017, 2022]


def test_read_index_verifies_manifest_and_pin(data_dir, mirror, titles):
    registry = published_registry(data_dir, mirror)
    original = published(data_dir, 2017)
    original.write_bytes(original.read_bytes()[:-1] + b'x')
    with pytest.raises(ValueError):
        iir.read_index(data_dir, titles, registry=registry)


def test_read_index_verifies_the_manifest_hash_of_a_valid_workbook(data_dir, mirror, titles):
    registry = published_registry(data_dir, mirror)
    rows = [(code, 'Changed' if i == 1 else entry) for i, (code, entry) in enumerate(
        INDEX_ROWS[2017])]
    write_index_workbook(
        published(data_dir, 2017), '2017NAICS', ('NAICS17', 'INDEX ITEM DESCRIPTION'), rows
    )
    new = published(data_dir, 2017)
    registry['naics_index_2017'] = replace(
        registry['naics_index_2017'],
        size=new.stat().st_size,
        sha256=manifest.sha256_file(new),
    )
    with pytest.raises(ValueError, match='recorded in'):
        iir.read_index(data_dir, titles, registry=registry)


@pytest.mark.parametrize(
    ('change', 'message'),
    [
        pytest.param({'size': 1}, 'size differs', id='size'),
        pytest.param({'sha256': '0' * 64}, 'SHA-256 differs', id='hash'),
    ],
)
def test_read_index_checks_each_pin_field(data_dir, mirror, titles, change, message):
    registry = published_registry(data_dir, mirror)
    registry['naics_index_2022'] = replace(registry['naics_index_2022'], **change)
    with pytest.raises(ValueError, match=message):
        iir.read_index(data_dir, titles, registry=registry)


def test_read_index_parses_with_the_leaves_of_the_given_titles(data_dir, mirror, titles):
    registry = published_registry(data_dir, mirror)
    without_leaf = titles.filter(~(pl.col('vintage').eq(2022) & pl.col('code').eq('517111')))
    with pytest.raises(ValueError, match='neither a leaf'):
        iir.read_index(data_dir, without_leaf, registry=registry)


def test_citations_are_verified_manifest_entries_sorted_by_path(data_dir, mirror):
    registry = published_registry(data_dir, mirror)
    expected = sorted(
        (asdict(entry) for entry in index_entries(data_dir)), key=lambda entry: entry['path']
    )
    assert iir.citations(data_dir, registry=dict(reversed(registry.items()))) == expected
    assert [entry['path'] for entry in expected] == list(INDEX_PATHS.values())
    original = published(data_dir, 2022)
    original.write_bytes(original.read_bytes()[:-1] + b'x')
    with pytest.raises(ValueError, match='SHA-256'):
        iir.citations(data_dir, registry=registry)
