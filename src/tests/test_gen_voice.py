"""gen_voice モジュールのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import gen_voice
import pytest


class _FixedNow:
    """固定時刻を返すテスト用オブジェクト。"""

    def isoformat(self, *, timespec: str) -> str:
        """固定の ISO 形式文字列を返す。"""
        assert timespec == 'seconds'
        return '2026-05-18T12:34:56'


class _FixedDateTime:
    """固定時刻の datetime 互換。"""

    @staticmethod
    def now() -> _FixedNow:
        """固定時刻オブジェクトを返す。"""
        return _FixedNow()


def test_load_config_prefers_explicit_arguments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """明示引数が config.toml より優先される。"""
    config_path = tmp_path / 'config.toml'
    config_path.write_text('[generate_voice]\nvoicepeak_path = "from-config.exe"\nnarrator = "Config Narrator"\n', encoding='utf-8')
    monkeypatch.setattr(gen_voice, '_CONFIG_PATH', config_path)

    voicepeak_path, narrator = gen_voice._load_config('from-arg.exe', 'Arg Narrator')

    assert voicepeak_path == 'from-arg.exe'
    assert narrator == 'Arg Narrator'


def test_load_config_allows_missing_narrator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ナレーター未設定でもフォールバックなしとして扱える。"""
    config_path = tmp_path / 'config.toml'
    config_path.write_text('[generate_voice]\nvoicepeak_path = "voicepeak.exe"\n', encoding='utf-8')
    monkeypatch.setattr(gen_voice, '_CONFIG_PATH', config_path)

    voicepeak_path, narrator = gen_voice._load_config(None, None)

    assert voicepeak_path == 'voicepeak.exe'
    assert narrator is None


def test_load_manifest_returns_empty_list_when_file_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """マニフェストがなければ空配列を返す。"""
    monkeypatch.setattr(gen_voice, '_MANIFEST_PATH', tmp_path / 'voice_manifest.json')

    assert gen_voice._load_manifest() == []


def test_save_manifest_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """マニフェストを JSON として保存する。"""
    manifest_path = tmp_path / 'voice_manifest.json'
    monkeypatch.setattr(gen_voice, '_MANIFEST_PATH', manifest_path)
    manifest: list[dict[str, object]] = [{'filename': '0700_001.wav', 'type': 'time_signal'}]

    gen_voice._save_manifest(manifest)

    assert json.loads(manifest_path.read_text(encoding='utf-8')) == manifest


def test_get_next_number_ignores_invalid_suffix(tmp_path: Path) -> None:
    """末尾番号を解釈できるファイルだけを採番対象にする。"""
    (tmp_path / '0700_001.wav').write_bytes(b'a')
    (tmp_path / '0700_bad.wav').write_bytes(b'b')
    (tmp_path / '0700_010.wav').write_bytes(b'c')

    assert gen_voice._get_next_number(tmp_path, '0700') == 11


def test_record_to_manifest_appends_duplicate_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """マニフェストに重複情報とハッシュを記録する。"""
    manifest: list[dict[str, object]] = []
    output_path = tmp_path / '0800_001.wav'
    output_path.write_bytes(b'wav')
    monkeypatch.setattr(gen_voice, 'datetime', _FixedDateTime)
    monkeypatch.setattr(gen_voice.dup_checker, 'check_file_duplicate', lambda output, folder: 'existing.wav')
    monkeypatch.setattr(gen_voice.dup_checker, 'compute_pcm_sha256', lambda output: 'abc123')

    gen_voice._record_to_manifest(
        manifest,
        filename='0800_001.wav',
        entry_type='time_signal',
        type_specific={'hhmm': '0800'},
        text='hello',
        narrator='Narrator',
        emotions='happy=50',
        output_path=output_path,
        dup_folder=tmp_path,
    )

    assert manifest == [
        {
            'filename': '0800_001.wav',
            'type': 'time_signal',
            'hhmm': '0800',
            'text': 'hello',
            'narrator': 'Narrator',
            'emotions': 'happy=50',
            'generated_at': '2026-05-18T12:34:56',
            'pcm_sha256': 'abc123',
            'duplicate_of': 'existing.wav',
        }
    ]


def test_validate_input_rejects_clicked_entry_without_name(capsys: pytest.CaptureFixture[str]) -> None:
    """Clicked の name 欠落を検出する。"""
    is_valid = gen_voice._validate_input({'clicked': [{'text': 'hello', 'narrator': 'Narrator'}]}, None)

    captured = capsys.readouterr()
    assert is_valid is False
    assert '"name" キーがありません' in captured.out


def test_validate_input_accepts_valid_entries() -> None:
    """必要キーが揃っていれば入力を受け入れる。"""
    input_data = {
        'time_signal': [
            {
                'hhmm': '0700',
                'texts': [
                    {'narrator': 'Narrator', 'emotion': 'happy', 'text': 'good morning'},
                ],
            }
        ],
        'clicked': [{'name': 'tap', 'narrator': 'Narrator', 'text': 'hello'}],
    }

    assert gen_voice._validate_input(input_data, None) is True


def test_validate_input_accepts_default_narrator_for_current_entries() -> None:
    """各エントリに narrator がなくても既定値があれば受け入れる。"""
    input_data = {
        'time_signal': [{'hhmm': '0700', 'texts': [{'text': 'good morning'}]}],
        'clicked': [{'name': 'tap', 'text': 'hello'}],
    }

    assert gen_voice._validate_input(input_data, 'Fallback Narrator') is True


def test_resolve_emotions_prefers_entry_value() -> None:
    """Emotion があれば CLI 指定より優先する。"""
    assert gen_voice._resolve_emotions({'emotion': 'happy'}, 'sad=20') == 'happy'


def test_get_output_dir_creates_narrator_specific_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ナレーターごとの出力先を作成して再利用する。"""
    monkeypatch.setattr(gen_voice, '_RESOURCE_VOICE_DIR', tmp_path)

    cache: dict[str, Path] = {}
    output_dir = gen_voice._get_output_dir('clicked', 'Narrator', cache)

    assert output_dir == tmp_path / 'clicked' / 'Narrator'
    assert output_dir.exists()
    assert gen_voice._get_output_dir('clicked', 'Narrator', cache) == output_dir
