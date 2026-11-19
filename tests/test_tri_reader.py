'''The TRI raw CSV reader: mapping, the three checks, transcoding and the window.'''

import csv
import io
from dataclasses import replace
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from tri_fixtures import (
    BYTE_ORDER_MARK,
    production_layout,
    rows_frame,
    seed_tri_files,
    tri_row,
    write_tri_csv,
)

from embedding_data import tri_raw
from embedding_data.tri_layout import load_layouts
from embedding_data.tri_reader import READ_SCHEMA, needs_transcoding, read_window, read_year

LAYOUTS = load_layouts()
RECORDED = date(2025, 11, 5)
# Synthetic rows: made-up facilities, parents and D&B numbers, never EPA data.
ACME = dict(
    state='TX', primary_naics='325199', naics_2='325110', naics_3='325120', naics_4='325130',
    naics_5='325140', naics_6='325150', parent_name='Acme Corp', parent_dnb='001234567',
    standardized_parent='ACME CORP', standardized_foreign_parent='ACME ABROAD')


def acme(year: int) -> dict[str, str]:
    '''The fields of the Acme rows. The 2022 layout maps no foreign parent field.'''
    return {name: value for name, value in ACME.items()
            if year > 2022 or name != 'standardized_foreign_parent'}


def three_rows(year: int = 2023) -> list[dict[str, str]]:
    return [tri_row(year, f'T{n}', **acme(year)) for n in (1, 2, 3)]


def accented_rows() -> list[dict[str, str]]:
    return [tri_row(2023, 'T1', parent_name='Café Holdings', standardized_parent='CAFÉ HOLDINGS'),
            tri_row(2023, 'T2', parent_name='Zoë & Sons, € 5', standardized_parent='ZOË & SONS')]


def write(tmp_path: Path, year: int, rows: list[dict[str, str]], *, folder: str = 'raw',
          **options) -> Path:
    '''Write one TRI file under `tmp_path / folder` and return its path.'''
    file = tmp_path / folder / f'{year}_us.csv'
    file.parent.mkdir(parents=True, exist_ok=True)
    write_tri_csv(file, year, rows, **options)
    return file


def read(tmp_path: Path, file: Path, year: int) -> pl.LazyFrame:
    return read_year(file, LAYOUTS[year], tmp_path / 'scratch')


def edit_text(file: Path, edit) -> None:
    file.write_text(edit(file.read_text(encoding='utf-8')), encoding='utf-8', newline='')


def edit_line(file: Path, index: int, edit) -> None:
    '''Replace line `index` of a file whose records are single lines.'''
    def edit_lines(text: str) -> str:
        lines = text.split('\n')
        lines[index] = edit(lines[index])
        return '\n'.join(lines)
    edit_text(file, edit_lines)


def entries(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir()) if directory.exists() else []


def test_reads_the_mapped_columns_as_strings(tmp_path):
    rows = [tri_row(2023, 'T1', form='A', federal=True, **ACME),
            tri_row(2023, 'T2', form='R', federal=False, **{**ACME, 'parent_dnb': '000000042'})]
    frame = read(tmp_path, write(tmp_path, 2023, rows), 2023)
    assert list(frame.collect_schema().items()) == list(READ_SCHEMA.items())
    assert frame.collect().to_dicts() == [
        {'year': 2023, 'reporting_year': '2023', 'trifd': 'T1', 'form_type': 'A', 'state': 'TX',
         'federal': 'YES', 'primary_naics': '325199', 'naics_2': '325110', 'naics_3': '325120',
         'naics_4': '325130', 'naics_5': '325140', 'naics_6': '325150',
         'parent_name': 'Acme Corp', 'parent_dnb': '001234567',
         'standardized_parent': 'ACME CORP', 'standardized_foreign_parent': 'ACME ABROAD'},
        {'year': 2023, 'reporting_year': '2023', 'trifd': 'T2', 'form_type': 'R', 'state': 'TX',
         'federal': 'NO', 'primary_naics': '325199', 'naics_2': '325110', 'naics_3': '325120',
         'naics_4': '325130', 'naics_5': '325140', 'naics_6': '325150',
         'parent_name': 'Acme Corp', 'parent_dnb': '000000042',
         'standardized_parent': 'ACME CORP', 'standardized_foreign_parent': 'ACME ABROAD'},
    ]


def test_cells_keep_their_exact_text(tmp_path):
    rows = [tri_row(2023, 'T1', parent_name='  Acme, "Inc."  ', parent_dnb='NA',
                    standardized_parent='NA', primary_naics='0325', naics_2='31M')]
    row = read(tmp_path, write(tmp_path, 2023, rows), 2023).collect().row(0, named=True)
    assert row['parent_name'] == '  Acme, "Inc."  '
    assert (row['parent_dnb'], row['standardized_parent']) == ('NA', 'NA')
    assert (row['primary_naics'], row['naics_2']) == ('0325', '31M')


def test_blank_cells_read_as_empty_strings(tmp_path):
    plain = write(tmp_path, 2023, [tri_row(2023, 'T1', form_type='', federal='')])
    quoted = write(tmp_path, 2023, [tri_row(2023, 'T1', form_type='', federal='')],
                   folder='quoted')
    # The same record with every blank cell written as a quoted empty string.
    edit_line(quoted, 1, lambda line: ','.join(
        '""' if cell == '' else cell for cell in line.split(',')))
    assert '""' in quoted.read_text()
    for file in (plain, quoted):
        frame = read(tmp_path, file, 2023).collect()
        assert sum(frame.null_count().row(0)) == 0
        assert frame.row(0, named=True) == {
            'year': 2023, 'reporting_year': '2023', 'trifd': 'T1', 'form_type': '',
            'state': '', 'federal': '', 'primary_naics': '', 'naics_2': '', 'naics_3': '',
            'naics_4': '', 'naics_5': '', 'naics_6': '', 'parent_name': '', 'parent_dnb': '',
            'standardized_parent': '', 'standardized_foreign_parent': ''}


def test_a_header_only_file_reads_no_rows(tmp_path):
    frame = read(tmp_path, write(tmp_path, 2023, []), 2023)
    assert list(frame.collect_schema().items()) == list(READ_SCHEMA.items())
    assert frame.collect().height == 0


def change_header(file: Path, change) -> None:
    def edit(head: str) -> str:
        buffer = io.StringIO(newline='')
        csv.writer(buffer, lineterminator='').writerow(change(next(csv.reader([head]))))
        return buffer.getvalue()
    edit_line(file, 0, edit)


@pytest.mark.parametrize('change', [
    lambda cells: [cells[0] + ' ID', *cells[1:]],
    lambda cells: [*cells[:3], cells[3] + ' ', *cells[4:]],
    lambda cells: [*cells[:3], cells[3].lower(), *cells[4:]],
    lambda cells: [*cells, '123. ADDED'],
    lambda cells: cells[:-1],
    lambda cells: [cells[1], cells[0], *cells[2:]],
], ids=['renamed_cell', 'padded_cell', 'recased_cell', 'added_column', 'dropped_column',
        'swapped_order'])
def test_changed_header_fails(change, tmp_path):
    file = write(tmp_path, 2023, three_rows())
    change_header(file, change)
    with pytest.raises(ValueError, match='changed header'):
        read(tmp_path, file, 2023)


def test_a_file_with_no_header_fails(tmp_path):
    file = write(tmp_path, 2023, three_rows())
    file.write_bytes(b'')
    with pytest.raises(ValueError, match='changed header'):
        read(tmp_path, file, 2023)


@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('value', ['2022', '2024', '', '2023.0', '20230', 'x'])
def test_reporting_year_mismatch_fails(position, value, tmp_path):
    rows = three_rows()
    rows[position] = tri_row(2023, 'T9', reporting_year=value)
    file = write(tmp_path, 2023, rows)
    with pytest.raises(ValueError, match='reporting year mismatch'):
        read(tmp_path, file, 2023)


@pytest.mark.parametrize('file_year, layout_year', [(2022, 2023), (2023, 2024), (2024, 2022)])
def test_each_file_is_checked_against_the_year_of_its_layout(file_year, layout_year, tmp_path):
    file = write(tmp_path, file_year, three_rows(file_year))
    with pytest.raises(ValueError, match='reporting year mismatch'):
        read_year(file, LAYOUTS[layout_year], tmp_path / 'scratch')


def test_reporting_year_is_compared_stripped_and_kept_as_delivered(tmp_path):
    rows = [tri_row(2023, 'T1', reporting_year=' 2023'),
            tri_row(2023, 'T2', reporting_year='2023 ')]
    frame = read(tmp_path, write(tmp_path, 2023, rows), 2023)
    assert frame.collect()['reporting_year'].to_list() == [' 2023', '2023 ']


# Each oddity of a file, its options for `write_tri_csv`, and whether it needs transcoding.
ODDITIES = {
    'bom': (dict(bom=True), True),
    'cp1252': (dict(encoding='cp1252'), True),
    'bom_and_cp1252': (dict(bom=True, encoding='cp1252'), True),
    'bom_crlf_and_cp1252': (dict(bom=True, newline='\r\n', encoding='cp1252'), True),
    'crlf': (dict(newline='\r\n'), False),
    'utf8': (dict(), False),
}


def read_plain_and_odd(tmp_path, **options):
    '''Read the accented rows from a plain UTF-8 file and from a file written with `options`.'''
    scratch = tmp_path / 'scratch'
    rows = accented_rows()
    plain = read_window({2023: write(tmp_path, 2023, rows, folder='plain')}, LAYOUTS, scratch)
    odd = read_window({2023: write(tmp_path, 2023, rows, folder='odd', **options)},
                      LAYOUTS, scratch)
    return plain, odd


def test_bom_crlf_and_cp1252_read_like_plain_utf8(tmp_path):
    (plain, plain_years), (odd, transcoded) = read_plain_and_odd(
        tmp_path, bom=True, newline='\r\n', encoding='cp1252')
    assert odd.collect().equals(plain.collect())
    assert plain.collect()['parent_name'].to_list() == ['Café Holdings', 'Zoë & Sons, € 5']
    assert plain_years == []
    assert transcoded == [2023]


@pytest.mark.parametrize('name', ODDITIES)
def test_each_oddity_reads_like_plain_utf8(name, tmp_path):
    options, transcodes = ODDITIES[name]
    (plain, _), (odd, transcoded) = read_plain_and_odd(tmp_path, **options)
    assert odd.collect().equals(plain.collect())
    assert transcoded == ([2023] if transcodes else [])


def test_utf8_and_windows_1252_lines_in_one_file_read_by_line(tmp_path):
    rows = [tri_row(2023, 'T1', parent_name='Zoë Holdings, UTF-8'),
            tri_row(2023, 'T2', parent_name='Café Holdings, Windows-1252'),
            tri_row(2023, 'T3', parent_name='Naïve Corp: UTF-8 é and Windows-1252 ')]
    file = write(tmp_path, 2023, rows)
    data = file.read_bytes().replace('Café'.encode(), 'Café'.encode('cp1252'))
    # The last name now holds UTF-8 letters and one Windows-1252 byte in the same line.
    data = data.replace(b'Windows-1252 ,', b'Windows-1252 \xe9,')
    file.write_bytes(data)
    assert needs_transcoding(file)
    names = read(tmp_path, file, 2023).collect()['parent_name'].to_list()
    assert names == ['Zoë Holdings, UTF-8', 'Café Holdings, Windows-1252',
                     'Naïve Corp: UTF-8 é and Windows-1252 é']


def test_a_byte_that_windows_1252_leaves_undefined_still_fails(tmp_path):
    file = write(tmp_path, 2023, three_rows())
    file.write_bytes(file.read_bytes().replace(b'Acme Corp', b'Acme \x81 Corp', 1))
    with pytest.raises(ValueError):
        read(tmp_path, file, 2023)


@pytest.mark.parametrize('content, expected', [
    (b'', False),
    (b'a,b\n1,2\n', False),
    (b'a,b\r\n1,2\r\n', False),
    (b'a,b\n1,Caf\xc3\xa9\n', False),
    (b'a,b\n1,2', False),
    (b'a,b\n1,2\n' + BYTE_ORDER_MARK, False),
    (BYTE_ORDER_MARK + b'a,b\n1,2\n', True),
    (BYTE_ORDER_MARK, True),
    (b'a,b\n1,Caf\xe9\n', True),
    (b'a,b\n1,2\n3,Caf\xe9', True),
    (b'a,b\n' + b'1,2\n' * 5000 + b'1,Caf\xe9\n' + b'1,2\n' * 5000, True),
    (b'Caf\xe9,b\n1,2\n', True),
    (b'a,\xff\n', True),
], ids=['empty', 'ascii', 'crlf', 'valid_utf8', 'no_final_newline', 'bom_not_leading', 'bom',
        'bom_only', 'cp1252_line', 'cp1252_last_line', 'cp1252_midfile', 'cp1252_header',
        'invalid_utf8_byte'])
def test_needs_transcoding(content, expected, tmp_path):
    file = tmp_path / 'file.csv'
    file.write_bytes(content)
    assert needs_transcoding(file) is expected


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
def test_quoted_newline_keeps_one_record(newline, tmp_path):
    rows = [tri_row(2023, 'T1', parent_name='Acme\nCorp\n'),
            tri_row(2023, 'T2', parent_name='Plain Corp'),
            tri_row(2023, 'T3', parent_name='"Quoted"\nname, with comma')]
    file = write(tmp_path, 2023, rows, newline=newline)
    # One header line, three record ends and three quoted newlines.
    assert file.read_bytes().count(b'\n') == 7
    frame = read(tmp_path, file, 2023).collect()
    assert frame['trifd'].to_list() == ['T1', 'T2', 'T3']
    assert frame['parent_name'].to_list() == [
        'Acme\nCorp\n', 'Plain Corp', '"Quoted"\nname, with comma']


@pytest.mark.parametrize('index', [1, 2, 3])
@pytest.mark.parametrize('edit', [
    lambda line: ','.join(line.split(',')[:-1]),
    lambda line: line + ',extra',
    lambda line: '',
    lambda line: 'T9,2023',
], ids=['short', 'long', 'blank_line', 'two_cells'])
def test_ragged_row_fails(index, edit, tmp_path):
    file = write(tmp_path, 2023, three_rows())
    edit_line(file, index, edit)
    with pytest.raises(ValueError, match='row count differs'):
        read(tmp_path, file, 2023)


def test_a_blank_line_after_the_last_record_fails(tmp_path):
    file = write(tmp_path, 2023, three_rows())
    edit_text(file, lambda text: text + '\n')
    with pytest.raises(ValueError, match='row count differs'):
        read(tmp_path, file, 2023)


def test_a_carriage_return_between_two_records_fails_the_row_count(tmp_path):
    # The csv module reads three full records, and Polars ends a line only at a newline.
    file = write(tmp_path, 2023, three_rows())
    lines = file.read_bytes().split(b'\n')
    file.write_bytes(b'\n'.join(lines[:2]) + b'\r' + b'\n'.join(lines[2:]))
    with pytest.raises(ValueError, match='row count differs'):
        read(tmp_path, file, 2023)


def test_a_stray_quote_in_a_cell_fails_the_row_count(tmp_path):
    # The csv module accepts a quote inside an unquoted cell, and Polars does not.
    file = write(tmp_path, 2023, three_rows())
    edit_text(file, lambda text: text.replace('Acme Corp', 'Acme "Corp', 1))
    with pytest.raises(ValueError, match='row count differs'):
        read(tmp_path, file, 2023)


def test_transcoded_copies_stay_in_scratch(tmp_path):
    scratch = tmp_path / 'scratch'
    plain = write(tmp_path, 2022, three_rows(2022))
    odd = write(tmp_path, 2023, accented_rows(), bom=True, newline='\r\n', encoding='cp1252')
    before = {path.name: path.read_bytes() for path in plain.parent.iterdir()}
    frame, transcoded = read_window({2022: plain, 2023: odd}, LAYOUTS, scratch)
    assert transcoded == [2023]
    assert entries(scratch) == ['2023.utf8.csv']
    assert {path.name: path.read_bytes() for path in plain.parent.iterdir()} == before
    copy = (scratch / '2023.utf8.csv').read_bytes()
    assert not copy.startswith(BYTE_ORDER_MARK)
    assert copy.decode('utf-8').startswith('1. YEAR,2. TRIFD,')
    assert frame.collect().height == 5


def test_a_transcoded_copy_is_replaced_and_a_plain_file_writes_nothing(tmp_path):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    (scratch / '2023.utf8.csv').write_bytes(b'stale')
    (scratch / '2022.utf8.csv').write_bytes(b'stale')
    odd = write(tmp_path, 2023, accented_rows(), encoding='cp1252')
    plain = write(tmp_path, 2022, three_rows(2022))
    read_window({2022: plain, 2023: odd}, LAYOUTS, scratch)
    assert (scratch / '2023.utf8.csv').read_text(encoding='utf-8').startswith('1. YEAR,')
    assert (scratch / '2022.utf8.csv').read_bytes() == b'stale'
    assert entries(scratch) == ['2022.utf8.csv', '2023.utf8.csv']


def test_the_scratch_directory_is_created_when_a_file_needs_it(tmp_path):
    scratch = tmp_path / 'made' / 'scratch'
    read_year(write(tmp_path, 2023, accented_rows(), bom=True), LAYOUTS[2023], scratch)
    assert entries(scratch) == ['2023.utf8.csv']
    plain_scratch = tmp_path / 'unused'
    read_year(write(tmp_path, 2022, three_rows(2022)), LAYOUTS[2022], plain_scratch)
    assert not plain_scratch.exists()


def test_reading_a_recorded_snapshot_leaves_it_intact(tmp_path):
    data_dir = tmp_path / 'data'
    originals = tmp_path / 'originals'
    seed_tri_files(data_dir, originals, {2022: three_rows(2022), 2024: three_rows(2024)},
                   RECORDED)
    odd = write(tmp_path, 2023, accented_rows(), folder='originals', bom=True, newline='\r\n',
                encoding='cp1252')
    tri_raw.import_file(data_dir, 2023, odd, processed_as_of=RECORDED)
    files = tri_raw.select_files(data_dir, RECORDED)
    assert sorted(files) == [2022, 2023, 2024]
    scratch = tmp_path / 'scratch'
    frame, transcoded = read_window(files, LAYOUTS, scratch)
    assert transcoded == [2023]
    assert frame.collect()['year'].to_list() == [2022] * 3 + [2023] * 2 + [2024] * 3
    assert entries(scratch) == ['2023.utf8.csv']
    # `select_files` refuses an extra file in a snapshot directory and a changed byte.
    assert tri_raw.select_files(data_dir, RECORDED) == files
    assert entries(files[2023].parent) == ['2023_us.csv']


def test_seed_tri_files_imports_each_year_it_is_given(tmp_path):
    data_dir = tmp_path / 'data'
    imported = seed_tri_files(
        data_dir, tmp_path / 'originals', {year: three_rows(year) for year in tri_raw.WINDOW},
        RECORDED)
    assert imported == tri_raw.select_files(data_dir, RECORDED)
    frame, transcoded = read_window(imported, LAYOUTS, tmp_path / 'scratch')
    assert transcoded == []
    assert frame.collect().height == 9


def test_read_window_returns_the_years_in_window_order_and_the_transcoded_years(tmp_path):
    files = {
        2024: write(tmp_path, 2024, three_rows(2024), bom=True),
        2023: write(tmp_path, 2023, accented_rows(), encoding='cp1252'),
        2022: write(tmp_path, 2022, three_rows(2022)),
    }
    frame, transcoded = read_window(files, LAYOUTS, tmp_path / 'scratch')
    assert transcoded == [2023, 2024]
    assert list(frame.collect_schema().items()) == list(READ_SCHEMA.items())
    table = frame.collect()
    assert table['year'].to_list() == [2022] * 3 + [2023] * 2 + [2024] * 3
    assert table['reporting_year'].to_list() == ['2022'] * 3 + ['2023'] * 2 + ['2024'] * 3


def test_read_window_fails_on_a_bad_year(tmp_path):
    files = {
        2022: write(tmp_path, 2022, three_rows(2022)),
        2023: write(tmp_path, 2023, [tri_row(2023, 'T1', reporting_year='2022')]),
    }
    with pytest.raises(ValueError, match='reporting year mismatch'):
        read_window(files, LAYOUTS, tmp_path / 'scratch')


@pytest.mark.parametrize('field', ['state', 'parent_name', 'standardized_foreign_parent'])
def test_an_unmapped_field_reads_as_an_empty_string(field, tmp_path):
    layout = replace(LAYOUTS[2023], columns={**LAYOUTS[2023].columns, field: None})
    file = write(tmp_path, 2023, three_rows())
    row = read_year(file, layout, tmp_path / 'scratch').collect().row(0, named=True)
    mapped = read(tmp_path, file, 2023).collect().row(0, named=True)
    assert mapped[field] != ''
    assert row == {**mapped, field: ''}


@pytest.mark.parametrize('kept', [0, 1, 2, 3, 4])
def test_a_missing_naics_cell_reads_as_an_empty_string(kept, tmp_path):
    layout = replace(LAYOUTS[2023], other_naics=LAYOUTS[2023].other_naics[:kept])
    file = write(tmp_path, 2023, three_rows())
    row = read_year(file, layout, tmp_path / 'scratch').collect().row(0, named=True)
    expected = [ACME[f'naics_{k}'] if k - 2 < kept else '' for k in range(2, 7)]
    assert [row[f'naics_{k}'] for k in range(2, 7)] == expected


def test_foreign_parent_is_empty_for_2022_and_read_from_its_cell_after(tmp_path):
    cell = LAYOUTS[2023].columns['standardized_foreign_parent']
    assert cell in LAYOUTS[2022].header
    for year, expected in ((2022, ''), (2023, 'ACME ABROAD'), (2024, 'ACME ABROAD')):
        row = tri_row(year, 'T1')
        row[cell] = 'ACME ABROAD'
        file = write(tmp_path, year, [row], folder=str(year))
        frame = read_year(file, LAYOUTS[year], tmp_path / 'scratch')
        assert frame.collect()['standardized_foreign_parent'].to_list() == [expected]


def test_tri_row_fills_every_header_cell_of_the_production_layout():
    layout = production_layout(2023)
    row = tri_row(2023, 'T1', primary_naics='325199', naics_6='325150')
    assert list(row) == list(layout.header)
    assert {cell: value for cell, value in row.items() if value} == {
        layout.columns['reporting_year']: '2023', layout.columns['trifd']: 'T1',
        layout.columns['form_type']: 'R', layout.columns['federal']: 'NO',
        layout.columns['primary_naics']: '325199', layout.other_naics[4]: '325150'}


def test_tri_row_takes_the_first_sorted_registered_value():
    layout = production_layout(2024)
    row = tri_row(2024, 'T1', form='A', federal=True)
    assert row[layout.columns['form_type']] == sorted(layout.values['form_a'])[0]
    assert row[layout.columns['federal']] == sorted(layout.values['federal_yes'])[0]
    row = tri_row(2024, 'T1', form='R', federal=False)
    assert row[layout.columns['form_type']] == sorted(layout.values['form_r'])[0]
    assert row[layout.columns['federal']] == sorted(layout.values['federal_no'])[0]
    row = tri_row(2024, 'T1', form_type='X', federal='MAYBE', reporting_year='1999')
    assert [row[layout.columns[name]] for name in ('form_type', 'federal', 'reporting_year')] == [
        'X', 'MAYBE', '1999']


@pytest.mark.parametrize('year, field', [
    (2022, 'standardized_foreign_parent'), (2023, 'colour'), (2023, 'document_control_number'),
])
def test_tri_row_refuses_unknown_and_unmapped_fields(year, field):
    with pytest.raises(ValueError):
        tri_row(year, 'T1', **{field: 'x'})


def test_write_tri_csv_writes_the_production_header_and_the_options(tmp_path):
    file = tmp_path / 'file.csv'
    write_tri_csv(file, 2022, [tri_row(2022, 'T1', parent_name='Café')], bom=True,
                  newline='\r\n', encoding='cp1252')
    data = file.read_bytes()
    assert data.startswith(BYTE_ORDER_MARK + b'1. YEAR,2. TRIFD,')
    assert b'Caf\xe9' in data
    assert data.count(b'\r\n') == 2


def test_rows_frame_is_a_lazy_frame_in_read_schema():
    frame = rows_frame([{'year': 2023, 'trifd': 'T1', 'parent_dnb': '001234567'},
                        {'year': 2024, 'reporting_year': '2024'}])
    assert isinstance(frame, pl.LazyFrame)
    assert list(frame.collect_schema().items()) == list(READ_SCHEMA.items())
    table = frame.collect()
    assert table['year'].to_list() == [2023, 2024]
    assert table['parent_dnb'].to_list() == ['001234567', '']
    assert sum(table.null_count().row(0)) == 0
    assert rows_frame([]).collect().height == 0
    with pytest.raises(ValueError):
        rows_frame([{'year': 2023, 'colour': 'x'}])
