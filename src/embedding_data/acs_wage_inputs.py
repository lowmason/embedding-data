'''Select the pinned Stage 8 mapping run and Stage 4 codes run that the wage build reads.

For each run, the selection hashes `outputs.json` against the detached pin before it reads any
other file of that run, and then hashes the run's whole inventory. It does not re-derive the
Stage 8 tables: Stage 8's own `verify` does that, once, as a read-only preflight. The mapping
run must record the same codes selection that the caller gives. The cited core DDI must match
its raw manifest entry and must give the wage rules' codes their delivered labels. The
selection is taken twice, and any difference between the two is refused.
'''

import json
import math
import platform
import re
import sys
from copy import deepcopy
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path

from embedding_data import ipums_ddi, manifest, paths, target_io
from embedding_data.acs_wage_rules import DDI_LABELS

RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
MAPPING_ROOT = 'derived/acs/mapping'
CODES_ROOT = 'derived/codes'
CORE_TABLE = 'acs_core_canonical.parquet'
# Stage 8's eight tables and Stage 4's twelve tables, each with `inputs.json` and `report.json`.
MAPPING_FILES = frozenset({
    'acs_code_lookup.parquet',
    'acs_area_lookup.parquet',
    'puma_county_factors.parquet',
    'puma_msa_factors.parquet',
    'puma_msa_coverage.parquet',
    'acs_core_canonical.parquet',
    'acs_five_year_canonical.parquet',
    'acs_vintage_canonical.parquet',
    'inputs.json',
    'report.json',
})
CODES_FILES = frozenset({
    'naics_nodes.parquet',
    'naics_edges.parquet',
    'soc_nodes.parquet',
    'soc_edges.parquet',
    'naics_native_nodes.parquet',
    'naics_concordance.parquet',
    'filing_rules.parquet',
    'code_paths.parquet',
    'filing_rule_labels.parquet',
    'filing_rule_membership.parquet',
    'ita_naics_lookup.parquet',
    'ita_300a_canonical.parquet',
    'inputs.json',
    'report.json',
})
SOFTWARE_ROOT = paths.PROJECT_ROOT
# The command group's modules and every module that importing them loads. Later modules of the
# command group add their own files.
SOFTWARE_FILES = (
    'src/embedding_data/__init__.py',
    'src/embedding_data/acs_wage_bundle.py',
    'src/embedding_data/acs_wage_checks.py',
    'src/embedding_data/acs_wage_inputs.py',
    'src/embedding_data/acs_wage_rules.py',
    'src/embedding_data/geography_parsers.py',
    'src/embedding_data/geography_references.py',
    'src/embedding_data/ipums_ddi.py',
    'src/embedding_data/ita_catalog.py',
    'src/embedding_data/ita_references.py',
    'src/embedding_data/ita_summary.py',
    'src/embedding_data/manifest.py',
    'src/embedding_data/osha_benchmark_download.py',
    'src/embedding_data/osha_encoding.py',
    'src/embedding_data/paths.py',
    'src/embedding_data/target_io.py',
    'pyproject.toml',
    'uv.lock',
)


@dataclass(frozen=True)
class SelectedWageInputs:
    data_dir: Path
    mapping_run: str
    mapping_outputs_sha256: str
    codes_run: str
    codes_outputs_sha256: str
    core: Path
    naics_nodes: Path
    naics_edges: Path
    ddi: Path
    labels: dict
    provenance: dict

    def verify(self) -> None:
        '''Select again with the same runs and pins, and refuse any difference.'''
        try:
            current = select_wage_inputs(
                self.data_dir,
                self.mapping_run,
                mapping_outputs_sha256=self.mapping_outputs_sha256,
                codes_run=self.codes_run,
                codes_outputs_sha256=self.codes_outputs_sha256,
            )
        except (ValueError, OSError) as error:
            raise ValueError('selected inputs changed') from error
        if current != self:
            raise ValueError('selected inputs changed')


def _unique_object(pairs: list) -> dict:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('duplicate JSON key')
    return dict(pairs)


def _finite(text: str) -> float:
    # `1e999` is not a JSON constant, but it parses to infinity.
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('non-finite JSON number')
    return value


def _reject_constant(name: str) -> None:
    raise ValueError('non-finite JSON number')


def read_json(file: Path) -> dict:
    '''Read a JSON object, refusing another root, a duplicate key and a non-finite number.'''
    value = json.loads(
        file.read_text(encoding='utf-8'),
        object_pairs_hook=_unique_object,
        parse_float=_finite,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f'{file.name}: JSON root is not an object')
    return value


def confirm_labels(ddi: dict) -> dict:
    '''Return a copy of `DDI_LABELS` when the delivered DDI gives each listed code its label.'''
    delivered = {
        variable['name']: {category['value']: category['label']
                           for category in variable['categories']}
        for variable in ddi['variables']
    }
    if any(
        delivered.get(name, {}).get(code) != label
        for name, labels in DDI_LABELS.items()
        for code, label in labels.items()
    ):
        raise ValueError('delivered DDI labels differ')
    return deepcopy(DDI_LABELS)


def freeze_software() -> dict:
    '''The executing files, Python identity, installed distributions and `uv.lock` hash.'''
    return {
        'files': {name: target_io.file_record(SOFTWARE_ROOT / name) for name in SOFTWARE_FILES},
        'python': platform.python_version(),
        'python_full': sys.version,
        'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((dist.metadata['Name'], dist.version)
                                    for dist in distributions())),
        'uv_lock_sha256': manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock'),
    }


def _field(recorded: dict, *keys: str) -> object:
    '''The value at `keys` in the mapping run's inputs, refusing a missing level.'''
    value = recorded
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ValueError('mapping inputs lack a selected field')
        value = value[key]
    return value


def _pinned_run(data_dir: Path, root: str, run_id: str, pin: str,
                names: frozenset[str]) -> tuple[Path, dict]:
    '''Check a run's detached pin before any other read, then its whole inventory.'''
    directory = target_io.relative_file(data_dir, f'{root}/{run_id}')
    outputs_file = target_io.relative_file(directory, 'outputs.json')
    if manifest.sha256_file(outputs_file) != pin:
        raise ValueError('detached inventory checksum differs')
    outputs = read_json(outputs_file)
    target_io.verify_inventory(directory, outputs, names)
    return directory, {'run_id': run_id, 'outputs_sha256': pin, 'outputs': outputs}


def _snapshot(data_dir: Path, mapping_run: str, mapping_outputs_sha256: str, codes_run: str,
              codes_outputs_sha256: str) -> SelectedWageInputs:
    if not all(isinstance(run, str) and RUN_ID.fullmatch(run)
               for run in (mapping_run, codes_run)):
        raise ValueError('unsafe selected run ID')
    if not all(isinstance(pin, str) and PIN.fullmatch(pin)
               for pin in (mapping_outputs_sha256, codes_outputs_sha256)):
        raise ValueError('invalid detached checksum')
    mapping, mapping_record = _pinned_run(data_dir, MAPPING_ROOT, mapping_run,
                                          mapping_outputs_sha256, MAPPING_FILES)
    recorded = read_json(mapping / 'inputs.json')
    request = ('selected_upstreams', 'request')
    if (_field(recorded, *request, 'codes_run'),
            _field(recorded, *request, 'codes_outputs_sha256')) != (codes_run,
                                                                    codes_outputs_sha256):
        raise ValueError('codes selection differs from the mapping run')
    codes, codes_record = _pinned_run(data_dir, CODES_ROOT, codes_run, codes_outputs_sha256,
                                      CODES_FILES)
    citations = _field(recorded, 'sources', 'acs/core', 'raw_citations')
    cited = [citation for citation in (citations if isinstance(citations, list) else [])
             if isinstance(citation, dict) and str(citation.get('path')).endswith('.xml')]
    if len(cited) != 1:
        raise ValueError('mapping run does not cite one core DDI')
    try:
        [entry] = target_io.verify_raw(data_dir, cited)
    except KeyError:
        raise ValueError('cited raw file is not recorded') from None
    ddi = target_io.relative_file(data_dir / 'raw', entry['path'])
    labels = confirm_labels(ipums_ddi.read_ddi(ddi))
    return SelectedWageInputs(
        data_dir=data_dir,
        mapping_run=mapping_run,
        mapping_outputs_sha256=mapping_outputs_sha256,
        codes_run=codes_run,
        codes_outputs_sha256=codes_outputs_sha256,
        core=target_io.relative_file(mapping, CORE_TABLE),
        naics_nodes=target_io.relative_file(codes, 'naics_nodes.parquet'),
        naics_edges=target_io.relative_file(codes, 'naics_edges.parquet'),
        ddi=ddi,
        labels=labels,
        provenance={'mapping': mapping_record, 'codes': codes_record, 'ddi': entry},
    )


def select_wage_inputs(data_dir: Path, mapping_run: str, *, mapping_outputs_sha256: str,
                       codes_run: str, codes_outputs_sha256: str) -> SelectedWageInputs:
    '''Authenticate the pinned runs and the delivered DDI twice, refusing any difference.'''
    arguments = (Path(data_dir), mapping_run, mapping_outputs_sha256, codes_run,
                 codes_outputs_sha256)
    first = _snapshot(*arguments)
    second = _snapshot(*arguments)
    if first != second:
        raise ValueError('selected inputs changed during validation')
    return second
