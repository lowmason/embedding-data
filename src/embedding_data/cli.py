'''Command-line entry point for the embedding-data extract scripts.'''

import typer

from embedding_data import (
    acs_benchmark_extract,
    codes_cli,
    cps_benchmark_extract,
    geography_cli,
    manifest_audit,
    osha_benchmark_download,
    targets_cli,
)

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


# The callback supplies the top-level help and keeps the app a command group
# even with one command, which Typer would otherwise collapse into that command.
@app.callback()
def extracts() -> None:
    '''Download IPUMS extracts and OSHA ITA data for the embedding benchmark.'''


app.command('acs', help=acs_benchmark_extract.__doc__.splitlines()[0])(acs_benchmark_extract.main)
app.command('cps', help=cps_benchmark_extract.__doc__.splitlines()[0])(cps_benchmark_extract.main)
app.command('osha', help=osha_benchmark_download.__doc__.splitlines()[0])(
    osha_benchmark_download.main
)

app.command('audit', help=manifest_audit.__doc__.splitlines()[0])(manifest_audit.main)

app.add_typer(codes_cli.app, name='codes')
app.add_typer(geography_cli.app, name='geography')
app.add_typer(targets_cli.app, name='targets')
