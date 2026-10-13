from pathlib import Path
from tempfile import TemporaryDirectory

def before_scenario(context, scenario):
    temporary_directory = TemporaryDirectory()
    context.add_cleanup(temporary_directory.cleanup)
    context.data_directory = Path(temporary_directory.name) / 'data'
    context.dotenv_path = Path(temporary_directory.name) / '.env'
