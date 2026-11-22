'''Independent reconciler for one published Stage 14 USAspending vendor-link bundle.

Usage: `python scripts/reconcile_usaspending_vendor_links.py --data-dir D --run ID
--outputs-sha256 PIN`.

Independence. This script is written from the stage spec (`specs/usaspending-vendor-links.md`:
Reading, Report rules, Corporate groups, Firm table, Pair table, Vendor-link target and Bundle),
the plan's Settled Defaults and the owner decisions, not from the build modules. It imports only
the standard library and Polars, which it uses to read Parquet files. It imports no
`embedding_data` module, and it was written without reading the build modules or their tests.
`SUBAWARD_HEADERS` and `EXTRACT_LAYOUT` are its own literal copies of the two committed registry
documents. It reads the four raw ZIP files that `inputs.json` cites with `zipfile`, `csv` and
`str.split`, applies the rules with `re`, `datetime` and `decimal`, and recounts everything with
plain Python sets and dicts. Then it compares its counts with the four tables and `report.json`.

Order of trust. It checks the SHA-256 of `outputs.json` against the detached pin before it reads
any other file of the run, and each bundle file against its record in that inventory before it
reads that file. It checks each raw file against the SHA-256 that `inputs.json` records, and the
Stage 4 codes bundle against the codes pin and the `naics_nodes.parquet` record in `inputs.json`.

Memory. Pass 1 streams the subaward members and keeps one small tally for each distinct pair of
usable reports. Pass 2 streams the extract member line by line and keeps firm facts only for the
UEIs on usable reports: their codes, five flags and nothing else.

Readings that the spec text leaves open, as this script takes them:
- An extract line ends only at CRLF. The first line must start with the BOF prefix and the last
  with the EOF prefix. Their counts are not record counts and are not read.
- An extract data line with the wrong field count is skipped and counted (owner, 2026-11-19). Its
  UEI, the stripped field at the UEI position, counts as an unreadable firm when it is on a usable
  report. A line with the right field count whose last field is not the record end is refused.
- Every subaward member must match the year's member pattern. A leading BOM is removed, the
  header must equal the registry header exactly, and a record with another field count, a
  `csv.Error` or a byte that is not UTF-8 is refused. The subaward type is compared as delivered
  on every row, and any other value is refused.
- Every strip uses the ASCII set `WHITESPACE`: UEIs, parent UEIs, dates, amounts, primary codes
  and the EVS source value.
- A malformed primary code on a firm whose codes the build reads makes the build fail, so a
  published bundle cannot hold one. Such a firm gets the status `malformed_code`, which is no spec
  status, and the check `firms.no_malformed_read_code` is false.
- The firm counts of `report.json` (`firms`) cover the UEIs on usable reports, whatever their
  status. `mixed_blank` counts those with a readable row whose primary code is blank and one
  whose code is not. `code_not_in_string` counts those with a readable row whose well-formed
  primary code is not an item of that same row's code string. An item is a stripped
  `~`-separated part that is a 6-digit code and a `Y`, `N` or `E` flag (the E5 layout text).
- `flag_intra_group` follows the three group conditions alone, for a self link too.
- The intra-group sensitivity admits the `intra_group` pairs of two eligible firms.
- A share with a zero denominator is null.
- The target table is compared by its key (supplier, buyer, measure), because the spec fixes no
  row order for it. The other three tables are compared in the spec's sort order.

Output: one sorted JSON line of check names, booleans and counts, never a UEI or any other row
value. The exit status is 0 when every check is equal, 1 when one differs, and 2 on a refusal: a
wrong pin, a changed raw file, a bad bundle or an unreadable input. A refusal prints a fixed
reason.
'''

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from decimal import Context, Decimal
from itertools import zip_longest
from pathlib import Path

import polars as pl

# ---- the rules' constants

WHITESPACE = ' \t\n\r\x0b\x0c'
UEI = re.compile('[A-Z0-9]{12}')
CODE = re.compile('[0-9]{6}')
# One item of the NAICS code string: a 6-digit code and a Y, N or E flag (findings, E5 layout).
CODE_STRING_ITEM = re.compile('([0-9]{6})[YNE]')
CODE_STRING_SEPARATOR = '~'
AMOUNT = re.compile(r'-?[0-9]{1,36}(\.[0-9]{1,2})?')
WINDOW = (2024, 2025, 2026)
SUBAWARD_TYPE = 'sub-contract'
DNB_CUTOFF = date(2022, 4, 4)
REPORT_STATUSES = ('uei_unusable', 'action_date_invalid', 'outside_window', 'usable')
FIRM_STATUSES = ('not_in_sam', 'dnb_era_record', 'naics_missing', 'naics_conflict',
                 'naics_not_2022', 'eligible')
PAIR_STATUSES = ('self_link', 'intra_group', 'prime_ineligible', 'sub_ineligible', 'eligible')
# The firm status of a read firm with a malformed primary code. The build fails on such a firm.
MALFORMED_CODE = 'malformed_code'
CODED = frozenset({'naics_conflict', 'naics_not_2022', 'eligible'})
TOLERANCE = 1e-12
# Sums of amounts are exact: 80 digits hold any sum of Decimal(38, 2) values.
AMOUNTS = Context(prec=80)
FIELD_SIZE_LIMIT = 2**31 - 1

# ---- the bundle's layout

RUN_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_-]*')
BUNDLES = Path('derived/usaspending/vendor-links')
CODES = Path('derived/codes')
RAW = Path('raw')
NODES = 'naics_nodes.parquet'
SUBAWARD_PATH = re.compile(r'usaspending/subcontracts/([0-9]{4}-[0-9]{2}-[0-9]{2})/FY([0-9]{4})/'
                           r'[A-Za-z0-9][A-Za-z0-9_.-]*')
EXTRACT_PATH = re.compile(r'sam/entity-extract/public-monthly-v2/([0-9]{4}-[0-9]{2})/'
                          r'[A-Za-z0-9][A-Za-z0-9_.-]*')
PAIR_SCHEMA = {
    'prime_uei': pl.String, 'sub_uei': pl.String, 'n_reports': pl.UInt64,
    'n_fy2024': pl.UInt64, 'n_fy2025': pl.UInt64, 'n_fy2026': pl.UInt64,
    'prime_status': pl.String, 'sub_status': pl.String, 'prime_node_id': pl.String,
    'sub_node_id': pl.String, 'flag_intra_group': pl.Boolean, 'pair_status': pl.String,
    'amount_sum': pl.Decimal(38, 2),
}
SUPPORT_SCHEMA = {
    'unit_a': pl.String, 'unit_b': pl.String, 's_suppliers': pl.UInt64, 'b_buyers': pl.UInt64,
    'l_pairs': pl.UInt64, 'l_fy2024': pl.UInt64, 'l_fy2025': pl.UInt64, 'l_fy2026': pl.UInt64,
    's_including_intra_group': pl.UInt64, 'b_including_intra_group': pl.UInt64,
    'l_including_intra_group': pl.UInt64, 'amount_sum': pl.Decimal(38, 2),
    'n_reports': pl.UInt64,
}
MARGINAL_SCHEMA = {
    'node_id': pl.String, 'n_suppliers': pl.UInt64, 'n_buyers': pl.UInt64,
    'n_supplier_pairs': pl.UInt64, 'n_buyer_pairs': pl.UInt64,
    'n_suppliers_partial': pl.UInt64, 'n_buyers_partial': pl.UInt64,
    'n_suppliers_including_intra_group': pl.UInt64,
    'n_buyers_including_intra_group': pl.UInt64,
}
TARGET_SCHEMA = {
    'source': pl.String, 'family': pl.String, 'unit_a_type': pl.String, 'unit_a': pl.String,
    'unit_b_type': pl.String, 'unit_b': pl.String, 'measure': pl.String, 'value': pl.Float64,
    'se': pl.Float64, 'se_method': pl.String, 'n_unweighted': pl.UInt64,
    'n_weighted': pl.Float64, 'sample_set': pl.String, 'vintage': pl.String,
    'universe': pl.String, 'flags': pl.List(pl.String),
}
# Each table: its check prefix, schema, key columns, and whether its row order is compared.
TABLES = {
    'vendor_link_pairs': ('pairs', PAIR_SCHEMA, ('prime_uei', 'sub_uei'), True),
    'vendor_link_support': ('support', SUPPORT_SCHEMA, ('unit_a', 'unit_b'), True),
    'vendor_link_marginals': ('marginals', MARGINAL_SCHEMA, ('node_id',), True),
    'vendor_links': ('targets', TARGET_SCHEMA, ('unit_a', 'unit_b', 'measure'), False),
}
FLOAT_COLUMNS = frozenset({'value', 'se', 'n_weighted'})
BUNDLE_FILES = (*(f'{table}.parquet' for table in TABLES), 'inputs.json', 'report.json')
SOURCE = 'usaspending_sam'
FAMILY = 'vendor_links'
UNIT_TYPE = 'naics_national_industry'
SAMPLE_SET = 'usaspending_subcontracts_fy2024_2026'
VINTAGE = 'naics=2022'
SIZE_GATE = 'size_gate_pending'
SENSITIVITY_LABEL = 'numerator:intra_group_sensitivity:true'
UNIVERSE = (
    'USAspending.gov contract subaward reports (FFATA subcontracts) with subaward action dates '
    'in federal fiscal years 2024–2026, downloaded under snapshot {snapshot}, joined by UEI '
    'to the SAM.gov public monthly entity extract of {month}. The population is federal prime '
    'contractors and the subcontractors they report, not a frame of firms or of '
    'business-to-business trade. A link is a distinct prime–subcontractor pair. Links '
    'within one corporate group, as the reported parent UEIs show, are excluded. Industries are '
    "each firm's self-reported primary NAICS 2022 code in SAM.gov at the extract date, not at "
    'the subaward date. Links, codes and amounts are self-reported and unvalidated.'
)

# ---- the two registries, literal copies of the committed JSON documents

# The subaward header row of every window year, in delivered order.
_SUBAWARD_HEADER = ['prime_award_unique_key', 'prime_award_piid', 'prime_award_parent_piid',
                    'prime_award_amount', 'prime_award_disaster_emergency_fund_codes',
                    'prime_award_outlayed_amount_from_COVID-19_supplementals',
                    'prime_award_obligated_amount_from_COVID-19_supplementals',
                    'prime_award_outlayed_amount_from_IIJA_supplemental',
                    'prime_award_obligated_amount_from_IIJA_supplemental',
                    'prime_award_total_outlayed_amount', 'prime_award_base_action_date',
                    'prime_award_base_action_date_fiscal_year', 'prime_award_latest_action_date',
                    'prime_award_latest_action_date_fiscal_year',
                    'prime_award_period_of_performance_start_date',
                    'prime_award_period_of_performance_current_end_date',
                    'prime_award_period_of_performance_potential_end_date',
                    'prime_award_awarding_agency_code', 'prime_award_awarding_agency_name',
                    'prime_award_awarding_sub_agency_code',
                    'prime_award_awarding_sub_agency_name', 'prime_award_awarding_office_code',
                    'prime_award_awarding_office_name', 'prime_award_funding_agency_code',
                    'prime_award_funding_agency_name', 'prime_award_funding_sub_agency_code',
                    'prime_award_funding_sub_agency_name', 'prime_award_funding_office_code',
                    'prime_award_funding_office_name',
                    'prime_award_treasury_accounts_funding_this_award',
                    'prime_award_federal_accounts_funding_this_award',
                    'prime_award_object_classes_funding_this_award',
                    'prime_award_program_activities_funding_this_award', 'prime_awardee_uei',
                    'prime_awardee_duns', 'prime_awardee_name', 'prime_awardee_dba_name',
                    'prime_awardee_parent_uei', 'prime_awardee_parent_duns',
                    'prime_awardee_parent_name', 'prime_awardee_country_code',
                    'prime_awardee_country_name', 'prime_awardee_address_line_1',
                    'prime_awardee_city_name', 'prime_awardee_county_fips_code',
                    'prime_awardee_county_name', 'prime_awardee_state_fips_code',
                    'prime_awardee_state_code', 'prime_awardee_state_name',
                    'prime_awardee_zip_code', 'prime_award_summary_recipient_cd_original',
                    'prime_award_summary_recipient_cd_current',
                    'prime_awardee_foreign_postal_code', 'prime_awardee_business_types',
                    'prime_award_primary_place_of_performance_city_name',
                    'prime_award_primary_place_of_performance_county_fips_code',
                    'prime_award_primary_place_of_performance_county_name',
                    'prime_award_primary_place_of_performance_state_fips_code',
                    'prime_award_primary_place_of_performance_state_code',
                    'prime_award_primary_place_of_performance_state_name',
                    'prime_award_primary_place_of_performance_address_zip_code',
                    'prime_award_summary_place_of_performance_cd_original',
                    'prime_award_summary_place_of_performance_cd_current',
                    'prime_award_primary_place_of_performance_country_code',
                    'prime_award_primary_place_of_performance_country_name',
                    'prime_award_base_transaction_description', 'prime_award_project_title',
                    'prime_award_naics_code', 'prime_award_naics_description',
                    'prime_award_national_interest_action_code',
                    'prime_award_national_interest_action', 'subaward_type',
                    'subaward_sam_report_id', 'subaward_sam_report_year',
                    'subaward_sam_report_month', 'subaward_number', 'subaward_amount',
                    'subaward_action_date', 'subaward_action_date_fiscal_year', 'subawardee_uei',
                    'subawardee_duns', 'subawardee_name', 'subawardee_dba_name',
                    'subawardee_parent_uei', 'subawardee_parent_duns', 'subawardee_parent_name',
                    'subawardee_country_code', 'subawardee_country_name',
                    'subawardee_address_line_1', 'subawardee_city_name', 'subawardee_state_code',
                    'subawardee_state_name', 'subawardee_zip_code',
                    'subaward_recipient_cd_original', 'subaward_recipient_cd_current',
                    'subawardee_foreign_postal_code', 'subawardee_business_types',
                    'subaward_primary_place_of_performance_city_name',
                    'subaward_primary_place_of_performance_state_code',
                    'subaward_primary_place_of_performance_state_name',
                    'subaward_primary_place_of_performance_address_zip_code',
                    'subaward_place_of_performance_cd_original',
                    'subaward_place_of_performance_cd_current',
                    'subaward_primary_place_of_performance_country_code',
                    'subaward_primary_place_of_performance_country_name', 'subaward_description',
                    'subawardee_highly_compensated_officer_1_name',
                    'subawardee_highly_compensated_officer_1_amount',
                    'subawardee_highly_compensated_officer_2_name',
                    'subawardee_highly_compensated_officer_2_amount',
                    'subawardee_highly_compensated_officer_3_name',
                    'subawardee_highly_compensated_officer_3_amount',
                    'subawardee_highly_compensated_officer_4_name',
                    'subawardee_highly_compensated_officer_4_amount',
                    'subawardee_highly_compensated_officer_5_name',
                    'subawardee_highly_compensated_officer_5_amount', 'usaspending_permalink',
                    'subaward_sam_report_last_modified_date']
_SUBAWARD_PATTERN = ('All_Contracts_Subawards_[0-9]{4}-[0-9]{2}-[0-9]{2}_H[0-9]{2}'
                     'M[0-9]{2}S[0-9]+_[0-9]+\\.csv')
_SUBAWARD_COLUMNS = {'action_date': 'subaward_action_date',
                     'amount': 'subaward_amount',
                     'prime_naics': 'prime_award_naics_code',
                     'prime_parent_uei': 'prime_awardee_parent_uei',
                     'prime_uei': 'prime_awardee_uei',
                     'report_id': 'subaward_sam_report_id',
                     'sub_parent_uei': 'subawardee_parent_uei',
                     'sub_uei': 'subawardee_uei',
                     'subaward_naics': None,
                     'subaward_type': 'subaward_type'}
SUBAWARD_HEADERS = {
    'version': 'usaspending-subaward-headers-v1',
    'years': {
        '2024': {'columns': dict(_SUBAWARD_COLUMNS), 'date_format': '%Y-%m-%d',
                 'header': list(_SUBAWARD_HEADER), 'member_pattern': _SUBAWARD_PATTERN},
        '2025': {'columns': dict(_SUBAWARD_COLUMNS), 'date_format': '%Y-%m-%d',
                 'header': list(_SUBAWARD_HEADER), 'member_pattern': _SUBAWARD_PATTERN},
        '2026': {'columns': dict(_SUBAWARD_COLUMNS), 'date_format': '%Y-%m-%d',
                 'header': list(_SUBAWARD_HEADER), 'member_pattern': _SUBAWARD_PATTERN},
    },
}
EXTRACT_LAYOUT = {'bof_prefix': 'BOF PUBLIC V2 00000000 ',
                  'date_format': '%Y%m%d',
                  'delimiter': '|',
                  'encoding': 'utf-8',
                  'eof_prefix': 'EOF PUBLIC V2 00000000 ',
                  'evs_dnb': ['D&B'],
                  'field_count': 142,
                  'layout': 'SAM Master Extract Mapping v6.0 Public File V2 Layout',
                  'member_pattern': 'SAM_PUBLIC_UTF-8_MONTHLY_V2_[0-9]{8}_[0-9a-f]{32}\\.dat',
                  'positions': {'evs_source': 122,
                                'last_update_date': 10,
                                'naics_code_string': 35,
                                'primary_naics': 33,
                                'registration_status': 6,
                                'uei': 1},
                  'record_end': '!end',
                  'restricted_positions': [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
                  'version': 'sam-extract-layout-v1'}


class Refused(Exception):
    '''An input that the pins do not authenticate, or a raw file that the rules cannot read.

    The message is a fixed reason with no row content.
    '''


# ---- value rules

def strip(value: str) -> str:
    return value.strip(WHITESPACE)


def usable_uei(value: str | None) -> str | None:
    '''The stripped UEI when it matches `^[A-Z0-9]{12}$`, else None (blank or malformed).'''
    if value is None:
        return None
    stripped = strip(value)
    return stripped if UEI.fullmatch(stripped) else None


def parse_date(value: str, date_format: str) -> date | None:
    '''The date when the stripped value round-trips exactly through `date_format`, else None.'''
    stripped = strip(value)
    try:
        parsed = datetime.strptime(stripped, date_format)
    except ValueError:
        return None
    return parsed.date() if parsed.strftime(date_format) == stripped else None


def fiscal_year(day: date) -> int:
    '''The calendar year of the date plus three months.'''
    return day.year + 1 if day.month >= 10 else day.year


def parse_amount(value: str) -> Decimal | None:
    '''The stripped amount as a Decimal when it is a plain number with at most two decimals.'''
    stripped = strip(value)
    return Decimal(stripped) if AMOUNT.fullmatch(stripped) else None


def classify_report(prime: str, sub: str, action_date: str,
                    date_format: str) -> tuple[str, str | None, str | None, int | None]:
    '''The report status, then the stripped prime and subcontractor UEIs and the fiscal year of
    a usable report (None for the others).'''
    prime_uei, sub_uei = usable_uei(prime), usable_uei(sub)
    if prime_uei is None or sub_uei is None:
        return 'uei_unusable', None, None, None
    day = parse_date(action_date, date_format)
    if day is None:
        return 'action_date_invalid', None, None, None
    year = fiscal_year(day)
    if year not in WINDOW:
        return 'outside_window', None, None, None
    return 'usable', prime_uei, sub_uei, year


def group_shown(prime: str, sub: str, prime_parent: str | None, sub_parent: str | None) -> bool:
    '''True when one report shows a corporate group. A parent counts only when it is a valid
    UEI; None stands for an unmapped parent field.'''
    prime_parent, sub_parent = usable_uei(prime_parent), usable_uei(sub_parent)
    return ((sub_parent is not None and sub_parent == prime)
            or (prime_parent is not None and prime_parent == sub)
            or (prime_parent is not None and prime_parent == sub_parent))


# ---- pass 1: the subaward reports

class PairTally:
    '''The usable reports of one (prime UEI, subcontractor UEI) pair.'''

    __slots__ = ('n_reports', 'by_year', 'amount', 'intra_group')

    def __init__(self):
        self.n_reports = 0
        self.by_year = [0] * len(WINDOW)
        self.amount = Decimal(0)
        self.intra_group = False


class Reports:
    '''Report statuses by file year (`'2024'` and so on) and in `'total'`, and the pair tallies.'''

    __slots__ = ('by_status', 'pairs')

    def __init__(self):
        self.by_status = {'total': Counter()}
        self.pairs: dict[tuple[str, str], PairTally] = {}


def column_indexes(layout: dict) -> dict[str, int | None]:
    '''The header position of each mapped field. An unmapped field is None.'''
    header = layout['header']
    return {field: None if cell is None else header.index(cell)
            for field, cell in layout['columns'].items()}


def cell(record: list[str], index: int | None) -> str | None:
    return None if index is None else record[index]


def tally_reports(years: Iterable[tuple[int, Iterable[list[str]]]], registry: dict) -> Reports:
    '''Classify every record of every file year and tally the usable ones by pair.

    `years` holds (file year, records) items; each record is a full row in header order.
    '''
    result = Reports()
    for file_year, records in years:
        layout = registry['years'][str(file_year)]
        index = column_indexes(layout)
        counts = result.by_status.setdefault(str(file_year), Counter())
        for record in records:
            if record[index['subaward_type']] != SUBAWARD_TYPE:
                raise Refused('subaward type differs')
            status, prime, sub, year = classify_report(
                record[index['prime_uei']], record[index['sub_uei']],
                record[index['action_date']], layout['date_format'])
            counts[status] += 1
            result.by_status['total'][status] += 1
            if status != 'usable':
                continue
            tally = result.pairs.get((prime, sub))
            if tally is None:
                tally = result.pairs[(prime, sub)] = PairTally()
            tally.n_reports += 1
            tally.by_year[year - WINDOW[0]] += 1
            amount = parse_amount(record[index['amount']])
            if amount is not None:
                tally.amount = AMOUNTS.add(tally.amount, amount)
            if not tally.intra_group:
                tally.intra_group = group_shown(
                    prime, sub, cell(record, index.get('prime_parent_uei')),
                    cell(record, index.get('sub_parent_uei')))
    return result


def subaward_records(file: Path, layout: dict) -> Iterator[list[str]]:
    '''Every record of every CSV member of one subaward ZIP, after the header check.'''
    previous = csv.field_size_limit(FIELD_SIZE_LIMIT)
    try:
        with zipfile.ZipFile(file) as archive:
            members = archive.infolist()
            if not all(re.fullmatch(layout['member_pattern'], member.filename)
                       for member in members):
                raise Refused('raw member is unexpected')
            header = layout['header']
            for member in members:
                with archive.open(member) as raw, io.TextIOWrapper(
                        raw, encoding='utf-8-sig', newline='') as text:
                    reader = csv.reader(text, strict=True)
                    if next(reader, None) != header:
                        raise Refused('subaward header differs')
                    for record in reader:
                        if len(record) != len(header):
                            raise Refused('subaward record is unreadable')
                        yield record
    except (csv.Error, UnicodeDecodeError, zipfile.BadZipFile):
        raise Refused('subaward record is unreadable') from None
    finally:
        csv.field_size_limit(previous)


def read_subawards(files: dict[int, Path], registry: dict) -> Reports:
    return tally_reports(((year, subaward_records(file, registry['years'][str(year)]))
                          for year, file in sorted(files.items())), registry)


# ---- pass 2: the extract

class FirmRows:
    '''What the firm rules need from the extract rows of one UEI.'''

    __slots__ = ('codes', 'blank', 'malformed', 'dnb', 'date_invalid', 'code_not_in_string')

    def __init__(self):
        self.codes: set[str] = set()
        self.blank = False
        self.malformed = False
        self.dnb = False
        self.date_invalid = False
        # A row's well-formed primary code is not an item of that row's code string.
        self.code_not_in_string = False


def mixed_blank(rows: FirmRows) -> bool:
    '''True when the firm has a row with a blank primary code and a row with a non-blank one.'''
    return rows.blank and bool(rows.codes or rows.malformed)


def string_codes(value: str) -> set[str]:
    '''The codes of the stripped `~`-separated items that are a code and a flag.'''
    codes = set()
    for item in value.split(CODE_STRING_SEPARATOR):
        match = CODE_STRING_ITEM.fullmatch(strip(item))
        if match is not None:
            codes.add(match[1])
    return codes


class Extract:
    '''Firm facts of the wanted UEIs and the extract-wide counts.'''

    __slots__ = ('firms', 'unreadable_lines', 'unreadable_ueis', 'invalid_date_rows')

    def __init__(self):
        self.firms: dict[str, FirmRows] = {}
        self.unreadable_lines = 0
        self.unreadable_ueis: set[str] = set()
        self.invalid_date_rows = 0


def data_lines(lines: Iterable[str], layout: dict) -> Iterator[str]:
    '''The data lines between the BOF and the EOF line, without their CRLF line ends.'''
    iterator = iter(lines)
    first = next(iterator, None)
    if first is None or not first.startswith(layout['bof_prefix']):
        raise Refused('extract framing differs')
    pending = None
    for line in iterator:
        if pending is not None:
            yield pending
        pending = line.removesuffix('\r\n')
    if pending is None or not pending.startswith(layout['eof_prefix']):
        raise Refused('extract framing differs')


def position(layout: dict, field: str) -> int | None:
    '''The 0-based index of a registered 1-based position, or None when it is not mapped.'''
    value = layout['positions'].get(field)
    return None if value is None else value - 1


def tally_extract(lines: Iterable[str], layout: dict, wanted: set[str]) -> Extract:
    '''Read the extract lines (BOF line first, EOF line last) and keep the rows of `wanted`.'''
    result = Extract()
    uei_at = position(layout, 'uei')
    code_at = position(layout, 'primary_naics')
    update_at = position(layout, 'last_update_date')
    evs_at = position(layout, 'evs_source')
    string_at = position(layout, 'naics_code_string')
    dnb_values = set(layout['evs_dnb'])
    record_end = layout['record_end']
    for line in data_lines(lines, layout):
        fields = line.split(layout['delimiter'])
        if len(fields) != layout['field_count']:
            result.unreadable_lines += 1
            if uei_at < len(fields) and strip(fields[uei_at]) in wanted:
                result.unreadable_ueis.add(strip(fields[uei_at]))
            continue
        if record_end is not None and fields[-1] != record_end:
            raise Refused('extract record end differs')
        update = parse_date(fields[update_at], layout['date_format'])
        if update is None:
            result.invalid_date_rows += 1
        uei = strip(fields[uei_at])
        if uei not in wanted:
            continue
        rows = result.firms.get(uei)
        if rows is None:
            rows = result.firms[uei] = FirmRows()
        code = strip(fields[code_at])
        if not code:
            rows.blank = True
        elif CODE.fullmatch(code):
            rows.codes.add(code)
            if string_at is not None and code not in string_codes(fields[string_at]):
                rows.code_not_in_string = True
        else:
            rows.malformed = True
        if update is None:
            rows.date_invalid = True
            rows.dnb = True
        elif update < DNB_CUTOFF:
            rows.dnb = True
        if evs_at is not None and strip(fields[evs_at]) in dnb_values:
            rows.dnb = True
    return result


def extract_text(file: Path, layout: dict) -> Iterator[str]:
    '''The lines of the one extract member, each with its CRLF. Only CRLF ends a line.'''
    try:
        with zipfile.ZipFile(file) as archive:
            members = archive.infolist()
            if len(members) != 1 or not re.fullmatch(layout['member_pattern'],
                                                      members[0].filename):
                raise Refused('raw member is unexpected')
            with archive.open(members[0]) as raw, io.TextIOWrapper(
                    raw, encoding=layout['encoding'], newline='\r\n') as text:
                yield from text
    except (UnicodeDecodeError, zipfile.BadZipFile):
        raise Refused('extract line is unreadable') from None


# ---- firms, pairs and the estimates

def classify_firm(rows: FirmRows | None, nodes: dict[str, str]) -> tuple[str, str | None]:
    '''The firm status and, for an eligible firm, its NAICS 2022 national-industry node ID.'''
    if rows is None:
        return 'not_in_sam', None
    if rows.dnb:
        return 'dnb_era_record', None
    if rows.malformed:
        return MALFORMED_CODE, None
    if not rows.codes:
        return 'naics_missing', None
    if len(rows.codes) > 1:
        return 'naics_conflict', None
    (code,) = rows.codes
    if code not in nodes:
        return 'naics_not_2022', None
    return 'eligible', nodes[code]


def classify_pair(prime: str, sub: str, intra_group: bool, prime_status: str,
                  sub_status: str) -> str:
    if prime == sub:
        return 'self_link'
    if intra_group:
        return 'intra_group'
    if prime_status != 'eligible':
        return 'prime_ineligible'
    if sub_status != 'eligible':
        return 'sub_ineligible'
    return 'eligible'


# Positions in a pair row, which follows `PAIR_SCHEMA`.
P_PRIME, P_SUB, P_REPORTS, P_FY = 0, 1, 2, 3
P_PRIME_STATUS, P_SUB_STATUS, P_PRIME_NODE, P_SUB_NODE, P_INTRA, P_STATUS, P_AMOUNT = range(6, 13)


def pair_rows(pairs: dict[tuple[str, str], PairTally],
              firms: dict[str, tuple[str, str | None]]) -> dict[tuple[str, str], tuple]:
    '''The expected pair table: one row tuple in `PAIR_SCHEMA` order for each pair.'''
    rows = {}
    for (prime, sub), tally in pairs.items():
        prime_status, prime_node = firms[prime]
        sub_status, sub_node = firms[sub]
        status = classify_pair(prime, sub, tally.intra_group, prime_status, sub_status)
        rows[(prime, sub)] = (prime, sub, tally.n_reports, *tally.by_year, prime_status,
                              sub_status, prime_node, sub_node, tally.intra_group, status,
                              tally.amount)
    return rows


def admitted(row: tuple) -> bool:
    '''True for a pair that the intra-group sensitivity admits beside the eligible pairs.'''
    return (row[P_STATUS] == 'intra_group' and row[P_PRIME_STATUS] == 'eligible'
            and row[P_SUB_STATUS] == 'eligible')


class Links:
    '''The firm sets of one set of pairs: suppliers and buyers by industry and by cell.'''

    def __init__(self, rows: Iterable[tuple]):
        self.suppliers = defaultdict(set)
        self.buyers = defaultdict(set)
        self.cell_suppliers = defaultdict(set)
        self.cell_buyers = defaultdict(set)
        self.cell_pairs = Counter()
        for row in rows:
            supplier, buyer = row[P_SUB_NODE], row[P_PRIME_NODE]
            self.suppliers[supplier].add(row[P_SUB])
            self.buyers[buyer].add(row[P_PRIME])
            self.cell_suppliers[(supplier, buyer)].add(row[P_SUB])
            self.cell_buyers[(supplier, buyer)].add(row[P_PRIME])
            self.cell_pairs[(supplier, buyer)] += 1


def share(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def estimates(rows: dict[tuple[str, str], tuple], universe: str) -> dict:
    '''The support, marginal and target rows and the sensitivity summary from the pair rows.'''
    eligible = [row for row in rows.values() if row[P_STATUS] == 'eligible']
    including = eligible + [row for row in rows.values() if admitted(row)]
    headline, sensitivity = Links(eligible), Links(including)
    prime_ineligible_subs = {row[P_SUB] for row in rows.values()
                             if row[P_STATUS] == 'prime_ineligible'}
    sub_ineligible_primes = {row[P_PRIME] for row in rows.values()
                             if row[P_STATUS] == 'sub_ineligible'}
    by_cell = defaultdict(list)
    for row in eligible:
        by_cell[(row[P_SUB_NODE], row[P_PRIME_NODE])].append(row)
    support, targets = {}, {}
    for (supplier, buyer), members in by_cell.items():
        cell_key = (supplier, buyer)
        suppliers = len(headline.cell_suppliers[cell_key])
        buyers = len(headline.cell_buyers[cell_key])
        suppliers_including = len(sensitivity.cell_suppliers[cell_key])
        buyers_including = len(sensitivity.cell_buyers[cell_key])
        by_year = [sum(1 for row in members if row[P_FY + offset] > 0)
                   for offset in range(len(WINDOW))]
        amount = Decimal(0)
        for row in members:
            amount = AMOUNTS.add(amount, row[P_AMOUNT])
        support[cell_key] = (supplier, buyer, suppliers, buyers, len(members), *by_year,
                             suppliers_including, buyers_including,
                             sensitivity.cell_pairs[cell_key], amount,
                             sum(row[P_REPORTS] for row in members))
        for measure, count, including_count, denominator in (
                ('supplier_share', suppliers, suppliers_including,
                 len(headline.suppliers[supplier])),
                ('buyer_share', buyers, buyers_including, len(headline.buyers[buyer]))):
            flags = sorted([SIZE_GATE, *([SENSITIVITY_LABEL] if including_count != count
                                         else [])])
            targets[(supplier, buyer, measure)] = (
                SOURCE, FAMILY, UNIT_TYPE, supplier, UNIT_TYPE, buyer, measure,
                count / denominator, None, 'none', count, float(count), SAMPLE_SET, VINTAGE,
                universe, flags)
    supplier_pairs, buyer_pairs = Counter(), Counter()
    for supplier, buyer in by_cell:
        supplier_pairs[supplier] += len(by_cell[(supplier, buyer)])
        buyer_pairs[buyer] += len(by_cell[(supplier, buyer)])
    marginals = {}
    for node in set(headline.suppliers) | set(headline.buyers):
        suppliers, buyers = headline.suppliers.get(node, set()), headline.buyers.get(node, set())
        marginals[(node,)] = (
            node, len(suppliers), len(buyers), supplier_pairs[node], buyer_pairs[node],
            len(suppliers & prime_ineligible_subs), len(buyers & sub_ineligible_primes),
            len(sensitivity.suppliers.get(node, set())), len(sensitivity.buyers.get(node, set())))
    summary = {
        'n_pairs': {'eligible': len(eligible), 'including_intra_group': len(including)},
        'n_buyers': {'eligible': len({row[P_PRIME] for row in eligible}),
                     'including_intra_group': len({row[P_PRIME] for row in including})},
        'n_suppliers': {'eligible': len({row[P_SUB] for row in eligible}),
                        'including_intra_group': len({row[P_SUB] for row in including})},
        'cells_only_intra_group': len(set(sensitivity.cell_pairs) - set(headline.cell_pairs)),
    }
    return {'support': support, 'marginals': marginals, 'targets': targets, 'summary': summary}


# ---- the expected report

def status_counts(statuses: Iterable[str], names: tuple[str, ...]) -> dict[str, int]:
    '''Counts of every named status, zero included, and of any other status that occurs.'''
    counts = Counter(statuses)
    return {name: counts.get(name, 0) for name in names} | {
        name: count for name, count in counts.items() if name not in names}


def coverage(ueis: set[str], firms: dict[str, tuple[str, str | None]]) -> dict:
    eligible = sum(1 for uei in ueis if firms[uei][0] == 'eligible')
    return {'eligible': eligible, 'total': len(ueis), 'share': share(eligible, len(ueis))}


def trigger(ueis: set[str], firms: dict[str, tuple[str, str | None]]) -> dict:
    not_2022 = sum(1 for uei in ueis if firms[uei][0] == 'naics_not_2022')
    with_code = sum(1 for uei in ueis if firms[uei][0] in CODED)
    return {'naics_not_2022': not_2022, 'with_code': with_code,
            'share': share(not_2022, with_code)}


def expected_report(reports: Reports, extract: Extract, firms: dict, rows: dict,
                    summary: dict) -> dict[str, tuple[tuple[str, ...], object, str]]:
    '''Each report check: its path in `report.json`, its expected value and its mode.

    The mode `exact` compares the value whole. `named` compares the named counts of a dict and
    its `share` within the tolerance. `close` compares one float within the tolerance.
    '''
    primes = {prime for prime, _sub in rows}
    subs = {sub for _prime, sub in rows}
    everyone = primes | subs
    checks = {}
    for section, counts in reports.by_status.items():
        path = ('reports', 'total') if section == 'total' else ('reports', 'by_file_year', section)
        checks[f'report.reports.{section}.by_status'] = (
            (*path, 'by_status'), status_counts(counts.elements(), REPORT_STATUSES), 'exact')
    for role, ueis in (('all', everyone), ('prime', primes), ('subcontractor', subs)):
        checks[f'report.firms.{role}'] = (
            ('firms', role), status_counts((firms[uei][0] for uei in ueis), FIRM_STATUSES),
            'exact')
    read = [extract.firms[uei] for uei in everyone if uei in extract.firms]
    for name, count in (('last_update_invalid', sum(1 for rows in read if rows.date_invalid)),
                        ('mixed_blank', sum(1 for rows in read if mixed_blank(rows))),
                        ('code_not_in_string',
                         sum(1 for rows in read if rows.code_not_in_string))):
        checks[f'report.firms.{name}'] = (('firms', name), count, 'exact')
    checks['report.pairs'] = (
        ('pairs',), status_counts((row[P_STATUS] for row in rows.values()), PAIR_STATUSES)
        | {'total': len(rows)}, 'exact')
    for name in ('n_pairs', 'n_buyers', 'n_suppliers', 'cells_only_intra_group'):
        checks[f'report.{name}'] = ((name,), summary[name], 'exact')
    for role, ueis in (('prime', primes), ('subcontractor', subs)):
        checks[f'report.join_coverage.{role}'] = (
            ('join_coverage', role), coverage(ueis, firms), 'named')
    pooled = trigger(everyone, firms)
    for name in ('naics_not_2022', 'with_code'):
        checks[f'report.trigger.{name}'] = (('trigger', name), pooled[name], 'exact')
    checks['report.trigger.share'] = (('trigger', 'share'), pooled['share'], 'close')
    for offset, year in enumerate(WINDOW):
        year_primes = {row[P_PRIME] for row in rows.values() if row[P_FY + offset] > 0}
        year_subs = {row[P_SUB] for row in rows.values() if row[P_FY + offset] > 0}
        for role, ueis in (('prime', year_primes), ('subcontractor', year_subs)):
            checks[f'report.join_coverage.{year}.{role}'] = (
                ('join_coverage', 'by_fiscal_year', str(year), role), coverage(ueis, firms),
                'named')
        checks[f'report.trigger.{year}'] = (
            ('trigger', 'by_fiscal_year', str(year)), trigger(year_primes | year_subs, firms),
            'named')
    checks['report.extract.unreadable_lines'] = (
        ('extract', 'unreadable_lines'), extract.unreadable_lines, 'exact')
    not_in_sam = {uei for uei in extract.unreadable_ueis if firms[uei][0] == 'not_in_sam'}
    for name, ueis in (('unreadable_firms', extract.unreadable_ueis),
                       ('unreadable_firms_not_in_sam', not_in_sam)):
        checks[f'report.extract.{name}'] = (
            ('extract', name), {'all': len(ueis), 'prime': len(ueis & primes),
                                'subcontractor': len(ueis & subs)}, 'exact')
    checks['report.extract.last_update_invalid_rows'] = (
        ('extract', 'last_update_by_year', 'invalid'), extract.invalid_date_rows, 'exact')
    return checks


# ---- comparison

MISSING = object()


def dig(document: object, path: tuple[str, ...]) -> object:
    '''The value at `path`, or MISSING when a step is absent or not a dict.'''
    for step in path:
        if not isinstance(document, dict) or step not in document:
            return MISSING
        document = document[step]
    return document


def close(expected: float | None, actual: object) -> bool:
    '''Both null, or two numbers within the tolerance.'''
    if expected is None or actual is None:
        return expected is None and actual is None
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    return abs(expected - actual) <= TOLERANCE


def named_equal(expected: dict, actual: object) -> bool:
    '''Each named count equal, and `share` within the tolerance.'''
    if not isinstance(actual, dict):
        return False
    return all(close(value, actual.get(name, MISSING)) if name == 'share'
               else actual.get(name, MISSING) == value for name, value in expected.items())


def report_equal(expected: dict, report: object) -> dict[str, bool]:
    results = {}
    for name, (path, value, mode) in expected.items():
        actual = dig(report, path)
        if mode == 'exact':
            results[name] = actual is not MISSING and actual == value
        elif mode == 'close':
            results[name] = actual is not MISSING and close(value, actual)
        else:
            results[name] = named_equal(value, actual)
    return results


def same(expected: object, actual: object, floating: bool) -> bool:
    return close(expected, actual) if floating else expected == actual


def table_differences(prefix: str, frame: pl.DataFrame, schema: dict, key: tuple[str, ...],
                      expected: dict[tuple, tuple], ordered: bool) -> dict[str, int]:
    '''Differing counts: `<prefix>.schema`, `<prefix>.rows` (keys missing, extra, repeated or
    out of order) and one for each other column, over the rows whose key matches.'''
    columns = list(schema)
    present = [column for column in columns if column in frame.columns]
    differing = {f'{prefix}.schema': int(list(frame.schema.items()) != list(schema.items()))}
    if not all(column in present for column in key):
        differing[f'{prefix}.rows'] = max(1, len(expected), frame.height)
        return differing
    actual = frame.select(present).rows()
    key_at = [present.index(column) for column in key]
    actual_keys = [tuple(row[i] for i in key_at) for row in actual]
    if ordered:
        differing[f'{prefix}.rows'] = sum(
            first != second for first, second in zip_longest(actual_keys, sorted(expected)))
    else:
        counted, wanted = Counter(actual_keys), Counter(iter(expected))
        differing[f'{prefix}.rows'] = sum(((counted - wanted) + (wanted - counted)).values())
    by_key = {}
    for row_key, row in zip(actual_keys, actual, strict=True):
        by_key.setdefault(row_key, row)
    for column in columns:
        if column in key:
            continue
        if column not in present:
            differing[f'{prefix}.{column}'] = max(1, len(expected))
            continue
        expected_at, actual_at = columns.index(column), present.index(column)
        floating = column in FLOAT_COLUMNS
        differing[f'{prefix}.{column}'] = sum(
            1 for row_key, row in expected.items() if row_key in by_key
            and not same(row[expected_at], by_key[row_key][actual_at], floating))
    return differing


# ---- authentication

def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(file: Path) -> object:
    try:
        return json.loads(file.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Refused('bundle file is malformed') from None


def pinned_inventory(directory: Path, pin: str) -> dict:
    '''The bundle inventory, once `outputs.json` matches the pin and names the six files.'''
    outputs = directory / 'outputs.json'
    if not outputs.is_file() or sha256(outputs) != pin:
        raise Refused('detached pin differs')
    inventory = read_json(outputs)
    if not isinstance(inventory, dict) or set(inventory) != set(BUNDLE_FILES):
        raise Refused('bundle inventory is malformed')
    return inventory


def bundle_file(directory: Path, inventory: dict, name: str) -> Path:
    '''One bundle file, once its bytes match its record in the pinned inventory.'''
    file = directory / name
    record = inventory[name]
    expected = record.get('sha256') if isinstance(record, dict) else None
    if not file.is_file() or sha256(file) != expected:
        raise Refused('bundle file differs from its inventory')
    return file


def raw_selection(inputs: object) -> tuple[str, str, dict[int, tuple[str, str]],
                                           tuple[str, str]]:
    '''The snapshot label, the extract month, the subaward (path, SHA-256) by file year and
    the extract (path, SHA-256) that `inputs.json` cites. Paths are relative to `raw/`.'''
    malformed = 'recorded inputs are malformed'
    try:
        subawards = [(entry['path'], entry['sha256']) for entry in inputs['raw']['subawards']]
        extract = (inputs['raw']['extract']['path'], inputs['raw']['extract']['sha256'])
    except (KeyError, TypeError):
        raise Refused(malformed) from None
    files, snapshots = {}, set()
    for path, digest in subawards:
        match = SUBAWARD_PATH.fullmatch(path) if isinstance(path, str) else None
        if match is None or not isinstance(digest, str) or int(match[2]) in files:
            raise Refused(malformed)
        snapshots.add(match[1])
        files[int(match[2])] = (path, digest)
    if len(snapshots) != 1 or tuple(sorted(files)) != WINDOW:
        raise Refused(malformed)
    match = EXTRACT_PATH.fullmatch(extract[0]) if isinstance(extract[0], str) else None
    if match is None or not isinstance(extract[1], str):
        raise Refused(malformed)
    return snapshots.pop(), match[1], files, extract


def raw_file(data_dir: Path, path: str, digest: str) -> Path:
    file = data_dir / RAW / path
    if not file.is_file() or sha256(file) != digest:
        raise Refused('raw file differs from inputs.json')
    return file


def national_industries(data_dir: Path, inputs: dict) -> dict[str, str]:
    '''Code to node ID of every NAICS 2022 national industry in the pinned Stage 4 nodes.'''
    try:
        codes = inputs['codes']
        run, pin, recorded = codes['run_id'], codes['outputs_sha256'], codes['outputs'][NODES]
    except (KeyError, TypeError):
        raise Refused('recorded inputs are malformed') from None
    if not isinstance(run, str) or not RUN_ID.fullmatch(run) or not isinstance(pin, str):
        raise Refused('recorded inputs are malformed')
    directory = data_dir / CODES / run
    outputs = directory / 'outputs.json'
    if not outputs.is_file() or sha256(outputs) != pin:
        raise Refused('codes pin differs')
    record = dig(read_json(outputs), (NODES,))
    nodes = directory / NODES
    if (not isinstance(record, dict) or record != recorded or not nodes.is_file()
            or sha256(nodes) != record.get('sha256')):
        raise Refused('codes nodes differ from the recorded inventory')
    frame = pl.read_parquet(nodes, columns=['node_id', 'system', 'vintage', 'level', 'code'])
    return {code: node_id for node_id, system, vintage, level, code in frame.iter_rows()
            if system == 'naics' and vintage == 2022 and level == 'national_industry'}


# ---- the run

def reconcile(data_dir: Path, run_id: str, pin: str) -> dict:
    '''Recompute the bundle from its raw files and compare. Returns checks and counts.'''
    if not RUN_ID.fullmatch(run_id):
        raise Refused('unsafe run ID')
    directory = data_dir / BUNDLES / run_id
    inventory = pinned_inventory(directory, pin)
    files = {name: bundle_file(directory, inventory, name) for name in BUNDLE_FILES}
    inputs = read_json(files['inputs.json'])
    report = read_json(files['report.json'])
    snapshot, month, subaward_entries, extract_entry = raw_selection(inputs)
    subaward_files = {year: raw_file(data_dir, *entry)
                      for year, entry in subaward_entries.items()}
    extract_file = raw_file(data_dir, *extract_entry)
    nodes = national_industries(data_dir, inputs)

    reports = read_subawards(subaward_files, SUBAWARD_HEADERS)
    wanted = {uei for pair in reports.pairs for uei in pair}
    extract = tally_extract(extract_text(extract_file, EXTRACT_LAYOUT), EXTRACT_LAYOUT, wanted)
    firms = {uei: classify_firm(extract.firms.get(uei), nodes) for uei in wanted}
    rows = pair_rows(reports.pairs, firms)
    computed = estimates(rows, UNIVERSE.format(snapshot=snapshot, month=month))

    expected_tables = {'vendor_link_pairs': rows, 'vendor_link_support': computed['support'],
                       'vendor_link_marginals': computed['marginals'],
                       'vendor_links': computed['targets']}
    differing = {}
    for table, (prefix, schema, key, ordered) in TABLES.items():
        frame = pl.read_parquet(files[f'{table}.parquet'])
        differing.update(table_differences(prefix, frame, schema, key, expected_tables[table],
                                           ordered))
    checks = {name: count == 0 for name, count in differing.items()}
    checks.update(report_equal(expected_report(reports, extract, firms, rows,
                                               computed['summary']), report))
    malformed = sum(1 for status, _node in firms.values() if status == MALFORMED_CODE)
    checks['firms.no_malformed_read_code'] = malformed == 0
    checks['inputs.registries'] = dig(inputs, ('registries',)) == {
        'subaward_headers': SUBAWARD_HEADERS, 'extract_layout': EXTRACT_LAYOUT}
    checks['inputs.selection'] = (dig(inputs, ('snapshot',)), dig(inputs, ('sam_month',)),
                                  dig(inputs, ('window',))) == (snapshot, month, list(WINDOW))
    equal = all(checks.values())
    total = reports.by_status['total']
    return {
        'equal': equal,
        'status': 'equal' if equal else 'unequal',
        'checks': checks,
        'differing': {name: count for name, count in differing.items() if count},
        'counts': {
            'reports': sum(total.values()), 'usable': total['usable'], 'pairs': len(rows),
            'firms': len(firms), 'cells': len(computed['support']),
            'targets': len(computed['targets']), 'marginals': len(computed['marginals']),
            'unreadable_lines': extract.unreadable_lines, 'malformed_read_codes': malformed,
        },
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    result.add_argument('--data-dir', type=Path, required=True)
    result.add_argument('--run', required=True)
    result.add_argument('--outputs-sha256', required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    '''Print one sorted JSON line. Return 0 when equal, 1 when unequal, 2 on a refusal.'''
    arguments = parser().parse_args(argv)
    result = {'check': 'vendor_links', 'run': arguments.run}
    try:
        result.update(reconcile(arguments.data_dir, arguments.run, arguments.outputs_sha256))
    except Refused as refusal:
        result.update(equal=False, status='refused', reason=str(refusal))
    except Exception:
        # An exception's text may hold a row value, so only a fixed reason is printed.
        result.update(equal=False, status='refused', reason='reconciliation failed')
    print(json.dumps(result, sort_keys=True))
    if result['status'] == 'refused':
        return 2
    return 0 if result['equal'] is True else 1


if __name__ == '__main__':
    sys.exit(main())
