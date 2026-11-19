'''The Stage 14 streaming readers: subaward ZIP files and the SAM.gov extract.

Every ZIP here is synthetic and uses the invented test registries. The UEIs are made up.
No value is a name or an address, except the plan's `Fixture Name Co` marker and
`DNB_SENTINEL`, which stand in for text that must reach no scratch file and no frame. Each
refusal matches the exact message (`\\A...\\Z`), so a refusal at the wrong check fails.
'''

import codecs
import csv
import dataclasses
import hashlib
import io
import json
import re
import tracemalloc
import zipfile

import polars as pl
import pytest
from vendor_link_fixtures import (  # noqa: F401
    DNB_SENTINEL,
    TEST_EXTRACT_LAYOUT,
    TEST_SUBAWARD_LAYOUTS,
    extract_line,
    no_live_sam,
    subaward_record,
    write_extract_zip,
    write_subaward_zip,
    zip_bytes,
)

from embedding_data import vendor_link_readers
from embedding_data.vendor_link_readers import (
    EXTRACT_SCHEMA,
    SUBAWARD_SCHEMA,
    UNREADABLE_SCHEMA,
)

LAYOUT = TEST_SUBAWARD_LAYOUTS[2024]
MEMBER_1 = 'Contracts_Subawards_1.csv'
MEMBER_2 = 'Contracts_Subawards_2.csv'
FIELDS = ('prime_uei', 'prime_parent_uei', 'sub_uei', 'sub_parent_uei', 'action_date', 'amount',
          'subaward_type', 'report_id', 'subaward_naics', 'prime_naics')
EXTRACT = TEST_EXTRACT_LAYOUT
EXTRACT_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.dat'
EXTRACT_ZIP = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP'
BOF = 'BOF FIXTURE V2 00000000 20261102 0000000 0000000'
EOF = 'EOF FIXTURE V2 00000000 20261102 0000000 0000000'


def exactly(message):
    return pytest.raises(ValueError, match=rf'\A{re.escape(message)}\Z')


def digest(record):
    text = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def record_of(n, *, year=2024, **fields):
    '''A report whose made-up UEIs carry the number `n`.'''
    values = {'prime_uei': f'PRIME{n:07d}', 'sub_uei': f'SUBAW{n:07d}',
              'action_date': '2024-03-01', 'subaward_type': 'sub-contract'} | fields
    return subaward_record(TEST_SUBAWARD_LAYOUTS[year], **values)


def member_bytes(records, *, header=LAYOUT.header, bom=False):
    text = io.StringIO()
    csv.writer(text, lineterminator='\r\n').writerows([list(header), *records])
    return (codecs.BOM_UTF8 if bom else b'') + text.getvalue().encode('utf-8')


def csv_lines(records):
    '''Records as CSV lines with no header.'''
    text = io.StringIO()
    csv.writer(text, lineterminator='\r\n').writerows(records)
    return text.getvalue().encode('utf-8')


def broken_quote_line(n, last_cell):
    '''A record line whose unquoted cells come from `record_of(n)` and whose last cell is
    raw text, so that it can break the CSV quote rules.'''
    return (','.join(record_of(n)[:-1]) + ',' + last_cell + '\r\n').encode('utf-8')


def subaward_files(directory, members_by_year, *, layouts=TEST_SUBAWARD_LAYOUTS, **options):
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for year, members in members_by_year.items():
        files[year] = directory / f'FY{year}.zip'
        write_subaward_zip(files[year], layouts[year], members, **options)
    return files


def read_all(directory, members_by_year, **options):
    files = subaward_files(directory, members_by_year, **options)
    return vendor_link_readers.read_subawards(files, TEST_SUBAWARD_LAYOUTS,
                                              directory / 'scratch')


def read(directory, records, **options):
    return read_all(directory, {2024: {MEMBER_1: records}}, **options).rows


def read_file(directory, file, *, year=2024, layouts=TEST_SUBAWARD_LAYOUTS):
    return vendor_link_readers.read_subawards({year: file}, layouts, directory / 'scratch')


def parts(directory):
    return sorted(path.name for path in (directory / 'scratch').rglob('*.parquet'))


@pytest.fixture
def field_size_limit():
    '''Start each test at a small known limit and put the old limit back afterwards.'''
    previous = csv.field_size_limit(4096)
    yield 4096
    csv.field_size_limit(previous)


def test_the_module_constants():
    assert list(SUBAWARD_SCHEMA.items()) == [
        ('file_year', pl.Int64), ('member', pl.String), ('record', pl.UInt64),
        ('prime_uei', pl.String), ('prime_parent_uei', pl.String), ('sub_uei', pl.String),
        ('sub_parent_uei', pl.String), ('action_date', pl.String), ('amount', pl.String),
        ('subaward_type', pl.String), ('report_id', pl.String), ('subaward_naics', pl.String),
        ('prime_naics', pl.String), ('row_digest', pl.String)]
    assert list(EXTRACT_SCHEMA.items()) == [
        ('line', pl.UInt64), ('uei', pl.String), ('registration_status', pl.String),
        ('last_update_date', pl.String), ('primary_naics', pl.String),
        ('naics_code_string', pl.String), ('evs_source', pl.String)]
    assert vendor_link_readers.BATCH_ROWS == 200_000
    assert vendor_link_readers.FIELD_SIZE_LIMIT == 1 << 30


def test_reads_the_mapped_columns_as_strings(tmp_path):
    values = {'prime_uei': '0ABC123DEF45', 'prime_parent_uei': '0PAR123DEF45',
              'sub_uei': '1XYZ987WVU65', 'sub_parent_uei': '1PAR987WVU65',
              'action_date': '2024-03-01', 'amount': '1200.50', 'subaward_type': 'sub-contract',
              'report_id': '00042', 'subaward_naics': '000100', 'prime_naics': '000000'}
    record = subaward_record(LAYOUT, **values)
    rows = read(tmp_path, [record])
    assert rows.collect_schema() == SUBAWARD_SCHEMA
    assert rows.collect().rows(named=True) == [
        {'file_year': 2024, 'member': MEMBER_1, 'record': 1, **values,
         'row_digest': digest(record)}]


def test_the_rows_are_a_lazy_frame_in_schema_order(tmp_path):
    result = read_all(tmp_path, {2024: {MEMBER_1: [record_of(1)]}})
    assert isinstance(result.rows, pl.LazyFrame)
    assert list(result.rows.collect_schema().items()) == list(SUBAWARD_SCHEMA.items())


def test_values_are_kept_exactly_as_delivered(tmp_path):
    values = {'prime_uei': ' 0ABC123DEF45 ', 'sub_uei': '\t1xyz987wvu65', 'amount': '0012.500',
              'action_date': '03/01/2024 ', 'subaward_type': 'Sub-Contract', 'report_id': '',
              'prime_parent_uei': 'café', 'sub_parent_uei': '"', 'subaward_naics': '31-33',
              'prime_naics': '5415'}
    record = subaward_record(LAYOUT, **values)
    row = read(tmp_path, [record]).collect().row(0, named=True)
    assert {field: row[field] for field in FIELDS} == values


def test_subaward_read_is_frozen(tmp_path):
    result = read_all(tmp_path, {2024: {MEMBER_1: [record_of(1)]}})
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.records = {}


def test_every_csv_member_is_read_and_other_members_fail(tmp_path):
    members = {MEMBER_1: [record_of(1), record_of(2)], MEMBER_2: [record_of(3)]}
    result = read_all(tmp_path, {2024: members})
    rows = result.rows.collect()
    assert rows.height == 3
    assert rows['member'].to_list() == [MEMBER_1, MEMBER_1, MEMBER_2]
    assert rows['record'].to_list() == [1, 2, 1]
    assert rows['prime_uei'].to_list() == ['PRIME0000001', 'PRIME0000002', 'PRIME0000003']
    assert result.members == {2024: (MEMBER_1, MEMBER_2)}
    assert result.records == {2024: 3}
    for index, extra in enumerate(({'readme.txt': b'About these files\r\n'}, {'folder/': b''})):
        directory = tmp_path / f'other-{index}'
        directory.mkdir()
        file = directory / 'FY2024.zip'
        write_subaward_zip(file, LAYOUT, members, extra=extra)
        with exactly('unexpected ZIP member'):
            read_file(directory, file)
        assert parts(directory) == []


def test_members_are_read_in_name_order(tmp_path):
    members = {MEMBER_2: [record_of(3)], 'Contracts_Subawards_10.csv': [record_of(2)],
               MEMBER_1: [record_of(1)]}
    result = read_all(tmp_path, {2024: members})
    names = (MEMBER_1, 'Contracts_Subawards_10.csv', MEMBER_2)
    assert result.members == {2024: names}
    rows = result.rows.collect()
    assert rows['member'].to_list() == list(names)
    assert rows['prime_uei'].to_list() == ['PRIME0000001', 'PRIME0000002', 'PRIME0000003']


def test_a_repeated_member_name_is_read_once_for_each_entry(tmp_path):
    buffer = io.BytesIO()
    with pytest.warns(UserWarning, match='Duplicate name'):
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr(MEMBER_1, member_bytes([record_of(1)]))
            archive.writestr(MEMBER_1, member_bytes([record_of(2), record_of(3)]))
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(buffer.getvalue())
    result = read_file(tmp_path, file)
    rows = result.rows.collect()
    assert rows['prime_uei'].to_list() == ['PRIME0000001', 'PRIME0000002', 'PRIME0000003']
    assert rows['record'].to_list() == [1, 1, 2]
    assert result.members == {2024: (MEMBER_1, MEMBER_1)}
    assert result.records == {2024: 3}


@pytest.mark.parametrize('name', [
    'Contracts_Subawards_3.csv.bak',
    'x_Contracts_Subawards_3.csv',
    'Contracts_Subawards_.csv',
    'Contracts_Subawards_3.CSV',
    'nested/Contracts_Subawards_3.csv',
    'readme.txt',
])
def test_a_member_that_does_not_fully_match_the_pattern_fails(name, tmp_path):
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record_of(1)]},
                       extra={name: member_bytes([record_of(2)])})
    with exactly('unexpected ZIP member'):
        read_file(tmp_path, file)
    assert parts(tmp_path) == []


def test_a_directory_entry_fails_even_when_the_pattern_admits_it(tmp_path):
    layouts = {2024: dataclasses.replace(LAYOUT, member_pattern='.*')}
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record_of(1)]}, extra={'folder/': b''})
    with exactly('unexpected ZIP member'):
        read_file(tmp_path, file, layouts=layouts)
    assert parts(tmp_path) == []


def test_a_zip_without_members_fails(tmp_path):
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes({}))
    with exactly('no subaward CSV member'):
        read_file(tmp_path, file)


def test_quoted_newline_and_comma_keep_one_report(tmp_path):
    layout = TEST_SUBAWARD_LAYOUTS[2024]
    record = subaward_record(layout, prime_uei='AAAAAAAAAAA1', sub_uei='BBBBBBBBBBB2',
                             cell_description='Line one,\nline "two"')
    rows = read(tmp_path, [record]).collect()
    assert rows.height == 1 and rows['sub_uei'].item() == 'BBBBBBBBBBB2'


def test_quoted_commas_quotes_and_line_breaks_leave_every_column_in_place(tmp_path):
    values = {'prime_uei': 'AAAAAAAAAAA1', 'prime_parent_uei': 'AAAAAAAAAAP1',
              'sub_uei': 'BBBBBBBBBBB2', 'sub_parent_uei': 'BBBBBBBBBBP2',
              'action_date': '2024-03-01', 'amount': '7.00', 'subaward_type': 'sub-contract',
              'report_id': 'R1', 'subaward_naics': '541511', 'prime_naics': '541512'}
    first = subaward_record(LAYOUT, **values, cell_description='Line one,\nline "two"',
                            cell_subawardee_business_types='a,"b"\r\nc,\rd')
    second = record_of(2)
    rows = read(tmp_path, [first, second]).collect()
    assert rows['record'].to_list() == [1, 2]
    assert {field: rows[field][0] for field in FIELDS} == values
    assert rows['prime_uei'][1] == 'PRIME0000002'
    assert rows['row_digest'].to_list() == [digest(first), digest(second)]


def test_a_quoted_crlf_or_cr_stays_in_the_record(tmp_path):
    record = record_of(1, cell_description='first\r\nsecond\rthird\nfourth')
    rows = read(tmp_path, [record]).collect()
    assert rows['row_digest'].to_list() == [digest(record)]


@pytest.mark.parametrize('change', ['renamed_cell', 'added_cell', 'swapped_cells', 'ragged'])
def test_changed_header_or_ragged_record_fails(change, tmp_path):
    header = list(LAYOUT.header)
    records = [record_of(1)]
    if change == 'renamed_cell':
        header[3] = 'prime_awardee_uei_v2'
    elif change == 'added_cell':
        header.append('subaward_extra_cell')
    elif change == 'swapped_cells':
        header[3], header[13] = header[13], header[3]
    else:
        records.append(record_of(2)[:-1])
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, dataclasses.replace(LAYOUT, header=tuple(header)),
                       {MEMBER_1: records})
    with exactly('ragged subaward record' if change == 'ragged' else 'changed header'):
        read_file(tmp_path, file)
    assert parts(tmp_path) == []


@pytest.mark.parametrize('case', ['padded_cell', 'other_case', 'dropped_last_cell', 'no_header',
                                  'second_member', 'two_byte_order_marks'])
def test_every_member_must_start_with_the_exact_header(case, tmp_path):
    header = list(LAYOUT.header)
    good = member_bytes([record_of(1)])
    if case == 'padded_cell':
        header[0] = ' ' + header[0]
    elif case == 'other_case':
        header[3] = header[3].upper()
    elif case == 'dropped_last_cell':
        header.pop()
    members = {MEMBER_1: member_bytes([record_of(2)], header=header)}
    if case == 'no_header':
        members = {MEMBER_1: b''}
    elif case == 'second_member':
        members = {MEMBER_1: good, MEMBER_2: member_bytes([record_of(2)], header=header[1:])}
    elif case == 'two_byte_order_marks':
        members = {MEMBER_1: codecs.BOM_UTF8 + member_bytes([record_of(2)], bom=True)}
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes(members))
    with exactly('changed header'):
        read_file(tmp_path, file)


@pytest.mark.parametrize('case', ['short', 'long', 'blank_line', 'second_member'])
def test_every_record_must_have_the_header_width(case, tmp_path):
    bad = {'short': record_of(3)[:-1], 'long': record_of(3) + [''], 'blank_line': [],
           'second_member': record_of(3)[1:]}[case]
    members = {MEMBER_1: [record_of(1), record_of(2), bad]}
    if case == 'second_member':
        members = {MEMBER_1: [record_of(1)], MEMBER_2: [record_of(2), bad]}
    with exactly('ragged subaward record'):
        read_all(tmp_path, {2024: members})


def test_each_year_is_read_with_its_own_layout(tmp_path):
    members = {
        2026: {MEMBER_1: [record_of(3, year=2026, cell_subaward_fsrs_report_month='11')]},
        2025: {MEMBER_1: [record_of(2, year=2025, subaward_naics='541512')]},
        2024: {MEMBER_1: [record_of(1, subaward_naics='541511')]},
    }
    result = read_all(tmp_path, members)
    rows = result.rows.collect()
    assert rows['file_year'].to_list() == [2024, 2025, 2026]
    assert rows['prime_uei'].to_list() == ['PRIME0000001', 'PRIME0000002', 'PRIME0000003']
    assert rows['subaward_naics'].to_list() == ['541511', '541512', '']
    assert result.records == {2024: 1, 2025: 1, 2026: 1}
    assert result.members == {2024: (MEMBER_1,), 2025: (MEMBER_1,), 2026: (MEMBER_1,)}
    assert list(result.records) == list(result.members) == list(result.bom) == [2024, 2025, 2026]
    other = tmp_path / 'other'
    other.mkdir()
    file = other / 'FY2026.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record_of(1)]})
    with exactly('changed header'):
        read_file(other, file, year=2026)


def test_an_unmapped_optional_field_reads_as_empty_text(tmp_path):
    layouts = {2024: dataclasses.replace(
        LAYOUT, columns=LAYOUT.columns | {'report_id': None, 'prime_parent_uei': None})}
    record = record_of(1, report_id='R1', prime_parent_uei='0PAR123DEF45')
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record]})
    row = read_file(tmp_path, file, layouts=layouts).rows.collect().row(0, named=True)
    assert row['report_id'] == '' and row['prime_parent_uei'] == ''
    assert row['prime_uei'] == 'PRIME0000001'


def test_bom_is_removed_and_reported(tmp_path):
    records = [record_of(1), record_of(2)]
    plain = read_all(tmp_path / 'plain', {2024: {MEMBER_1: records}})
    marked = read_all(tmp_path / 'marked', {2024: {MEMBER_1: records}}, bom=True)
    assert plain.bom == {2024: False}
    assert marked.bom == {2024: True}
    assert marked.rows.collect().equals(plain.rows.collect())


def test_a_bom_on_any_member_is_reported_for_its_year(tmp_path):
    members = {2024: {MEMBER_1: [record_of(1)]}, 2025: {MEMBER_1: [record_of(2, year=2025)]}}
    files = subaward_files(tmp_path, members)
    files[2024].write_bytes(zip_bytes({
        MEMBER_1: member_bytes([record_of(1)]),
        MEMBER_2: member_bytes([record_of(3)], bom=True)}))
    result = vendor_link_readers.read_subawards(files, TEST_SUBAWARD_LAYOUTS,
                                                tmp_path / 'scratch')
    assert result.bom == {2024: True, 2025: False}
    assert result.rows.collect()['prime_uei'].to_list() == [
        'PRIME0000001', 'PRIME0000003', 'PRIME0000002']


def not_utf8_members(case):
    '''Members whose bytes are not UTF-8 at one place. `MARK` marks that place.'''
    def marked(replacement, **fields):
        return member_bytes([record_of(1, cell_description='MARK', **fields)]).replace(
            b'MARK', replacement)

    if case == 'latin_1_letter':
        return {MEMBER_1: marked(b'caf\xe9')}
    if case == 'windows_1252_quote':
        return {MEMBER_1: marked(b'\x93quoted\x94')}
    if case == 'encoded_surrogate':
        return {MEMBER_1: marked(b'\xed\xa0\x80')}
    if case == 'in_the_header':
        return {MEMBER_1: member_bytes([record_of(1)]).replace(b'description', b'descr\xe9ption')}
    if case == 'cut_at_the_end':
        return {MEMBER_1: member_bytes([record_of(1)]) + b'\xc3'}
    if case == 'after_the_first_chunk':
        long = member_bytes([record_of(1, cell_description='y' * 100_000),
                             record_of(2, cell_description='MARK')])
        return {MEMBER_1: long.replace(b'MARK', b'\xe9')}
    return {MEMBER_1: member_bytes([record_of(1)]), MEMBER_2: marked(b'\xe9')}


@pytest.mark.parametrize('case', ['latin_1_letter', 'windows_1252_quote', 'encoded_surrogate',
                                  'in_the_header', 'cut_at_the_end', 'after_the_first_chunk',
                                  'second_member'])
def test_bytes_that_are_not_utf8_fail(case, tmp_path):
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes(not_utf8_members(case)))
    with exactly('subaward file is not UTF-8'):
        read_file(tmp_path, file)
    if case != 'second_member':
        assert parts(tmp_path) == []


def test_row_digest_marks_identical_rows_only(tmp_path):
    same = record_of(1)
    other = record_of(1, cell_prime_award_project_title='changed')
    rows = read(tmp_path, [same, same, other]).collect()
    digests = rows['row_digest'].to_list()
    assert digests[0] == digests[1] != digests[2]
    assert rows['row_digest'].n_unique() == 2


def test_row_digest_is_the_sha256_of_the_compact_json_of_every_cell(tmp_path):
    record = record_of(1, cell_description='Café "über", – \U0001f600',
                       cell_prime_awardee_name='x\\y')
    row = read(tmp_path, [record]).collect().row(0, named=True)
    expected = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    assert row['row_digest'] == expected
    assert re.fullmatch('[0-9a-f]{64}', row['row_digest'])


def test_identical_rows_in_other_members_and_years_share_a_digest(tmp_path):
    record = record_of(1)
    other_year = record_of(1, year=2025)
    assert other_year == record
    result = read_all(tmp_path, {2024: {MEMBER_1: [record], MEMBER_2: [record]},
                                 2025: {MEMBER_1: [other_year]}})
    assert result.rows.collect()['row_digest'].to_list() == [digest(record)] * 3


def test_scratch_holds_only_the_mapped_columns(tmp_path):
    record = record_of(1, cell_subawardee_name='Fixture Name Co')
    read(tmp_path, [record]).collect()
    files = [path for path in (tmp_path / 'scratch').rglob('*') if path.is_file()]
    assert files
    for path in files:
        assert b'Fixture Name Co' not in path.read_bytes()


def test_every_scratch_file_is_a_part_in_the_subaward_schema(tmp_path):
    record = record_of(1, cell_subawardee_name='Fixture Name Co', cell_description='Free text')
    rows = read(tmp_path, [record, record_of(2)]).collect()
    files = [path for path in (tmp_path / 'scratch').rglob('*') if path.is_file()]
    assert [path.relative_to(tmp_path / 'scratch').as_posix() for path in files] == [
        'subawards/2024-000-00000.parquet']
    assert list(pl.read_parquet_schema(files[0]).items()) == list(SUBAWARD_SCHEMA.items())
    assert not any(value in ('Fixture Name Co', 'Free text')
                   for row in rows.iter_rows() for value in row)


def test_batches_go_to_numbered_scratch_parts(tmp_path, monkeypatch):
    monkeypatch.setattr(vendor_link_readers, 'BATCH_ROWS', 2)
    members = {
        2024: {MEMBER_1: [record_of(n) for n in range(1, 6)],
               MEMBER_2: [record_of(6), record_of(7)],
               'Contracts_Subawards_3.csv': []},
        2025: {MEMBER_1: [record_of(8, year=2025)]},
    }
    result = read_all(tmp_path, members)
    assert parts(tmp_path) == ['2024-000-00000.parquet', '2024-000-00001.parquet',
                               '2024-000-00002.parquet', '2024-001-00000.parquet',
                               '2025-000-00000.parquet']
    folder = tmp_path / 'scratch' / 'subawards'
    assert [pl.read_parquet(folder / name).height for name in parts(tmp_path)] == [2, 2, 1, 2, 1]
    rows = result.rows.collect()
    assert rows['prime_uei'].to_list() == [f'PRIME{n:07d}' for n in range(1, 9)]
    assert rows['record'].to_list() == [1, 2, 3, 4, 5, 1, 2, 1]
    assert result.records == {2024: 7, 2025: 1}
    assert result.members[2024] == (MEMBER_1, MEMBER_2, 'Contracts_Subawards_3.csv')


def test_members_without_records_give_an_empty_frame(tmp_path):
    result = read_all(tmp_path, {2024: {MEMBER_1: [], MEMBER_2: []}})
    assert result.records == {2024: 0}
    assert result.members == {2024: (MEMBER_1, MEMBER_2)}
    frame = result.rows.collect()
    assert frame.height == 0
    assert list(frame.schema.items()) == list(SUBAWARD_SCHEMA.items())


def test_a_part_left_in_scratch_makes_the_row_count_differ(tmp_path):
    folder = tmp_path / 'scratch' / 'subawards'
    folder.mkdir(parents=True)
    stale = {'file_year': [2023], 'member': ['old.csv'], 'record': [1],
             **{field: [''] for field in FIELDS}, 'row_digest': ['0' * 64]}
    pl.DataFrame(stale, schema=SUBAWARD_SCHEMA).write_parquet(folder / '2023-000-00000.parquet')
    with exactly('row count differs'):
        read(tmp_path, [record_of(1)])


def test_a_field_longer_than_the_csv_default_reads_and_the_limit_is_restored(
        tmp_path, field_size_limit):
    record = record_of(1, cell_description='x' * 200_000)
    rows = read(tmp_path, [record]).collect()
    assert rows['row_digest'].to_list() == [digest(record)]
    assert csv.field_size_limit() == field_size_limit


def test_a_field_over_the_limit_is_malformed_and_the_limit_is_restored(
        tmp_path, monkeypatch, field_size_limit):
    monkeypatch.setattr(vendor_link_readers, 'FIELD_SIZE_LIMIT', 64)
    with exactly('malformed subaward CSV'):
        read(tmp_path, [record_of(1, cell_description='x' * 65)])
    assert csv.field_size_limit() == field_size_limit
    assert parts(tmp_path) == []


@pytest.mark.parametrize('last_cell', ['"open', '"x"y'],
                         ids=['unclosed_quote_in_the_last_cell', 'text_after_a_closing_quote'])
def test_a_quote_that_breaks_the_csv_rules_is_malformed(last_cell, tmp_path):
    content = (member_bytes([record_of(1)]) + broken_quote_line(2, last_cell)
               + csv_lines([record_of(3), record_of(4)]))
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes({MEMBER_1: content}))
    with exactly('malformed subaward CSV'):
        read_file(tmp_path, file)
    assert parts(tmp_path) == []


def test_the_limit_is_restored_after_a_refusal(tmp_path, field_size_limit):
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record_of(1), []]})
    with exactly('ragged subaward record'):
        read_file(tmp_path, file)
    assert csv.field_size_limit() == field_size_limit


def test_subaward_headers_describes_every_member_in_name_order(tmp_path):
    latin = member_bytes([record_of(6, cell_description='MARK')]).replace(b'MARK', b'caf\xe9')
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes({
        'readme.txt': b'About these files\r\nOne line\r\n',
        MEMBER_2: member_bytes([record_of(4) + ['extra'], record_of(5)], bom=True),
        'latin.csv': latin,
        'folder/': b'',
        MEMBER_1: member_bytes([record_of(1, cell_description='a,\r\nb'), record_of(2)[:-1],
                                record_of(3)]),
    }))
    header = list(LAYOUT.header)
    assert vendor_link_readers.subaward_headers(file) == {'members': [
        {'name': MEMBER_1, 'header': header, 'bom': False, 'utf8_valid': True, 'records': 3,
         'ragged': 1},
        {'name': MEMBER_2, 'header': header, 'bom': True, 'utf8_valid': True, 'records': 2,
         'ragged': 1},
        {'name': 'folder/', 'header': None, 'bom': False, 'utf8_valid': True, 'records': 0,
         'ragged': 0},
        {'name': 'latin.csv', 'header': header, 'bom': False, 'utf8_valid': False,
         'records': 1, 'ragged': 0},
        {'name': 'readme.txt', 'header': ['About these files'], 'bom': False,
         'utf8_valid': True, 'records': 1, 'ragged': 0},
    ]}


def test_subaward_headers_reads_long_fields_and_restores_the_limit(tmp_path, field_size_limit):
    file = tmp_path / 'FY2024.zip'
    write_subaward_zip(file, LAYOUT, {MEMBER_1: [record_of(1, cell_description='x' * 200_000)]})
    members = vendor_link_readers.subaward_headers(file)['members']
    assert [(member['records'], member['ragged']) for member in members] == [(1, 0)]
    assert csv.field_size_limit() == field_size_limit


def malformed_member(case):
    '''Member bytes that break the CSV rules at one place.'''
    if case == 'unclosed_quote_in_the_header':
        return b'prime_award_unique_key,"open\r\n' + csv_lines([record_of(1), record_of(2)])
    if case == 'unclosed_quote_in_a_later_record':
        return (member_bytes([record_of(1)]) + broken_quote_line(2, '"open')
                + csv_lines([record_of(3)]))
    if case == 'text_after_a_closing_quote':
        return member_bytes([record_of(1)]) + broken_quote_line(2, '"x"y')
    if case == 'after_a_byte_that_is_not_utf8':
        return (member_bytes([record_of(1)]).replace(b'description', b'descr\xe9ption', 1)
                + broken_quote_line(2, '"open'))
    return member_bytes([record_of(1, cell_description='x' * 65)])


@pytest.mark.parametrize('case', ['unclosed_quote_in_the_header',
                                  'unclosed_quote_in_a_later_record',
                                  'text_after_a_closing_quote', 'after_a_byte_that_is_not_utf8',
                                  'field_over_the_limit'])
def test_subaward_headers_refuses_a_member_that_breaks_the_csv_rules(
        case, tmp_path, monkeypatch, field_size_limit):
    if case == 'field_over_the_limit':
        monkeypatch.setattr(vendor_link_readers, 'FIELD_SIZE_LIMIT', 64)
    file = tmp_path / 'FY2024.zip'
    file.write_bytes(zip_bytes({'readme.txt': b'About these files\r\n',
                                MEMBER_1: malformed_member(case)}))
    with exactly('malformed subaward CSV'):
        vendor_link_readers.subaward_headers(file)
    assert csv.field_size_limit() == field_size_limit


def firm(n, **fields):
    '''An extract data line for a made-up UEI numbered `n`.'''
    values = {'uei': f'FIRMA{n:07d}', 'registration_status': 'A', 'last_update_date': '20250101',
              'primary_naics': '541511', 'naics_code_string': '541511Y~541512N'} | fields
    return extract_line(EXTRACT, **values)


def extract_file(directory, lines, *, layout=EXTRACT, member=EXTRACT_MEMBER, **framing):
    file = directory / EXTRACT_ZIP
    write_extract_zip(file, layout, lines, member=member, **framing)
    return file


def raw_extract(directory, members):
    file = directory / EXTRACT_ZIP
    file.write_bytes(zip_bytes(members))
    return file


def test_extract_keeps_only_registered_positions(tmp_path):
    file = extract_file(tmp_path, [firm(1), firm(2, evs_source='D&B')])
    frame = vendor_link_readers.read_extract(file, TEST_EXTRACT_LAYOUT)
    assert list(frame.schema.items()) == list(EXTRACT_SCHEMA.items())
    assert DNB_SENTINEL not in frame.write_csv()


def test_extract_reads_each_mapped_position_as_delivered(tmp_path):
    first = {'uei': ' 0ABC123DEF45 ', 'registration_status': 'A',
             'last_update_date': '20220404', 'primary_naics': '000000',
             'naics_code_string': '541511Y~caféN', 'evs_source': 'D&B'}
    second = {'uei': '1xyz987wvu65', 'registration_status': 'E', 'last_update_date': '',
              'primary_naics': '', 'naics_code_string': '', 'evs_source': ''}
    lines = [extract_line(EXTRACT, **first), extract_line(EXTRACT, **second)]
    assert all(DNB_SENTINEL in line for line in lines)
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, lines), EXTRACT)
    assert frame.rows(named=True) == [{'line': 2, **first}, {'line': 3, **second}]
    assert DNB_SENTINEL not in frame.write_csv()


@pytest.mark.parametrize('defect', ['no_bof', 'no_eof', 'short_line', 'long_line',
                                    'no_record_end', 'second_member'])
def test_extract_framing_and_field_count_failures(defect, tmp_path):
    fields = firm(3).split('|')
    lines = [firm(1), firm(2)]
    framing = {}
    if defect == 'no_bof':
        framing['bof'] = firm(3)
    elif defect == 'no_eof':
        framing['eof'] = firm(3)
    elif defect == 'short_line':
        lines.append('|'.join(fields[:-2] + fields[-1:]))
    elif defect == 'long_line':
        lines.append('|'.join(fields[:-1] + ['', fields[-1]]))
    elif defect == 'no_record_end':
        lines.append('|'.join(fields[:-1] + ['']))
    file = extract_file(tmp_path, lines, **framing)
    if defect == 'second_member':
        with zipfile.ZipFile(file) as archive:
            content = archive.read(EXTRACT_MEMBER)
        file.write_bytes(zip_bytes({EXTRACT_MEMBER: content,
                                    'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261103.dat': content}))
    if defect in ('short_line', 'long_line'):
        # Owner decision 2026-11-19: a line of the wrong field count is skipped, not refused.
        frame = vendor_link_readers.read_extract(file, TEST_EXTRACT_LAYOUT)
        assert frame['line'].to_list() == [2, 3]
        return
    message = {'no_bof': 'missing extract framing', 'no_eof': 'missing extract framing',
               'no_record_end': 'missing record end',
               'second_member': 'unexpected extract member'}[defect]
    with exactly(message):
        vendor_link_readers.read_extract(file, TEST_EXTRACT_LAYOUT)


EXTRACT_MEMBER_CASES = {
    'no_member': (),
    'suffix': (EXTRACT_MEMBER + '.bak',),
    'prefix': ('x' + EXTRACT_MEMBER,),
    'other_name': ('readme.txt',),
    'two_matching': (EXTRACT_MEMBER, 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261103.dat'),
    'and_a_folder': ('folder/', EXTRACT_MEMBER),
    'v3': ('SAM_PUBLIC_UTF-8_MONTHLY_V3_20261102.dat',),
}


@pytest.mark.parametrize('reader', ['read_extract', 'extract_summary'])
@pytest.mark.parametrize('case', list(EXTRACT_MEMBER_CASES))
def test_the_extract_has_exactly_one_fully_matching_member(case, reader, tmp_path):
    good = f'{BOF}\r\n{firm(1)}\r\n{EOF}'.encode()
    members = {name: b'' if name.endswith('/') else good for name in EXTRACT_MEMBER_CASES[case]}
    with exactly('unexpected extract member'):
        getattr(vendor_link_readers, reader)(raw_extract(tmp_path, members), EXTRACT)


@pytest.mark.parametrize('separator, tail', [('\r\n', ''), ('\r\n', '\r\n'), ('\n', ''),
                                             ('\n', '\n')], ids=['crlf', 'crlf_after_eof',
                                                                 'lf', 'lf_after_eof'])
def test_one_line_end_is_removed_from_each_line(separator, tail, tmp_path):
    text = separator.join([BOF, firm(1), firm(2), EOF]) + tail
    frame = vendor_link_readers.read_extract(
        raw_extract(tmp_path, {EXTRACT_MEMBER: text.encode()}), EXTRACT)
    assert frame['uei'].to_list() == ['FIRMA0000001', 'FIRMA0000002']
    assert frame['line'].to_list() == [2, 3]


def test_a_carriage_return_inside_a_value_does_not_end_the_line(tmp_path):
    line = firm(1, naics_code_string='541511Y\r541512N')
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, [line, firm(2)]), EXTRACT)
    assert frame['naics_code_string'].to_list() == ['541511Y\r541512N', '541511Y~541512N']
    assert frame['line'].to_list() == [2, 3]


def test_only_one_carriage_return_is_removed(tmp_path):
    text = f'{BOF}\r\n{firm(1)}\r\r\n{EOF}'
    with exactly('missing record end'):
        vendor_link_readers.read_extract(
            raw_extract(tmp_path, {EXTRACT_MEMBER: text.encode()}), EXTRACT)


def test_a_quote_is_literal_text(tmp_path):
    fields = firm(1, naics_code_string='541511"Y').split('|')
    fields[19], fields[20] = '"open', 'close"'
    frame = vendor_link_readers.read_extract(
        extract_file(tmp_path, ['|'.join(fields), firm(2, uei='"FIRMA000002')]), EXTRACT)
    assert frame['naics_code_string'].to_list() == ['541511"Y', '541511Y~541512N']
    assert frame['uei'].to_list() == ['FIRMA0000001', '"FIRMA000002']


@pytest.mark.parametrize('framing', [
    {'bof': 'X' + BOF},
    {'bof': BOF.lower()},
    {'bof': BOF.replace('00000000 ', '00000000', 1)},
    {'eof': 'X' + EOF},
    {'eof': EOF.lower()},
    {'eof': EOF.replace('00000000 ', '00000000', 1)},
    {'bof': EOF, 'eof': BOF},
    {'bof': BOF.replace(' V2 ', ' V3 ')},
    {'eof': EOF.replace(' V2 ', ' V3 ')},
], ids=['bof_inside', 'bof_case', 'bof_without_space', 'eof_inside', 'eof_case',
        'eof_without_space', 'swapped', 'bof_v3', 'eof_v3'])
def test_the_framing_lines_start_with_their_prefixes(framing, tmp_path):
    with exactly('missing extract framing'):
        vendor_link_readers.read_extract(extract_file(tmp_path, [firm(1)], **framing), EXTRACT)


def test_the_eof_line_must_be_the_last_line(tmp_path):
    # The EOF line inside the data has one field, so it is skipped, and the last line fails.
    file = extract_file(tmp_path, [firm(1), EOF], eof=firm(2))
    with exactly('missing extract framing'):
        vendor_link_readers.read_extract(file, EXTRACT)


@pytest.mark.parametrize('text', ['', BOF, BOF + '\r\n'], ids=['empty', 'bof', 'bof_line'])
def test_a_member_without_two_framing_lines_fails(text, tmp_path):
    with exactly('missing extract framing'):
        vendor_link_readers.read_extract(
            raw_extract(tmp_path, {EXTRACT_MEMBER: text.encode()}), EXTRACT)


def test_an_extract_without_data_lines_gives_an_empty_frame(tmp_path):
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, []), EXTRACT)
    assert frame.height == 0
    assert list(frame.schema.items()) == list(EXTRACT_SCHEMA.items())


def test_the_extract_delimiter_comes_from_the_layout(tmp_path):
    layout = dataclasses.replace(EXTRACT, delimiter='\t')
    line = extract_line(layout, uei='FIRMA0000001', naics_code_string='541511Y|541512N')
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, [line], layout=layout),
                                             layout)
    assert frame.select('uei', 'naics_code_string').rows() == [('FIRMA0000001',
                                                                '541511Y|541512N')]


def test_without_a_record_end_the_last_field_is_not_checked(tmp_path):
    layout = dataclasses.replace(EXTRACT, record_end=None)
    fields = extract_line(layout, uei='FIRMA0000002').split('|')
    fields[-1] = 'x'
    lines = [extract_line(layout, uei='FIRMA0000001'), '|'.join(fields)]
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, lines, layout=layout), layout)
    assert frame['uei'].to_list() == ['FIRMA0000001', 'FIRMA0000002']


def test_an_unmapped_evs_source_reads_as_empty_text(tmp_path):
    layout = dataclasses.replace(EXTRACT, positions=EXTRACT.positions | {'evs_source': None},
                                 evs_dnb=frozenset())
    fields = extract_line(layout, uei='FIRMA0000001').split('|')
    fields[32] = 'D&B'
    frame = vendor_link_readers.read_extract(
        extract_file(tmp_path, ['|'.join(fields)], layout=layout), layout)
    assert frame['evs_source'].to_list() == ['']


def test_reading_the_extract_writes_no_file(tmp_path):
    file = extract_file(tmp_path, [firm(1)])
    vendor_link_readers.read_extract(file, EXTRACT)
    vendor_link_readers.extract_summary(file, EXTRACT)
    assert [path.name for path in tmp_path.rglob('*')] == [EXTRACT_ZIP]


def test_extract_summary_counts_the_lines_and_shows_matching_framing(tmp_path):
    fields = firm(3).split('|')
    lines = [firm(1), firm(2), '|'.join(fields[:-2] + fields[-1:]),
             '|'.join(fields[:-1] + ['', fields[-1]]), '|'.join(fields[:-1] + [''])]
    summary = vendor_link_readers.extract_summary(extract_file(tmp_path, lines), EXTRACT)
    assert summary == {'member': EXTRACT_MEMBER, 'data_lines': 5,
                       'field_counts': {40: 3, 39: 1, 41: 1}, 'unreadable_lines': 2,
                       'bof_matches': True, 'eof_matches': True, 'record_end_matches': 4,
                       'bof': BOF, 'eof': EOF}


@pytest.mark.parametrize('framing', [
    {'bof': firm(8)},
    {'eof': firm(9)},
    {'bof': firm(8), 'eof': firm(9)},
    {'bof': 'X' + BOF},
    {'eof': 'X' + EOF},
    {'bof': BOF.replace('00000000 ', '00000000', 1)},
    {'eof': EOF.replace('00000000 ', '00000000', 1)},
    {'bof': BOF.replace(' V2 ', ' V3 ')},
    {'eof': EOF.replace(' V2 ', ' V3 ')},
], ids=['bof', 'eof', 'both', 'bof_inside', 'eof_inside', 'bof_without_space',
        'eof_without_space', 'bof_v3', 'eof_v3'])
def test_extract_summary_hides_framing_lines_that_do_not_match(framing, tmp_path):
    summary = vendor_link_readers.extract_summary(
        extract_file(tmp_path, [firm(1)], **framing), EXTRACT)
    assert summary['bof_matches'] is ('bof' not in framing)
    assert summary['eof_matches'] is ('eof' not in framing)
    assert ('bof' in summary) is ('bof' not in framing)
    assert ('eof' in summary) is ('eof' not in framing)
    text = json.dumps(summary)
    assert DNB_SENTINEL not in text
    assert not any(value in text for value in framing.values())
    assert summary['data_lines'] == 1 and summary['field_counts'] == {40: 1}


def peak_memory(read):
    '''The peak traced Python memory, in bytes, while `read()` runs, and its result.'''
    tracemalloc.start()
    try:
        result = read()
        return tracemalloc.get_traced_memory()[1], result
    finally:
        tracemalloc.stop()


def test_subaward_members_stream_without_holding_their_text(tmp_path):
    filler = 'z' * 16_000
    records = [record_of(n, cell_description=filler) for n in range(1, 1001)]
    files = subaward_files(tmp_path, {2024: {MEMBER_1: records}})
    peak, result = peak_memory(lambda: vendor_link_readers.read_subawards(
        files, TEST_SUBAWARD_LAYOUTS, tmp_path / 'scratch'))
    assert result.records == {2024: 1000}
    # The text is 16 MB. Streaming measured 0.8 MB.
    assert peak < 4_000_000


def test_the_extract_streams_line_by_line(tmp_path):
    fields = firm(1).split('|')
    fields[19] = 'z' * 8_000
    file = extract_file(tmp_path, ['|'.join(fields)] * 1000)
    peak, frame = peak_memory(lambda: vendor_link_readers.read_extract(file, EXTRACT))
    assert frame.height == 1000
    summary_peak, summary = peak_memory(lambda: vendor_link_readers.extract_summary(file, EXTRACT))
    assert summary['data_lines'] == 1000
    # The text is 8 MB. Streaming measured 0.4 MB and 0.25 MB.
    assert peak < 2_000_000 and summary_peak < 2_000_000


@pytest.mark.parametrize('text, expected', [
    ('', {'data_lines': 0, 'field_counts': {}, 'unreadable_lines': 0, 'bof_matches': False,
          'eof_matches': False, 'record_end_matches': 0}),
    (BOF + '\r\n', {'data_lines': 0, 'field_counts': {}, 'unreadable_lines': 0,
                    'bof_matches': True, 'eof_matches': False, 'record_end_matches': 0,
                    'bof': BOF}),
    (f'{BOF}\r\n{EOF}', {'data_lines': 0, 'field_counts': {}, 'unreadable_lines': 0,
                         'bof_matches': True, 'eof_matches': True, 'record_end_matches': 0,
                         'bof': BOF, 'eof': EOF}),
], ids=['empty', 'bof_only', 'framing_only'])
def test_extract_summary_of_a_short_member(text, expected, tmp_path):
    summary = vendor_link_readers.extract_summary(
        raw_extract(tmp_path, {EXTRACT_MEMBER: text.encode()}), EXTRACT)
    assert summary == {'member': EXTRACT_MEMBER, **expected}


def test_extract_summary_without_a_record_end(tmp_path):
    layout = dataclasses.replace(EXTRACT, record_end=None)
    lines = [extract_line(layout, uei='FIRMA0000001')]
    summary = vendor_link_readers.extract_summary(
        extract_file(tmp_path, lines, layout=layout), layout)
    assert summary['record_end_matches'] is None
    assert summary['field_counts'] == {40: 1}


# ---- lines of the wrong field count (owner decision 2026-11-19: skip and count them)

def widened(line, change):
    '''`line` with `change` empty fields added before its last field, or `-change` fields
    removed before it. The last field, the record end, stays last.'''
    fields = line.split('|')
    if change > 0:
        fields[-1:-1] = [''] * change
    else:
        del fields[change - 1:-1]
    return '|'.join(fields)


@pytest.mark.parametrize('change', [-1, 1], ids=['short', 'long'])
def test_a_line_of_the_wrong_field_count_is_skipped(change, tmp_path):
    lines = [firm(1), widened(firm(9), change), firm(2)]
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, lines), EXTRACT)
    assert frame.select('line', 'uei').rows() == [(2, 'FIRMA0000001'), (4, 'FIRMA0000002')]


def test_short_and_long_lines_are_skipped_together(tmp_path):
    lines = [firm(1), widened(firm(7), 2), firm(2), widened(firm(8), -1), widened(firm(9), 1),
             firm(3)]
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, lines), EXTRACT)
    assert frame.select('line', 'uei').rows() == [
        (2, 'FIRMA0000001'), (4, 'FIRMA0000002'), (7, 'FIRMA0000003')]
    assert DNB_SENTINEL not in frame.write_csv()


@pytest.mark.parametrize('line', ['|'.join(firm(9).split('|')[:-1]), firm(9) + '|x'],
                         ids=['short', 'long'])
def test_a_line_of_the_wrong_field_count_is_skipped_without_a_record_end(line, tmp_path):
    frame = vendor_link_readers.read_extract(extract_file(tmp_path, [firm(1), line, firm(2)]),
                                             EXTRACT)
    assert frame['line'].to_list() == [2, 4]


def test_unreadable_extract_lines_lists_each_skipped_line(tmp_path):
    lines = [firm(1), widened(firm(7, uei=' FIRMA0000007\t'), 2), firm(2),
             widened(firm(8), -1), widened(firm(9), 1), firm(3)]
    frame = vendor_link_readers.unreadable_extract_lines(extract_file(tmp_path, lines), EXTRACT)
    assert list(UNREADABLE_SCHEMA.items()) == [('line', pl.Int64), ('uei', pl.String),
                                               ('fields', pl.Int64)]
    assert list(frame.schema.items()) == list(UNREADABLE_SCHEMA.items())
    assert frame.rows() == [(3, ' FIRMA0000007\t', 42), (5, 'FIRMA0000008', 39),
                            (6, 'FIRMA0000009', 41)]
    assert DNB_SENTINEL not in frame.write_csv()


def test_extract_summary_counts_each_unreadable_line(tmp_path):
    lines = [firm(1), widened(firm(7), 1), widened(firm(8), 1), widened(firm(9), -1), firm(2)]
    summary = vendor_link_readers.extract_summary(extract_file(tmp_path, lines), EXTRACT)
    assert (summary['data_lines'], summary['field_counts'], summary['unreadable_lines']) == (
        5, {40: 2, 41: 2, 39: 1}, 3)


@pytest.mark.parametrize('lines', [[], [firm(1), firm(2)]], ids=['no_data_line', 'readable'])
def test_unreadable_extract_lines_is_empty_when_every_line_is_readable(lines, tmp_path):
    frame = vendor_link_readers.unreadable_extract_lines(extract_file(tmp_path, lines), EXTRACT)
    assert frame.height == 0
    assert list(frame.schema.items()) == list(UNREADABLE_SCHEMA.items())


@pytest.mark.parametrize('position', [1, 3])
def test_the_unreadable_uei_comes_from_the_registered_position(position, tmp_path):
    layout = dataclasses.replace(EXTRACT, positions=EXTRACT.positions | {'uei': position})
    line = widened(extract_line(layout, uei='FIRMA0000005', registration_status='A'), 1)
    frame = vendor_link_readers.unreadable_extract_lines(
        extract_file(tmp_path, [line], layout=layout), layout)
    assert frame.rows() == [(2, 'FIRMA0000005', 41)]


def test_a_line_shorter_than_the_uei_position_has_an_empty_uei(tmp_path):
    lines = [firm(1), 'FIRMA0000004', 'FIRMA|FIRMA0000005', '', firm(2)]
    file = extract_file(tmp_path, lines)
    assert vendor_link_readers.unreadable_extract_lines(file, EXTRACT).rows() == [
        (3, '', 1), (4, 'FIRMA0000005', 2), (5, '', 1)]
    assert vendor_link_readers.read_extract(file, EXTRACT)['line'].to_list() == [2, 6]


def test_unreadable_extract_lines_does_not_check_the_record_end(tmp_path):
    lines = ['|'.join(firm(1).split('|')[:-1] + ['']), widened(firm(2), 1)]
    frame = vendor_link_readers.unreadable_extract_lines(extract_file(tmp_path, lines), EXTRACT)
    assert frame.rows() == [(3, 'FIRMA0000002', 41)]


@pytest.mark.parametrize('case', list(EXTRACT_MEMBER_CASES))
def test_unreadable_extract_lines_needs_exactly_one_fully_matching_member(case, tmp_path):
    good = f'{BOF}\r\n{widened(firm(1), 1)}\r\n{EOF}'.encode()
    members = {name: b'' if name.endswith('/') else good for name in EXTRACT_MEMBER_CASES[case]}
    with exactly('unexpected extract member'):
        vendor_link_readers.unreadable_extract_lines(raw_extract(tmp_path, members), EXTRACT)


LONG_LINE = widened(firm(1), 1)


@pytest.mark.parametrize('text', [
    '', BOF, f'{BOF}\r\n{LONG_LINE}', f'{LONG_LINE}\r\n{EOF}',
    f'X{BOF}\r\n{LONG_LINE}\r\n{EOF}', f'{BOF}\r\n{LONG_LINE}\r\nX{EOF}',
    f'{EOF}\r\n{LONG_LINE}\r\n{BOF}',
], ids=['empty', 'bof', 'no_eof', 'no_bof', 'bof_inside', 'eof_inside', 'swapped'])
def test_unreadable_extract_lines_needs_the_framing_lines(text, tmp_path):
    with exactly('missing extract framing'):
        vendor_link_readers.unreadable_extract_lines(
            raw_extract(tmp_path, {EXTRACT_MEMBER: text.encode()}), EXTRACT)


def test_unreadable_extract_lines_streams_line_by_line(tmp_path):
    fields = firm(1).split('|')
    fields[19] = 'z' * 8_000
    file = extract_file(tmp_path, [widened('|'.join(fields), 1)] * 1000)
    peak, frame = peak_memory(lambda: vendor_link_readers.unreadable_extract_lines(file, EXTRACT))
    assert frame.height == 1000
    # The text is 8 MB.
    assert peak < 2_000_000
