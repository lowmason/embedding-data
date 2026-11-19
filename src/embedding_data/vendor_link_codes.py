'''Select the NAICS 2022 national-industry node IDs of the pinned Stage 4 codes bundle.

Stage 14 reads `naics_nodes.parquet` only. The selector authenticates the detached pin,
verifies the bundle inventory with `target_io.verify_inventory`, checks the schema version
and the run identity, and then reads that one table. It does not call Stage 10's
`select_codes`, which also re-checks the ITA source summary, and it imports no upstream
builder. So the table names, the node schema and the schema version are literals here, and
the tests compare them with the Stage 4 constants.
'''

import json
import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data import manifest, target_io

RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
CODES_SCHEMA_VERSION = 'codes-ita-v1'
CODE_TABLES = (
    'naics_nodes', 'naics_edges', 'soc_nodes', 'soc_edges', 'naics_native_nodes',
    'naics_concordance', 'filing_rules', 'code_paths', 'filing_rule_labels',
    'filing_rule_membership', 'ita_naics_lookup', 'ita_300a_canonical')
INVENTORY_NAMES = {name + '.parquet' for name in CODE_TABLES} | {'inputs.json', 'report.json'}
NODE_SCHEMA = {'node_id': pl.String, 'system': pl.String, 'vintage': pl.Int64,
               'level': pl.String, 'code': pl.String, 'title': pl.String}
NODE_PREFIX = 'naics:2022:national_industry:'
NODE_FILE = 'naics_nodes.parquet'


@dataclass(frozen=True)
class SelectedNodes:
    data_dir: Path
    codes_run: str
    codes_outputs_sha256: str
    outputs: dict
    node_ids: frozenset[str]

    def verify(self) -> None:
        '''Reselect the pinned bundle and refuse any difference from this selection.'''
        try:
            current = select_nodes(self.data_dir, self.codes_run,
                                   codes_outputs_sha256=self.codes_outputs_sha256)
        except (ValueError, OSError) as error:
            raise ValueError('selected codes inputs changed') from error
        if current != self:
            raise ValueError('selected codes inputs changed')

    def provenance(self) -> dict:
        return {'run_id': self.codes_run, 'outputs_sha256': self.codes_outputs_sha256,
                'outputs': self.outputs}


def _read_object(directory: Path, name: str) -> dict:
    value = json.loads(target_io.relative_file(directory, name).read_text())
    if not isinstance(value, dict):
        raise ValueError(f'{name}: not a JSON object')
    return value


def _check_versions(inputs: dict, report: dict, codes_run: str) -> None:
    if inputs.get('schema_version') != CODES_SCHEMA_VERSION:
        raise ValueError('inputs.json schema version differs')
    if report.get('schema_version') != CODES_SCHEMA_VERSION:
        raise ValueError('report.json schema version differs')
    if inputs.get('run_id') != codes_run:
        raise ValueError('inputs.json run identity differs')


def _node_ids(directory: Path, report: dict) -> frozenset[str]:
    nodes = pl.scan_parquet(target_io.relative_file(directory, NODE_FILE))
    schema = nodes.collect_schema()
    if list(schema.items()) != list(NODE_SCHEMA.items()):
        raise ValueError(f'{NODE_FILE}: ordered schema differs')
    tables = report.get('tables')
    recorded = tables.get(NODE_FILE) if isinstance(tables, dict) else None
    if (not isinstance(recorded, dict)
            or recorded.get('rows') != nodes.select(pl.len()).collect().item()
            or recorded.get('schema') != {name: str(dtype) for name, dtype in schema.items()}):
        raise ValueError(f'{NODE_FILE}: rows or schema differ from the report')
    ids = (nodes.filter(pl.col('system').eq('naics'), pl.col('vintage').eq(2022),
                        pl.col('level').eq('national_industry'))
           .select('node_id').collect().to_series().to_list())
    if not all(isinstance(node_id, str) and node_id.startswith(NODE_PREFIX)
               for node_id in ids):
        raise ValueError(f'{NODE_FILE}: a national-industry node ID lacks the 2022 prefix')
    if len(set(ids)) != len(ids):
        raise ValueError(f'{NODE_FILE}: a national-industry node ID repeats')
    return frozenset(ids)


def select_nodes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedNodes:
    '''Authenticate the pinned codes bundle and read its NAICS 2022 national-industry nodes.'''
    if not RUN_ID.fullmatch(codes_run):
        raise ValueError('unsafe selected run ID')
    if not PIN.fullmatch(codes_outputs_sha256):
        raise ValueError('invalid detached checksum')
    directory = target_io.relative_file(data_dir, f'derived/codes/{codes_run}')
    if manifest.sha256_file(target_io.relative_file(directory, 'outputs.json')) != (
            codes_outputs_sha256):
        raise ValueError('detached inventory checksum differs')
    outputs = _read_object(directory, 'outputs.json')
    target_io.verify_inventory(directory, outputs, INVENTORY_NAMES)
    inputs = _read_object(directory, 'inputs.json')
    report = _read_object(directory, 'report.json')
    _check_versions(inputs, report, codes_run)
    return SelectedNodes(data_dir, codes_run, codes_outputs_sha256, outputs,
                         _node_ids(directory, report))
