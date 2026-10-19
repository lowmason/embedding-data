'''Bind Stage 9 to explicit authenticated Stage 8 and upstream identities.'''

import platform
import sys
from dataclasses import asdict, dataclass
from importlib.metadata import distributions
from pathlib import Path

from embedding_data import acs_mapping_bundle, acs_mapping_inputs, manifest, target_io
from embedding_data.acs_mapping_contract import (
    AREA_RULE_VERSION,
    CODE_RULE_VERSION,
    FORMAT_VERSION,
    SelectionRequest,
)
from embedding_data.acs_mapping_inputs import SelectedInputs

SOFTWARE_ROOT = Path(__file__).resolve().parents[2]
SOFTWARE_FILES = tuple(dict.fromkeys((*acs_mapping_inputs.SOFTWARE_FILES,
    'src/embedding_data/target_contract.py',
    'src/embedding_data/acs_target_contract.py',
    'src/embedding_data/acs_target_inputs.py',
    'src/embedding_data/acs_target_rules.py',
    'src/embedding_data/acs_target_units.py',
        'src/embedding_data/acs_target_weights.py',
        'src/embedding_data/acs_target_membership.py',
        'src/embedding_data/acs_target_estimation.py',
        'src/embedding_data/acs_target_projection.py', 'pyproject.toml', 'uv.lock')))
MAPPING_TABLES = (
    'acs_code_lookup', 'acs_area_lookup', 'puma_county_factors', 'puma_msa_factors',
    'puma_msa_coverage', 'acs_core_canonical', 'acs_five_year_canonical',
    'acs_vintage_canonical',
)


@dataclass(frozen=True)
class SelectedTargets:
    data_dir: Path
    mapping_run: str
    mapping_outputs_sha256: str
    request: SelectionRequest
    upstream: SelectedInputs
    mapping_directory: Path
    tables: dict[str, Path]
    provenance: dict
    software: dict

    def verify(self) -> None:
        selected = select_targets(
            self.data_dir, self.mapping_run,
            expected_mapping_outputs_sha256=self.mapping_outputs_sha256,
            request=self.request)
        if selected != self:
            raise ValueError('selected targets, provenance or executing software changed')


def freeze_target_software() -> dict:
    '''Freeze literal executing members, full Python identity and all distributions.'''
    return {
        'files': {name: target_io.file_record(SOFTWARE_ROOT / name) for name in SOFTWARE_FILES},
        'python': platform.python_version(), 'python_full': sys.version,
        'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((dist.metadata['Name'], dist.version)
                                    for dist in distributions())),
        'uv_lock_sha256': manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock'),
    }


def _mapping_snapshot(data_dir, mapping_run, pin, request):
    upstream = acs_mapping_inputs.select_inputs(data_dir, request)
    upstream.verify()
    directory = acs_mapping_bundle.run_directory(data_dir, mapping_run)
    verified = acs_mapping_bundle.verify_bundle(
        directory, data_dir, expected_outputs_sha256=pin)
    # The detached pin and public verifier authenticate every mapping byte first.
    recorded = acs_mapping_inputs._read_json(directory / 'inputs.json')
    if recorded['selected_upstreams']['request'] != asdict(request):
        raise ValueError('mapping upstream selection differs from explicit request')
    if recorded['selected_upstreams']['provenance'] != upstream.provenance:
        raise ValueError('mapping upstream provenance differs')
    sources = {profile: {**asdict(source),
                        'parquet': source.parquet.relative_to(data_dir).as_posix()}
               for profile, source in upstream.sources.items()}
    if recorded['sources'] != sources:
        raise ValueError('mapping source identities differ from selected upstreams')
    rules = {'classification': CODE_RULE_VERSION, 'area': AREA_RULE_VERSION,
             'transform': FORMAT_VERSION}
    if recorded['rules'] != rules or recorded['frames'] != acs_mapping_bundle.FRAMES:
        raise ValueError('mapping rules or frames differ from frozen Stage 8 constants')
    tables = {name: directory / (name + '.parquet') for name in MAPPING_TABLES}
    provenance = {
        'selected_upstreams': {'request': asdict(request), 'provenance': upstream.provenance},
        'mapping': {**verified, 'software': recorded['software'],
                    'inputs': target_io.file_record(directory / 'inputs.json'),
                    'tables': {name: target_io.file_record(file)
                               for name, file in tables.items()},
                    'references': recorded['references'], 'rules': rules,
                    'frames': recorded['frames']},
        'sources': sources,
    }
    return upstream, directory, tables, provenance


def select_targets(data_dir: Path, mapping_run: str, *,
                   expected_mapping_outputs_sha256: str,
                   request: SelectionRequest) -> SelectedTargets:
    '''Authenticate the explicit selection twice and reject concurrent drift.'''
    data_dir = Path(data_dir)
    software = freeze_target_software()
    snapshot = _mapping_snapshot(data_dir, mapping_run, expected_mapping_outputs_sha256, request)
    rechecked = _mapping_snapshot(data_dir, mapping_run, expected_mapping_outputs_sha256, request)
    if rechecked != snapshot:
        raise ValueError('selected mapping inputs changed during validation')
    if freeze_target_software() != software:
        raise ValueError('executing target software or dependency identity changed')
    upstream, directory, tables, provenance = snapshot
    return SelectedTargets(data_dir, mapping_run, expected_mapping_outputs_sha256,
                           request, upstream, directory, tables, provenance, software)
