"""gui モジュールのテスト。"""

from pathlib import Path

import gui


def test_load_selected_character_returns_none_when_file_missing(tmp_path: Path) -> None:
    """状態ファイルがなければ None を返す。"""
    assert gui._load_selected_character(tmp_path / 'missing.json') is None


def test_load_selected_character_returns_none_for_invalid_json(tmp_path: Path) -> None:
    """JSON が壊れていれば None を返す。"""
    state_file = tmp_path / 'state.json'
    state_file.write_text('{invalid', encoding='utf-8')

    assert gui._load_selected_character(state_file) is None


def test_save_and_load_selected_character_round_trip(tmp_path: Path) -> None:
    """保存したキャラクター名を後で復元できる。"""
    state_file = tmp_path / 'state.json'

    gui._save_selected_character('SEKAI', state_file)

    assert gui._load_selected_character(state_file) == 'SEKAI'


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
