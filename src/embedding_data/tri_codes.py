'''Select the pinned Stage 4 NAICS 2022 national-industry nodes for the TRI parent links.

Stage 5 needs one classification table, `naics_nodes.parquet`. This selector authenticates
the detached `outputs.json` pin, verifies the bundle inventory, checks the schema version
and the run identity, and reads that one table. It never calls Stage 10's `select_codes`,
which also re-checks the ITA source summary. It reads no raw citation, no source summary
and no canonical table.

The constants repeat Stage 4's on purpose, so that importing this module stays light.
`tests/test_tri_codes.py` ties each one to its Stage 4 source.
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
CODE_TABLES = ('naics_nodes', 'naics_edges', 'soc_nodes', 'soc_edges', 'naics_native_nodes',
               'naics_concordance', 'filing_rules', 'code_paths', 'filing_rule_labels',
               'filing_rule_membership', 'ita_naics_lookup', 'ita_300a_canonical')
INVENTORY_NAMES = {name + '.parquet' for name in CODE_TABLES} | {'inputs.json', 'report.json'}
NODE_SCHEMA = {'node_id': pl.String, 'system': pl.String, 'vintage': pl.Int64,
               'level': pl.String, 'code': pl.String, 'title': pl.String}
NODE_PREFIX = 'naics:2022:national_industry:'
NODES_FILE = 'naics_nodes.parquet'


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
            raise ValueError('selected codes nodes changed') from error
        if current != self:
            raise ValueError('selected codes nodes changed')

    def provenance(self) -> dict:
        '''The pinned run, its detached checksum and the inventory that the checksum covers.'''
        return {'run_id': self.codes_run, 'outputs_sha256': self.codes_outputs_sha256,
                'outputs': self.outputs}


def _object(value: object, label: str, *required: str) -> dict:
    if not isinstance(value, dict) or not set(required) <= set(value):
        raise ValueError(f'{label}: not an object with the required fields')
    return value


def _read_object(file: Path, *required: str) -> dict:
    return _object(json.loads(file.read_text()), file.name, *required)


def select_nodes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedNodes:
    '''Authenticate the pinned codes bundle and read its NAICS 2022 national-industry IDs.'''
    if not RUN_ID.fullmatch(codes_run):
        raise ValueError('unsafe selected run ID')
    if not PIN.fullmatch(codes_outputs_sha256):
        raise ValueError('invalid detached checksum')
    directory = target_io.relative_file(data_dir, f'derived/codes/{codes_run}')
    outputs_file = target_io.relative_file(directory, 'outputs.json')
    if manifest.sha256_file(outputs_file) != codes_outputs_sha256:
        raise ValueError('detached inventory checksum differs')
    outputs = json.loads(outputs_file.read_text())
    target_io.verify_inventory(directory, outputs, INVENTORY_NAMES)
    inputs = _read_object(directory / 'inputs.json', 'schema_version', 'run_id')
    report = _read_object(directory / 'report.json', 'schema_version', 'tables')
    if inputs['schema_version'] != CODES_SCHEMA_VERSION:
        raise ValueError('inputs.json: schema version differs')
    if report['schema_version'] != CODES_SCHEMA_VERSION:
        raise ValueError('report.json: schema version differs')
    if inputs['run_id'] != codes_run:
        raise ValueError('inputs.json: run identity differs')
    tables = _object(report['tables'], 'report.json tables', NODES_FILE)
    recorded = _object(tables[NODES_FILE], f'report.json {NODES_FILE}', 'rows', 'schema')
    frame = pl.scan_parquet(target_io.relative_file(directory, NODES_FILE))
    schema = frame.collect_schema()
    if list(schema.items()) != list(NODE_SCHEMA.items()):
        raise ValueError('naics_nodes: ordered schema differs')
    if (recorded['rows'] != frame.select(pl.len()).collect().item()
            or recorded['schema'] != {name: str(dtype) for name, dtype in schema.items()}):
        raise ValueError('naics_nodes: rows or schema differ from report.json')
    ids = (frame
           .filter((pl.col('system') == 'naics') & (pl.col('vintage') == 2022)
                   & (pl.col('level') == 'national_industry'))
           .select('node_id').collect().to_series().to_list())
    if not all(node_id is not None and node_id.startswith(NODE_PREFIX) for node_id in ids):
        raise ValueError('naics_nodes: a node ID lacks the prefix')
    if len(set(ids)) != len(ids):
        raise ValueError('naics_nodes: a node ID repeats')
    return SelectedNodes(data_dir, codes_run, codes_outputs_sha256, outputs, frozenset(ids))
