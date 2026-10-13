import polars as pl

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
