'''Command-line entry point for the embedding-data extract scripts.'''

import typer

from embedding_data import acs_benchmark_extract, cps_benchmark_extract, osha_benchmark_download

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
