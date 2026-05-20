"""gui モジュールのテスト。"""

from pathlib import Path

import gui


def test_load_selected_character_returns_none_when_file_missing(tmp_path: Path) -> None:
    """状態ファイルがなければ None を返す。"""
    assert gui._load_selected_character(tmp_path / 'missing.json') is None


def test_load_selected_image_returns_none_when_file_missing(tmp_path: Path) -> None:
    """状態ファイルがなければ画像名も None を返す。"""
    assert gui._load_selected_image(tmp_path / 'missing.json') is None


def test_load_selected_character_returns_none_for_invalid_json(tmp_path: Path) -> None:
    """JSON が壊れていれば None を返す。"""
    state_file = tmp_path / 'state.json'
    state_file.write_text('{invalid', encoding='utf-8')

    assert gui._load_selected_character(state_file) is None


def test_save_and_load_selected_character_round_trip(tmp_path: Path) -> None:
    """保存したキャラクター名を後で復元できる。"""
    state_file = tmp_path / 'state.json'

    gui._save_ui_state('SEKAI', '02.png', state_file)

    assert gui._load_selected_character(state_file) == 'SEKAI'


def test_save_and_load_selected_image_round_trip(tmp_path: Path) -> None:
    """保存した画像名を後で復元できる。"""
    state_file = tmp_path / 'state.json'

    gui._save_ui_state('SEKAI', '02.png', state_file)

    assert gui._load_selected_image(state_file) == '02.png'


def test_load_ui_state_supports_legacy_character_only_format(tmp_path: Path) -> None:
    """旧形式の状態ファイルでもキャラクター名は復元する。"""
    state_file = tmp_path / 'state.json'
    state_file.write_text('"SEKAI"', encoding='utf-8')

    assert gui._load_ui_state(state_file) == {
        'selected_character': 'SEKAI',
        'selected_image': None,
    }


def test_resolve_initial_character_prefers_previous_selection() -> None:
    """前回選択が存在すればそのまま復元する。"""
    selected, message = gui._resolve_initial_character(['COKO', 'SEKAI'], 'SEKAI')

    assert selected == 'SEKAI'
    assert message is None


def test_resolve_initial_character_falls_back_to_first_sorted_character() -> None:
    """前回選択がなければ先頭キャラクターへフォールバックする。"""
    selected, message = gui._resolve_initial_character(['COKO', 'Miyamai Moca', 'SEKAI'], 'Ghost')

    assert selected == 'COKO'
    assert message == '前回選択していた「Ghost」が存在しません。代わりに「COKO」を選択しました'


def test_resolve_initial_character_returns_none_when_no_characters() -> None:
    """キャラクター一覧が空なら選択しない。"""
    selected, message = gui._resolve_initial_character([], 'Ghost')

    assert selected is None
    assert message is None


def test_resolve_image_path_prefers_previous_image_name(tmp_path: Path) -> None:
    """前回画像名が存在すればその画像を復元する。"""
    images = [tmp_path / '01.png', tmp_path / '02.png']

    selected = gui._resolve_image_path(images, '02.png')

    assert selected == tmp_path / '02.png'


def test_resolve_image_path_falls_back_to_first_image_when_missing(tmp_path: Path) -> None:
    """前回画像がなければ先頭画像へ戻す。"""
    images = [tmp_path / '01.png', tmp_path / '02.png']

    selected = gui._resolve_image_path(images, '99.png')

    assert selected == tmp_path / '01.png'
