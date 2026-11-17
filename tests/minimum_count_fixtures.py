'''Tiny published Stage 4, Stage 6 and Stage 10 bundles for the minimum-count script.

Rows go through the frozen builders unchanged, so each fixture table has the schema and the
rules of the real bundles. `publish` writes the three bundles with the real file names and
`outputs.json` layout, and `republish` rewrites an inventory after a test changes a file.
'''

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from ita_establishment_fixtures import canonical_frame, naics_reference, native

from embedding_data import (
    ita_area_mix,
    ita_co_ownership,
    ita_establishment_links,
    ita_text_pairs,
    manifest,
    target_io,
)
from embedding_data.ita_establishment_records import KEY_SCHEMA, keyed_records

ESTABLISHMENT_RUN = 'fixture_stage10'
AREA_MIX_RUN = 'fixture_stage6'
CODES_RUN = 'fixture_codes'
ESTABLISHMENT_ROOT = Path('derived/osha/establishment-targets')
AREA_MIX_ROOT = Path('derived/targets')
CODES_ROOT = Path('derived/codes')
CANONICAL = 'ita_300a_canonical.parquet'
COUNTY = 'county:2025:39035'


def row(
    year: int,
    establishment: int,
    code: str,
    description: str,
    *,
    ein: str = '123456789',
    mapping: dict | None = None,
    **changes,
) -> dict:
    '''A canonical override row of one establishment in one filing year.

    The name and street come from `establishment` only, so equal establishments in later
    years make same-ID links. `mapping` defaults to `native(code)`.
    '''
    return {
        'year_filing_for': year,
        'establishment_id': establishment,
        'establishment_name': f'Plant {establishment}',
        'street_address': f'{establishment} Main St',
        'ein': ein,
        'industry_description': description,
        **(mapping if mapping is not None else native(code)),
        **changes,
    }


def golden_rows() -> list[dict]:
    '''One EIN with a plumbing contractor and a restaurant, each filing 2023 to 2025.'''
    return [
        row(year, establishment, code, description)
        for year in (2023, 2024, 2025)
        for establishment, code, description in (
            (1, '238220', 'Plumbing contractor'),
            (2, '722511', 'Restaurant'),
        )
    ]


@dataclass(frozen=True)
class Frames:
    canonical: pl.DataFrame
    links: pl.DataFrame
    pairs: pl.DataFrame
    members: pl.DataFrame
    co_ownership: pl.DataFrame
    support: pl.DataFrame
    assignments: pl.DataFrame
    area_mix: pl.DataFrame
    establishment_report: dict
    area_mix_report: dict


def _reference_codes(canonical: pl.DataFrame) -> list[str]:
    '''The 2022 leaves the rows name: native codes and every 2022 candidate.'''
    native_codes = canonical.filter(pl.col('naics_mapping_status').eq('native_2022'))
    found = set(native_codes['naics_code'].drop_nulls().to_list())
    for candidates in canonical['naics_2022_candidates'].to_list():
        found.update(candidates or [])
    return sorted(found)


def _assignments(canonical: pl.DataFrame, counties: list[str | None]) -> pl.DataFrame:
    if len(counties) != canonical.height:
        raise ValueError('one county per canonical row')
    county = pl.Series('county_id', counties, dtype=pl.String)
    assigned = county.is_not_null()
    return canonical.with_columns(
        source_row=pl.int_range(pl.len(), dtype=pl.UInt64),
        county_id=county,
        assignment_method=pl.when(assigned).then(pl.lit('census_exact'))
        .otherwise(pl.lit('unassigned')),
        assignment_reason=pl.when(assigned).then(pl.lit('exact_census_compatible'))
        .otherwise(pl.lit('no_compatible_county:absent')),
    )


def build_frames(rows: list[dict], counties: list[str | None] | None = None) -> Frames:
    '''The frozen builders' tables for canonical override rows.

    Every row is assigned to `COUNTY` unless `counties` gives one county (or None) per row.
    '''
    lazy = canonical_frame(rows)
    canonical = lazy.collect()
    nodes, code_paths = naics_reference(_reference_codes(canonical))
    records = keyed_records(lazy, pl.DataFrame(schema=KEY_SCHEMA))
    links = ita_establishment_links.build_links(records)
    pairs = ita_text_pairs.build_pairs(records, nodes, code_paths)
    co_ownership = ita_co_ownership.estimate(records)
    assignments = _assignments(
        canonical, [COUNTY] * canonical.height if counties is None else counties)
    area_mix = ita_area_mix.estimate(assignments.lazy(), nodes)
    return Frames(
        canonical=canonical,
        links=links.links.collect(),
        pairs=pairs.pairs.collect(),
        members=pairs.members.collect(),
        co_ownership=co_ownership.targets.collect(),
        support=co_ownership.support.collect(),
        assignments=assignments,
        area_mix=area_mix.targets.collect(),
        establishment_report={'pairs': {
            'records_by_year_status_basis': pairs.report['records_by_year_status_basis']}},
        area_mix_report={'partition_by_year': area_mix.report['partition_by_year']},
    )


@dataclass(frozen=True)
class Published:
    data_dir: Path
    establishment: Path
    area_mix: Path
    codes: Path
    establishment_pin: str
    area_mix_pin: str
    codes_pin: str

    def argv(self) -> list[str]:
        '''The seven command-line options that select these bundles.'''
        return [
            '--data-dir', str(self.data_dir),
            '--establishment-run', self.establishment.name,
            '--establishment-outputs-sha256', self.establishment_pin,
            '--area-mix-run', self.area_mix.name,
            '--area-mix-outputs-sha256', self.area_mix_pin,
            '--codes-run', self.codes.name,
            '--codes-outputs-sha256', self.codes_pin,
        ]


def republish(directory: Path) -> str:
    '''Rewrite `outputs.json` from the current files and return its SHA-256.'''
    names = sorted(p.name for p in directory.iterdir() if p.name != 'outputs.json')
    outputs = directory / 'outputs.json'
    target_io.write_json(outputs, target_io.inventory(directory, names))
    return manifest.sha256_file(outputs)


def _bundle(directory: Path, tables: dict[str, pl.DataFrame], documents: dict) -> str:
    directory.mkdir(parents=True)
    for name, frame in tables.items():
        frame.write_parquet(directory / f'{name}.parquet')
    for name, value in documents.items():
        target_io.write_json(directory / name, value)
    return republish(directory)


def publish(root: Path, frames: Frames) -> Published:
    '''Write the codes, Stage 6 and Stage 10 bundles under `root / 'data'`.'''
    data_dir = root / 'data'
    codes = data_dir / CODES_ROOT / CODES_RUN
    codes_pin = _bundle(codes, {'ita_300a_canonical': frames.canonical}, {})
    canonical = {
        'path': (CODES_ROOT / CODES_RUN / CANONICAL).as_posix(),
        **target_io.file_record(codes / CANONICAL),
    }
    establishment = data_dir / ESTABLISHMENT_ROOT / ESTABLISHMENT_RUN
    establishment_pin = _bundle(
        establishment,
        {
            'ita_establishment_links': frames.links,
            'ita_text_pairs': frames.pairs,
            'ita_text_pair_members': frames.members,
            'ita_co_ownership': frames.co_ownership,
            'co_ownership_support': frames.support,
        },
        {
            'inputs.json': {
                'canonical': canonical,
                'codes': {'run_id': CODES_RUN, 'outputs_sha256': codes_pin},
            },
            'report.json': frames.establishment_report,
        },
    )
    area_mix = data_dir / AREA_MIX_ROOT / AREA_MIX_RUN
    area_mix_pin = _bundle(
        area_mix,
        {'ita_county_assignments': frames.assignments, 'ita_area_mix': frames.area_mix},
        {'inputs.json': {'canonical': canonical}, 'report.json': frames.area_mix_report},
    )
    return Published(data_dir, establishment, area_mix, codes, establishment_pin,
                     area_mix_pin, codes_pin)
