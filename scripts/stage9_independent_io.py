'''Detached authentication and immutable Stage9 before-state, without science imports.'''

import hashlib
import importlib.util
import json
import platform
import re
import sys
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST_FIELDS = (
    'codes_run',
    'codes_outputs_sha256',
    'geography_run',
    'geography_outputs_sha256',
    'ipums_run',
    'ipums_outputs_sha256',
    'ipums_references_receipt_sha256',
)
TABLES = (
    'targets_observed',
    'targets_canonical',
    'targets_allocated_area_mix',
    'target_units',
    'target_support',
    'replicate_estimates',
    'eligibility_diagnostics',
    'allocation_residuals',
)
MEMBERS = {name + '.parquet' for name in TABLES} | {'inputs.json', 'report.json', 'outputs.json'}


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stage8 = load_sibling('reconcile_stage8')
safe, relative, digest, record = stage8.safe, stage8.relative, stage8.digest, stage8.record
read, require, check_record = stage8.read, stage8.require, stage8.check_record


def identifier(value):
    require(
        isinstance(value, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', value),
        'unsafe run ID',
    )
    return value


def target_directory(data_dir, run_id):
    return relative(data_dir, 'derived/acs/targets/' + identifier(run_id))


def software():
    names = sorted(
        {
            p.relative_to(ROOT).as_posix()
            for directory in ('src', 'scripts', 'tests', 'features')
            for p in (ROOT / directory).rglob('*.py')
        }
        | {'uv.lock', 'pyproject.toml'}
    )
    return {
        'files': {name: record(relative(ROOT, name)) for name in names},
        'python': sys.version,
        'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((d.metadata['Name'], d.version) for d in distributions())),
    }


def write_exclusive(file, value):
    safe(file)
    with file.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def selected_mapping(data_dir, mapping_run, pin, request):
    require(
        isinstance(request, dict)
        and set(request) == set(REQUEST_FIELDS)
        and all(isinstance(v, str) for v in request.values()),
        'explicit request must contain exactly seven string fields',
    )
    for name in REQUEST_FIELDS:
        if name.endswith('_run'):
            identifier(request[name])
        else:
            require(re.fullmatch('[0-9a-f]{64}', request[name]), 'invalid request pin')
    directory = relative(data_dir, 'derived/acs/mapping/' + identifier(mapping_run))
    inputs = stage8.authenticate_bundle(directory, pin)
    require(
        inputs['selected_upstreams']['request'] == request,
        'mapping differs from explicit seven-field request',
    )
    upstreams, compatibility = stage8.upstreams(data_dir, inputs)
    files = stage8.reference_files(data_dir, inputs['references'])
    records = [
        stage8.loads(line) for line in (data_dir / 'raw/manifest.jsonl').read_bytes().splitlines()
    ]
    manifest = {r['path']: r for r in records}
    require(len(manifest) == len(records), 'duplicate manifest path')

    def authenticate_citations(value):
        if isinstance(value, list):
            for member in value:
                authenticate_citations(member)
        elif isinstance(value, dict):
            if {'path', 'sha256', 'size'} <= set(value):
                name = value['path']
                root = data_dir if name.startswith('derived/') else data_dir / 'raw'
                check_record(
                    relative(root, name), value, 'upstream reference/source citation differs'
                )
                if root == data_dir / 'raw':
                    require(
                        name in manifest
                        and all(manifest[name].get(k) == value[k] for k in ('sha256', 'size')),
                        'citation differs from raw manifest',
                    )
            for member in value.values():
                authenticate_citations(member)

    authenticate_citations([inputs, upstreams])
    for kind, file in files.items():
        original = inputs['references']['receipt']['originals'][kind]
        check_record(file, original, 'mapping reference original differs')
    for source in inputs['sources'].values():
        check_record(
            relative(data_dir, source['parquet']),
            source['parquet_record'],
            'selected original changed',
        )
        for citation in source['raw_citations']:
            file = relative(data_dir / 'raw', citation['path'])
            check_record(file, citation, 'selected raw citation differs')
    return directory, inputs, upstreams, files, compatibility


def inventory(data_dir, excluded):
    result = {}
    for directory in ('raw', 'derived'):
        for file in safe(data_dir / directory).rglob('*'):
            safe(file)
            if file.is_file() and not any(file == p or file.is_relative_to(p) for p in excluded):
                name = file.relative_to(data_dir).as_posix()
                if name != 'raw/manifest.jsonl':
                    result[name] = record(file)
    return dict(sorted(result.items()))


def freeze(
    data_dir: Path,
    control_dir: Path,
    *,
    mapping_run: str,
    mapping_outputs_sha256: str,
    request: dict[str, str],
    first_run: str,
    replay_run: str,
) -> dict:
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    first, replay = (target_directory(data_dir, run) for run in (first_run, replay_run))
    require(first != replay, 'first and replay IDs must differ')
    require(not data_dir.is_relative_to(control_dir), 'control path contains data root')
    for path in (
        control_dir,
        control_dir.with_name(control_dir.name + '.part'),
        first,
        replay,
        first.with_suffix('.part'),
        replay.with_suffix('.part'),
    ):
        safe(path)
        require(not path.exists(), 'occupied control/final/partial path')
    require(
        not any(control_dir == p or control_dir.is_relative_to(p) for p in (first, replay)),
        'control path overlaps target',
    )
    _, inputs, _, _, compatibility = selected_mapping(
        data_dir, mapping_run, mapping_outputs_sha256, request
    )
    prefix = safe(data_dir / 'raw/manifest.jsonl').read_bytes()
    require(not prefix or prefix.endswith(b'\n'), 'manifest prefix lacks record boundary')
    # Authenticate every existing manifested original independently of selected paths.
    manifest = [stage8.loads(line) for line in prefix.splitlines()]
    require(len({r['path'] for r in manifest}) == len(manifest), 'duplicate manifest path')
    for citation in manifest:
        check_record(
            relative(data_dir / 'raw', citation['path']),
            citation,
            'manifested immutable original differs',
        )
    value = {
        'version': 'stage9-independent-v1',
        'data_dir': str(data_dir),
        'control_dir': str(control_dir),
        'mapping_run': mapping_run,
        'mapping_outputs_sha256': mapping_outputs_sha256,
        'request': request,
        'first_run': first_run,
        'replay_run': replay_run,
        'excluded_paths': [str(control_dir), str(first), str(replay)],
        'manifest_prefix': {'size': len(prefix), 'sha256': hashlib.sha256(prefix).hexdigest()},
        'files': inventory(data_dir, (control_dir, first, replay)),
        'software': software(),
        'mapping_inputs': inputs,
        'software_compatibility': compatibility,
    }
    control_dir.mkdir(parents=True)
    with (control_dir / 'manifest-prefix.jsonl').open('xb') as stream:
        stream.write(prefix)
    write_exclusive(control_dir / 'freeze.json', value)
    response = {
        'freeze_sha256': digest(control_dir / 'freeze.json'),
        'protected_file_count': len(value['files']),
        'manifest_prefix': value['manifest_prefix'],
    }
    require(
        value['files'] == inventory(data_dir, (control_dir, first, replay))
        and value['software'] == software()
        and (data_dir / 'raw/manifest.jsonl').read_bytes() == prefix,
        'input/software bytes changed during freeze',
    )
    write_exclusive(control_dir / 'freeze-response.json', response)
    return response


def authenticated_freeze(data_dir, control_dir, pin):
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    require(
        isinstance(pin, str)
        and re.fullmatch('[0-9a-f]{64}', pin)
        and digest(control_dir / 'freeze.json') == pin,
        'external freeze pin differs',
    )
    value = read(control_dir / 'freeze.json')
    require(value['version'] == 'stage9-independent-v1', 'unsupported independent freeze version')
    require(
        value['data_dir'] == str(data_dir) and value['control_dir'] == str(control_dir),
        'freeze roots differ',
    )
    expected = [
        str(control_dir),
        *(str(target_directory(data_dir, value[k])) for k in ('first_run', 'replay_run')),
    ]
    require(value['excluded_paths'] == expected, 'freeze exact exclusions differ')
    return value


def preservation(data_dir: Path, control_dir: Path, *, expected_freeze_sha256: str) -> dict:
    frozen = authenticated_freeze(data_dir, control_dir, expected_freeze_sha256)
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    require(frozen['software'] == software(), 'executing independent/source software changed')
    expected_response = {
        'freeze_sha256': expected_freeze_sha256,
        'protected_file_count': len(frozen['files']),
        'manifest_prefix': frozen['manifest_prefix'],
    }
    expected_bytes = (
        json.dumps(expected_response, sort_keys=True, indent=2, allow_nan=False) + '\n'
    ).encode()
    require(
        (control_dir / 'freeze-response.json').read_bytes() == expected_bytes,
        'freeze response control bytes differ',
    )
    require(
        not control_dir.with_name(control_dir.name + '.part').exists(), 'control partial remains'
    )
    prefix = (control_dir / 'manifest-prefix.jsonl').read_bytes()
    require(
        {'size': len(prefix), 'sha256': hashlib.sha256(prefix).hexdigest()}
        == frozen['manifest_prefix'],
        'saved manifest prefix differs',
    )
    current_manifest = (data_dir / 'raw/manifest.jsonl').read_bytes()
    require(current_manifest.startswith(prefix), 'raw manifest prefix changed or truncated')
    require(not current_manifest or current_manifest.endswith(b'\n'), 'suffix record truncated')
    suffix = [stage8.loads(line) for line in current_manifest[len(prefix) :].splitlines()]
    all_records = [stage8.loads(line) for line in current_manifest.splitlines()]
    require(len({r['path'] for r in all_records}) == len(all_records), 'duplicate manifest path')
    excluded = tuple(Path(p) for p in frozen['excluded_paths'])
    current = inventory(data_dir, excluded)
    for name, expected in frozen['files'].items():
        require(current.get(name) == expected, 'protected immutable file changed: ' + name)
    appended = {'raw/' + row['path']: row for row in suffix}
    additions = set(current) - set(frozen['files'])
    require(additions == set(appended), 'unaccounted new immutable files')
    for name, citation in appended.items():
        check_record(relative(data_dir, name), citation, 'manifest suffix immutable bytes differ')
    stage9_appends = [
        r
        for r in suffix
        if 'acs-target' in str(r.get('collection', '')) or '/targets/' in r['path']
    ]
    require(not stage9_appends, 'Stage9 must append zero raw records')
    bundles = {}
    for name in ('first_run', 'replay_run'):
        final = target_directory(data_dir, frozen[name])
        require(not final.with_suffix('.part').exists(), 'execution partial remains')
        require(
            not list(final.parent.glob(final.name + '-scratch-*')), 'execution scratch remains'
        )
        if final.exists():
            require(
                {p.name for p in final.iterdir()} == MEMBERS,
                'new final does not contain exactly eleven declared files',
            )
            for file in final.iterdir():
                require(safe(file).is_file(), 'nonregular final member')
        bundles[frozen[name]] = 'complete' if final.exists() else 'absent'
    return {
        'failure_count': 0,
        'protected_files_equal': True,
        'manifest_prefix_equal': True,
        'manifest_appends_accounted': len(suffix),
        'stage9_raw_records_appended': 0,
        'bundles': bundles,
    }
