'''The fixture chain from raw delivery to the wage microdata bundle, through the real commands.'''

import json

import polars as pl
from acs_target_fixtures import install_counted_guards
from acs_wage_fixtures import CONTROLS, DUPLICATED_CONTROL, wage_mapping

from embedding_data import manifest
from embedding_data.acs_wage_microdata import app

# AGE marker to the expected values of its control row. AGE 48 has no wage and is absent.
# AGE 49 also holds the highest 2024 wage of its state, so its top-code flag is not asserted.
EXPECTED_CONTROLS = {
    41: {'flag_headline': True},
    42: {'flag_any_allocated': True, 'flag_headline': False},
    43: {'flag_any_allocated': True, 'flag_headline': True},
    44: {'flag_full_time_full_year': False, 'flag_headline': False},
    45: {'flag_full_time_full_year': False, 'flag_headline': False},
    46: {'flag_wage_salary': False, 'flag_headline': False},
    47: {'flag_wage_salary': False, 'flag_headline': False},
    48: None,
    49: {'YEAR': 2024, 'industry_node_code': '811192', 'flag_headline': True},
    50: {'flag_incwage_topcoded': True, 'flag_headline': True},
}


def digests(data_dir):
    '''Every path under the data directory outside the wage runs: a file's SHA-256, else None.'''
    runs = data_dir / 'derived' / 'acs' / 'wage-microdata'
    return {
        path.relative_to(data_dir).as_posix():
            manifest.sha256_file(path) if path.is_file() else None
        for path in sorted(data_dir.rglob('*')) if not path.is_relative_to(runs)
    }


def invoke(runner, data_dir, command, *arguments):
    '''Run one command through the app. Return its one printed JSON line, parsed.'''
    result = runner.invoke(app, [command, *arguments, '--data-dir', str(data_dir)])
    assert result.exit_code == 0, (command, result.output)
    assert result.stderr == ''
    assert result.stdout.count('\n') == 1
    value = json.loads(result.stdout)
    assert result.stdout == json.dumps(value, sort_keys=True) + '\n'
    return value


def build_arguments(chain, run_id):
    return [run_id, '--mapping-run', chain['mapping_run'], '--mapping-outputs-sha256',
            chain['mapping_outputs_sha256'], '--codes-run', chain['codes_run'],
            '--codes-outputs-sha256', chain['codes_outputs_sha256']]


def test_raw_to_wage_microdata_is_offline_verified_and_replayable(
        cli_runner, tmp_path, monkeypatch):
    chain = wage_mapping(tmp_path, monkeypatch)  # raw, converter, Stages 4/5/7, then Stage 8
    data_dir = chain['data_dir']
    runs = data_dir / 'derived' / 'acs' / 'wage-microdata'
    before = digests(data_dir)
    assert {'raw/manifest.jsonl', 'derived/acs/mapping/mapping/acs_core_canonical.parquet'
            } <= set(before)
    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    install_counted_guards(monkeypatch, counts)

    first = invoke(cli_runner, data_dir, 'build', *build_arguments(chain, 'first'))
    verified = invoke(cli_runner, data_dir, 'verify', 'first', '--outputs-sha256',
                      first['outputs_sha256'])
    replay = invoke(cli_runner, data_dir, 'build', *build_arguments(chain, 'replay'))
    replay_verified = invoke(cli_runner, data_dir, 'verify', 'replay', '--outputs-sha256',
                             replay['outputs_sha256'])
    compared = invoke(cli_runner, data_dir, 'compare-runs', 'first', 'replay')

    first_directory = runs / 'first'
    persons = pl.read_parquet(first_directory / 'acs_wage_persons.parquet')
    report = json.loads((first_directory / 'report.json').read_text())

    assert first['directory'] == str(first_directory)
    assert replay['directory'] == str(runs / 'replay')
    assert verified['run_id'] == 'first'
    assert verified['outputs_sha256'] == first['outputs_sha256']
    assert replay_verified['run_id'] == 'replay'
    assert replay_verified['outputs_sha256'] == replay['outputs_sha256']
    assert verified['mapping_run'] == chain['mapping_run']
    assert verified['codes_run'] == chain['codes_run']
    assert verified['rows'] == persons.height
    assert 0 < persons['flag_headline'].sum() < persons.height
    assert verified['headline_rows'] == persons['flag_headline'].sum()
    assert compared == {
        'equal': True,
        'table': {'schema_equal': True, 'values_equal': True, 'first_rows': persons.height,
                  'second_rows': persons.height},
        'report_equal': True,
        'trust_established': False,
    }
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}
    assert sorted(path.name for path in runs.iterdir()) == ['first', 'replay']
    assert digests(data_dir) == before  # spec item 7, in the fixture

    assert set(EXPECTED_CONTROLS) == set(CONTROLS)
    for age, expected in EXPECTED_CONTROLS.items():
        rows = persons.filter(pl.col('AGE') == age)
        if expected is None:
            assert rows.height == 0, age
        else:
            copies = 2 if age == DUPLICATED_CONTROL else 1
            assert rows.select(list(expected)).to_dicts() == [expected] * copies, age
    assert report['rows']['total'] == persons.height
    assert report['funnel'][-1]['step'] == 'headline'
    assert report['funnel'][-1]['total'] == persons['flag_headline'].sum()
