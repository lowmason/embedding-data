import re
from datetime import date
from html.parser import HTMLParser
from itertools import product

import polars as pl

from embedding_data.classification_tables import naics_tables
from embedding_data.naics_relationships import candidates

RULES = {
    'designated_2012': (2012, date(2017, 1, 1), date(2023, 12, 31), 'E', 66),
    'designated_2017': (2017, date(2024, 1, 1), None, 'E', 65),
    'partially_exempt_2007': (2007, date(2015, 1, 1), None, 'B', 82),
}
RULE_SCHEMA = {
    'rule_id': pl.String,
    'vintage': pl.Int64,
    'code': pl.String,
    'effective_from': pl.Date,
    'effective_to': pl.Date,
    'source_file': pl.String,
}


class OriginalText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def parse_rule(text, rule_id, *, expected_count=None):
    if rule_id not in RULES:
        raise ValueError('unknown rule identity')
    reader = OriginalText()
    reader.feed(text)
    original = ''.join(reader.parts)
    part, count = RULES[rule_id][3:]
    heading = f'Appendix A to Subpart {part} of Part 1904'
    # The final enacted appendix follows the discussions and proposed tables.
    start = original.rfind(heading)
    challenge = re.search(r'<title>[^<]*(?:request access|access denied)', text, re.IGNORECASE)
    if start < 0 or challenge:
        raise ValueError('original final appendix missing or challenge HTML')
    tail = original[start + len(heading) :]
    next_appendix = re.search(r'^Appendix [A-Z] to Subpart [A-Z]', tail, re.MULTILINE)
    if next_appendix:
        tail = tail[: next_appendix.start()]
    dotted_lines = [line for line in tail.splitlines() if re.match(r'^[^ \t].*\.{2,}', line)]
    entries = [
        re.fullmatch(r'([0-9]{2,6}|31-33|44-45|48-49)\.{2,}[ \t]+(\S.*)', line)
        for line in dotted_lines
    ]
    if any(match is None for match in entries):
        raise ValueError('malformed or untitled final-table row')
    codes = [match[1] for match in entries]
    if len(codes) != (count if expected_count is None else expected_count):
        raise ValueError('filing appendix count changed')
    if len(codes) != len(set(codes)):
        raise ValueError('duplicate listed rule code')
    return sorted(codes)


def expand_rule(codes, rule_id, structures, source_file):
    vintage, start, end, part, count = RULES[rule_id]
    native = structures.filter(pl.col('vintage').eq(vintage))
    known = set(native['code'].to_list())
    if not codes or len(codes) != len(set(codes)) or not set(codes).issubset(known):
        raise ValueError('invalid or duplicate listed rule node')
    # Reconstruct paths from validated native parentage, not cross-vintage prefix matching.
    titles = native.select('vintage', 'code', 'title')
    nodes, edges, paths = naics_tables(titles, vintage)
    listed_ids = set(native.filter(pl.col('code').is_in(codes))['node_id'].to_list())
    leaves = native.filter(pl.col('level').eq('national_industry'))
    path_of = dict(paths.iter_rows())
    members = [
        r['code']
        for r in leaves.iter_rows(named=True)
        if listed_ids.intersection(path_of[r['node_id']])
    ]
    if not members:
        raise ValueError('empty expanded rule')
    return pl.DataFrame(
        [(rule_id, vintage, code, start, end, source_file) for code in sorted(members)],
        schema=RULE_SCHEMA,
        orient='row',
    )


def validate_rules(rules, structures):
    if rules.schema != RULE_SCHEMA or rules.select('rule_id', 'code').is_duplicated().any():
        raise ValueError('incompatible or duplicate rule membership')
    if any(rules[c].null_count() for c in rules.columns if c != 'effective_to'):
        raise ValueError('null required rule field')
    if set(rules['rule_id'].to_list()) != set(RULES):
        raise ValueError('missing or extra rule identity')
    for identity, (vintage, start, end, part, count) in RULES.items():
        group = rules.filter(pl.col('rule_id').eq(identity))
        leaves = set(
            structures.filter(
                pl.col('vintage').eq(vintage).and_(pl.col('level').eq('national_industry'))
            )['code'].to_list()
        )
        if (
            not set(group['code'].to_list()).issubset(leaves)
            or group.filter(
                pl.col('vintage')
                .ne(vintage)
                .or_(pl.col('effective_from').ne(start))
                .or_(pl.col('effective_to').ne_missing(pl.lit(end, dtype=pl.Date)))
            ).height
        ):
            raise ValueError('invalid rule vintage, period or endpoint')
        if group['source_file'].n_unique() != 1 or group['source_file'][0].strip() == '':
            raise ValueError('invalid rule provenance')


LEGACY_LABELS = {'5173': 2002, '5181': 2002}
LABEL_SCHEMA = {
    'rule_id': pl.String,
    'vintage': pl.Int64,
    'listed_code': pl.String,
    'label_vintage': pl.Int64,
    'flag_rule_label_legacy': pl.Boolean,
    'source_file': pl.String,
}
MEMBERSHIP_SCHEMA = {
    **RULE_SCHEMA,
    'membership_candidates': pl.List(pl.Boolean),
    'flag_rule_label_bridged': pl.Boolean,
}


def legacy_membership(whole, legacy_leaves, predecessors):
    result = {}
    for code, incoming in sorted(predecessors.items()):
        if not incoming:
            raise ValueError('missing legacy predecessor coverage')
        touched = bool(set(incoming).intersection(legacy_leaves))
        bits = {True} if code in whole else {p in legacy_leaves for p in incoming}
        result[code] = (sorted(bits), touched)
    return result


def rule_tables(listed, structures, relations, sources):
    label_rows, membership_rows = [], []
    for identity, codes in listed.items():
        vintage, start, end, part, count = RULES[identity]
        native = structures.filter(pl.col('vintage').eq(vintage))
        known = set(native['code'].to_list())
        exceptions = set(codes).difference(known)
        if identity != 'partially_exempt_2007' and exceptions:
            raise ValueError('invalid nonexemption listed rule node')
        if not exceptions.issubset(LEGACY_LABELS):
            raise ValueError('unsupported legacy rule label')
        valid = sorted(set(codes).intersection(known))
        if not codes or len(codes) != len(set(codes)):
            raise ValueError('empty or duplicate original rule labels')
        whole = (
            set(expand_rule(valid, identity, structures, sources[identity])['code'].to_list())
            if valid
            else set()
        )
        leaves = set(native.filter(pl.col('level').eq('national_industry'))['code'].to_list())
        bits = {code: ([code in whole], False) for code in leaves}
        for code in codes:
            label_rows.append(
                (
                    identity,
                    vintage,
                    code,
                    LEGACY_LABELS[code] if code in exceptions else vintage,
                    code in exceptions,
                    sources[identity],
                )
            )
        if exceptions:
            old = structures.filter(pl.col('vintage').eq(2002))
            if not exceptions.issubset(set(old['code'].to_list())):
                raise ValueError('legacy label missing from 2002 structure')
            old_nodes, old_edges, old_paths = naics_tables(
                old.select('vintage', 'code', 'title'), 2002
            )
            exception_ids = set(
                old.filter(pl.col('code').is_in(sorted(exceptions)))['node_id'].to_list()
            )
            paths_by_id = dict(old_paths.iter_rows())
            legacy_leaves = {
                code
                for identifier, code in old.filter(pl.col('level').eq('national_industry'))
                .select('node_id', 'code')
                .iter_rows()
                if exception_ids.intersection(paths_by_id[identifier])
            }
            bridge = relations.filter(
                pl.col('source_vintage').eq(2002).and_(pl.col('target_vintage').eq(2007))
            )
            predecessors = {}
            for source, target in bridge.select('source_code', 'target_code').iter_rows():
                predecessors.setdefault(target, set()).add(source)
            if set(predecessors) != leaves or not legacy_leaves.issubset(
                set(bridge['source_code'].to_list())
            ):
                raise ValueError('incomplete legacy bridge')
            bits = legacy_membership(whole, legacy_leaves, predecessors)
        for code in sorted(leaves):
            possibilities, touched = bits[code]
            membership_rows.append(
                (identity, vintage, code, start, end, sources[identity], possibilities, touched)
            )
    labels = pl.DataFrame(label_rows, schema=LABEL_SCHEMA, orient='row').sort(
        'rule_id', 'listed_code'
    )
    membership = pl.DataFrame(membership_rows, schema=MEMBERSHIP_SCHEMA, orient='row').sort(
        'rule_id', 'code'
    )
    definite = membership.filter(
        pl.col('membership_candidates')
        .list.len()
        .eq(1)
        .and_(pl.col('membership_candidates').list.contains(True))
    ).select(list(RULE_SCHEMA))
    validate_rules(definite, structures)
    validate_membership(membership, structures)
    return {'labels': labels, 'rules': definite, 'membership': membership}


def validate_membership(membership, structures):
    if (
        membership.schema != MEMBERSHIP_SCHEMA
        or membership.select('rule_id', 'code').is_duplicated().any()
    ):
        raise ValueError('incompatible or duplicate rule possibilities')
    if any(membership[c].null_count() for c in membership.columns if c != 'effective_to'):
        raise ValueError('null required membership field')
    if set(membership['rule_id'].to_list()) != set(RULES):
        raise ValueError('missing membership rule identity')
    for identity, (vintage, start, end, part, count) in RULES.items():
        group = membership.filter(pl.col('rule_id').eq(identity))
        leaves = set(
            structures.filter(
                pl.col('vintage').eq(vintage).and_(pl.col('level').eq('national_industry'))
            )['code'].to_list()
        )
        if set(group['code'].to_list()) != leaves:
            raise ValueError('incomplete rule membership coverage')
        if group.filter(
            pl.col('vintage')
            .ne(vintage)
            .or_(pl.col('effective_from').ne(start))
            .or_(pl.col('effective_to').ne_missing(pl.lit(end, dtype=pl.Date)))
        ).height:
            raise ValueError('invalid membership vintage or period')
        if group['source_file'].n_unique() != 1 or group['source_file'][0].strip() == '':
            raise ValueError('invalid membership provenance')
        for possibilities, touched in group.select(
            'membership_candidates', 'flag_rule_label_bridged'
        ).iter_rows():
            if possibilities not in ([False], [True], [False, True]):
                raise ValueError('invalid or empty membership possibility set')
            if len(possibilities) > 1 and (identity != 'partially_exempt_2007' or not touched):
                raise ValueError('unexplained reference membership ambiguity')


FILING_KEYS = {
    'year_filing_for': pl.Int64,
    'naics_code': pl.String,
    'naics_year': pl.Int64,
    'size_class': pl.Int64,
}
FILING_COLUMNS = {
    'filing_industry_status': pl.String,
    'flag_outside_filing_industry': pl.Boolean,
    'flag_outside_filing_rule': pl.Boolean,
    'flag_filing_rule_label_bridged': pl.Boolean,
    'flag_filing_reference_ambiguous': pl.Boolean,
}
FILING_LOOKUP_SCHEMA = {**FILING_KEYS, **FILING_COLUMNS}


def active_rule(rules, family, nominal_date):
    selected = rules.filter(
        pl.col('rule_id')
        .str.starts_with(family)
        .and_(pl.col('effective_from').le(nominal_date))
        .and_(pl.col('effective_to').is_null().or_(pl.col('effective_to').ge(nominal_date)))
    )
    identities = selected.select('rule_id', 'vintage').unique()
    if identities.height != 1:
        raise ValueError('unsupported or overlapping filing-rule period')
    rule_id, vintage = identities.row(0)
    return vintage, {
        code: (possibilities, touched)
        for code, possibilities, touched in selected.select(
            'code', 'membership_candidates', 'flag_rule_label_bridged'
        ).iter_rows()
    }


def evaluate(year, code, vintage, size_class, structures, relations, rules):
    if year is None:
        raise ValueError('missing filing year')
    if code is not None and not re.fullmatch(r'[0-9]{6}', code):
        raise ValueError('malformed source NAICS code')
    nominal = date(year + 1, 1, 1)
    designated_vintage, designated = active_rule(rules, 'designated_', nominal)
    exempt_vintage, exempt = active_rule(rules, 'partially_exempt_', nominal)
    leaves = {
        v: set(
            structures.filter(
                pl.col('vintage').eq(v).and_(pl.col('level').eq('national_industry'))
            )['code'].to_list()
        )
        for v in (2012, 2017, 2022)
    }
    if vintage is not None and vintage not in leaves:
        raise ValueError('incompatible native vintage')
    if size_class not in (None, 1, 2, 3):
        raise ValueError('unsupported harmonized size class')
    outside, bridged, reference_ambiguous = None, False, False
    if size_class is None:
        status = 'missing_size'
    elif size_class == 1:
        status = 'not_applicable_below_size'
    elif code is None:
        status = 'missing_code'
    elif vintage is not None and code not in leaves[vintage]:
        status = 'invalid_native_code'
    else:
        interpretations = (
            [vintage] if vintage is not None else [v for v in leaves if code in leaves[v]]
        )
        if not interpretations:
            status = 'unknown_vintage_unmapped'
        else:
            evaluations = set()
            for native in interpretations:
                exemption = candidates(relations, native, code, exempt_vintage)
                if not set(exemption).issubset(exempt):
                    raise ValueError('missing rule membership candidate')
                bridged = bridged or any(exempt[e][1] for e in exemption)
                reference_ambiguous = reference_ambiguous or any(
                    len(exempt[e][0]) > 1 for e in exemption
                )
                exempt_bits = {bit for e in exemption for bit in exempt[e][0]}
                if size_class == 3:
                    evaluations.update(exempt_bits)
                else:
                    designation = candidates(relations, native, code, designated_vintage)
                    if not set(designation).issubset(designated):
                        raise ValueError('missing designated membership candidate')
                    designated_bits = {bit for d in designation for bit in designated[d][0]}
                    evaluations.update(
                        not d or e for d, e in product(designated_bits, exempt_bits)
                    )
            if len(evaluations) == 1:
                status, outside = 'determinate', evaluations.pop()
            else:
                status = 'candidate_disagreement'
    return {
        'filing_industry_status': status,
        'flag_outside_filing_industry': outside,
        'flag_outside_filing_rule': True if size_class == 1 else outside,
        'flag_filing_rule_label_bridged': bridged,
        'flag_filing_reference_ambiguous': reference_ambiguous,
    }


def build_filing_lookup(keys, structures, relations, rules):
    if keys.schema != FILING_KEYS or keys.is_duplicated().any():
        raise ValueError('duplicate or incompatible filing lookup key')
    validate_membership(rules, structures)
    rows = []
    for row in keys.iter_rows(named=True):
        result = evaluate(
            row['year_filing_for'],
            row['naics_code'],
            row['naics_year'],
            row['size_class'],
            structures,
            relations,
            rules,
        )
        rows.append({**row, **result})
    return pl.DataFrame(rows, schema=FILING_LOOKUP_SCHEMA).sort(
        list(FILING_KEYS), nulls_last=False
    )


def add_filing_flags(source, lookup):
    names = source.collect_schema().names()
    if '_filing_row' in names or any(c in names for c in FILING_COLUMNS):
        raise ValueError('filing output/temporary column collision')
    if lookup.schema != FILING_LOOKUP_SCHEMA or lookup.select(*FILING_KEYS).is_duplicated().any():
        raise ValueError('duplicate or incompatible filing lookup')
    joined = source.with_row_index('_filing_row').join(
        lookup.lazy(),
        on=list(FILING_KEYS),
        how='left',
        nulls_equal=True,
        validate='m:1',
        maintain_order='left',
    )
    if joined.select(pl.col('filing_industry_status').is_null().any()).collect().item():
        raise ValueError('missing filing lookup result')
    return joined.sort('_filing_row').drop('_filing_row').select(*names, *FILING_COLUMNS)
