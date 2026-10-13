import csv
import io
import json
import re

import httpx
import polars as pl
import pytest
from ita_fixtures import record, write_release, year_file

from embedding_data import ita_references as refs
from embedding_data import ita_verification_run as run
from embedding_data import paths
from embedding_data.osha_benchmark_download import record_download

def test_raw_summary_to_cached_offline_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'BATCH_LIMIT', 3)
    for year in range(2016, 2026):
        write_release(
            tmp_path, year,
            year_file(year, [record(year, state='MA', city='Town', establishment_id='10')])
        )
    for url in refs.TITLE_FILES.values():
        file = refs.reference_path(tmp_path, 'naics/' + url.rsplit('/', 1)[1])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'fixture workbook boundary')
        record_download(paths.manifest_path(tmp_path), file, url)
    hud = refs.reference_path(tmp_path, 'hud/2025Q4/fixture.xlsx')
    hud.parent.mkdir(parents=True, exist_ok=True)
    hud.write_bytes(b'fixture HUD workbook boundary')
    record_download(paths.manifest_path(tmp_path), hud, refs.HUD_SOURCE)
    # Only small-workbook I/O boundaries are replaced; real raw harmonization,
    # normalization, sampling, response parsing and report transforms run.
    monkeypatch.setattr(
        refs, 'read_titles', lambda _: pl.DataFrame(
            {
                'vintage': [2022],
                'code': ['31-33'],
                'title': ['Manufacturing'],
            }
        )
    )
    monkeypatch.setattr(
        run.county, 'read_hud', lambda _: pl.DataFrame(
            {
                'zip_key': ['02134'],
                'county_geoid': ['25025'],
                'bus_ratio': [1.0],
            }
        )
    )
    directory = run.prepare(tmp_path, hud, 'fixture')
    batches = sorted((directory / 'requests').glob('*.csv'))
    assert len(batches) == 4
    assert all(len(list(csv.reader(file.open()))) <= 3 for file in batches)

    def respond(request):
        if request.url.path.endswith('/benchmarks'):
            return httpx.Response(
                200,
                stream=httpx.ByteStream(
                    json.dumps(
                        {
                            'benchmarks': [{
                                'id': '4',
                                'benchmarkName': 'Public_AR_Current',
                            }]
                        }
                    ).encode()
                )
            )
        if request.url.path.endswith('/vintages'):
            return httpx.Response(
                200,
                stream=httpx.ByteStream(
                    json.dumps({
                        'vintages': [{
                            'id': '425',
                            'vintageName': 'ACS2025_Current',
                        }]
                    }).encode()
                )
            )
        output = io.StringIO()
        writer = csv.writer(output)
        filename = re.search(rb'filename="([^"]+)"', request.content).group(1).decode()
        with (directory / 'requests' / filename).open(newline='') as stream:
            row_keys = [row[0] for row in csv.reader(stream)]
        for row_key in row_keys:
            writer.writerow(
                [
                    row_key, 'address', 'Match', 'Exact', 'matched', '-71,42', '7', 'L', '25',
                    '025', '1', '1'
                ]
            )
        return httpx.Response(200, content=output.getvalue().encode())

    monkeypatch.setattr(
        run, 'make_client', lambda: httpx.Client(transport=httpx.MockTransport(respond))
    )
    run.acquire_geocodes(tmp_path, 'fixture')
    monkeypatch.setattr(
        run, 'make_client', lambda: (_ for _ in ()).throw(AssertionError('network'))
    )
    before = paths.manifest_path(tmp_path).read_bytes()
    first = run.measure(tmp_path, 'fixture')
    second = run.measure(tmp_path, 'fixture')
    assert first == second
    assert first['v3_overall']['n_sample'] == 10
    assert {item['year_filing_for'] for item in first['v1']} == set(range(2016, 2026))
    assert paths.manifest_path(tmp_path).read_bytes() == before
    assert all(
        item['n_same_ein_address'] == 1 for item in first['v2'] if item['base_year'] == 2023
    )
    original = batches[0].read_bytes()
    batches[0].write_bytes(original + b'changed')
    with pytest.raises(ValueError, match='input changed'):
        run.measure(tmp_path, 'fixture')
    batches[0].write_bytes(original)
    with monkeypatch.context() as patch:
        patch.setattr(run, 'version', lambda _: 'changed')
        with pytest.raises(ValueError, match='dependency version changed'):
            run.measure(tmp_path, 'fixture')
    sha256_file = run.manifest.sha256_file
    with monkeypatch.context() as patch:
        patch.setattr(
            run.manifest, 'sha256_file', lambda file: (
                'changed' if file.name == 'ita_verification.py' else sha256_file(file)
            )
        )
        with pytest.raises(ValueError, match='code changed'):
            run.measure(tmp_path, 'fixture')
