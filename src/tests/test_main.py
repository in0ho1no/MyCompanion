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


# ---------------------------------------------------------------------------
# _IMAGE_EXTS
# ---------------------------------------------------------------------------


def test_image_exts_contains_standard_formats() -> None:
    """標準的な画像拡張子がすべて含まれている。"""
    for ext in ('.gif', '.png', '.jpg', '.jpeg'):
        assert ext in media._IMAGE_EXTS


def test_image_exts_contains_webp() -> None:
    """Webp 形式がサポート対象に含まれている。"""
    assert '.webp' in media._IMAGE_EXTS


# ---------------------------------------------------------------------------
# _list_characters
# ---------------------------------------------------------------------------


def test_list_characters_returns_empty_when_directory_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """画像ルートディレクトリが存在しなければ空リストを返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path / 'missing')

    assert media._list_characters() == []


def test_list_characters_returns_empty_when_no_subdirectories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """サブディレクトリが存在しなければ空リストを返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_characters() == []


def test_list_characters_returns_sorted_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリ名を昇順で返す。"""
    for name in ('SEKAI', 'COKO', 'Miyamai Moca'):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_characters() == ['COKO', 'Miyamai Moca', 'SEKAI']


def test_list_characters_ignores_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ファイルはキャラクター一覧に含めない。"""
    (tmp_path / 'CharA').mkdir()
    (tmp_path / 'not_a_dir.png').write_bytes(b'x')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_characters() == ['CharA']


# ---------------------------------------------------------------------------
# _character_dir_exists
# ---------------------------------------------------------------------------


def test_character_dir_exists_returns_true_for_existing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリが存在するとき True を返す。"""
    (tmp_path / 'Moca').mkdir()
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._character_dir_exists('Moca') is True


def test_character_dir_exists_returns_false_for_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリが存在しないとき False を返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._character_dir_exists('Ghost') is False


def test_character_dir_exists_returns_false_when_path_is_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """同名のファイルが存在しても False を返す（ディレクトリではないため）。"""
    (tmp_path / 'Moca').write_bytes(b'x')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._character_dir_exists('Moca') is False


# ---------------------------------------------------------------------------
# _find_character_image_by_name
# ---------------------------------------------------------------------------


def test_find_character_image_by_name_returns_none_when_directory_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリが存在しなければ None を返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image_by_name('Ghost') is None


def test_find_character_image_by_name_returns_none_when_no_images(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ディレクトリが存在しても画像がなければ None を返す。"""
    (tmp_path / 'Moca').mkdir()
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image_by_name('Moca') is None


def test_find_character_image_by_name_prefers_extension_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """拡張子の優先順 (gif > png > jpg > jpeg > webp) に従う。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    (char_dir / 'image.jpg').write_bytes(b'jpg')
    (char_dir / 'image.png').write_bytes(b'png')
    (char_dir / 'image.gif').write_bytes(b'gif')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image_by_name('Moca') == char_dir / 'image.gif'


def test_find_character_image_by_name_finds_webp_when_only_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """他の形式が存在しないとき webp を返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    webp_path = char_dir / 'image.webp'
    webp_path.write_bytes(b'webp')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image_by_name('Moca') == webp_path


def test_find_character_image_by_name_returns_first_alphabetically_within_extension(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """同じ拡張子が複数あるとき最初のファイル（昇順）を返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    (char_dir / 'c.png').write_bytes(b'c')
    (char_dir / 'a.png').write_bytes(b'a')
    (char_dir / 'b.png').write_bytes(b'b')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._find_character_image_by_name('Moca') == char_dir / 'a.png'


# ---------------------------------------------------------------------------
# _list_character_images
# ---------------------------------------------------------------------------


def test_list_character_images_returns_empty_when_directory_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリが存在しなければ空リストを返す。"""
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_character_images('Ghost') == []


def test_list_character_images_returns_empty_when_no_images(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ディレクトリが存在しても画像がなければ空リストを返す。"""
    (tmp_path / 'Moca').mkdir()
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_character_images('Moca') == []


def test_list_character_images_sorted_by_filename_ascending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ファイル名の昇順で返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    (char_dir / 'c.png').write_bytes(b'c')
    (char_dir / 'a.png').write_bytes(b'a')
    (char_dir / 'b.png').write_bytes(b'b')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_character_images('Moca') == [
        char_dir / 'a.png',
        char_dir / 'b.png',
        char_dir / 'c.png',
    ]


def test_list_character_images_includes_all_supported_extensions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """サポート対象の全拡張子を列挙する。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    for ext in ('.gif', '.png', '.jpg', '.jpeg', '.webp'):
        (char_dir / f'image{ext}').write_bytes(b'x')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    result = media._list_character_images('Moca')

    assert len(result) == 5
    assert {p.suffix for p in result} == {'.gif', '.png', '.jpg', '.jpeg', '.webp'}


def test_list_character_images_ignores_non_image_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """画像以外のファイルは含めない。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    (char_dir / 'image.png').write_bytes(b'png')
    (char_dir / 'readme.txt').write_text('x', encoding='utf-8')
    (char_dir / 'voice.wav').write_bytes(b'wav')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    assert media._list_character_images('Moca') == [char_dir / 'image.png']


# ---------------------------------------------------------------------------
# _clicked_dir_exists
# ---------------------------------------------------------------------------


def test_clicked_dir_exists_returns_true_for_existing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """クリック音声ディレクトリが存在するとき True を返す。"""
    (tmp_path / 'Moca').mkdir()
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._clicked_dir_exists('Moca') is True


def test_clicked_dir_exists_returns_false_for_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """クリック音声ディレクトリが存在しないとき False を返す。"""
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._clicked_dir_exists('Ghost') is False


def test_clicked_dir_exists_returns_false_when_path_is_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """同名のファイルが存在しても False を返す（ディレクトリではないため）。"""
    (tmp_path / 'Moca').write_bytes(b'x')
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._clicked_dir_exists('Moca') is False


# ---------------------------------------------------------------------------
# _get_clicked_files_for_character
# ---------------------------------------------------------------------------


def test_get_clicked_files_for_character_returns_empty_when_directory_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクターディレクトリが存在しなければ空リストを返す。"""
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._get_clicked_files_for_character('Ghost') == []


def test_get_clicked_files_for_character_returns_only_wavs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WAV ファイルのみを返し、他の拡張子は除外する。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    wav_path = char_dir / 'greeting_001.wav'
    wav_path.write_bytes(b'wav')
    (char_dir / 'ignore.txt').write_text('x', encoding='utf-8')
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    assert media._get_clicked_files_for_character('Moca') == [wav_path]


def test_get_clicked_files_for_character_returns_sorted_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """複数ファイルをパス昇順で返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    paths = [char_dir / f'{name}.wav' for name in ('shy_001', 'greeting_001', 'idle_001')]
    for p in paths:
        p.write_bytes(b'wav')
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    result = media._get_clicked_files_for_character('Moca')

    assert result == sorted(paths)


def test_get_clicked_files_for_character_does_not_include_other_characters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """選択キャラクター以外の音声ファイルは含めない。"""
    (tmp_path / 'Moca').mkdir()
    (tmp_path / 'Moca' / 'greeting_001.wav').write_bytes(b'wav')
    (tmp_path / 'COKO').mkdir()
    (tmp_path / 'COKO' / 'hello_001.wav').write_bytes(b'wav')
    monkeypatch.setattr(media, '_CLICKED_DIR', tmp_path)

    result = media._get_clicked_files_for_character('Moca')

    assert result == [tmp_path / 'Moca' / 'greeting_001.wav']


# ---------------------------------------------------------------------------
# _pomodoro_dir_exists / _get_pomodoro_files_for_character
# ---------------------------------------------------------------------------


def test_pomodoro_dir_exists_returns_true_for_existing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ポモドーロ音声ディレクトリが存在するとき True を返す。"""
    (tmp_path / 'Moca').mkdir()
    monkeypatch.setattr(media, '_POMODORO_DIR', tmp_path)

    assert media._pomodoro_dir_exists('Moca') is True


def test_pomodoro_dir_exists_returns_false_for_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ポモドーロ音声ディレクトリが存在しないとき False を返す。"""
    monkeypatch.setattr(media, '_POMODORO_DIR', tmp_path)

    assert media._pomodoro_dir_exists('Ghost') is False


def test_get_pomodoro_files_for_character_returns_matching_wavs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """指定名に一致するポモドーロ音声のみ返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    wanted = char_dir / 'pomodoro_focus_start_001.wav'
    wanted.write_bytes(b'wav')
    (char_dir / 'pomodoro_break_start_001.wav').write_bytes(b'wav')
    monkeypatch.setattr(media, '_POMODORO_DIR', tmp_path)

    assert media._get_pomodoro_files_for_character('Moca', 'pomodoro_focus_start') == [wanted]


def test_list_character_images_sorts_across_extensions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """異なる拡張子のファイルもファイル名昇順で混在させて返す。"""
    char_dir = tmp_path / 'Moca'
    char_dir.mkdir()
    (char_dir / 'b.gif').write_bytes(b'gif')
    (char_dir / 'a.webp').write_bytes(b'webp')
    (char_dir / 'c.png').write_bytes(b'png')
    monkeypatch.setattr(media, '_IMAGE_DIR', tmp_path)

    result = media._list_character_images('Moca')

    assert [p.name for p in result] == ['a.webp', 'b.gif', 'c.png']
