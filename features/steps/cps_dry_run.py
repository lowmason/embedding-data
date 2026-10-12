import json
import os
from unittest.mock import patch

from behave import given, then, when
from typer.testing import CliRunner

from embedding_data import cps_benchmark_extract as benchmark


@given('this CPS sample catalog:')
def set_sample_catalog(context):
    context.catalog = {row['sample_id']: row['description'] for row in context.table}


@when('I preview the default CPS extracts')
@when('I preview monthly CPS extracts starting at "{start}"')
def preview_extracts(context, start=None):
    arguments = [] if start is None else ['monthly', '--start', start]
    arguments.extend(['--dry-run', '--out', str(context.output_directory)])
    with (
        patch.dict(os.environ, {'IPUMS_API_KEY': 'behave-test-key'}),
        patch.object(benchmark, 'DOTENV_PATH', context.dotenv_path),
        patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        context.client = client_factory.return_value
        context.client.get_all_sample_info.return_value = context.catalog
        context.client.submit_extract.side_effect = AssertionError('A dry-run must not submit extracts')
        context.client.wait_for_extract.side_effect = AssertionError('A dry-run must not wait for extracts')
        context.client.download_extract.side_effect = AssertionError('A dry-run must not download extracts')
        context.result = CliRunner().invoke(benchmark.app, arguments)

    assert context.result.exit_code == 0, context.result.output or repr(context.result.exception)


@then('the "{name}" definition contains these samples in order:')
def check_definition_samples(context, name):
    definition_path = context.output_directory / name / 'extract.json'
    assert definition_path.exists(), f'Missing definition: {definition_path}'
    definition = json.loads(definition_path.read_text())
    expected_samples = [row['sample_id'] for row in context.table]

    assert list(definition['samples']) == expected_samples, definition['samples']
    assert definition['collection'] == 'cps', definition['collection']
    assert definition['dataQualityFlags'] is True


@then('no "{name}" definition is written')
def check_missing_definition(context, name):
    definition_path = context.output_directory / name / 'extract.json'

    assert not definition_path.exists(), f'Unexpected definition: {definition_path}'


@then('no extracts are submitted or downloaded')
def check_no_extract_requests(context):
    context.client.submit_extract.assert_not_called()
    context.client.wait_for_extract.assert_not_called()
    context.client.download_extract.assert_not_called()
    assert list(context.output_directory.rglob('*.csv.gz')) == []
    assert list(context.output_directory.rglob('*.parquet')) == []
