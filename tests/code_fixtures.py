import csv
import io
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import polars as pl

from embedding_data import code_references as cr
from embedding_data import ita_summary, manifest, paths

def titles(vintage: int, leaves=('111111', '111112')) -> pl.DataFrame:
    codes = ['11', '111', '1111', '11111', *leaves]
    return pl.DataFrame(
        {
            'vintage': [vintage] * len(codes),
            'code': codes,
            'title': [f'Fixture {code}' for code in codes],
        },
        schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    )


def soc_sheet() -> pl.DataFrame:
    return pl.DataFrame(
        [
            ['Major Group', 'Minor Group', 'Broad Group', 'Detailed Occupation', None],
            ['29-0000', None, None, None, 'Healthcare Practitioners'],
            [None, '29-1200', None, None, 'Health Diagnosing Practitioners'],
            [None, None, '29-1210', None, 'Physicians'],
            [None, None, None, '29-1221', 'Pediatricians'],
        ],
        orient='row',
        schema={f'c{i}': pl.String for i in range(5)},
    )


def pair_sheet(source, target, pairs):
    rows = [
        [
            f'{source} NAICS Code',
            f'{source} NAICS Title\n(piece in {target})',
            f'{target} NAICS Code',
            f'{target} NAICS Title',
        ]
    ]
    rows += [[a, 'Fixture source', b, 'Fixture target'] for a, b in pairs]
    return pl.DataFrame(rows, orient='row', schema={f'c{i}': pl.String for i in range(4)})


def toy_reference_tables():
    from embedding_data.classification_tables import naics_tables
    from embedding_data.naics_relationships import parse_concordance, validate_relationships

    native = []
    for v in (2002, 2007, 2012, 2017, 2022):
        leaves = ('111111', '111112', '111113') if v == 2022 else ('111111', '111112')
        nodes, edges, paths = naics_tables(titles(v, leaves), v)
        native.append(nodes)
        if v == 2022:
            canonical_paths = paths
    structures = pl.concat(native)
    frames = [
        parse_concordance(pair_sheet(a, b, pairs), a, b, f'fixture_{a}_{b}.xlsx')
        for a, b, pairs in [
            (2002, 2007, [('111111', '111111'), ('111112', '111112')]),
            (2007, 2012, [('111111', '111111'), ('111112', '111112')]),
            (2012, 2017, [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]),
            (2017, 2022, [('111111', '111111'), ('111112', '111112'), ('111112', '111113')]),
        ]
    ]
    relations = pl.concat(frames)
    validate_relationships(relations, structures)
    return structures, relations, canonical_paths


def write_xlsx(file: Path, rows: list[list[str | None]]) -> None:
    namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    sheet_rows = []
    for i, row in enumerate(rows, 1):
        cells = ''.join(
            f'<c r="{chr(65 + j)}{i}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            for j, value in enumerate(row)
            if value is not None
        )
        sheet_rows.append(f'<row r="{i}">{cells}</row>')
    with ZipFile(file, 'w') as archive:
        archive.writestr(
            '[Content_Types].xml',
            """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml"
 ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            '_rels/.rels',
            """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            'xl/workbook.xml',
            f"""<workbook xmlns="{namespace}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Fixture" sheetId="1" r:id="rId1"/></sheets></workbook>""",
        )
        archive.writestr(
            'xl/_rels/workbook.xml.rels',
            """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
 Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            'xl/worksheets/sheet1.xml',
            f'<worksheet xmlns="{namespace}"><sheetData>'
            + ''.join(sheet_rows)
            + '</sheetData></worksheet>',
        )


def seed_code_tree(data_dir: Path) -> dict[str, cr.Reference]:
    originals = data_dir / 'originals'
    originals.mkdir(parents=True)
    registry = dict(cr.REGISTRY)
    for v in (2002, 2007, 2012, 2017, 2022):
        leaves = ('111111', '111112', '111113') if v == 2022 else ('111111', '111112')
        frame = titles(v, leaves)
        file = originals / f'naics_{v}.xlsx'
        write_xlsx(
            file,
            [
                [f'{v} NAICS Code', f'{v} NAICS Title'],
                *[list(r) for r in frame.select('code', 'title').iter_rows()],
            ],
        )
        kind = f'naics_{v}'
        registry[kind] = replace(
            registry[kind],
            relative=f'naics/fixture_{v}.xlsx',
            family='naics',
            expected=(frame.height, len(leaves)),
        )
        cr.import_reference(data_dir, kind, file, registry=registry)
    for a, b, pairs in [
        (2002, 2007, [('111111', '111111'), ('111112', '111112')]),
        (2007, 2012, [('111111', '111111'), ('111112', '111112')]),
        (2012, 2017, [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]),
        (2017, 2022, [('111111', '111111'), ('111112', '111112'), ('111112', '111113')]),
    ]:
        kind = f'concordance_{a}_{b}'
        file = originals / f'{kind}.xlsx'
        write_xlsx(file, [list(r) for r in pair_sheet(a, b, pairs).iter_rows()])
        registry[kind] = replace(registry[kind], relative=f'naics/{kind}.xlsx')
        cr.import_reference(data_dir, kind, file, registry=registry)
    file = originals / 'soc.xlsx'
    write_xlsx(file, [list(r) for r in soc_sheet().iter_rows()])
    registry['soc_2018'] = replace(
        registry['soc_2018'], relative='soc/fixture.xlsx', expected=(4, 1)
    )
    cr.import_reference(data_dir, 'soc_2018', file, registry=registry)
    for kind, part, code in [
        ('designated_2012', 'E', '11'),
        ('designated_2017', 'E', '11'),
        ('partially_exempt_2007', 'B', '111112'),
    ]:
        file = originals / f'{kind}.htm'
        file.write_text(
            f'<html><pre>Appendix A to Subpart {part} of Part 1904\n'
            f'NAICS Industry\n{code}...... Fixture title\n</pre></html>'
        )
        registry[kind] = replace(registry[kind], expected=1)
        cr.import_reference(data_dir, kind, file, registry=registry)
    for year in (2022, 2023):
        directory = paths.raw_dir(data_dir, 'osha') / 'summary' / str(year)
        directory.mkdir(parents=True)
        raw = directory / f'fixture_{year}.zip'
        row = {name: 'Fixture' for name in ita_summary.TEXT_COLUMNS}
        row.update(
            year_filing_for=str(year),
            id='1',
            establishment_id='1',
            establishment_type='1',
            size='2',
            annual_average_employees='30',
            total_hours_worked='60000',
            naics_code='111112',
        )
        if year >= 2023:
            row['naics_year'] = '2017'
        csv_text = io.StringIO()
        writer = csv.DictWriter(csv_text, fieldnames=list(row))
        writer.writeheader()
        writer.writerows(
            [row, row]
        )  # Deliberate identical rows, not an accidental fixture duplicate.
        with ZipFile(raw, 'w') as archive:
            archive.writestr('fixture.csv', csv_text.getvalue())
        entry = manifest.describe_file(
            raw,
            paths.manifest_path(data_dir).parent,
            retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
            client='fixture',
            client_version='1',
            source_url='https://www.osha.gov/fixture',
        )
        manifest.append_entries(paths.manifest_path(data_dir), [entry])
    ita_summary.build_summary_table(
        data_dir
    )  # Fixture setup only; production code_build never calls this.
    return registry
