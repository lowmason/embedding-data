import gzip
import importlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

import polars as pl
import pytest

from embedding_data import acs_benchmark_extract as acs
from embedding_data import cps_benchmark_extract as cps
from embedding_data import manifest, paths

@pytest.fixture
def conversion():
    return importlib.import_module('embedding_data.ipums_conversion')


def write_delivery(root, source='acs', set_name='core', number=123):
    collection = {'acs': 'usa', 'cps': 'cps'}[source]
    name = f'{collection}_{number:05d}'
    directory = root / 'raw' / source / set_name / name
    directory.mkdir(parents=True)
    if source == 'acs':
        definition = acs.build_extract(set_name).build()
        csv = 'INDNAICS,OCCSOC,INCWAGE_CPIU_2010\n31M,1110XX,12.5\n001,001010,\n'
        expected = [
            {'INDNAICS': '31M', 'OCCSOC': '1110XX', 'INCWAGE_CPIU_2010': 12.5},
            {'INDNAICS': '001', 'OCCSOC': '001010', 'INCWAGE_CPIU_2010': None},
        ]
    else:
        definition = cps.build_extract(set_name, ['cps2025_03s']).build()
        csv = 'IND,OCC,INDLY,OCCLY,INCWAGE_CPIU_2010\n170,20,770,30,12.5\n0,,9999,0,\n'
        expected = [
            {'IND': '0170', 'OCC': '0020', 'INDLY': '0770', 'OCCLY': '0030',
             'INCWAGE_CPIU_2010': 12.5},
            {'IND': '0000', 'OCC': None, 'INDLY': '9999', 'OCCLY': '0000',
             'INCWAGE_CPIU_2010': None},
        ]
    with gzip.open(directory / f'{name}.csv.gz', 'wt') as stream:
        stream.write(csv)
    (directory / f'{name}.xml').write_text('<codeBook/>\n')
    (directory / 'extract.json').write_text(json.dumps(definition))
    entries = [
        manifest.describe_file(
            file, root / 'raw', retrieved_at=datetime(2026, 10, 12, tzinfo=UTC),
            client='ipumspy', client_version='fixture', collection=collection,
            extract_number=number, samples=definition['samples'],
        )
        for file in sorted(directory.iterdir())
    ]
    manifest.append_entries(paths.manifest_path(root), entries)
    output = root / 'derived' / source / set_name / f'{name}.parquet'
    return directory, output, expected


def bytes_tree(root):
    return {
        file.relative_to(root): file.read_bytes() for file in root.rglob('*') if file.is_file()
    }


@pytest.mark.parametrize('source,set_name,module', [('acs', 'core', acs), ('cps', 'asec', cps)])
def test_convert_only_is_offline_and_repeatable(tmp_path, cli_runner, source, set_name, module):
    _, output, expected = write_delivery(tmp_path, source, set_name)
    raw_before = bytes_tree(tmp_path / 'raw')
    dotenv = tmp_path / 'forbidden.env'
    dotenv.write_text('fixture file whose loader must never run\n')
    with (
        patch.object(module, 'DOTENV_PATH', dotenv),
        patch.object(module, 'load_dotenv', side_effect=AssertionError('dotenv loaded')),
        patch.object(module, 'IpumsApiClient', side_effect=AssertionError('client created')),
    ):
        arguments = [set_name, '--convert-only', '--data-dir', str(tmp_path)]
        result = cli_runner.invoke(module.app, arguments)
        assert result.exit_code == 0, result.output
        assert pl.read_parquet(output).to_dicts() == expected
        assert pl.read_parquet(output).schema == {
            column: pl.Float64 if column == 'INCWAGE_CPIU_2010' else pl.String
            for column in expected[0]
        }
        before = (output.read_bytes(), output.stat().st_mtime_ns)
        result = cli_runner.invoke(module.app, arguments)
        assert result.exit_code == 0, result.output
        assert (output.read_bytes(), output.stat().st_mtime_ns) == before
    assert bytes_tree(tmp_path / 'raw') == raw_before
    assert sorted(file.name for file in output.parent.iterdir()) == [output.name]


@pytest.mark.parametrize('module,set_name', [(acs, 'core'), (cps, 'monthly')])
def test_convert_only_refuses_dry_run_before_credentials(tmp_path, cli_runner, module, set_name):
    with (
        patch.object(module, 'DOTENV_PATH', tmp_path / 'absent.env'),
        patch.object(module, 'load_dotenv', side_effect=AssertionError('dotenv loaded')),
        patch.object(module, 'IpumsApiClient', side_effect=AssertionError('client created')),
    ):
        result = cli_runner.invoke(module.app, [
            set_name, '--convert-only', '--dry-run', '--data-dir', str(tmp_path),
        ])
    assert result.exit_code == 2, result.output
    assert '--convert-only cannot be combined with --dry-run' in result.output
    assert list(tmp_path.iterdir()) == []


def test_recovery_preflights_every_selected_set_before_writing(tmp_path, conversion):
    _, output, _ = write_delivery(tmp_path)
    second, _, _ = write_delivery(tmp_path, set_name='vintage', number=124)
    (second / 'usa_00124.xml').unlink()
    with pytest.raises(FileNotFoundError):
        conversion.recover(tmp_path, 'acs', ['core', 'vintage'])
    assert not output.exists()
    assert not (tmp_path / 'derived').exists()


def test_recovery_selects_only_requested_immediate_deliveries(tmp_path, conversion):
    _, output, expected = write_delivery(tmp_path)
    other, other_output, _ = write_delivery(tmp_path, set_name='vintage', number=124)
    (other / 'usa_00124.xml').unlink()
    interrupted = tmp_path / 'raw/acs/core/usa_00125.part'
    interrupted.mkdir()
    (interrupted / 'usa_00125.csv.gz').write_bytes(b'interrupted')
    before = bytes_tree(tmp_path / 'raw')
    assert conversion.recover(tmp_path, 'acs', ['core']) == [output]
    assert pl.read_parquet(output).to_dicts() == expected
    assert not other_output.exists()
    assert bytes_tree(tmp_path / 'raw') == before


@pytest.mark.parametrize('kind', ['missing', 'interrupted', 'nested'])
def test_recovery_requires_a_complete_delivery(tmp_path, conversion, kind):
    if kind == 'interrupted':
        directory, _, _ = write_delivery(tmp_path)
        directory.rename(directory.with_name(directory.name + '.part'))
    elif kind == 'nested':
        directory, _, _ = write_delivery(tmp_path)
        nested = directory.parent / 'extra'
        nested.mkdir()
        directory.rename(nested / directory.name)
    with pytest.raises(ValueError, match='no complete deliver'):
        conversion.recover(tmp_path, 'acs', ['core'])
    assert not (tmp_path / 'derived').exists()


@pytest.mark.parametrize(
    'damage', ['hash', 'xml', 'unrecorded', 'collection', 'number', 'samples'],
)
def test_recovery_refuses_invalid_delivery_without_writes(tmp_path, conversion, damage):
    directory, _, _ = write_delivery(tmp_path)
    manifest_path = paths.manifest_path(tmp_path)
    if damage == 'hash':
        (directory / 'usa_00123.csv.gz').write_bytes(b'changed synthetic bytes')
    elif damage == 'xml':
        (directory / 'usa_00123.xml').unlink()
    else:
        entries = manifest.read_manifest(manifest_path)
        if damage == 'unrecorded':
            entries = [entry for entry in entries if not entry.path.endswith('extract.json')]
        else:
            changed = {'collection': 'cps', 'number': 999, 'samples': ('wrong',)}[damage]
            field = {'number': 'extract_number'}.get(damage, damage)
            entries[0] = replace(entries[0], **{field: changed})
        manifest_path.write_text(''.join(json.dumps(entry.__dict__) + '\n' for entry in entries))
    before = bytes_tree(tmp_path)
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        conversion.recover(tmp_path, 'acs', ['core'])
    assert bytes_tree(tmp_path) == before
    assert not (tmp_path / 'derived').exists()


@pytest.mark.parametrize(
    'target', ['raw-file', 'raw-directory', 'derived-parent', 'final', 'partial'],
)
def test_recovery_refuses_symlinks(tmp_path, conversion, target):
    directory, output, _ = write_delivery(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    if target == 'raw-file':
        file = directory / 'usa_00123.xml'
        saved = outside / file.name
        file.rename(saved)
        file.symlink_to(saved)
    elif target == 'raw-directory':
        saved = outside / directory.name
        directory.rename(saved)
        directory.symlink_to(saved, target_is_directory=True)
    else:
        output.parent.mkdir(parents=True)
        if target == 'derived-parent':
            output.parent.rmdir()
            output.parent.symlink_to(outside, target_is_directory=True)
        else:
            file = output if target == 'final' else output.with_name(output.name + '.part')
            file.symlink_to(outside / 'absent')
    before = bytes_tree(outside)
    with pytest.raises((ValueError, FileExistsError)):
        conversion.recover(tmp_path, 'acs', ['core'])
    assert bytes_tree(outside) == before
    assert not output.exists()


@pytest.mark.parametrize('occupied', ['final', 'partial'])
def test_convert_preserves_occupied_paths(tmp_path, conversion, occupied):
    directory, output, _ = write_delivery(tmp_path)
    output.parent.mkdir(parents=True)
    file = output if occupied == 'final' else output.with_name(output.name + '.part')
    file.write_bytes(b'previous bytes')
    before = (file.read_bytes(), file.stat().st_mtime_ns)
    with pytest.raises(FileExistsError):
        conversion.convert(directory / 'usa_00123.csv.gz', output, 'acs')
    assert (file.read_bytes(), file.stat().st_mtime_ns) == before
    assert sorted(path.name for path in output.parent.iterdir()) == [file.name]


def test_recovery_preflights_partial_in_later_delivery(tmp_path, conversion):
    _, first, _ = write_delivery(tmp_path)
    _, second, _ = write_delivery(tmp_path, number=124)
    second.parent.mkdir(parents=True)
    partial = second.with_name(second.name + '.part')
    partial.write_bytes(b'previous partial')
    with pytest.raises(FileExistsError):
        conversion.recover(tmp_path, 'acs', ['core'])
    assert not first.exists()
    assert partial.read_bytes() == b'previous partial'


def test_sink_failure_removes_only_owned_staging_and_scratch(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)
    raw_before = bytes_tree(tmp_path / 'raw')

    def interrupted_sink(self, stream, **kwargs):
        stream.write(b'partial parquet bytes')
        raise OSError('synthetic interrupted sink')

    with patch.object(pl.LazyFrame, 'sink_parquet', interrupted_sink):
        with pytest.raises(OSError, match='synthetic interrupted sink'):
            conversion.convert(directory / 'usa_00123.csv.gz', output, 'acs')
    assert list(output.parent.iterdir()) == []
    assert bytes_tree(tmp_path / 'raw') == raw_before


def test_decompression_owns_unique_scratch_and_cleans_on_failure(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)
    output.parent.mkdir(parents=True)
    previous = output.with_suffix('.csv')
    previous.write_text('previous unrelated scratch')
    with pytest.raises(RuntimeError, match='stop'):
        with conversion.decompressed_csv(directory / 'usa_00123.csv.gz', output.parent) as csv:
            assert csv.parent.parent == output.parent
            assert csv.read_text().startswith('INDNAICS,')
            raise RuntimeError('stop')
    assert list(output.parent.iterdir()) == [previous]
    assert previous.read_text() == 'previous unrelated scratch'


def test_publication_race_preserves_the_concurrent_final(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)
    real_link = conversion.os.link

    def occupy_final(partial, destination):
        destination.write_bytes(b'concurrent final')
        return real_link(partial, destination)

    with patch.object(conversion.os, 'link', occupy_final):
        with pytest.raises(FileExistsError):
            conversion.convert(directory / 'usa_00123.csv.gz', output, 'acs')
    assert output.read_bytes() == b'concurrent final'
    assert list(output.parent.iterdir()) == [output]


def test_invalid_parquet_is_never_published(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)

    def invalid_sink(self, stream, **kwargs):
        stream.write(b'invalid parquet')

    with patch.object(pl.LazyFrame, 'sink_parquet', invalid_sink):
        with pytest.raises(pl.exceptions.ComputeError):
            conversion.convert(directory / 'usa_00123.csv.gz', output, 'acs')
    assert list(output.parent.iterdir()) == []


def test_bad_gzip_cleans_owned_scratch(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)
    csv_gz = directory / 'usa_00123.csv.gz'
    csv_gz.write_bytes(b'not gzip')
    with pytest.raises(gzip.BadGzipFile):
        conversion.convert(csv_gz, output, 'acs')
    assert list(output.parent.iterdir()) == []


def test_recovery_converts_multiple_selected_sets(tmp_path, conversion):
    _, first, _ = write_delivery(tmp_path)
    _, second, expected = write_delivery(tmp_path, set_name='vintage', number=124)
    assert conversion.recover(tmp_path, 'acs', ['core', 'vintage', 'core']) == [first, second]
    assert pl.read_parquet(second).to_dicts() == expected


def test_existing_final_does_not_bypass_raw_verification(tmp_path, conversion):
    directory, output, _ = write_delivery(tmp_path)
    conversion.recover(tmp_path, 'acs', ['core'])
    before = (output.read_bytes(), output.stat().st_mtime_ns)
    (directory / 'usa_00123.xml').write_text('changed fixture')
    with pytest.raises(ValueError, match='SHA-256'):
        conversion.recover(tmp_path, 'acs', ['core'])
    assert (output.read_bytes(), output.stat().st_mtime_ns) == before
