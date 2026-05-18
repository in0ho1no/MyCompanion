"""check_duplicate モジュールのテスト。"""

from __future__ import annotations

import wave
from pathlib import Path

import check_duplicate


def _write_wav(path: Path, frames: bytes) -> None:
    """テスト用の単純な WAV ファイルを書き出す。"""
    with wave.open(str(path), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(frames)


def test_compute_pcm_sha256_uses_pcm_payload(tmp_path: Path) -> None:
    """同じ PCM データなら同じハッシュになる。"""
    first = tmp_path / 'first.wav'
    second = tmp_path / 'second.wav'
    frames = b'\x01\x02\x03\x04'
    _write_wav(first, frames)
    _write_wav(second, frames)

    assert check_duplicate.compute_pcm_sha256(first) == check_duplicate.compute_pcm_sha256(second)


def test_check_file_duplicate_returns_matching_name(tmp_path: Path) -> None:
    """同じ音声データがあれば重複元のファイル名を返す。"""
    original = tmp_path / 'original.wav'
    duplicate = tmp_path / 'duplicate.wav'
    _write_wav(original, b'\x01\x02')
    _write_wav(duplicate, b'\x01\x02')

    assert check_duplicate.check_file_duplicate(duplicate, tmp_path) == 'original.wav'


def test_check_file_duplicate_returns_none_for_missing_file(tmp_path: Path) -> None:
    """対象ファイルがなければ重複判定しない。"""
    assert check_duplicate.check_file_duplicate(tmp_path / 'missing.wav', tmp_path) is None


def test_check_all_duplicates_collects_pairs(tmp_path: Path) -> None:
    """フォルダ内の重複ペアを列挙する。"""
    _write_wav(tmp_path / 'a.wav', b'\x00\x01')
    _write_wav(tmp_path / 'b.wav', b'\x10\x11')
    _write_wav(tmp_path / 'c.wav', b'\x00\x01')

    assert check_duplicate.check_all_duplicates(tmp_path) == [('a.wav', 'c.wav')]
