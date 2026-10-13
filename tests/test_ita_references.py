import httpx
import polars as pl
import pytest

from embedding_data import ita_references, manifest, paths

def test_title_parser_handles_preamble_ranges_and_trilateral_marker():
    raw = pl.DataFrame(
        {
            'a': ['2017 NAICS Structure', '2017 NAICS Code', '31-33', '332312'],
            'b': [None, '2017 NAICS Title', 'ManufacturingT', 'Fabricated Structural Metal'],
            'c': [None, 'Change Indicator', None, None],
        }
    )
    titles = ita_references.parse_titles(raw, 2017)
    assert titles.to_dicts() == [
        {
            'vintage': 2017,
            'code': '31-33',
            'title': 'Manufacturing'
        },
        {
            'vintage': 2017,
            'code': '332312',
            'title': 'Fabricated Structural Metal'
        },
    ]
    with pytest.raises(ValueError, match='header'):
        ita_references.parse_titles(raw, 2022)

def test_reference_replay_never_requests_again(tmp_path):
    requested = []

    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(200, stream=httpx.ByteStream(b'fixture bytes'))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        file = ita_references.fetch_reference(
            tmp_path,
            client,
            'https://www.census.gov/fixture.xls',
            'naics/fixture.xls',
        )
        before = paths.manifest_path(tmp_path).read_bytes()
        again = ita_references.fetch_reference(
            tmp_path,
            client,
            'https://www.census.gov/fixture.xls',
            'naics/fixture.xls',
        )
        assert again == file
        assert requested == ['https://www.census.gov/fixture.xls']
        assert paths.manifest_path(tmp_path).read_bytes() == before
        file.unlink()
        with pytest.raises(FileNotFoundError):
            ita_references.fetch_reference(
                tmp_path,
                client,
                'https://www.census.gov/fixture.xls',
                'naics/fixture.xls',
            )
        assert len(requested) == 1

def test_manual_hud_import_validates_and_records_import_time_proxy(tmp_path, monkeypatch):
    workbook = tmp_path / 'ZIP_COUNTY_122025.xlsx'
    workbook.write_bytes(b'original manual workbook')
    monkeypatch.setattr(
        pl, 'read_excel', lambda *args, **kwargs: pl.DataFrame(
            {
                'ZIP': ['2134'],
                'COUNTY': ['25025'],
                'BUS_RATIO': ['1.0'],
            }
        )
    )
    file = ita_references.import_hud(tmp_path, workbook, '2025Q4')
    assert file.read_bytes() == workbook.read_bytes()
    entry = manifest.entry_for(paths.manifest_path(tmp_path), file)
    assert entry.client == 'manual-import'
    assert entry.proxies == ('retrieved_at', )
    before = paths.manifest_path(tmp_path).read_bytes()
    assert ita_references.import_hud(tmp_path, workbook, '2025Q4') == file
    assert paths.manifest_path(tmp_path).read_bytes() == before
    monkeypatch.setattr(
        pl, 'read_excel', lambda *args, **kwargs: pl.DataFrame({'HTML': ['login']})
    )
    with pytest.raises(ValueError, match='columns missing'):
        ita_references.import_hud(tmp_path, workbook, '2025Q3')
    assert paths.manifest_path(tmp_path).read_bytes() == before

@pytest.mark.parametrize('missing_column', ['ZIP', 'COUNTY'])
def test_hud_reader_rejects_missing_geographic_keys(tmp_path, monkeypatch, missing_column):
    raw = pl.DataFrame(
        {'ZIP': ['02134'], 'COUNTY': ['25025'], 'BUS_RATIO': ['1.0']}
    ).with_columns(pl.lit(None, dtype=pl.String).alias(missing_column))
    monkeypatch.setattr(pl, 'read_excel', lambda *args, **kwargs: raw)
    with pytest.raises(ValueError, match='invalid or duplicate'):
        ita_references.read_hud(tmp_path / 'fixture.xlsx')
