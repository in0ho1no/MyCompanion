"""media モジュールのテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

import media


def test_find_character_image_returns_none_when_directory_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """画像ディレクトリがなければ None を返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path / 'missing')

    assert media._find_character_image() is None


def test_find_character_image_prefers_extension_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """拡張子の優先順に従って最初の画像を返す。"""
    jpg_path = tmp_path / 'character.jpg'
    png_path = tmp_path / 'character.png'
    jpg_path.write_bytes(b'jpg')
    png_path.write_bytes(b'png')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image() == png_path


def test_find_character_image_searches_narrator_subdirectories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクター別サブディレクトリ内の画像も探索する。"""
    narrator_dir = tmp_path / 'Miyamai Moca'
    narrator_dir.mkdir()
    image_path = narrator_dir / '1.png'
    image_path.write_bytes(b'png')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image() == image_path


def test_get_time_signal_files_filters_by_hhmm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """指定時刻に一致する WAV だけを返す。"""
    narrator_dir = tmp_path / 'Narrator'
    narrator_dir.mkdir()
    expected = narrator_dir / '0700_001.wav'
    expected.write_bytes(b'a')
    (narrator_dir / '0700_002.wav').write_bytes(b'b')
    (narrator_dir / '0800_001.wav').write_bytes(b'c')
    monkeypatch.setattr(media, '_TIME_SIGNAL_DIR', tmp_path)

    files = sorted(media._get_time_signal_files('0700'))

    assert files == sorted([expected, narrator_dir / '0700_002.wav'])


def test_get_clicked_files_returns_only_wavs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """クリック音声は wav 拡張子のみ列挙する。"""
    narrator_dir = tmp_path / 'Narrator'
    narrator_dir.mkdir()
    wav_path = narrator_dir / 'hello.wav'
    wav_path.write_bytes(b'wav')
    (narrator_dir / 'ignore.txt').write_text('x', encoding='utf-8')
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._get_clicked_files() == [wav_path]


def test_play_wav_invokes_winsound(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Winsound に非同期再生フラグ付きで委譲する。"""
    called: dict[str, int | str] = {}

    def fake_play_sound(path: str, flags: int) -> None:
        called['path'] = path
        called['flags'] = flags

    monkeypatch.setattr(media.winsound, 'PlaySound', fake_play_sound)
    wav_path = tmp_path / 'voice.wav'

    media._play_wav(wav_path)

    assert called == {
        'path': str(wav_path),
        'flags': media.winsound.SND_FILENAME | media.winsound.SND_ASYNC,
    }
