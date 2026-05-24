"""list_voices モジュールのテスト。"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from tools.list_voices import list_voices


def test_load_voicepeak_path_reads_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """config.toml から voicepeak_path を取得する。"""
    config_path = tmp_path / 'config.toml'
    config_path.write_text('[generate_voice]\nvoicepeak_path = "C:/VoicePeak/voicepeak.exe"\n', encoding='utf-8')
    monkeypatch.setattr(list_voices, 'CONFIG_PATH', config_path)

    assert list_voices.load_voicepeak_path() == 'C:/VoicePeak/voicepeak.exe'


def test_load_voicepeak_path_returns_none_when_section_is_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """generate_voice セクションが辞書でなければ None を返す。"""
    config_path = tmp_path / 'config.toml'
    config_path.write_text('generate_voice = "invalid"\n', encoding='utf-8')
    monkeypatch.setattr(list_voices, 'CONFIG_PATH', config_path)

    assert list_voices.load_voicepeak_path() is None


def test_run_voicepeak_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI の標準出力を返す。"""
    completed = subprocess.CompletedProcess(args=['voicepeak.exe'], returncode=0, stdout='ok\n', stderr='')
    monkeypatch.setattr(list_voices.subprocess, 'run', lambda *args, **kwargs: completed)

    assert list_voices.run_voicepeak('voicepeak.exe', ['--list-narrator']) == 'ok'


def test_run_voicepeak_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI が失敗したら RuntimeError を送出する。"""
    completed = subprocess.CompletedProcess(args=['voicepeak.exe'], returncode=2, stdout='', stderr='failure')
    monkeypatch.setattr(list_voices.subprocess, 'run', lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match='voicepeak exited with code 2: failure'):
        list_voices.run_voicepeak('voicepeak.exe', ['--list-narrator'])


def test_get_narrators_filters_blank_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """空行を除外してナレーター名を返す。"""
    monkeypatch.setattr(list_voices, 'run_voicepeak', lambda exe, args: 'A\n\nB\n')

    assert list_voices.get_narrators('voicepeak.exe') == ['A', 'B']


def test_get_emotions_filters_blank_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """空行を除外して感情名を返す。"""
    monkeypatch.setattr(list_voices, 'run_voicepeak', lambda exe, args: 'happy\n\ncalm\n')

    assert list_voices.get_emotions('voicepeak.exe', 'Narrator') == ['happy', 'calm']


def test_build_voices_data_collects_emotions_and_warns_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """感情取得失敗時は警告を出しつつ空配列で継続する。"""
    monkeypatch.setattr(list_voices, 'get_narrators', lambda exe: ['A', 'B'])

    def fake_get_emotions(exe: str, narrator: str) -> list[str]:
        if narrator == 'A':
            return ['happy']
        raise RuntimeError('boom')

    monkeypatch.setattr(list_voices, 'get_emotions', fake_get_emotions)

    data = list_voices.build_voices_data('voicepeak.exe')

    assert data['voicepeak_path'] == 'voicepeak.exe'
    assert data['narrators_count'] == 2
    assert data['voices'] == [
        {'narrator': 'A', 'emotions': ['happy']},
        {'narrator': 'B', 'emotions': []},
    ]
    assert isinstance(data['generated_at'], str)


def test_parse_args_reads_voicepeak_path_and_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI 引数を Path と文字列で解釈する。"""
    monkeypatch.setattr(
        list_voices.argparse.ArgumentParser,
        'parse_args',
        lambda self: argparse.Namespace(voicepeak_path='vp.exe', output=Path('out.json')),
    )

    args = list_voices.parse_args()

    assert args.voicepeak_path == 'vp.exe'
    assert args.output == Path('out.json')
