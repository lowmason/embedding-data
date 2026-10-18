'''Synthetic complete Stage 4/5/7 bundles with independent detached pins.'''
from dataclasses import dataclass
from pathlib import Path

from code_fixtures import seed_code_tree
from geography_fixtures import seed_geography_tree
from target_fixtures import forbid_external_access
from test_ipums_verification_run import complete_inputs

from embedding_data import code_build, geography_build, ipums_verification_run, manifest

@dataclass(frozen=True)
class FixtureInputs:
    data_dir: Path
    request: object
    sources: dict
    upstream_pins: dict


def seed_selected_inputs(tmp_path: Path, monkeypatch) -> FixtureInputs:
    from embedding_data.acs_mapping_inputs import SelectionRequest

    root, selection = complete_inputs.__wrapped__(tmp_path, monkeypatch)
    codes = code_build.build(root, 'fixture_codes', registry=seed_code_tree(root))
    geography = geography_build.build(root, 'fixture_geography',
                                      registry=seed_geography_tree(root))
    forbid_external_access(monkeypatch)
    run = ipums_verification_run.measure(root, 'fixture_ipums', 'references', selection)
    pins = {name: manifest.sha256_file(directory / 'outputs.json')
            for name, directory in [('codes', codes), ('geography', geography), ('ipums', run)]}
    receipt = root / 'raw/references/ipums-verification/references/receipt.json'
    request = SelectionRequest('fixture_codes', pins['codes'], 'fixture_geography',
                               pins['geography'], 'fixture_ipums', pins['ipums'],
                               manifest.sha256_file(receipt))
    import json
    sources = json.loads((run / 'inputs.json').read_text())['deliveries']
    return FixtureInputs(root, request, sources, pins)
