'''The five Stage 11 CPS job-flow commands: output, failure line, offline use and exit codes.'''

import io
import json
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import httpx
import polars as pl
import pytest
from cps_flow_fixtures import (
    job_flow_rows,
    no_live_clients,  # noqa: F401
    offline_guards,
    reference_originals,
    seed_upstreams,
)
from typer.main import get_command
from vendor_link_fixtures import module_file, subprocess_modules

from embedding_data import (
    cps_flow_bundle,
    cps_flow_inputs,
    cps_flow_references,
    cps_job_flows,
    manifest,
)
from embedding_data.cps_flow_bundle import SOFTWARE_FILES, run_directory
from embedding_data.cps_job_flows import app

COMMANDS = ('acquire-references', 'import-reference', 'build', 'verify', 'compare-runs')
RAW = 'raw/references/cps-job-flows'
BUNDLES = 'derived/cps/job-flows'
SECRET = 'CPSIDV 8822000000000001 at 1 Main St'
PIN = '2' * 64
# Each build option, with the `InputRequest` field it fills.
OPTIONS = (
    ('--stage7-run', 'stage7_run'),
    ('--stage7-outputs-sha256', 'stage7_outputs_sha256'),
    ('--stage7-receipt', 'stage7_receipt'),
    ('--stage7-receipt-sha256', 'stage7_receipt_sha256'),
    ('--stage8-receipt', 'stage8_receipt'),
    ('--stage8-receipt-sha256', 'stage8_receipt_sha256'),
    ('--stage8-mapping-run', 'stage8_mapping_run'),
    ('--stage8-mapping-outputs-sha256', 'stage8_mapping_outputs_sha256'),
    ('--codes-run', 'codes_run'),
    ('--codes-outputs-sha256', 'codes_outputs_sha256'),
    ('--cps-receipt', 'cps_receipt'),
    ('--cps-receipt-sha256', 'cps_receipt_sha256'),
)
REAL_MAKE_CLIENT = cps_flow_references.make_client


def invoke(runner, command, data_dir, *arguments):
    return runner.invoke(app, [command, *arguments, '--data-dir', str(data_dir)])


def one_sorted_line(result):
    '''The parsed single JSON line of stdout, which must be printed with sorted keys.'''
    assert result.stdout.count('\n') == 1
    value = json.loads(result.stdout)
    assert result.stdout == json.dumps(value, sort_keys=True) + '\n'
    return value


def build_arguments(run_id, request):
    return [run_id, *(argument for option, field in OPTIONS
                      for argument in (option, getattr(request, field)))]


def bundle_path(run_id):
    return f'{BUNDLES}/{run_id}'


def failure(command, reason, run_id='run_1', path=None):
    path = bundle_path(run_id) if path is None else path
    return f'CPS job flows {command} failed: {reason}; run {run_id}; path {path}\n'


def reference_failure(command, reason):
    return f'CPS job flows {command} failed: {reason}; run -; path {RAW}\n'


def no_publication(data_dir, run_id):
    root = data_dir / BUNDLES
    return not (root / run_id).exists() and not (root / (run_id + '.part')).exists()


def seed(root, changes=None):
    rows, people = job_flow_rows(changes)
    return seed_upstreams(root, monthly=rows, asec=people)


@pytest.fixture
def seeded(tmp_path):
    return seed(tmp_path)


def serve(monkeypatch, directory, overrides=None):
    '''Patch `make_client` with a partial that injects a mock transport serving the originals.'''
    served = {cps_flow_references.REGISTRY[kind].url: file.read_bytes()
              for kind, file in reference_originals(directory).items()}
    calls = []

    def handler(request):
        calls.append(request)
        url = str(request.url)
        if overrides and url in overrides:
            return overrides[url](request)
        body = served[url]
        return httpx.Response(200, headers={'content-length': str(len(body))},
                              stream=httpx.ByteStream(body))

    monkeypatch.setattr(cps_flow_references, 'make_client', partial(
        REAL_MAKE_CLIENT, transport=httpx.MockTransport(handler)))
    return calls


def test_the_five_commands_are_exactly_these(cli_runner):
    assert [command.name for command in app.registered_commands] == list(COMMANDS)
    assert sorted(get_command(app).commands) == sorted(COMMANDS)
    result = cli_runner.invoke(app, ['--help'])
    assert result.exit_code == 0, result.output
    for command in COMMANDS:
        assert command in result.stdout


def test_acquire_and_import_print_one_sorted_json_line(cli_runner, data_directory, monkeypatch,
                                                       tmp_path):
    calls = serve(monkeypatch, tmp_path / 'served')
    acquired = invoke(cli_runner, 'acquire-references', data_directory, 'acquired')
    assert acquired.exit_code == 0, acquired.output
    assert acquired.stderr == ''
    assert one_sorted_line(acquired) == f'{RAW}/acquired'
    assert [str(call.url) for call in calls] == [
        item.url for item in cps_flow_references.REGISTRY.values()]

    originals = reference_originals(tmp_path / 'originals')
    kinds = list(originals)
    for kind in kinds[:-1]:
        staged = invoke(cli_runner, 'import-reference', data_directory, 'imported', kind,
                        str(originals[kind]))
        assert staged.exit_code == 0, staged.output
        assert staged.stderr == ''
        assert one_sorted_line(staged) == f'{RAW}/imported.part'
    published = invoke(cli_runner, 'import-reference', data_directory, 'imported', kinds[-1],
                       str(originals[kinds[-1]]))
    assert published.exit_code == 0, published.output
    assert published.stderr == ''
    assert one_sorted_line(published) == f'{RAW}/imported'
    receipt = cps_flow_references.check_references(data_directory, 'imported')
    assert receipt['reference_id'] == 'imported'
    assert manifest.sha256_file(data_directory / RAW / 'imported' / 'receipt.json')


def test_build_verify_compare_round_trip(cli_runner, seeded):
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('r1', seeded.request))
    assert built.exit_code == 0, built.output
    assert built.stderr == ''
    published = one_sorted_line(built)
    pin = manifest.sha256_file(seeded.data_dir / BUNDLES / 'r1' / 'outputs.json')
    assert published['run_id'] == 'r1'
    assert published['directory'] == bundle_path('r1')
    assert published['outputs_sha256'] == pin
    assert str(seeded.data_dir) not in built.output

    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'r1', '--outputs-sha256', pin)
    assert verified.exit_code == 0, verified.output
    assert verified.stderr == ''
    report = one_sorted_line(verified)
    assert report['run_id'] == 'r1'
    assert report['outputs_sha256'] == pin
    assert set(report['rows']) == set(cps_flow_bundle.TABLES)

    replay = invoke(cli_runner, 'build', seeded.data_dir,
                    *build_arguments('r2', seeded.request))
    assert replay.exit_code == 0, replay.output
    compared = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'r1', 'r2')
    assert compared.exit_code == 0, compared.output
    assert compared.stderr == ''
    result = one_sorted_line(compared)
    assert result['equal'] is True
    assert result['report_equal'] is True
    assert result['trust_established'] is False
    assert sorted(result['tables']) == sorted(cps_flow_bundle.TABLES)
    assert str(seeded.data_dir) not in compared.output


def test_failure_prints_only_the_fixed_line_and_exits_2(cli_runner, seeded):
    request = seeded.request
    arguments = build_arguments('r1', request)
    arguments[arguments.index('--stage7-outputs-sha256') + 1] = '1' * 64
    result = invoke(cli_runner, 'build', seeded.data_dir, *arguments)
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.stderr == (
        'CPS job flows build failed: validation; run r1; path derived/cps/job-flows/r1\n')
    assert result.stdout == ''
    assert no_publication(seeded.data_dir, 'r1')


def test_unequal_comparison_exits_1(cli_runner, seeded, tmp_path_factory):
    # The second run reads one changed link weight, so its tables differ and both still verify.
    other = seed(tmp_path_factory.mktemp('changed'), {'E1': {'LNKFW1MWT': '1500.1235'}})
    for data_dir, request, run_id in ((seeded.data_dir, seeded.request, 'r1'),
                                      (other.data_dir, other.request, 'r2')):
        built = invoke(cli_runner, 'build', data_dir, *build_arguments(run_id, request))
        assert built.exit_code == 0, built.output
    shutil.copytree(run_directory(other.data_dir, 'r2'), run_directory(seeded.data_dir, 'r2'))
    result = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'r1', 'r2')
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stderr == ''
    compared = one_sorted_line(result)
    assert compared['equal'] is False
    assert compared['trust_established'] is False
    assert any(table['values_equal'] is False for table in compared['tables'].values())


def test_no_offline_command_reads_env_or_builds_a_client(cli_runner, seeded, tmp_path,
                                                         monkeypatch):
    originals = reference_originals(tmp_path / 'originals')
    imports = tmp_path / 'imports'
    counts = offline_guards(monkeypatch)
    for kind, file in originals.items():
        imported = invoke(cli_runner, 'import-reference', imports, 'refs', kind, str(file))
        assert imported.exit_code == 0, imported.output
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('r1', seeded.request))
    assert built.exit_code == 0, built.output
    pin = one_sorted_line(built)['outputs_sha256']
    replay = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('r2', seeded.request))
    assert replay.exit_code == 0, replay.output
    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'r1', '--outputs-sha256', pin)
    assert verified.exit_code == 0, verified.output
    compared = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'r1', 'r2')
    assert compared.exit_code == 0, compared.output
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}


def test_import_closure_is_the_recorded_one():
    # OD5: the owner accepted that the shared Stage 7 and 8 modules load both packages.
    modules = subprocess_modules('embedding_data.cps_job_flows', prefix=None)
    assert ('dotenv' in modules, 'ipumspy' in modules) == (True, True)


def test_software_files_equal_the_measured_import_closure():
    closure = {module_file(module)
               for module in subprocess_modules('embedding_data.cps_job_flows')}
    assert closure | {'pyproject.toml', 'uv.lock'} == set(SOFTWARE_FILES)


# Additional coverage beyond the plan tests.

def test_module_constants_and_paths():
    assert cps_job_flows.NO_RUN == '-'
    assert cps_job_flows.RAW == RAW == cps_flow_references.SNAPSHOT_ROOT
    assert cps_job_flows.BUNDLES == BUNDLES
    assert run_directory(Path('root'), 'run_1') == Path('root') / bundle_path('run_1')
    assert cps_job_flows._run_path('run_1') == bundle_path('run_1')
    assert cps_job_flows._run_path('../escape') == f'{BUNDLES}/../escape'


def test_the_command_module_is_a_file_of_the_frozen_software():
    assert 'src/embedding_data/cps_job_flows.py' in SOFTWARE_FILES
    assert list(SOFTWARE_FILES) == sorted(SOFTWARE_FILES)


def test_a_refused_kind_is_a_validation_failure_that_keeps_the_others_staged(
        cli_runner, data_directory, monkeypatch, tmp_path):
    refused = cps_flow_references.REGISTRY['bls_cps_industry_2022'].url
    serve(monkeypatch, tmp_path / 'served',
          {refused: lambda request: httpx.Response(403)})
    result = invoke(cli_runner, 'acquire-references', data_directory, 'refs')
    assert result.exit_code == 2
    assert result.stderr == reference_failure('acquire-references', 'validation')
    assert result.stdout == ''
    assert 'bls_cps_industry_2022' not in result.output
    assert (data_directory / RAW / 'refs.part' / 'staging-state.json').is_file()
    assert not (data_directory / RAW / 'refs').exists()


def test_acquire_failure_is_a_network_line_only_when_the_client_raises_http_errors(
        cli_runner, data_directory, monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError(SECRET)

    monkeypatch.setattr(cps_flow_references, 'acquire', fail)
    result = invoke(cli_runner, 'acquire-references', data_directory, 'refs')
    assert result.exit_code == 2
    assert result.stderr == reference_failure('acquire-references', 'network')
    assert result.stdout == ''


def test_import_reference_failure_prints_only_the_fixed_line(cli_runner, data_directory,
                                                             tmp_path):
    file = tmp_path / 'original.csv'
    file.write_bytes(b'synthetic import\n')
    result = invoke(cli_runner, 'import-reference', data_directory, 'refs', 'not_a_kind',
                    str(file))
    assert result.exit_code == 2
    assert result.stderr == reference_failure('import-reference', 'validation')
    assert result.stdout == ''
    assert not data_directory.exists()


@pytest.mark.parametrize('error,reason', [
    (ValueError(SECRET), 'validation'),
    # Both an OSError and a ValueError: validation is checked first.
    (io.UnsupportedOperation(SECRET), 'validation'),
    (FileExistsError(17, SECRET), 'filesystem'),
    (PermissionError(13, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (httpx.HTTPStatusError(SECRET, request=httpx.Request('GET', 'https://example.test'),
                           response=httpx.Response(500)), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
    (pl.exceptions.ComputeError(SECRET), 'unexpected'),
], ids=['value', 'unsupported', 'exists', 'permission', 'connect', 'status', 'runtime', 'key',
        'polars'])
def test_failure_reason_follows_the_exception_type(cli_runner, data_directory, monkeypatch,
                                                   tmp_path, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(cps_flow_references, 'acquire', fail)
    monkeypatch.setattr(cps_flow_references, 'import_reference', fail)
    for name in ('build', 'verify_bundle', 'compare_runs'):
        monkeypatch.setattr(cps_flow_bundle, name, fail)
    original = tmp_path / 'original.csv'
    expected = {
        'acquire-references': (['refs'], 'run -', RAW),
        'import-reference': (['refs', 'bls_cps_industry_2022', str(original)], 'run -', RAW),
        'build': (build_arguments('run_1', SimpleNamespace(**{
            field: 'x' for _, field in OPTIONS})), 'run run_1', bundle_path('run_1')),
        'verify': (['run_1', '--outputs-sha256', PIN], 'run run_1', bundle_path('run_1')),
        'compare-runs': (['run_1', 'run_2'], 'run run_1,run_2',
                         f'{bundle_path("run_1")},{bundle_path("run_2")}'),
    }
    for command, (arguments, run, path) in expected.items():
        result = invoke(cli_runner, command, data_directory, *arguments)
        assert result.exit_code == 2
        assert type(result.exception) is SystemExit
        assert result.stderr == (
            f'CPS job flows {command} failed: {reason}; {run}; path {path}\n')
        assert result.stdout == ''
        assert '8822000000000001' not in result.output
        assert not data_directory.exists()


def recorder(calls, name, result):
    def record(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result

    return record


def test_commands_wire_arguments_and_print_data_relative_paths(cli_runner, data_directory,
                                                               monkeypatch, tmp_path):
    calls = []
    # Keys out of sorted order, so the printed lines show `sort_keys`.
    built = {'run_id': 'run_1', 'directory': str(run_directory(data_directory, 'run_1')),
             'outputs_sha256': PIN}
    verified = {'run_id': 'run_1', 'outputs_sha256': PIN, 'rows': {'b': 2, 'a': 1}}
    compared = {'equal': True, 'tables': {}, 'report_equal': True, 'trust_established': False}
    snapshot = data_directory / RAW / 'refs'
    for owner, name, result in (
            (cps_flow_references, 'acquire', snapshot),
            (cps_flow_references, 'import_reference', snapshot),
            (cps_flow_bundle, 'build', built),
            (cps_flow_bundle, 'verify_bundle', verified),
            (cps_flow_bundle, 'compare_runs', compared)):
        monkeypatch.setattr(owner, name, recorder(calls, name, result))

    file = tmp_path / 'original.csv'
    values = {field: f'value_{index}' for index, (_, field) in enumerate(OPTIONS)}
    request = cps_flow_inputs.InputRequest(**values)
    outputs = {
        'acquire-references': invoke(cli_runner, 'acquire-references', data_directory, 'refs'),
        'import-reference': invoke(cli_runner, 'import-reference', data_directory, 'refs',
                                   'some_kind', str(file)),
        'build': invoke(cli_runner, 'build', data_directory,
                        *build_arguments('run_1', request)),
        'verify': invoke(cli_runner, 'verify', data_directory, 'run_1', '--outputs-sha256', PIN),
        'compare-runs': invoke(cli_runner, 'compare-runs', data_directory, 'run_1', 'run_2'),
    }
    for command, result in outputs.items():
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''
    assert outputs['acquire-references'].stdout == json.dumps(f'{RAW}/refs') + '\n'
    assert outputs['import-reference'].stdout == json.dumps(f'{RAW}/refs') + '\n'
    assert outputs['build'].stdout == json.dumps({
        'directory': bundle_path('run_1'), 'outputs_sha256': PIN, 'run_id': 'run_1',
    }, sort_keys=True) + '\n'
    assert outputs['verify'].stdout == json.dumps({
        'outputs_sha256': PIN, 'rows': {'a': 1, 'b': 2}, 'run_id': 'run_1',
    }, sort_keys=True) + '\n'
    assert outputs['compare-runs'].stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert calls == [
        ('acquire', (data_directory, 'refs'), {}),
        ('import_reference', (data_directory, 'refs', 'some_kind', file), {}),
        ('build', (data_directory, 'run_1', request), {}),
        ('verify_bundle', (run_directory(data_directory, 'run_1'), data_directory),
         {'expected_outputs_sha256': PIN}),
        ('compare_runs', (run_directory(data_directory, 'run_1'),
                          run_directory(data_directory, 'run_2')), {}),
    ]


@pytest.mark.parametrize('equal,report_equal,code', [
    (True, True, 0),
    (False, True, 1),  # The tables differ and the reports agree.
    (False, False, 1),
], ids=['equal', 'tables_differ', 'both_differ'])
def test_the_compare_exit_code_follows_the_equal_field_alone(
        cli_runner, data_directory, monkeypatch, equal, report_equal, code):
    compared = {'equal': equal, 'report_equal': report_equal, 'tables': {},
                'trust_established': False}
    monkeypatch.setattr(cps_flow_bundle, 'compare_runs', lambda first, second: compared)
    result = invoke(cli_runner, 'compare-runs', data_directory, 'run_1', 'run_2')
    assert result.exit_code == code
    assert type(result.exception) is (SystemExit if code else type(None))
    assert result.stdout == json.dumps(compared, sort_keys=True) + '\n'
    # Outside the guard: an unequal comparison is not the fixed failure line.
    assert result.stderr == ''


def forbid_bundle_operations(monkeypatch):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a refused command reached the bundle or the references')

    for name in ('build', 'verify_bundle', 'compare_runs'):
        monkeypatch.setattr(cps_flow_bundle, name, forbidden)
    for name in ('acquire', 'import_reference'):
        monkeypatch.setattr(cps_flow_references, name, forbidden)


@pytest.mark.parametrize('missing', [option for option, _ in OPTIONS])
def test_each_build_option_is_required(cli_runner, data_directory, monkeypatch, missing):
    forbid_bundle_operations(monkeypatch)
    request = cps_flow_inputs.InputRequest(**{field: 'x' for _, field in OPTIONS})
    arguments = build_arguments('run_1', request)
    position = arguments.index(missing)
    del arguments[position:position + 2]
    result = invoke(cli_runner, 'build', data_directory, *arguments)
    assert result.exit_code == 2, result.output
    assert 'Missing option' in result.output
    assert missing in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('acquire-references', []),
    ('import-reference', ['refs', 'kind']),
    ('build', ['run_1']),
    ('verify', ['--outputs-sha256', PIN]),
    ('verify', ['run_1']),
    ('compare-runs', ['run_1']),
], ids=['acquire_id', 'import_file', 'build_options', 'verify_run', 'verify_pin',
        'compare_second'])
def test_each_required_argument_fails_before_work(cli_runner, data_directory, monkeypatch,
                                                  command, arguments):
    forbid_bundle_operations(monkeypatch)
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2, result.output
    assert 'Missing' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('acquire-references', ['refs']),
    ('import-reference', ['refs', 'kind', 'original.csv']),
    ('build', build_arguments('run_1', SimpleNamespace(**{field: 'x' for _, field in OPTIONS}))),
    ('verify', ['run_1', '--outputs-sha256', PIN]),
    ('compare-runs', ['run_1', 'run_2']),
], ids=COMMANDS)
def test_data_dir_is_required(cli_runner, monkeypatch, tmp_path, command, arguments):
    forbid_bundle_operations(monkeypatch)
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, [command, *arguments])
    assert result.exit_code == 2
    assert 'Missing option' in result.output
    assert '--data-dir' in result.output
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('command,arguments,run,path', [
    ('build', ['../escape'], '../escape', f'{BUNDLES}/../escape'),
    ('verify', ['../escape', '--outputs-sha256', PIN], '../escape', f'{BUNDLES}/../escape'),
    ('compare-runs', ['../escape', 'run_2'], '../escape,run_2',
     f'{BUNDLES}/../escape,{bundle_path("run_2")}'),
    ('compare-runs', ['run_1', 'a b'], 'run_1,a b', f'{bundle_path("run_1")},{BUNDLES}/a b'),
], ids=['build', 'verify', 'compare-first', 'compare-second'])
def test_an_unsafe_run_id_gives_the_fixed_line_and_writes_nothing(
        cli_runner, data_directory, command, arguments, run, path):
    if command == 'build':
        arguments = build_arguments(arguments[0], SimpleNamespace(**{
            field: 'x' for _, field in OPTIONS}))
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2
    assert result.stderr == failure(command, 'validation', run, path)
    assert result.stdout == ''
    assert not data_directory.exists()


def test_build_failure_keeps_an_occupied_run_name(cli_runner, seeded):
    occupied = seeded.data_dir / BUNDLES / 'r1.part'
    occupied.mkdir(parents=True)
    (occupied / 'kept.txt').write_bytes(b'owner evidence\n')
    result = invoke(cli_runner, 'build', seeded.data_dir,
                    *build_arguments('r1', seeded.request))
    assert result.exit_code == 2
    assert result.stderr == failure('build', 'validation', 'r1')
    assert [path.name for path in occupied.iterdir()] == ['kept.txt']


def test_verify_refuses_a_wrong_pin_with_the_fixed_line(cli_runner, seeded):
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('r1', seeded.request))
    assert built.exit_code == 0, built.output
    result = invoke(cli_runner, 'verify', seeded.data_dir, 'r1', '--outputs-sha256', PIN)
    assert result.exit_code == 2
    assert result.stderr == failure('verify', 'validation', 'r1')
    assert result.stdout == ''


def test_top_level_cli_does_not_register_these_commands():
    from embedding_data import cli

    assert all(command.callback.__module__ != cps_job_flows.__name__
               for command in cli.app.registered_commands)
    assert all(group.typer_instance is not app for group in cli.app.registered_groups)
    assert not {'acquire-references', 'import-reference', 'verify', 'compare-runs'} & set(
        get_command(cli.app).commands)


def test_app_disables_pretty_exceptions_and_locals():
    assert app.pretty_exceptions_enable is False
    assert app.pretty_exceptions_show_locals is False


def test_module_runs_with_python_m(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.cps_job_flows', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in COMMANDS:
        assert command in result.stdout
