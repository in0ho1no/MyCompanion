"""gui モジュールのテスト。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import flet as ft
import pytest

import gui


@dataclass
class _FakePage:
    """GUI 組み立てテスト向けの簡易 Page。"""

    overlay: list[Any] = field(default_factory=list)
    controls: list[ft.Control] = field(default_factory=list)
    updated: int = 0
    tasks: list[Any] = field(default_factory=list)
    title: str = ''
    bgcolor: str | None = None
    padding: int | None = None
    window: SimpleNamespace = field(
        default_factory=lambda: SimpleNamespace(
            always_on_top=False,
            width=0,
            height=0,
            maximizable=True,
            resizable=True,
        )
    )

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updated += 1

    def run_task(self, task: Any) -> None:
        self.tasks.append(task)


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


def test_build_gui_restores_selected_character_and_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """GUI 構築時に前回のキャラクターと画像を復元する。"""
    page = _FakePage()
    saved_states: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO', 'SEKAI'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'SEKAI', 'selected_image': '02.png'},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(
        gui,
        '_list_character_images',
        lambda character: [Path(f'{character}/01.png'), Path(f'{character}/02.png')],
    )
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: saved_states.append((character, image_name)))

    view = gui._build_gui(page)

    assert view.selected_char_label.value == 'SEKAI'
    assert view.char_image_area.alignment == ft.Alignment.CENTER
    assert isinstance(view.char_image_area.content, ft.Image)
    assert view.char_image_area.content.src == 'SEKAI\\02.png'
    assert saved_states[-1] == ('SEKAI', '02.png')


def test_character_menu_click_updates_image_and_persists_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """キャラクター選択で画像と保存状態が更新される。"""
    page = _FakePage()
    saved_states: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO', 'SEKAI'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': None, 'selected_image': None},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(
        gui,
        '_list_character_images',
        lambda character: [Path(f'{character}/01.png'), Path(f'{character}/02.png')] if character == 'COKO' else [Path('SEKAI/10.png')],
    )
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: saved_states.append((character, image_name)))

    view = gui._build_gui(page)
    view.select_character('SEKAI')

    assert view.selected_char_label.value == 'SEKAI'
    assert isinstance(view.char_image_area.content, ft.Image)
    assert view.char_image_area.content.src == 'SEKAI\\10.png'
    assert saved_states[-1] == ('SEKAI', '10.png')
    assert page.updated == 1


def test_character_image_handlers_cycle_and_reload_images(monkeypatch: pytest.MonkeyPatch) -> None:
    """右クリックで次画像へ進み、中クリックで先頭画像へ戻す。"""
    page = _FakePage()
    saved_states: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': '01.png'},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(
        gui,
        '_list_character_images',
        lambda character: [Path('COKO/01.png'), Path('COKO/02.png')],
    )
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: saved_states.append((character, image_name)))

    view = gui._build_gui(page)

    view.cycle_image()

    assert isinstance(view.char_image_area.content, ft.Image)
    assert view.char_image_area.content.src == 'COKO\\02.png'
    assert saved_states[-1] == ('COKO', '02.png')

    view.reload_image()

    assert isinstance(view.char_image_area.content, ft.Image)
    assert view.char_image_area.content.src == 'COKO\\01.png'
    assert saved_states[-1] == ('COKO', '01.png')


def test_wheel_click_handler_reloads_first_image_and_shows_snack(monkeypatch: pytest.MonkeyPatch) -> None:
    """ホイールクリックイベントで画像を先頭へ戻し、通知を表示する。"""
    page = _FakePage()
    saved_states: list[tuple[str | None, str | None]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': '01.png'},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(
        gui,
        '_list_character_images',
        lambda character: [Path('COKO/01.png'), Path('COKO/02.png')],
    )
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: saved_states.append((character, image_name)))

    view = gui._build_gui(page)
    view.cycle_image()

    assert view.char_container.on_tertiary_tap_down is not None
    wheel_click_handler = cast(Callable[[object], None], view.char_container.on_tertiary_tap_down)
    wheel_click_handler(SimpleNamespace())

    assert isinstance(view.char_image_area.content, ft.Image)
    assert view.char_image_area.content.src == 'COKO\\01.png'
    assert saved_states[-1] == ('COKO', '01.png')
    assert len(page.overlay) == 1
    snack = cast(ft.SnackBar, page.overlay[0])
    assert snack.open is True
    assert isinstance(snack.content, ft.Text)
    assert snack.content.value == '再読み込みしました'
