import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    with patch.dict(os.environ):
        os.environ.pop('IPUMS_API_KEY', None)
        os.environ.pop('PYTHON_DOTENV_DISABLED', None)
        yield CliRunner()


@pytest.fixture
def output_directory(tmp_path):
    return tmp_path / 'downloads'


@pytest.fixture
def dotenv_path(tmp_path):
    return tmp_path / '.env'
