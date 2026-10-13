'''Acquire immutable official ITA verification references and read NAICS titles.'''

import re
import shutil
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import manifest, paths
from embedding_data.osha_benchmark_download import download, record_download

TITLE_FILES = {
    2012: 'https://www.census.gov/naics/2012NAICS/2012_NAICS_Structure.xls',
    2017: 'https://www.census.gov/naics/2017NAICS/2017_NAICS_Structure.xlsx',
    2022: 'https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx',
}
HUD_SOURCE = 'https://www.huduser.gov/portal/datasets/usps_crosswalk.html'
CODE_PATTERN = r'^(?:[0-9]{2,6}|31-33|44-45|48-49)$'

def reference_path(data_dir: Path, relative: str) -> Path:
    return paths.raw_dir(data_dir, 'references') / relative

def existing_reference(data_dir: Path, file: Path) -> bool:
    try:
        manifest.recorded_entry_for(paths.manifest_path(data_dir), file)
    except KeyError:
        if file.exists():
            raise ValueError(f'{file}: exists without recorded provenance') from None
        return False
    manifest.entry_for(paths.manifest_path(data_dir), file)
    return True

def fetch_reference(data_dir: Path, client: httpx.Client, url: str, relative: str) -> Path:
    file = reference_path(data_dir, relative)
    if existing_reference(data_dir, file):
        return file
    file.parent.mkdir(parents=True, exist_ok=True)
    download(client, url, file)
    record_download(paths.manifest_path(data_dir), file, url)
    return file

def acquire_titles(data_dir: Path) -> list[Path]:
    destinations = [
        reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1]) for url in TITLE_FILES.values()
    ]
    for file in destinations:
        existing_reference(data_dir, file)
    with httpx.Client(http2=True, follow_redirects=True, timeout=120) as client:
        return [
            fetch_reference(data_dir, client, url, 'naics/' + url.rsplit('/', 1)[1])
            for url in TITLE_FILES.values()
        ]

def import_hud(data_dir: Path, workbook: Path, quarter: str) -> Path:
    if not re.fullmatch(r'[0-9]{4}Q[1-4]', quarter):
        raise ValueError('quarter must be YYYYQ1 through YYYYQ4')
    read_hud(workbook)
    file = reference_path(data_dir, f'hud/{quarter}/{workbook.name}')
    if existing_reference(data_dir, file):
        if manifest.sha256_file(workbook) != manifest.sha256_file(file):
            raise ValueError('this quarter/name already records different bytes')
        return file
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_name(file.name + '.part')
    try:
        shutil.copyfile(workbook, partial)
        partial.replace(file)
    finally:
        partial.unlink(missing_ok=True)
    entry = manifest.describe_file(
        file,
        paths.manifest_path(data_dir).parent,
        retrieved_at=datetime.now(UTC),
        client='manual-import',
        client_version=version('embedding-data'),
        source_url=HUD_SOURCE,
        proxies=('retrieved_at', ),
    )
    manifest.append_entries(paths.manifest_path(data_dir), [entry])
    return file

def read_hud(file: Path) -> pl.DataFrame:
    raw = pl.read_excel(file, read_options={'dtypes': 'string'})
    raw.columns = [name.strip().upper() for name in raw.columns]
    if {'COUNTY', 'GEOID'}.issubset(raw.columns):
        raise ValueError('ambiguous HUD COUNTY/GEOID columns')
    if 'GEOID' in raw.columns:
        if not re.fullmatch(r'ZIP[-_]COUNTY(?:[-_][0-9]+)?\.xlsx?', file.name, re.IGNORECASE):
            raise ValueError('HUD GEOID requires an unambiguous ZIP-COUNTY workbook name')
        raw = raw.rename({'GEOID': 'COUNTY'})
    if not {'ZIP', 'COUNTY', 'BUS_RATIO'}.issubset(raw.columns):
        raise ValueError('HUD ZIP/COUNTY/BUS_RATIO columns missing')
    state = pl.col('STATE').str.strip_chars() if 'STATE' in raw.columns else pl.lit(None)
    normalized = raw.lazy().select(
        zip_key=pl.col('ZIP').str.strip_chars().str.replace(r'\.0$', '').str.zfill(5),
        county_geoid=pl.col('COUNTY').str.strip_chars().str.replace(r'\.0$', ''),
        bus_ratio=pl.col('BUS_RATIO').cast(pl.Float64, strict=True),
        state=state,
    )
    noncounty = pl.any_horizontal([
        pl.col('county_geoid').eq(code).and_(pl.col('state').eq(state_code))
        for state_code, code in {'AS': '60', 'FM': '64', 'MH': '68', 'PW': '70'}.items()
    ]).and_(pl.col('bus_ratio').eq(0)).fill_null(False)
    result = normalized.with_columns(noncounty_geography=noncounty).sort(
        'zip_key', 'county_geoid'
    ).collect()
    invalid = result.filter(
        pl.col('zip_key').str.contains(r'^[0-9]{5}$').not_().or_(
            pl.col('county_geoid').str.contains(r'^[0-9]{5}$').not_().and_(
                pl.col('noncounty_geography').not_()
            )
        ).or_(pl.col('bus_ratio').is_null()).or_(pl.col('bus_ratio').is_finite().not_()).or_(
            pl.col('bus_ratio').is_between(0, 1).not_()
        ).fill_null(True)
    )
    if invalid.height or result.is_empty() or result.select(
        'zip_key', 'county_geoid'
    ).is_duplicated().any():
        raise ValueError('invalid or duplicate HUD candidates')
    return result.drop('state')


def parse_titles(raw: pl.DataFrame, vintage: int) -> pl.DataFrame:
    for index, row in enumerate(raw.rows()):
        cells = [str(value).strip() for value in row if value is not None]
        heading = ' | '.join(cells).lower()
        if len(cells) >= 2 and all(token in heading for token in (str(vintage), 'code', 'title')):
            names = [
                str(value).strip() if value is not None else f'column_{i}'
                for i, value in enumerate(row)
            ]
            body = raw.slice(index + 1)
            body.columns = names
            break
    else:
        raise ValueError(f'{vintage}: NAICS header not found')
    code_columns = [name for name in names if 'code' in name.lower()]
    title_columns = [name for name in names if 'title' in name.lower()]
    if len(code_columns) != 1 or len(title_columns) != 1:
        raise ValueError(f'{vintage}: ambiguous code/title header')
    result = (
        body.lazy().select(
            vintage=pl.lit(vintage, dtype=pl.Int64),
            code=pl.col(code_columns[0]).cast(pl.String
                                              ).str.strip_chars().str.replace(r'\.0$', ''),
            title=pl.col(title_columns[0]).cast(pl.String).str.strip_chars(),
        ).filter(pl.col('code').str.contains(CODE_PATTERN)).with_columns(
            title=pl.col('title').str.replace(r'([a-z)])T$', '${1}')
        ).sort('code').collect()
    )
    if result.is_empty() or result['code'].n_unique() != result.height:
        raise ValueError(f'{vintage}: empty or duplicate NAICS codes')
    if result['title'].null_count() or result.filter(pl.col('title').eq('')).height:
        raise ValueError(f'{vintage}: missing title')
    return result

def read_titles(data_dir: Path) -> pl.DataFrame:
    frames = []
    expected = {2012: (2209, 1065), 2017: (2196, 1057), 2022: (2125, 1012)}
    for vintage, url in TITLE_FILES.items():
        file = reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1])
        manifest.entry_for(paths.manifest_path(data_dir), file)
        raw = pl.read_excel(file, has_header=False, read_options={'dtypes': 'string'})
        frame = parse_titles(raw, vintage)
        actual = (frame.height, frame.filter(pl.col('code').str.len_chars().eq(6)).height)
        if actual != expected[vintage]:
            raise ValueError(f'{vintage}: structure counts changed: {actual}')
        frames.append(frame)
    return pl.concat(frames).sort('vintage', 'code')
