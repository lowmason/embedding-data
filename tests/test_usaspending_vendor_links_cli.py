'''The Stage 14 command group: subaward and SAM.gov extract acquisition and import, then build,
verify and compare-runs. Their JSON line, exit codes and fixed failure line.

The build, verify and compare tests seed synthetic raw files and a real Stage 4 codes bundle once
per module, and run the commands through the test registries. Fixture results show software
readiness only, never benchmarks.'''

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from types import SimpleNamespace

import httpx
import polars as pl
import pytest
import typer
from target_fixtures import forbid_external_access
from typer.main import get_command
from typer.testing import CliRunner
from vendor_link_fixtures import (  # noqa: F401
    EXTRACT_NAME,
    FAKE_KEY,
    MONTH,
    NAME,
    TEST_EXTRACT_LAYOUT,
    TEST_SUBAWARD_LAYOUTS,
    FakeSam,
    FakeUsaspending,
    extract_answer,
    extract_line,
    extract_name,
    install_sam,
    install_usaspending,
    module_file,
    no_live_sam,
    sample_extract,
    sample_zip,
    seed_codes_bundle,
    seed_raw,
    subaward_record,
    subprocess_modules,
    zip_bytes,
)

from embedding_data import (
    code_build,
    ita_summary,
    manifest,
    paths,
    sam_access,
    sam_raw,
    target_io,
    usaspending_raw,
    usaspending_vendor_links,
    vendor_link_bundle,
    vendor_link_layouts,
)

SECRET = 'EIN 123456789 at 1 Main St, key FAKEKEYfake0123456789ABCDEFghij'


def failure_line(command, reason):
    return (f'USAspending vendor links {command} failed: {reason}; run -; '
            'path raw/usaspending/subcontracts')


def acquire_arguments(data_directory, fiscal_year='2025', snapshot='2026-11-20'):
    return ['acquire-subawards', fiscal_year, '--snapshot', snapshot, '--data-dir',
            str(data_directory)]


def import_arguments(data_directory, file, fiscal_year='2025', snapshot='2026-11-20'):
    return ['import-subawards', fiscal_year, str(file), '--snapshot', snapshot, '--data-dir',
            str(data_directory)]


def original_file(tmp_path, name=NAME):
    file = tmp_path / 'downloads' / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(sample_zip())
    return file


def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, tmp_path,
                                                monkeypatch):
    install_usaspending(monkeypatch, FakeUsaspending())
    acquired = cli_runner.invoke(usaspending_vendor_links.app,
                                 acquire_arguments(data_directory))
    assert acquired.exit_code == 0, acquired.output
    expected = {'path': f'raw/usaspending/subcontracts/2026-11-20/FY2025/{NAME}'}
    assert acquired.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert acquired.stderr == ''
    file = original_file(tmp_path, 'FY2024_Subawards.zip')
    imported = cli_runner.invoke(usaspending_vendor_links.app,
                                 import_arguments(data_directory, file, '2024'))
    assert imported.exit_code == 0, imported.output
    expected = {'path': 'raw/usaspending/subcontracts/2026-11-20/FY2024/FY2024_Subawards.zip'}
    assert imported.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert imported.stderr == ''
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.client) for entry in entries] == [
        (f'usaspending/subcontracts/2026-11-20/FY2025/{NAME}', 'httpx'),
        ('usaspending/subcontracts/2026-11-20/FY2024/FY2024_Subawards.zip', 'manual-import')]


def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    file = original_file(tmp_path)
    result = cli_runner.invoke(usaspending_vendor_links.app, [
        'import-subawards', '2023', str(file), '--snapshot', '2026-11-20',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == ('USAspending vendor links import-subawards failed: '
                                     'validation; run -; path raw/usaspending/subcontracts')


@pytest.mark.parametrize('error, reason', [
    (ValueError(SECRET), 'validation'),
    (json.JSONDecodeError(SECRET, SECRET, 0), 'validation'),
    (FileNotFoundError(2, SECRET, SECRET), 'filesystem'),
    (PermissionError(13, SECRET, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (httpx.HTTPStatusError(SECRET, request=httpx.Request('GET', 'https://example.test'),
                           response=httpx.Response(403)), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
    (AssertionError(SECRET), 'unexpected'),
], ids=['value', 'json', 'missing_file', 'permission', 'connect', 'status', 'runtime', 'key',
        'assertion'])
@pytest.mark.parametrize('command, operation', [('acquire-subawards', 'acquire'),
                                                ('import-subawards', 'import_file')])
def test_failure_reason_follows_the_exception_type_and_hides_its_text(
        cli_runner, data_directory, tmp_path, monkeypatch, command, operation, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(usaspending_raw, operation, fail)
    arguments = (acquire_arguments(data_directory) if command == 'acquire-subawards'
                 else import_arguments(data_directory, original_file(tmp_path)))
    result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
    assert result.exit_code == 2
    assert result.stdout == ''
    assert result.stderr == failure_line(command, reason) + '\n'
    assert SECRET not in result.output


@pytest.mark.parametrize('snapshot', ['not-a-date', '2026-13-45', '2026-02-30', ''])
def test_a_bad_snapshot_date_fails_as_validation_before_any_work(
        cli_runner, data_directory, tmp_path, snapshot):
    for arguments in (acquire_arguments(data_directory, snapshot=snapshot),
                      import_arguments(data_directory, original_file(tmp_path),
                                       snapshot=snapshot)):
        result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
        assert result.exit_code == 2
        assert result.stderr == failure_line(arguments[0], 'validation') + '\n'
    assert not data_directory.exists()


def test_acquire_refuses_a_year_outside_the_window_as_validation(cli_runner, data_directory):
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               acquire_arguments(data_directory, '2023'))
    assert result.exit_code == 2
    assert result.stderr == failure_line('acquire-subawards', 'validation') + '\n'


def test_a_missing_network_patch_fails_instead_of_reaching_the_network(cli_runner,
                                                                       data_directory):
    result = cli_runner.invoke(usaspending_vendor_links.app, acquire_arguments(data_directory))
    assert result.exit_code == 2
    assert result.stderr == failure_line('acquire-subawards', 'unexpected') + '\n'


@pytest.mark.parametrize('drop', ['--data-dir', '--snapshot'])
def test_every_command_requires_an_explicit_data_root_and_snapshot(
        cli_runner, data_directory, tmp_path, drop):
    for arguments in (acquire_arguments(data_directory, '2023'),
                      import_arguments(data_directory, tmp_path / 'absent.zip', '2023')):
        index = arguments.index(drop)
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   arguments[:index] + arguments[index + 2:])
        assert result.exit_code == 2
        assert drop in result.output


def test_invoke_prints_one_sorted_json_line_and_returns_the_result(capsys):
    result = usaspending_vendor_links._invoke(
        'acquire-subawards', usaspending_vendor_links.NO_RUN, 'somewhere',
        lambda: {'b': 1, 'a': [2, 3]})
    assert result == {'b': 1, 'a': [2, 3]}
    assert capsys.readouterr() == ('{"a": [2, 3], "b": 1}\n', '')


def test_invoke_failure_exits_two_with_only_the_fixed_line(capsys):
    def fail():
        raise OSError(SECRET)

    with pytest.raises(typer.Exit) as stopped:
        usaspending_vendor_links._invoke('import-subawards', 'run_7', 'some/path', fail)
    assert stopped.value.exit_code == 2
    assert capsys.readouterr() == (
        '', 'USAspending vendor links import-subawards failed: filesystem; run run_7; '
        'path some/path\n')


def test_constants_and_typer_settings():
    module = usaspending_vendor_links
    assert module.NO_RUN == '-'
    assert module.SUBAWARDS == 'raw/usaspending/subcontracts'
    assert module.EXTRACTS == 'raw/sam/entity-extract/public-monthly-v2'
    assert module.app.pretty_exceptions_enable is False
    assert module.app.pretty_exceptions_show_locals is False


def test_module_runs_with_python_m_and_lists_its_commands(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.usaspending_vendor_links', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in ('acquire-subawards', 'import-subawards'):
        assert command in result.stdout


def test_importing_the_command_module_loads_no_credential_or_ipums_library(tmp_path):
    result = subprocess.run(
        [sys.executable, '-c',
         'import sys; import embedding_data.usaspending_vendor_links; '
         "print('dotenv' in sys.modules, 'ipumspy' in sys.modules)"],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'False False'


# --- SAM.gov extract commands


EXTRACT_DIRECTORY = 'raw/sam/entity-extract/public-monthly-v2'


def sam_failure_line(command, reason):
    return (f'USAspending vendor links {command} failed: {reason}; run -; '
            f'path {EXTRACT_DIRECTORY}')


def sam_acquire_arguments(data_directory, month=MONTH, *options):
    return ['acquire-sam-extract', '--month', month, '--data-dir', str(data_directory),
            *options]


def sam_import_arguments(data_directory, file, month=MONTH):
    return ['import-sam-extract', str(file), '--month', month, '--data-dir', str(data_directory)]


def extract_original(tmp_path, month='2026-10', *, committed=False):
    '''An extract download. Its member fits the invented test layout, which every test of
    this module installs, or with `committed` the committed layout, for a fresh process.'''
    file = tmp_path / 'downloads' / extract_name(month)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(sample_extract(month, committed=committed))
    return file


def test_sam_acquire_and_import_print_one_json_line(cli_runner, data_directory, tmp_path,
                                                    monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    acquired = cli_runner.invoke(usaspending_vendor_links.app,
                                 sam_acquire_arguments(data_directory))
    assert acquired.exit_code == 0, acquired.output
    expected = {'path': f'{EXTRACT_DIRECTORY}/2026-11/{EXTRACT_NAME}'}
    assert acquired.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert acquired.stderr == ''
    imported = cli_runner.invoke(usaspending_vendor_links.app, sam_import_arguments(
        data_directory, extract_original(tmp_path), '2026-10'))
    assert imported.exit_code == 0, imported.output
    expected = {'path': f'{EXTRACT_DIRECTORY}/2026-10/{extract_name("2026-10")}'}
    assert imported.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert imported.stderr == ''
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.client) for entry in entries] == [
        (f'sam/entity-extract/public-monthly-v2/2026-11/{EXTRACT_NAME}', 'httpx'),
        (f'sam/entity-extract/public-monthly-v2/2026-10/{extract_name("2026-10")}',
         'manual-import')]


def test_sam_commands_refuse_a_wrapped_extract_as_validation_and_record_nothing(
        cli_runner, data_directory, tmp_path, monkeypatch):
    # A ZIP around the extract ZIP, under the extract's own name, as a browser can save it.
    install_sam(monkeypatch, FakeSam(extract_answer(
        zip_bytes({EXTRACT_NAME: sample_extract()}))))
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    wrapped = tmp_path / 'downloads' / extract_name('2026-10')
    wrapped.parent.mkdir()
    wrapped.write_bytes(zip_bytes({wrapped.name: sample_extract('2026-10')}))
    for arguments in (sam_acquire_arguments(data_directory),
                      sam_import_arguments(data_directory, wrapped, '2026-10')):
        result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
        assert result.exit_code == 2
        assert result.stdout == ''
        assert result.stderr == sam_failure_line(arguments[0], 'validation') + '\n'
    assert [file for file in data_directory.rglob('*') if file.is_file()] == []


SAM_FAILURES = [
    (ValueError(SECRET), 'validation'),
    (FileNotFoundError(2, SECRET, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
]


@pytest.mark.parametrize('error, reason', SAM_FAILURES,
                         ids=['value', 'missing_file', 'connect', 'runtime'])
@pytest.mark.parametrize('command, operation', [('acquire-sam-extract', 'acquire'),
                                                ('import-sam-extract', 'import_file')])
def test_sam_failure_reason_follows_the_exception_type_and_hides_its_text(
        cli_runner, data_directory, tmp_path, monkeypatch, command, operation, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(sam_raw, operation, fail)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    arguments = (sam_acquire_arguments(data_directory) if command == 'acquire-sam-extract'
                 else sam_import_arguments(data_directory, extract_original(tmp_path)))
    result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
    assert result.exit_code == 2
    assert result.stdout == ''
    assert result.stderr == sam_failure_line(command, reason) + '\n'
    assert SECRET not in result.output


def test_acquire_sam_extract_passes_the_key_options_and_the_key(cli_runner, data_directory,
                                                                tmp_path, monkeypatch):
    seen = []

    def read(**options):
        seen.append(options)
        return FAKE_KEY

    def acquire(data_dir, month, *, credential):
        seen.append((data_dir, month, credential))
        return sam_raw.month_dir(data_dir, month) / EXTRACT_NAME

    monkeypatch.setattr(sam_access, 'read_credential', read)
    monkeypatch.setattr(sam_raw, 'acquire', acquire)
    env_file = tmp_path / 'sam.env'
    result = cli_runner.invoke(usaspending_vendor_links.app, sam_acquire_arguments(
        data_directory, MONTH, '--env-file', str(env_file), '--prompt'))
    assert result.exit_code == 0, result.output
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory))
    assert result.exit_code == 0, result.output
    assert seen == [{'env_file': env_file, 'prompt': True}, (data_directory, MONTH, FAKE_KEY),
                    {'env_file': None, 'prompt': False}, (data_directory, MONTH, FAKE_KEY)]


def test_import_sam_extract_reads_no_key_and_makes_no_client(cli_runner, data_directory,
                                                             tmp_path, monkeypatch):
    def forbidden(**options):
        raise AssertionError('read the key')

    monkeypatch.setattr(sam_access, 'read_credential', forbidden)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app, sam_import_arguments(
        data_directory, extract_original(tmp_path), '2026-10'))
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize('month', ['2026-13', '11/2026', ''])
def test_a_bad_month_fails_as_validation_before_the_key_is_read(
        cli_runner, data_directory, tmp_path, monkeypatch, month):
    asked = []

    def read(**options):
        asked.append(options)
        return FAKE_KEY

    monkeypatch.setattr(sam_access, 'read_credential', read)
    for arguments in (sam_acquire_arguments(data_directory, month),
                      sam_import_arguments(data_directory, extract_original(tmp_path), month)):
        result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
        assert result.exit_code == 2
        assert result.stderr == sam_failure_line(arguments[0], 'validation') + '\n'
    assert asked == []
    assert not data_directory.exists()


def test_prompt_without_a_terminal_fails_as_validation_before_any_request(
        cli_runner, data_directory, monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer()))
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory, MONTH, '--prompt'))
    assert result.exit_code == 2
    assert result.stderr == sam_failure_line('acquire-sam-extract', 'validation') + '\n'
    assert server.requests == []
    assert not data_directory.exists()


def test_a_missing_sam_patch_fails_closed_instead_of_reaching_the_network(
        cli_runner, data_directory, monkeypatch):
    # The guard's AssertionError is inside the protected scope, so it becomes the fixed error.
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory))
    assert result.exit_code == 2
    assert result.stderr == sam_failure_line('acquire-sam-extract', 'validation') + '\n'
    assert not paths.manifest_path(data_directory).exists()


@pytest.mark.parametrize('drop', ['--data-dir', '--month'])
def test_sam_commands_require_an_explicit_data_root_and_month(cli_runner, data_directory,
                                                              tmp_path, drop):
    for arguments in (sam_acquire_arguments(data_directory),
                      sam_import_arguments(data_directory, tmp_path / 'absent.ZIP')):
        index = arguments.index(drop)
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   arguments[:index] + arguments[index + 2:])
        assert result.exit_code == 2
        assert drop in result.output


def test_module_lists_the_sam_commands(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.usaspending_vendor_links', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in ('acquire-sam-extract', 'import-sam-extract'):
        assert command in result.stdout


# Runs both import commands in a fresh interpreter where every dotenv import is refused and no
# HTTP client can be built, then reports what was attempted.
OFFLINE_IMPORTS = """
import json
import os
import sys


class RefuseDotenv:
    attempts = []

    def find_spec(self, name, path=None, target=None):
        if name.partition('.')[0] == 'dotenv':
            RefuseDotenv.attempts.append(name)
            raise ImportError('dotenv refused')
        return None


sys.meta_path.insert(0, RefuseDotenv())
import httpx


def no_client(*args, **kwargs):
    raise AssertionError('HTTP client constructed')


httpx.Client.__init__ = no_client
from typer.testing import CliRunner

from embedding_data import usaspending_vendor_links

data_dir, extract, month, subawards = sys.argv[1:]
before = dict(os.environ)
runner = CliRunner()
codes = [runner.invoke(usaspending_vendor_links.app, arguments).exit_code for arguments in (
    ['import-sam-extract', extract, '--month', month, '--data-dir', data_dir],
    ['import-subawards', '2025', subawards, '--snapshot', '2026-11-20', '--data-dir', data_dir])]
print(json.dumps({'codes': codes, 'dotenv_imports': RefuseDotenv.attempts,
                  'dotenv_loaded': 'dotenv' in sys.modules,
                  'environ_unchanged': dict(os.environ) == before}))
"""


def test_import_commands_load_no_environment_file(data_directory, tmp_path):
    # dotenv cannot even be imported, so a wrong version that loads an env file fails here
    # without ever reading one.
    environment = {name: value for name, value in os.environ.items()
                   if name not in ('SAM_API_KEY', 'IPUMS_API_KEY')}
    result = subprocess.run(
        [sys.executable, '-c', OFFLINE_IMPORTS, str(data_directory),
         str(extract_original(tmp_path, MONTH, committed=True)), MONTH,
         str(original_file(tmp_path))],
        capture_output=True, text=True, cwd=tmp_path, env=environment, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'codes': [0, 0], 'dotenv_imports': [],
                                         'dotenv_loaded': False, 'environ_unchanged': True}
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.client for entry in entries] == ['manual-import', 'manual-import']


def test_importing_the_command_module_loads_no_census_access_module(tmp_path):
    result = subprocess.run(
        [sys.executable, '-c',
         'import sys; import embedding_data.usaspending_vendor_links; '
         "print('embedding_data.sam_access' in sys.modules, "
         "'embedding_data.ipums_census_access' in sys.modules, 'dotenv' in sys.modules)"],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'True False False'


# --- build, verify and compare-runs

COMMANDS = ('acquire-subawards', 'import-subawards', 'acquire-sam-extract',
            'import-sam-extract', 'build', 'verify', 'compare-runs')
VENDOR_LINKS = 'derived/usaspending/vendor-links'
SNAPSHOT_TEXT = '2026-11-20'
SNAPSHOT = date(2026, 11, 20)
# The extract month differs from the snapshot month, as in production.
SAM_MONTH = '2026-10'
EXTRACT_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261002.dat'
MEMBER = 'Contracts_Subawards_1.csv'
FIRST, REPLAY = 'vl_first', 'vl_replay'
CODES_PIN = '1' * 64
OUTPUTS_PIN = '2' * 64
P1, P2 = 'PRIMEA000001', 'PRIMEB000002'
S1, S2 = 'SUBAWA000001', 'SUBAWB000002'
# One usable report in each year of the window: three distinct pairs of four firms.
REPORTS = {2024: (P1, S1, '2024-03-01', '1000.00'), 2025: (P2, S2, '2025-02-01', '250.50'),
           2026: (P1, S2, '2026-03-01', '75.25')}
FIRM_CODES = {P1: '541511', P2: '236220', S1: '541512', S2: '336411'}
TABLES = ('vendor_links', 'vendor_link_marginals', 'vendor_link_support', 'vendor_link_pairs')


def use_test_registries(patch):
    '''Make the committed registry loaders return the invented test registries.'''
    patch.setattr(vendor_link_layouts, 'load_subaward_layouts',
                  lambda *args, **kwargs: TEST_SUBAWARD_LAYOUTS)
    patch.setattr(vendor_link_layouts, 'load_extract_layout',
                  lambda *args, **kwargs: TEST_EXTRACT_LAYOUT)


@pytest.fixture(autouse=True)
def committed_registries_replaced(monkeypatch):
    use_test_registries(monkeypatch)


def firm_line(uei, code):
    return extract_line(TEST_EXTRACT_LAYOUT, uei=uei, registration_status='A',
                        last_update_date='20250115', primary_naics=code,
                        naics_code_string=f'{code}Y', evs_source='SAM')


def seeded_subawards():
    return {year: {MEMBER: [subaward_record(
        TEST_SUBAWARD_LAYOUTS[year], prime_uei=prime, sub_uei=sub, action_date=action,
        amount=amount, subaward_type='sub-contract')]}
        for year, (prime, sub, action, amount) in REPORTS.items()}


def build_arguments(run_id, data_directory, codes, *, snapshot=SNAPSHOT_TEXT,
                    month=SAM_MONTH):
    return ['build', run_id, '--codes-run', codes[0], '--codes-outputs-sha256', codes[1],
            '--snapshot', snapshot, '--sam-month', month, '--data-dir', str(data_directory)]


def verify_arguments(run_id, data_directory, pin):
    return ['verify', run_id, '--outputs-sha256', pin, '--data-dir', str(data_directory)]


def compare_arguments(first, second, data_directory):
    return ['compare-runs', first, second, '--data-dir', str(data_directory)]


@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    '''A pristine data root: a real Stage 4 codes bundle and the three window years of synthetic
    subaward ZIPs and one extract, imported in the test registries. It holds no build.'''
    root = tmp_path_factory.mktemp('vendor_links_cli')
    codes = seed_codes_bundle(root / 'codes' / 'data', root / 'codes' / 'originals')
    pristine = root / 'pristine'
    shutil.copytree(root / 'codes' / 'data' / 'derived' / 'codes' / codes[0],
                    pristine / 'derived' / 'codes' / codes[0])
    seed_raw(pristine, root / 'originals', seeded_subawards(),
             [firm_line(uei, code) for uei, code in FIRM_CODES.items()],
             snapshot=SNAPSHOT, month=SAM_MONTH, subaward_layouts=TEST_SUBAWARD_LAYOUTS,
             extract_layout=TEST_EXTRACT_LAYOUT, extract_member=EXTRACT_MEMBER)
    return SimpleNamespace(root=root, pristine=pristine, codes=codes,
                           originals=root / 'originals')


@pytest.fixture(scope='module')
def built(seeded):
    '''A copy of the pristine root that holds the runs `FIRST` and `REPLAY`, each built by the
    `build` command. `printed` maps each run ID to its command result.'''
    data_dir = seeded.root / 'data'
    shutil.copytree(seeded.pristine, data_dir)
    runner = CliRunner()
    with pytest.MonkeyPatch.context() as patch:
        use_test_registries(patch)
        results = [runner.invoke(usaspending_vendor_links.app,
                                 build_arguments(run, data_dir, seeded.codes))
                   for run in (FIRST, REPLAY)]
    for result in results:
        assert result.exit_code == 0, result.output
    printed = dict(zip((FIRST, REPLAY), results, strict=True))
    return SimpleNamespace(
        seeded=seeded, data_dir=data_dir, codes=seeded.codes, printed=printed,
        pins={run: json.loads(result.stdout)['outputs_sha256']
              for run, result in printed.items()})


def fresh_root(seeded, tmp_path):
    data_dir = tmp_path / 'data'
    shutil.copytree(seeded.pristine, data_dir)
    return data_dir


def copy_of_built(built, tmp_path):
    data_dir = tmp_path / 'data'
    shutil.copytree(built.data_dir, data_dir)
    return data_dir


def run_path(data_directory, run_id):
    return vendor_link_bundle.run_directory(data_directory, run_id)


def one_sorted_json_line(result):
    '''The value of the one JSON line that a successful command printed. The line is sorted:
    printing the value again in key order gives the same text.'''
    assert result.exit_code == 0, result.output
    assert result.stderr == ''
    text = result.stdout
    assert text.endswith('\n') and text.count('\n') == 1
    value = json.loads(text)
    assert text == json.dumps(value, sort_keys=True) + '\n'
    return value


def vendor_failure(command, reason, run_id='run_1', second='run_2'):
    '''The exact stderr of one failed build, verify or compare-runs command.'''
    if command == 'compare-runs':
        run, path = f'{run_id},{second}', f'{VENDOR_LINKS}/{run_id},{VENDOR_LINKS}/{second}'
    else:
        run, path = run_id, f'{VENDOR_LINKS}/{run_id}'
    return f'USAspending vendor links {command} failed: {reason}; run {run}; path {path}\n'


def command_arguments(command, data_directory, codes=('codes_run', CODES_PIN)):
    '''Valid arguments of one new command, with `--data-dir`, for run `run_1` (and `run_2`).'''
    return {
        'build': build_arguments('run_1', data_directory, codes),
        'verify': verify_arguments('run_1', data_directory, OUTPUTS_PIN),
        'compare-runs': compare_arguments('run_1', 'run_2', data_directory),
    }[command]


BUNDLE_OPERATIONS = {'build': 'build', 'verify': 'verify_bundle', 'compare-runs': 'compare_runs'}


def forbid_bundle(monkeypatch):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a refused command reached the bundle module')

    for name in BUNDLE_OPERATIONS.values():
        monkeypatch.setattr(vendor_link_bundle, name, forbidden)


def tree_snapshot(root):
    '''Every path under root, with the bytes of each file and None for each directory.'''
    return sorted((path.relative_to(root).as_posix(), path.read_bytes() if path.is_file()
                   else None) for path in root.rglob('*'))


def repin(directory):
    '''Rewrite `outputs.json` for the current bundle bytes and return its new pin.'''
    target_io.write_json(directory / 'outputs.json',
                         target_io.inventory(directory, list(vendor_link_bundle.FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def tamper_table(directory):
    '''Repeat the first row of `vendor_link_pairs`, so a recomputation and a comparison differ
    and the bundle's own inventory still holds. Returns the new detached pin.'''
    file = directory / 'vendor_link_pairs.parquet'
    frame = pl.read_parquet(file)
    pl.concat([frame, frame.head(1)]).write_parquet(file)
    return repin(directory)


def tamper_report(directory):
    file = directory / 'report.json'
    report = json.loads(file.read_text())
    report['size_gate'] = 'tampered'
    target_io.write_json(file, report)
    return repin(directory)


def test_help_lists_exactly_seven_commands(cli_runner):
    app = usaspending_vendor_links.app
    assert sorted(command.name for command in app.registered_commands) == sorted(COMMANDS)
    assert sorted(get_command(app).commands) == sorted(COMMANDS)
    assert len(COMMANDS) == 7
    result = cli_runner.invoke(app, ['--help'])
    assert result.exit_code == 0, result.output
    for command in COMMANDS:
        assert command in result.stdout


@pytest.mark.parametrize('command, options', [
    ('build', ['--codes-run', '--codes-outputs-sha256', '--snapshot', '--sam-month',
               '--data-dir']),
    ('verify', ['--outputs-sha256', '--data-dir']),
    ('compare-runs', ['--data-dir']),
])
def test_each_new_command_lists_its_options_in_its_help(cli_runner, command, options):
    result = cli_runner.invoke(usaspending_vendor_links.app, [command, '--help'])
    assert result.exit_code == 0, result.output
    for option in options:
        assert option in result.stdout


def test_build_verify_and_compare_print_one_sorted_json_line(cli_runner, built):
    data_dir = built.data_dir
    for run in (FIRST, REPLAY):
        printed = one_sorted_json_line(built.printed[run])
        assert printed == {'run_id': run, 'directory': str(run_path(data_dir, run)),
                           'outputs_sha256': built.pins[run]}
        assert manifest.sha256_file(run_path(data_dir, run) / 'outputs.json') == (
            built.pins[run])
    verified = {}
    for run in (FIRST, REPLAY):
        verified[run] = one_sorted_json_line(cli_runner.invoke(
            usaspending_vendor_links.app, verify_arguments(run, data_dir, built.pins[run])))
        assert verified[run] == {
            'run_id': run, 'outputs_sha256': built.pins[run],
            'rows': {name: pl.read_parquet(run_path(data_dir, run) / f'{name}.parquet').height
                     for name in TABLES}}
    assert verified[FIRST]['rows'] == verified[REPLAY]['rows']
    assert verified[FIRST]['rows']['vendor_link_pairs'] == 3
    compared = one_sorted_json_line(cli_runner.invoke(
        usaspending_vendor_links.app, compare_arguments(FIRST, REPLAY, data_dir)))
    assert compared['equal'] is True
    assert compared['report_equal'] is True
    assert compared['trust_established'] is False
    assert sorted(compared['tables']) == sorted(TABLES)


def recorder(calls, name, result):
    def record(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result

    return record


def test_commands_wire_arguments_to_the_bundle_module(cli_runner, data_directory, monkeypatch):
    calls = []
    # Keys out of sorted order, so the printed line shows `sort_keys`.
    built_result = {'run_id': 'run_1', 'outputs_sha256': OUTPUTS_PIN, 'directory': 'published'}
    verified = {'run_id': 'run_1', 'rows': {'b': 2, 'a': 1}, 'outputs_sha256': OUTPUTS_PIN}
    compared = {'tables': {}, 'equal': True, 'trust_established': False}
    for name, result in zip(BUNDLE_OPERATIONS.values(), (built_result, verified, compared),
                            strict=True):
        monkeypatch.setattr(vendor_link_bundle, name, recorder(calls, name, result))
    codes = ('codes_run', CODES_PIN)
    outputs = {
        'build': cli_runner.invoke(usaspending_vendor_links.app,
                                   build_arguments('run_1', data_directory, codes)),
        'verify': cli_runner.invoke(usaspending_vendor_links.app,
                                    verify_arguments('run_1', data_directory, OUTPUTS_PIN)),
        'compare-runs': cli_runner.invoke(
            usaspending_vendor_links.app, compare_arguments('run_1', 'run_2', data_directory)),
    }
    for command, result in outputs.items():
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''
    for command, result in (('build', built_result), ('verify', verified),
                            ('compare-runs', compared)):
        assert outputs[command].stdout == json.dumps(result, sort_keys=True) + '\n'
    assert outputs['build'].stdout.startswith('{"directory": ')
    assert calls == [
        ('build', (data_directory, 'run_1'),
         {'codes_run': 'codes_run', 'codes_outputs_sha256': CODES_PIN, 'snapshot': SNAPSHOT,
          'sam_month': SAM_MONTH}),
        ('verify_bundle', (run_path(data_directory, 'run_1'), data_directory),
         {'expected_outputs_sha256': OUTPUTS_PIN}),
        ('compare_runs', (run_path(data_directory, 'run_1'), run_path(data_directory, 'run_2')),
         {}),
    ]
    assert type(calls[0][2]['snapshot']) is date
    assert type(calls[0][2]['sam_month']) is str


def test_build_failure_prints_only_the_fixed_line(cli_runner, data_directory):
    result = cli_runner.invoke(
        usaspending_vendor_links.app,
        build_arguments('bad', data_directory, ('codes_run', CODES_PIN), snapshot='bad-date'))
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.output.strip() == ('USAspending vendor links build failed: validation; '
                                     'run bad; path derived/usaspending/vendor-links/bad')
    assert result.stdout == ''
    assert not data_directory.exists()


NEW_FAILURES = [
    (ValueError(SECRET), 'validation'),
    (json.JSONDecodeError(SECRET, SECRET, 0), 'validation'),
    (FileNotFoundError(2, SECRET, SECRET), 'filesystem'),
    (PermissionError(13, SECRET, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
    (pl.exceptions.ComputeError(SECRET), 'unexpected'),
]


@pytest.mark.parametrize('error, reason', NEW_FAILURES, ids=[
    'value', 'json', 'missing_file', 'permission', 'connect', 'runtime', 'key', 'polars'])
@pytest.mark.parametrize('command', ['build', 'verify', 'compare-runs'])
def test_new_command_failure_reason_follows_the_exception_type_and_hides_its_text(
        cli_runner, data_directory, monkeypatch, command, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(vendor_link_bundle, BUNDLE_OPERATIONS[command], fail)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               command_arguments(command, data_directory))
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.stdout == ''
    assert result.stderr == vendor_failure(command, reason)
    assert SECRET not in result.output
    assert FAKE_KEY not in result.output
    assert not data_directory.exists()


def test_a_missing_codes_bundle_fails_as_filesystem_with_no_run_left(cli_runner,
                                                                    data_directory):
    result = cli_runner.invoke(usaspending_vendor_links.app, build_arguments(
        'run_1', data_directory, ('stage4_absent', CODES_PIN)))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('build', 'filesystem')
    assert result.stdout == ''
    root = data_directory / VENDOR_LINKS
    assert not (root / 'run_1').exists() and not (root / 'run_1.part').exists()


@pytest.mark.parametrize('snapshot', ['not-a-date', '2026-13-45', '2026-02-30', ''])
def test_build_with_a_bad_snapshot_date_fails_as_validation_before_any_work(
        cli_runner, data_directory, monkeypatch, snapshot):
    forbid_bundle(monkeypatch)
    result = cli_runner.invoke(usaspending_vendor_links.app, build_arguments(
        'run_1', data_directory, ('codes_run', CODES_PIN), snapshot=snapshot))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('build', 'validation')
    assert not data_directory.exists()


@pytest.mark.parametrize('month', ['2026-13', '2026-00', '11/2026', '2026-1', '', '2026-10-01'])
def test_build_with_a_bad_extract_month_fails_as_validation_before_any_work(
        cli_runner, data_directory, monkeypatch, month):
    forbid_bundle(monkeypatch)
    result = cli_runner.invoke(usaspending_vendor_links.app, build_arguments(
        'run_1', data_directory, ('codes_run', CODES_PIN), month=month))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('build', 'validation')
    assert not data_directory.exists()


@pytest.mark.parametrize('command, arguments', [
    ('build', ['../escape', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--snapshot', SNAPSHOT_TEXT, '--sam-month', SAM_MONTH]),
    ('verify', ['../escape', '--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['../escape', 'run_2']),
    ('compare-runs', ['run_1', 'a/b']),
], ids=['build', 'verify', 'compare-first', 'compare-second'])
def test_an_unsafe_run_id_fails_as_validation_and_writes_nothing(cli_runner, data_directory,
                                                                 monkeypatch, command,
                                                                 arguments):
    # The run ID check comes from `run_directory`, so verify and compare never reach the bundle
    # functions. `build` passes the ID on, and its own check refuses it.
    for name in ('verify_bundle', 'compare_runs'):
        monkeypatch.setattr(vendor_link_bundle, name, lambda *args, **kwargs: pytest.fail(
            'an unsafe run ID reached the bundle'))
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               [command, *arguments, '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    if command == 'compare-runs':
        first, second = arguments
        assert result.stderr == vendor_failure(command, 'validation', first, second)
    else:
        assert result.stderr == vendor_failure(command, 'validation', arguments[0])
    assert result.stdout == ''
    assert not data_directory.exists()


@pytest.mark.parametrize('arguments, kind', [
    (dict(snapshot='2026-11-21'), 'snapshot'), (dict(month='2026-09'), 'month')])
def test_build_without_the_selected_raw_files_fails_as_validation_and_leaves_no_run(
        cli_runner, seeded, tmp_path, arguments, kind):
    data_dir = fresh_root(seeded, tmp_path)
    result = cli_runner.invoke(usaspending_vendor_links.app, build_arguments(
        'run_1', data_dir, seeded.codes, **arguments))
    assert result.exit_code == 2, kind
    assert result.stderr == vendor_failure('build', 'validation')
    assert result.stdout == ''
    root = data_dir / VENDOR_LINKS
    assert not (root / 'run_1').exists() and not (root / 'run_1.part').exists()


@pytest.mark.parametrize('occupied', ['run_1.part', 'run_1'], ids=['staging', 'final'])
def test_build_failure_keeps_an_occupied_run_path(cli_runner, data_directory, occupied):
    # The real build refuses an occupied name before it reads anything. The failure must leave
    # a killed run's staging and a published bundle exactly as they were.
    root = data_directory / VENDOR_LINKS
    (root / occupied).mkdir(parents=True)
    (root / occupied / 'kept.txt').write_bytes(b'owner evidence\n')
    before = tree_snapshot(root)
    result = cli_runner.invoke(
        usaspending_vendor_links.app,
        build_arguments('run_1', data_directory, ('codes_run', CODES_PIN)))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('build', 'validation')
    assert result.stdout == ''
    assert tree_snapshot(root) == before


@pytest.mark.parametrize('command, drop', [
    ('build', '--codes-run'), ('build', '--codes-outputs-sha256'), ('build', '--snapshot'),
    ('build', '--sam-month'), ('build', '--data-dir'), ('verify', '--outputs-sha256'),
    ('verify', '--data-dir'), ('compare-runs', '--data-dir')])
def test_each_required_option_fails_before_any_work(cli_runner, data_directory, monkeypatch,
                                                    command, drop):
    forbid_bundle(monkeypatch)
    arguments = command_arguments(command, data_directory)
    index = arguments.index(drop)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               arguments[:index] + arguments[index + 2:])
    assert result.exit_code == 2
    assert 'Missing option' in result.output
    assert drop in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command, arguments', [
    ('build', ['--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--snapshot', SNAPSHOT_TEXT, '--sam-month', SAM_MONTH]),
    ('verify', ['--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['run_1']),
    ('compare-runs', []),
], ids=['build_run_id', 'verify_run_id', 'compare_second', 'compare_both'])
def test_each_required_argument_fails_before_any_work(cli_runner, data_directory, monkeypatch,
                                                      command, arguments):
    forbid_bundle(monkeypatch)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               [command, *arguments, '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert 'Missing' in result.output
    assert not data_directory.exists()


def test_verify_refuses_a_wrong_or_malformed_pin_and_a_missing_run(cli_runner, built):
    for pin in ('0' * 64, built.pins[FIRST].upper(), built.pins[FIRST][:-1], 'not a pin', ''):
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   verify_arguments(FIRST, built.data_dir, pin))
        assert result.exit_code == 2, pin
        assert result.stderr == vendor_failure('verify', 'validation', FIRST), pin
        assert result.stdout == ''
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               verify_arguments('vl_absent', built.data_dir, built.pins[FIRST]))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('verify', 'validation', 'vl_absent')


def test_verify_recomputes_a_bundle_whose_own_inventory_still_holds(cli_runner, built,
                                                                    tmp_path):
    data_dir = copy_of_built(built, tmp_path)
    pin = tamper_table(run_path(data_dir, FIRST))
    assert pin != built.pins[FIRST]
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               verify_arguments(FIRST, data_dir, pin))
    assert result.exit_code == 2
    assert result.stderr == vendor_failure('verify', 'validation', FIRST)
    assert result.stdout == ''
    # The untouched replay of the same copy still verifies.
    ok = cli_runner.invoke(usaspending_vendor_links.app,
                           verify_arguments(REPLAY, data_dir, built.pins[REPLAY]))
    assert ok.exit_code == 0, ok.output


def test_compare_refuses_a_missing_bundle(cli_runner, built):
    for first, second in ((FIRST, 'vl_absent'), ('vl_absent', FIRST)):
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   compare_arguments(first, second, built.data_dir))
        assert result.exit_code == 2
        assert result.stderr == vendor_failure('compare-runs', 'validation', first, second)
        assert result.stdout == ''


def test_unequal_compare_exits_1(cli_runner, data_directory, monkeypatch):
    compared = {'equal': False, 'report_equal': False, 'tables': {},
                'trust_established': False}
    monkeypatch.setattr(vendor_link_bundle, 'compare_runs', lambda first, second: compared)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               compare_arguments('run_1', 'run_2', data_directory))
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert result.stderr == ''


@pytest.mark.parametrize('tamper, differing', [
    (tamper_table, {'report_equal': True}),
    (tamper_report, {'report_equal': False}),
], ids=['table', 'report'])
def test_real_unequal_bundles_exit_1_and_print_the_comparison(cli_runner, built, tmp_path,
                                                              tamper, differing):
    data_dir = copy_of_built(built, tmp_path)
    tamper(run_path(data_dir, REPLAY))
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               compare_arguments(FIRST, REPLAY, data_dir))
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stderr == ''
    printed = json.loads(result.stdout)
    assert result.stdout == json.dumps(printed, sort_keys=True) + '\n'
    assert printed['equal'] is False
    assert printed['report_equal'] is differing['report_equal']
    assert printed['trust_established'] is False


def test_offline_commands_open_no_connection_and_read_no_key(cli_runner, seeded, tmp_path,
                                                             monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline command attempted external access')

    def no_client(*args, **kwargs):
        raise AssertionError('HTTP client constructed')

    forbid_external_access(monkeypatch)
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', no_client)
    monkeypatch.setattr(sam_access, 'read_credential', forbidden)
    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    monkeypatch.setattr(code_build, 'build', forbidden)
    for module in (usaspending_raw, sam_raw):
        monkeypatch.setattr(module, 'acquire', forbidden)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    before = dict(os.environ)
    data_dir = tmp_path / 'data'
    shutil.copytree(seeded.pristine / 'derived', data_dir / 'derived')
    arguments = [
        ['import-subawards', str(year), str(
            seeded.originals / f'FY{year}_Contracts_Subawards_fixture.zip'),
         '--snapshot', SNAPSHOT_TEXT, '--data-dir', str(data_dir)] for year in REPORTS]
    arguments.append(['import-sam-extract', str(seeded.originals / extract_name(SAM_MONTH)),
                      '--month', SAM_MONTH, '--data-dir', str(data_dir)])
    arguments += [build_arguments(FIRST, data_dir, seeded.codes),
                  build_arguments(REPLAY, data_dir, seeded.codes)]
    results = [cli_runner.invoke(usaspending_vendor_links.app, line) for line in arguments]
    for line, result in zip(arguments, results, strict=True):
        assert result.exit_code == 0, (line[0], result.output)
        assert result.stderr == ''
    pins = {json.loads(result.stdout)['run_id']: json.loads(result.stdout)['outputs_sha256']
            for result in results[-2:]}
    last = [cli_runner.invoke(usaspending_vendor_links.app, line) for line in (
        verify_arguments(FIRST, data_dir, pins[FIRST]),
        verify_arguments(REPLAY, data_dir, pins[REPLAY]),
        compare_arguments(FIRST, REPLAY, data_dir))]
    for result in last:
        assert result.exit_code == 0, result.output
        assert result.stderr == ''
    assert json.loads(last[2].stdout)['equal'] is True
    assert FAKE_KEY not in ''.join(result.output for result in [*results, *last])
    assert dict(os.environ) == before


def test_new_constants_and_the_failure_path_follow_the_run_directory(tmp_path):
    assert usaspending_vendor_links.VENDOR_LINKS == VENDOR_LINKS
    assert vendor_link_bundle.run_directory(tmp_path, 'run_9').relative_to(
        tmp_path).as_posix() == f'{VENDOR_LINKS}/run_9'


def test_command_module_loads_no_dotenv_ipumspy_or_census_access():
    loaded = subprocess_modules('embedding_data.usaspending_vendor_links', prefix=None)
    assert not {'dotenv', 'ipumspy', 'embedding_data.ipums_census_access'} & loaded


def test_importing_the_command_module_loads_the_bundle_module():
    # The unfiltered list holds third-party modules, so a missing name below means absent.
    loaded = subprocess_modules('embedding_data.usaspending_vendor_links', prefix=None)
    assert {'polars', 'embedding_data.vendor_link_bundle'} <= loaded


def test_software_files_equal_the_command_import_closure():
    closure = {module_file(m)
               for m in subprocess_modules('embedding_data.usaspending_vendor_links')}
    assert set(vendor_link_bundle.SOFTWARE_FILES) == closure | {
        'src/embedding_data/usaspending_subaward_headers.json',
        'src/embedding_data/sam_extract_layout.json', 'pyproject.toml', 'uv.lock'}
