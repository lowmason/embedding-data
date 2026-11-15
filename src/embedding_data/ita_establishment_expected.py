'''Adopted V1 and V2 reproduction values for the Stage 10 ITA establishment build.

The integers below are transcribed from the `## V1` and `## V2` tables of
`specs/findings/v1-v3-ita-verification.md`. The module never reads that finding. A
test compares these constants with the finding's Markdown tables, so a transcription
error fails the suite. The build compares counts computed by its own code with these
constants, which makes the gate independent of the build.
'''

from dataclasses import dataclass

import polars as pl

SOURCE_RECORDS = 3_206_055
YEARS = tuple(range(2016, 2026))
YEAR_PAIRS = ((2016, 2017), (2017, 2018), (2018, 2019), (2019, 2020), (2020, 2021),
              (2021, 2022), (2022, 2023), (2023, 2024), (2023, 2025), (2024, 2025))
V1_COLUMNS = (
    'n_rows', 'n_empty', 'n_placeholder', 'n_copied_any', 'n_native_title_match',
    'n_vintage_unknown', 'n_employer_unknown', 'n_employer_company', 'n_ein_padded',
    'n_mojibake', 'n_repeat_rows', 'n_repeat_excess')
V2_COLUMNS = (
    'n_cohort_ids', 'n_raw_reappeared', 'n_unique_cohort_ids', 'n_reappeared',
    'n_same_ein_address', 'n_same_ein_address_including_padded', 'n_same_raw_ein_address',
    'n_reappeared_ein_unknown', 'n_reappeared_ein_conflict', 'n_reappeared_address_conflict',
    'n_base_missing_id_rows', 'n_later_missing_id_rows', 'n_unique_address_matches',
    'n_address_matches_different_id')
ADOPTED_SOURCE = {
    'path': 'derived/osha/ita_300a_summary.parquet',
    'sha256': '6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8',
    'size': 139930636,
}
ADOPTED_BASIS = 'adopted_v1_v3_finding'

V1: dict[int, dict[str, int]] = {
    2016: {
        'n_rows': 214_978,
        'n_empty': 17_277,
        'n_placeholder': 34,
        'n_copied_any': 39_245,
        'n_native_title_match': 39_230,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 15_580,
        'n_employer_company': 199_398,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 123_220,
        'n_repeat_excess': 110_955,
    },
    2017: {
        'n_rows': 259_758,
        'n_empty': 20_434,
        'n_placeholder': 276,
        'n_copied_any': 39_574,
        'n_native_title_match': 39_554,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 20_781,
        'n_employer_company': 238_975,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 142_026,
        'n_repeat_excess': 127_967,
    },
    2018: {
        'n_rows': 289_534,
        'n_empty': 20_778,
        'n_placeholder': 130,
        'n_copied_any': 46_623,
        'n_native_title_match': 46_603,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 30_949,
        'n_employer_company': 257_633,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 153_840,
        'n_repeat_excess': 138_070,
    },
    2019: {
        'n_rows': 290_475,
        'n_empty': 23_223,
        'n_placeholder': 95,
        'n_copied_any': 42_944,
        'n_native_title_match': 42_923,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 4_203,
        'n_employer_company': 47_806,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 162_159,
        'n_repeat_excess': 144_992,
    },
    2020: {
        'n_rows': 293_391,
        'n_empty': 21_041,
        'n_placeholder': 35,
        'n_copied_any': 52_578,
        'n_native_title_match': 52_564,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 3_139,
        'n_employer_company': 28_765,
        'n_ein_padded': 0,
        'n_mojibake': 0,
        'n_repeat_rows': 168_025,
        'n_repeat_excess': 150_877,
    },
    2021: {
        'n_rows': 317_978,
        'n_empty': 19_404,
        'n_placeholder': 25,
        'n_copied_any': 59_754,
        'n_native_title_match': 59_721,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 3_787,
        'n_employer_company': 27_330,
        'n_ein_padded': 12_440,
        'n_mojibake': 0,
        'n_repeat_rows': 185_835,
        'n_repeat_excess': 166_826,
    },
    2022: {
        'n_rows': 346_799,
        'n_empty': 26_419,
        'n_placeholder': 26,
        'n_copied_any': 74_820,
        'n_native_title_match': 72_905,
        'n_vintage_unknown': 0,
        'n_employer_unknown': 5_136,
        'n_employer_company': 31_498,
        'n_ein_padded': 17_987,
        'n_mojibake': 0,
        'n_repeat_rows': 195_442,
        'n_repeat_excess': 176_018,
    },
    2023: {
        'n_rows': 394_234,
        'n_empty': 25_640,
        'n_placeholder': 57,
        'n_copied_any': 85_434,
        'n_native_title_match': 72_398,
        'n_vintage_unknown': 2_297,
        'n_employer_unknown': 6_670,
        'n_employer_company': 34_425,
        'n_ein_padded': 27_708,
        'n_mojibake': 0,
        'n_repeat_rows': 222_941,
        'n_repeat_excess': 200_097,
    },
    2024: {
        'n_rows': 398_620,
        'n_empty': 26_796,
        'n_placeholder': 12,
        'n_copied_any': 89_198,
        'n_native_title_match': 84_392,
        'n_vintage_unknown': 203,
        'n_employer_unknown': 8_069,
        'n_employer_company': 35_314,
        'n_ein_padded': 13_982,
        'n_mojibake': 0,
        'n_repeat_rows': 232_769,
        'n_repeat_excess': 210_672,
    },
    2025: {
        'n_rows': 400_288,
        'n_empty': 27_241,
        'n_placeholder': 27,
        'n_copied_any': 83_024,
        'n_native_title_match': 77_256,
        'n_vintage_unknown': 170,
        'n_employer_unknown': 8_094,
        'n_employer_company': 38_026,
        'n_ein_padded': 26,
        'n_mojibake': 0,
        'n_repeat_rows': 235_372,
        'n_repeat_excess': 213_142,
    },
}
V2: dict[tuple[int, int], dict[str, int]] = {
    (2016, 2017): {
        'n_cohort_ids': 214_977,
        'n_raw_reappeared': 129_292,
        'n_unique_cohort_ids': 214_976,
        'n_reappeared': 129_291,
        'n_same_ein_address': 0,
        'n_same_ein_address_including_padded': 0,
        'n_same_raw_ein_address': 0,
        'n_reappeared_ein_unknown': 129_291,
        'n_reappeared_ein_conflict': 0,
        'n_reappeared_address_conflict': 3_965,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 0,
        'n_address_matches_different_id': 0,
    },
    (2017, 2018): {
        'n_cohort_ids': 259_757,
        'n_raw_reappeared': 159_932,
        'n_unique_cohort_ids': 259_756,
        'n_reappeared': 157_531,
        'n_same_ein_address': 2,
        'n_same_ein_address_including_padded': 2,
        'n_same_raw_ein_address': 2,
        'n_reappeared_ein_unknown': 157_529,
        'n_reappeared_ein_conflict': 0,
        'n_reappeared_address_conflict': 8_003,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 2,
        'n_address_matches_different_id': 0,
    },
    (2018, 2019): {
        'n_cohort_ids': 286_884,
        'n_raw_reappeared': 177_598,
        'n_unique_cohort_ids': 284_234,
        'n_reappeared': 177_112,
        'n_same_ein_address': 635,
        'n_same_ein_address_including_padded': 635,
        'n_same_raw_ein_address': 635,
        'n_reappeared_ein_unknown': 176_445,
        'n_reappeared_ein_conflict': 16,
        'n_reappeared_address_conflict': 11_583,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 634,
        'n_address_matches_different_id': 0,
    },
    (2019, 2020): {
        'n_cohort_ids': 290_475,
        'n_raw_reappeared': 184_014,
        'n_unique_cohort_ids': 290_475,
        'n_reappeared': 184_008,
        'n_same_ein_address': 140_056,
        'n_same_ein_address_including_padded': 140_056,
        'n_same_raw_ein_address': 140_056,
        'n_reappeared_ein_unknown': 34_106,
        'n_reappeared_ein_conflict': 2_022,
        'n_reappeared_address_conflict': 8_875,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 143_794,
        'n_address_matches_different_id': 6_080,
    },
    (2020, 2021): {
        'n_cohort_ids': 293_385,
        'n_raw_reappeared': 185_386,
        'n_unique_cohort_ids': 293_379,
        'n_reappeared': 185_179,
        'n_same_ein_address': 132_404,
        'n_same_ein_address_including_padded': 139_236,
        'n_same_raw_ein_address': 132_404,
        'n_reappeared_ein_unknown': 21_031,
        'n_reappeared_ein_conflict': 4_320,
        'n_reappeared_address_conflict': 22_348,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 132_285,
        'n_address_matches_different_id': 6_236,
    },
    (2021, 2022): {
        'n_cohort_ids': 315_936,
        'n_raw_reappeared': 183_055,
        'n_unique_cohort_ids': 315_121,
        'n_reappeared': 182_686,
        'n_same_ein_address': 132_532,
        'n_same_ein_address_including_padded': 139_072,
        'n_same_raw_ein_address': 139_072,
        'n_reappeared_ein_unknown': 17_599,
        'n_reappeared_ein_conflict': 6_837,
        'n_reappeared_address_conflict': 21_483,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 136_339,
        'n_address_matches_different_id': 10_046,
    },
    (2022, 2023): {
        'n_cohort_ids': 346_799,
        'n_raw_reappeared': 197_342,
        'n_unique_cohort_ids': 346_799,
        'n_reappeared': 197_342,
        'n_same_ein_address': 146_502,
        'n_same_ein_address_including_padded': 153_998,
        'n_same_raw_ein_address': 153_998,
        'n_reappeared_ein_unknown': 22_745,
        'n_reappeared_ein_conflict': 4_365,
        'n_reappeared_address_conflict': 12_762,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 150_608,
        'n_address_matches_different_id': 9_092,
    },
    (2023, 2024): {
        'n_cohort_ids': 394_231,
        'n_raw_reappeared': 219_860,
        'n_unique_cohort_ids': 394_228,
        'n_reappeared': 219_860,
        'n_same_ein_address': 160_579,
        'n_same_ein_address_including_padded': 168_226,
        'n_same_raw_ein_address': 168_226,
        'n_reappeared_ein_unknown': 23_866,
        'n_reappeared_ein_conflict': 9_579,
        'n_reappeared_address_conflict': 20_138,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 171_544,
        'n_address_matches_different_id': 14_532,
    },
    (2023, 2025): {
        'n_cohort_ids': 394_231,
        'n_raw_reappeared': 180_123,
        'n_unique_cohort_ids': 394_228,
        'n_reappeared': 180_123,
        'n_same_ein_address': 133_770,
        'n_same_ein_address_including_padded': 140_354,
        'n_same_raw_ein_address': 133_795,
        'n_reappeared_ein_unknown': 19_211,
        'n_reappeared_ein_conflict': 3_300,
        'n_reappeared_address_conflict': 20_330,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 141_997,
        'n_address_matches_different_id': 13_056,
    },
    (2024, 2025): {
        'n_cohort_ids': 398_620,
        'n_raw_reappeared': 230_099,
        'n_unique_cohort_ids': 398_620,
        'n_reappeared': 230_099,
        'n_same_ein_address': 184_358,
        'n_same_ein_address_including_padded': 192_250,
        'n_same_raw_ein_address': 184_378,
        'n_reappeared_ein_unknown': 24_998,
        'n_reappeared_ein_conflict': 2_964,
        'n_reappeared_address_conflict': 11_601,
        'n_base_missing_id_rows': 0,
        'n_later_missing_id_rows': 0,
        'n_unique_address_matches': 195_188,
        'n_address_matches_different_id': 14_551,
    },
}


@dataclass(frozen=True)
class Expectations:
    '''Expected source record count and V1/V2 integer tables, with their basis.'''

    basis: str
    source_records: int
    v1: dict[int, dict[str, int]]
    v2: dict[tuple[int, int], dict[str, int]]

    def to_json(self) -> dict:
        '''Serialize with string keys: `'2016'` for years, `'2016-2017'` for pairs.'''
        return {
            'basis': self.basis,
            'source_records': self.source_records,
            'v1': {str(year): dict(cells) for year, cells in self.v1.items()},
            'v2': {f'{base}-{later}': dict(cells)
                   for (base, later), cells in self.v2.items()},
        }

    @classmethod
    def from_json(cls, value: dict) -> 'Expectations':
        '''Rebuild the integer-keyed tables that `to_json` wrote.'''
        pairs = {}
        for key, cells in value['v2'].items():
            base, later = key.split('-')
            pairs[(int(base), int(later))] = dict(cells)
        return cls(
            value['basis'], value['source_records'],
            {int(year): dict(cells) for year, cells in value['v1'].items()}, pairs)


ADOPTED = Expectations(ADOPTED_BASIS, SOURCE_RECORDS, V1, V2)


def expectations_for(source: dict, explicit: Expectations | None = None) -> Expectations:
    '''Return the adopted values for the adopted source, else the explicit ones.'''
    adopted = (source.get('sha256') == ADOPTED_SOURCE['sha256']
               and source.get('size') == ADOPTED_SOURCE['size'])
    if adopted:
        if explicit is not None:
            raise ValueError('the adopted source takes no explicit expectations')
        return ADOPTED
    if explicit is None:
        raise ValueError('a source other than the adopted one needs explicit expectations')
    if explicit.basis == ADOPTED_BASIS:
        raise ValueError('explicit expectations must not claim the adopted basis')
    return explicit


def matches(frame: pl.DataFrame, keys: list[str], columns: tuple[str, ...],
            table: dict[tuple[int, ...], dict[str, int]]) -> bool:
    '''True when the frame has exactly one row for each key, each with the table's cells.'''
    rows = frame.select(keys + list(columns)).rows()
    found = {row[:len(keys)]: dict(zip(columns, row[len(keys):])) for row in rows}
    return len(found) == len(rows) and found == table


def check_reproduction(expected: Expectations, *, source_records: int,
                       v1: pl.DataFrame, v2: pl.DataFrame) -> dict:
    '''Compare the build's counts with the expectations, exactly, or raise ValueError.'''
    if source_records != expected.source_records:
        raise ValueError('source record count differs')
    v1_table = {(year,): cells for year, cells in expected.v1.items()}
    if not matches(v1, ['year_filing_for'], V1_COLUMNS, v1_table):
        raise ValueError('V1 reproduction differs')
    if not matches(v2, ['base_year', 'later_year'], V2_COLUMNS, expected.v2):
        raise ValueError('V2 reproduction differs')
    return {'basis': expected.basis, 'source_records': 'equal', 'v1': 'equal', 'v2': 'equal'}
