'''Acquire, import and verify immutable registered classification originals.'''

import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import ita_references, manifest, paths
from embedding_data.classification_tables import naics_tables, soc_tables
from embedding_data.filing_rules import parse_rule, rule_tables
from embedding_data.naics_relationships import parse_concordance, validate_relationships
from embedding_data.osha_benchmark_download import USER_AGENT, download

@dataclass(frozen=True)
class Reference:
    kind: str
    url: str
    relative: str
    family: str
    vintage: int | None = None
    target: int | None = None
    expected: tuple[int, int] | int | None = None


REGISTRY = {
    f'naics_{v}': Reference(
        f'naics_{v}', url, 'naics/' + url.rsplit('/', 1)[1], 'naics', v, expected=counts
    )
    for v, url, counts in [
        (v, ita_references.TITLE_FILES[v], counts)
        for v, counts in [(2012, (2209, 1065)), (2017, (2196, 1057)), (2022, (2125, 1012))]
    ]
}
REGISTRY['naics_2007'] = Reference(
    'naics_2007',
    'https://www.census.gov/naics/reference_files_tools/2007/naics07.xls',
    'naics/naics07.xls',
    'naics',
    2007,
    expected=(2328, 1175),
)
REGISTRY['naics_2002'] = Reference(
    'naics_2002',
    'https://www.census.gov/naics/reference_files_tools/2002/naics_2_6_02.txt',
    'naics/naics_2_6_02.txt',
    'naics_text',
    2002,
    expected=(2341, 1179),
)
for source, target, suffix in [
    (2002, 2007, 'xls'),
    (2007, 2012, 'xls'),
    (2012, 2017, 'xlsx'),
    (2017, 2022, 'xlsx'),
]:
    filename = f'{source}_to_{target}_NAICS.{suffix}'
    kind = f'concordance_{source}_{target}'
    REGISTRY[kind] = Reference(
        kind,
        'https://www.census.gov/naics/concordances/' + filename,
        'naics/' + filename,
        'concordance',
        source,
        target,
    )
REGISTRY['soc_2018'] = Reference(
    'soc_2018',
    'https://www.bls.gov/soc/2018/soc_structure_2018.xlsx',
    'soc/soc_structure_2018.xlsx',
    'soc',
    2018,
    expected=(1447, 867),
)
for kind, issue, document, count in [
    ('designated_2012', '2016-05-12', '2016-10443', 66),
    ('designated_2017', '2023-07-21', '2023-15091', 65),
    ('partially_exempt_2007', '2014-09-18', '2014-21514', 82),
]:
    REGISTRY[kind] = Reference(
        kind,
        f'https://www.govinfo.gov/content/pkg/FR-{issue}/html/{document}.htm',
        f'filing-rules/{document}.htm',
        'rule',
        expected=count,
    )


def reference_path(data_dir, reference):
    return ita_references.reference_path(data_dir, reference.relative)


def parse_naics_text(text, vintage):
    import re

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = f'Code    {vintage} NAICS Title'
    if lines.count(heading) != 1:
        raise ValueError('missing or ambiguous NAICS text header')
    rows = []
    for line in lines[lines.index(heading) + 1 :]:
        match = re.fullmatch(r'([0-9]{2,6}|31-33|44-45|48-49)[ \t]+(\S.*)', line)
        if not match:
            raise ValueError('malformed NAICS text code/title row')
        rows.append((vintage, match[1], match[2]))
    return pl.DataFrame(
        rows, schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String}, orient='row'
    )


def parse_reference(file, reference):
    if reference.family == 'rule':
        return parse_rule(
            file.read_text(encoding='utf-8'), reference.kind, expected_count=reference.expected
        )
    if reference.family == 'naics_text':
        titles = parse_naics_text(file.read_text(encoding='utf-8'), reference.vintage)
        nodes, edges, graph_paths = naics_tables(titles, reference.vintage)
        actual = (nodes.height, nodes.filter(pl.col('level').eq('national_industry')).height)
        if actual != reference.expected:
            raise ValueError(f'{reference.kind}: structure counts changed: {actual}')
        return nodes
    raw = pl.read_excel(file, has_header=False, read_options={'dtypes': 'string'})
    if reference.family == 'concordance':
        return parse_concordance(
            raw, reference.vintage, reference.target, 'references/' + reference.relative
        )
    if reference.family == 'naics':
        titles = ita_references.parse_titles(raw, reference.vintage)
        nodes, edges, graph_paths = naics_tables(titles, reference.vintage)
        finest = 'national_industry'
    elif reference.family == 'soc':
        nodes, edges, graph_paths = soc_tables(raw)
        finest = 'detailed'
    else:
        raise ValueError('unsupported reference family')
    actual = (nodes.height, nodes.filter(pl.col('level').eq(finest)).height)
    if actual != reference.expected:
        raise ValueError(f'{reference.kind}: structure counts changed: {actual}')
    return nodes


def preflight(data_dir, registry):
    result = {}
    for kind, reference in registry.items():
        destination = reference_path(data_dir, reference)
        if destination.is_symlink() or destination.with_name(destination.name + '.part').exists():
            raise ValueError(f'{kind}: symlink or interrupted reference')
        result[kind] = ita_references.existing_reference(data_dir, destination)
    return result


def publish_original(data_dir, reference, original, *, imported):
    destination = reference_path(data_dir, reference)
    if ita_references.existing_reference(data_dir, destination):
        if manifest.sha256_file(original) != manifest.sha256_file(destination):
            raise ValueError('registered original already has different bytes')
        return destination
    original_hash = manifest.sha256_file(original)
    parse_reference(original, reference)
    citation = manifest.describe_file(
        original,
        original.parent,
        retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.url,
        proxies=('retrieved_at',) if imported else (),
    )
    if citation.sha256 != original_hash:
        raise ValueError('SHA-256 changed while validating original')
    citation = replace(
        citation, path=destination.relative_to(paths.manifest_path(data_dir).parent).as_posix()
    )
    manifest.check_appendable(paths.manifest_path(data_dir), [citation])
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + '.part')
    if partial.exists():
        raise ValueError('interrupted reference already exists')
    try:
        with partial.open('xb') as output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        if manifest.sha256_file(partial) != citation.sha256:
            raise ValueError('SHA-256 changed while copying original')
        # Re-check immediately before the publish boundary; never overwrite a destination.
        if destination.exists() or destination.is_symlink():
            raise ValueError('reference destination appeared during import')
        # A hard link publishes atomically and refuses a competing destination.
        os.link(partial, destination)
        manifest.append_entries(paths.manifest_path(data_dir), [citation])
    finally:
        partial.unlink(missing_ok=True)
    return destination


def import_reference(data_dir, kind, original, *, registry=REGISTRY):
    if kind not in registry:
        raise ValueError('unknown registered reference identity')
    preflight(data_dir, {kind: registry[kind]})
    return publish_original(data_dir, registry[kind], original, imported=True)


def acquire(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    missing_bls = any(
        not existing[k] and r.url.startswith('https://www.bls.gov/') for k, r in registry.items()
    )
    contact = os.environ.get('BLS_CONTACT_EMAIL', '').strip()
    if missing_bls and not contact:
        raise ValueError('set BLS_CONTACT_EMAIL or import-reference soc_2018 ORIGINAL')
    acquired = []
    with httpx.Client(
        http2=True, follow_redirects=True, timeout=120, headers={'User-Agent': USER_AGENT}
    ) as client:
        for kind, reference in registry.items():
            if existing[kind]:
                acquired.append(reference_path(data_dir, reference))
                continue
            headers = (
                {'User-Agent': f'embedding-data-reference/0.1 (contact: {contact})'}
                if (reference.url.startswith('https://www.bls.gov/'))
                else {'User-Agent': USER_AGENT}
            )
            client.headers.update(headers)
            with tempfile.TemporaryDirectory() as temporary:
                original = Path(temporary) / Path(reference.relative).name
                download(client, reference.url, original)
                acquired.append(publish_original(data_dir, reference, original, imported=False))
    return acquired


def read_references(data_dir, *, registry=REGISTRY):
    parsed = {}
    for kind, reference in registry.items():
        file = reference_path(data_dir, reference)
        manifest.entry_for(paths.manifest_path(data_dir), file)
        parsed[kind] = parse_reference(file, reference)
    structures = pl.concat([parsed[f'naics_{v}'] for v in (2002, 2007, 2012, 2017, 2022)])
    relations = pl.concat(
        [
            parsed[f'concordance_{a}_{b}']
            for a, b in [(2002, 2007), (2007, 2012), (2012, 2017), (2017, 2022)]
        ]
    )
    validate_relationships(relations, structures)
    identities = ('designated_2012', 'designated_2017', 'partially_exempt_2007')
    rules = rule_tables(
        {k: parsed[k] for k in identities},
        structures,
        relations,
        {k: 'references/' + registry[k].relative for k in identities},
    )
    return {
        'structures': structures.sort('vintage', 'node_id'),
        'soc_nodes': parsed['soc_2018'],
        'relations': relations.sort(
            'source_vintage', 'target_vintage', 'source_code', 'target_code'
        ),
        'rule_groups': pl.DataFrame(
            [
                (k, len(parsed[k]))
                for k in ('designated_2012', 'designated_2017', 'partially_exempt_2007')
            ],
            schema={'rule_id': pl.String, 'listed_groups': pl.Int64},
            orient='row',
        ).sort('rule_id'),
        'rules': rules['rules'],
        'rule_labels': rules['labels'],
        'rule_membership': rules['membership'],
    }
