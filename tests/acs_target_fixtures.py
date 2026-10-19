'''Small synthetic primitives shared by ACS target tests.'''

from embedding_data.target_contract import TARGET_SCHEMA

def minimal_target(**changes) -> dict:
    row = dict(
        zip(
            TARGET_SCHEMA,
            (
                'acs',
                'staffing_pattern',
                'acs_industry_category',
                'feature:acs_industry_category:industry-a',
                'acs_occupation_category',
                'feature:acs_occupation_category:occupation-a',
                'forward_share',
                0.25,
                0.0,
                'replicate',
                2,
                25.0,
                'annual-core-2023-2024',
                'acs-naics2022-soc2018',
                'civilian_employed:strict',
                ['size_gate_pending'],
            ),
            strict=True,
        )
    )
    return row | changes


def weights(point: str, overrides: dict[int, str] | None = None) -> dict[str, str]:
    overrides = overrides or {}
    return {'PERWT': point} | {f'REPWTP{r}': overrides.get(r, point) for r in range(1, 81)}


def authenticated_mapping(tmp_path, monkeypatch, prepare_acs=None) -> dict:
    '''Build a real pinned mapping from authenticated temporary upstreams.'''
    from pathlib import Path

    from acs_mapping_fixtures import build_fixture_mapping, seed_reconciliation_inputs

    fixture = seed_reconciliation_inputs(tmp_path, monkeypatch, prepare_acs=prepare_acs)
    response = build_fixture_mapping(fixture, 'mapping', monkeypatch)
    return {'data_dir': fixture.data_dir, 'request': fixture.request,
            'mapping': Path(response['directory']),
            'mapping_outputs_sha256': response['outputs_sha256']}
