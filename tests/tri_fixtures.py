'''Shared fixtures for the TRI parent-links tests: a real Stage 4 codes bundle.'''

from pathlib import Path

import ita_establishment_fixtures as establishment
import ita_fixtures

from embedding_data import code_build, ita_summary, manifest

def seed_codes_bundle(data_dir: Path, directory: Path) -> tuple[str, str]:
    '''Build a real Stage 4 bundle from the committed fixtures and return its run and pin.

    The raw ITA releases, the Stage 2 summary and the exact public Stage 4 originals are
    seeded first, because `code_build.build` reads all three. `directory` receives the
    original files before they are imported into `data_dir`.
    '''
    for year, rows in establishment.golden_releases().items():
        ita_fixtures.write_release(data_dir, year, ita_fixtures.year_file(year, rows))
    ita_summary.build_summary_table(data_dir)
    establishment.import_stage4_originals(data_dir, directory)
    bundle = code_build.build(data_dir, establishment.CODES_RUN)
    return establishment.CODES_RUN, manifest.sha256_file(bundle / 'outputs.json')
