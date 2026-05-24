"""gui モジュールのテスト。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import flet as ft
import pytest

import gui


def _button_label(button: ft.OutlinedButton) -> str:
    """テスト用にボタンラベル文字列を返す。"""
    assert isinstance(button.content, ft.Text)
    return button.content.value


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
    on_keyboard_event: Callable[[object], None] | None = None
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


def test_load_today_todos_carries_items_over_to_next_day(tmp_path: Path) -> None:
    """保存日が違っても Todo は翌日へ持ち越す。"""
    state_file = tmp_path / 'state.json'
    state_file.write_text(
        '{"todo_date": "2026-05-23", "todos": [{"text": "散歩", "done": false}]}',
        encoding='utf-8',
    )

    assert gui._load_today_todos(state_file, today='2026-05-24') == [gui._TodoItem(text='散歩', done=False)]


def test_normalize_todos_filters_invalid_entries_and_limits_to_ten() -> None:
    """Todo 復元時は不正項目を除外し、10 件までに制限する。"""
    raw: list[object] = [
        {'text': '  散歩  ', 'done': False},
        {'text': '', 'done': True},
        {'text': '   ', 'done': False},
        {'text': '読書', 'done': True},
        {'text': 123, 'done': False},
        'invalid',
    ] + [{'text': f'Task {index}', 'done': index % 2 == 0} for index in range(12)]

    todos = gui._normalize_todos(raw)

    assert len(todos) == 10
    assert todos[0] == gui._TodoItem(text='散歩', done=False)
    assert todos[1] == gui._TodoItem(text='読書', done=True)
    assert todos[-1] == gui._TodoItem(text='Task 7', done=False)


def test_save_today_todos_truncates_to_ten_items(tmp_path: Path) -> None:
    """Todo 保存時も 10 件までに切り詰める。"""
    state_file = tmp_path / 'state.json'
    todos = [gui._TodoItem(text=f'Task {index}', done=index % 2 == 0) for index in range(12)]

    gui._save_today_todos(todos, state_file, today='2026-05-24')

    assert gui._load_today_todos(state_file, today='2026-05-24') == todos[:10]


def test_save_ui_state_preserves_today_todos(tmp_path: Path) -> None:
    """キャラクター保存時に Todo 状態を消さない。"""
    state_file = tmp_path / 'state.json'

    gui._save_today_todos(
        [gui._TodoItem(text='散歩'), gui._TodoItem(text='読書', done=True)],
        state_file,
        today='2026-05-24',
    )
    gui._save_ui_state('SEKAI', '02.png', state_file)

    assert gui._load_ui_state(state_file) == {
        'selected_character': 'SEKAI',
        'selected_image': '02.png',
    }
    assert gui._load_today_todos(state_file, today='2026-05-24') == [
        gui._TodoItem(text='散歩', done=False),
        gui._TodoItem(text='読書', done=True),
    ]


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


def test_build_gui_sets_todo_hint_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo 入力欄のヒントに確定と削除操作を表示する。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(gui, '_load_today_todos', lambda state_file=gui._STATE_FILE, today=None: [])
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)

    view = gui._build_gui(page)

    assert view.todo_input.hint_text == 'Enter で確定・Delete で削除'


def test_build_gui_edits_reorders_and_checks_today_todos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo 選択編集、並び替え、チェック変更が保存される。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [
            gui._TodoItem(text='牛乳を買う'),
            gui._TodoItem(text='資料整理'),
            gui._TodoItem(text='散歩'),
        ],
    )
    monkeypatch.setattr(gui, '_today_key', lambda now=None: '2026-05-24')
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)

    assert view.todo_list_column.controls
    first_row = cast(ft.Container, view.todo_list_column.controls[0])
    first_row_content = cast(ft.Row, first_row.content)
    first_checkbox = cast(ft.Checkbox, first_row_content.controls[0])
    first_text_container = cast(ft.Container, first_row_content.controls[1])
    assert isinstance(first_text_container.content, ft.Text)
    assert first_text_container.content.value == '牛乳を買う'
    assert first_text_container.alignment == ft.Alignment.CENTER_LEFT
    assert first_checkbox.value is False

    view.select_todo(1)
    assert view.todo_input.value == '資料整理'
    selected_row = cast(ft.Container, view.todo_list_column.controls[1])
    selected_row_content = cast(ft.Row, selected_row.content)
    assert selected_row_content.controls[1] is view.todo_input

    view.todo_input.value = '資料整理 更新'
    view.commit_todo()
    assert saved_todos[-1] == [
        gui._TodoItem(text='牛乳を買う', done=False),
        gui._TodoItem(text='資料整理 更新', done=False),
        gui._TodoItem(text='散歩', done=False),
    ]

    view.move_todo_down(0)
    assert saved_todos[-1] == [
        gui._TodoItem(text='資料整理 更新', done=False),
        gui._TodoItem(text='牛乳を買う', done=False),
        gui._TodoItem(text='散歩', done=False),
    ]

    second_row = cast(ft.Container, view.todo_list_column.controls[1])
    second_row_content = cast(ft.Row, second_row.content)
    second_checkbox = cast(ft.Checkbox, second_row_content.controls[0])
    second_checkbox.value = True
    assert second_checkbox.on_change is not None
    toggle_handler = cast(Callable[[object], None], second_checkbox.on_change)
    toggle_handler(SimpleNamespace(control=second_checkbox))

    updated_second_row = cast(ft.Container, view.todo_list_column.controls[1])
    updated_second_row_content = cast(ft.Row, updated_second_row.content)
    updated_second_text_container = cast(ft.Container, updated_second_row_content.controls[1])
    assert isinstance(updated_second_text_container.content, ft.Text)
    assert updated_second_text_container.content.style is not None
    assert updated_second_text_container.content.style.decoration == ft.TextDecoration.LINE_THROUGH

    assert saved_todos[-1] == [
        gui._TodoItem(text='資料整理 更新', done=False),
        gui._TodoItem(text='牛乳を買う', done=True),
        gui._TodoItem(text='散歩', done=False),
    ]


def test_build_gui_reorder_keeps_selected_editor_when_target_row_moves(monkeypatch: pytest.MonkeyPatch) -> None:
    """選択中の行へ他項目が移動してきても編集対象を保つ。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [
            gui._TodoItem(text='牛乳を買う'),
            gui._TodoItem(text='資料整理'),
            gui._TodoItem(text='散歩'),
        ],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(gui, '_save_today_todos', lambda todos, state_file=gui._STATE_FILE, today=None: None)

    view = gui._build_gui(page)
    view.select_todo(1)
    view.move_todo_up(2)

    moved_row = cast(ft.Container, view.todo_list_column.controls[2])
    moved_row_content = cast(ft.Row, moved_row.content)
    assert moved_row_content.controls[1] is view.todo_input
    assert view.todo_input.value == '資料整理'


def test_build_gui_keyboard_event_ignores_non_delete_when_todo_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """空欄編集中でも Delete 系以外のキーでは Todo を消さない。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.select_todo(0)
    view.todo_input.value = ''

    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='A'))

    assert saved_todos == []
    selected_row = cast(ft.Container, view.todo_list_column.controls[0])
    selected_row_content = cast(ft.Row, selected_row.content)
    assert selected_row_content.controls[1] is view.todo_input


def test_build_gui_keyboard_event_ignores_delete_when_input_not_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delete 系のキーでも入力中に文字があれば Todo を消さない。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.select_todo(0)
    view.todo_input.value = '編集中'

    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Delete'))

    assert saved_todos == []
    assert view.todo_input.value == '編集中'


def test_build_gui_cancels_existing_todo_edit_with_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    """編集中の既存 Todo は Escape で未保存変更を破棄する。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.select_todo(0)
    view.todo_input.value = '牛乳を買う 変更中'

    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Escape'))

    assert saved_todos == []
    row = cast(ft.Container, view.todo_list_column.controls[0])
    row_content = cast(ft.Row, row.content)
    text_container = cast(ft.Container, row_content.controls[1])
    assert isinstance(text_container.content, ft.Text)
    assert text_container.content.value == '牛乳を買う'


def test_build_gui_cancels_new_todo_edit_with_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    """新規 Todo の入力行は Escape でキャンセルする。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)

    view = gui._build_gui(page)
    view.start_new_todo()
    view.todo_input.value = '資料整理'

    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Escape'))

    add_row = cast(ft.Container, view.todo_list_column.controls[1])
    add_button = cast(ft.TextButton, add_row.content)
    assert isinstance(add_button.content, ft.Text)
    assert add_button.content.value == '＋ 新しいTodo'


def test_build_gui_commits_selected_todo_with_enter_without_text_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """行選択直後でも Enter で Todo 編集を確定して閉じる。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.select_todo(0)

    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Enter'))

    assert saved_todos[-1] == [gui._TodoItem(text='牛乳を買う', done=False)]
    row = cast(ft.Container, view.todo_list_column.controls[0])
    row_content = cast(ft.Row, row.content)
    text_container = cast(ft.Container, row_content.controls[1])
    assert isinstance(text_container.content, ft.Text)
    assert text_container.content.value == '牛乳を買う'


def test_build_gui_starts_new_todo_inline_when_list_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo が空でも新規入力をその場で開始できる。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(gui, '_load_today_todos', lambda state_file=gui._STATE_FILE, today=None: [])
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)

    view = gui._build_gui(page)

    add_row = cast(ft.Container, view.todo_list_column.controls[0])
    add_button = cast(ft.TextButton, add_row.content)
    assert isinstance(add_button.content, ft.Text)
    assert add_button.content.value == '＋ 新しいTodo'

    view.start_new_todo()

    inline_add_row = cast(ft.Container, view.todo_list_column.controls[0])
    inline_add_row_content = cast(ft.Row, inline_add_row.content)
    assert inline_add_row_content.controls[1] is view.todo_input


def test_build_gui_starts_new_todo_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """新規 Todo は一覧末尾の行をその場編集して追加する。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)

    add_row = cast(ft.Container, view.todo_list_column.controls[1])
    add_button = cast(ft.TextButton, add_row.content)
    assert isinstance(add_button.content, ft.Text)
    assert add_button.content.value == '＋ 新しいTodo'

    view.start_new_todo()
    inline_add_row = cast(ft.Container, view.todo_list_column.controls[1])
    inline_add_row_content = cast(ft.Row, inline_add_row.content)
    assert inline_add_row_content.controls[1] is view.todo_input

    view.todo_input.value = '資料整理'
    view.commit_todo()

    assert saved_todos[-1] == [
        gui._TodoItem(text='牛乳を買う', done=False),
        gui._TodoItem(text='資料整理', done=False),
    ]


def test_build_gui_deletes_empty_selected_todo_with_backspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """空欄の編集中 Todo は Backspace/Delete で削除する。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [
            gui._TodoItem(text='牛乳を買う'),
            gui._TodoItem(text='資料整理'),
        ],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.select_todo(0)
    view.todo_input.value = ''

    assert hasattr(page, 'on_keyboard_event')
    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Backspace'))

    assert saved_todos[-1] == [gui._TodoItem(text='資料整理', done=False)]
    remaining_row = cast(ft.Container, view.todo_list_column.controls[0])
    remaining_row_content = cast(ft.Row, remaining_row.content)
    remaining_text_container = cast(ft.Container, remaining_row_content.controls[1])
    assert isinstance(remaining_text_container.content, ft.Text)
    assert remaining_text_container.content.value == '資料整理'


def test_build_gui_cancels_empty_new_todo_with_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    """空欄の新規 Todo 行は Delete でキャンセルする。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text='牛乳を買う')],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)

    view = gui._build_gui(page)
    view.start_new_todo()
    view.todo_input.value = ''

    assert hasattr(page, 'on_keyboard_event')
    keyboard_handler = cast(Callable[[object], None], page.on_keyboard_event)
    keyboard_handler(SimpleNamespace(key='Delete'))

    add_row = cast(ft.Container, view.todo_list_column.controls[1])
    add_button = cast(ft.TextButton, add_row.content)
    assert isinstance(add_button.content, ft.Text)
    assert add_button.content.value == '＋ 新しいTodo'


def test_build_gui_limits_todos_to_ten_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo は 10 件を超えて追加しない。"""
    page = _FakePage()
    saved_todos: list[list[gui._TodoItem]] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(
        gui,
        '_load_today_todos',
        lambda state_file=gui._STATE_FILE, today=None: [gui._TodoItem(text=f'Task {index}') for index in range(10)],
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_save_today_todos',
        lambda todos, state_file=gui._STATE_FILE, today=None: saved_todos.append([gui._TodoItem(text=item.text, done=item.done) for item in todos]),
    )

    view = gui._build_gui(page)
    view.start_new_todo()

    assert len(view.todo_list_column.controls) == 10
    assert saved_todos == []
    assert len(page.overlay) == 1
    snack = cast(ft.SnackBar, page.overlay[0])
    assert isinstance(snack.content, ft.Text)
    assert snack.content.value == 'Todo は最大10件までです'


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


def test_build_gui_initializes_pomodoro_panel(monkeypatch: pytest.MonkeyPatch) -> None:
    """GUI 構築時にポモドーロ表示を初期化する。"""
    page = _FakePage()

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_load_pomodoro_config',
        lambda config_path=gui._CONFIG_PATH: gui._PomodoroConfig(
            focus_seconds=120,
            break_seconds=60,
            sets=3,
        ),
    )

    view = gui._build_gui(page)

    assert view.pomodoro_phase_label.value == '未開始'
    assert view.pomodoro_timer_label.value == '02:00'
    assert view.pomodoro_status_label.value == '開始待ち'
    assert _button_label(view.pomodoro_start_button) == '開始'
    assert view.pomodoro_pause_button.disabled is True
    assert view.pomodoro_skip_button.disabled is True


def test_pomodoro_start_pause_skip_and_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """ポモドーロの開始・一時停止・スキップ・完了遷移を反映する。"""
    page = _FakePage()
    played_paths: list[str] = []

    monkeypatch.setattr(gui, '_list_characters', lambda: ['COKO'])
    monkeypatch.setattr(
        gui,
        '_load_ui_state',
        lambda state_file=gui._STATE_FILE: {'selected_character': 'COKO', 'selected_image': None},
    )
    monkeypatch.setattr(gui, '_character_dir_exists', lambda character: True)
    monkeypatch.setattr(gui, '_list_character_images', lambda character: [Path('COKO/01.png')])
    monkeypatch.setattr(gui, '_save_ui_state', lambda character, image_name, state_file=gui._STATE_FILE: None)
    monkeypatch.setattr(
        gui,
        '_load_pomodoro_config',
        lambda config_path=gui._CONFIG_PATH: gui._PomodoroConfig(
            focus_seconds=2,
            break_seconds=1,
            sets=2,
            auto_start_break=True,
            auto_start_focus=True,
        ),
    )
    monkeypatch.setattr(
        gui,
        '_get_pomodoro_files_for_character',
        lambda character, name: [Path(f'{character}/{name}_001.wav')],
    )
    monkeypatch.setattr(gui, '_play_wav', lambda path: played_paths.append(str(path)))

    view = gui._build_gui(page)

    view.start_pomodoro()
    assert view.pomodoro_phase_label.value == '集中 1 / 2'
    assert view.pomodoro_status_label.value == '実行中'
    assert _button_label(view.pomodoro_start_button) == '中止'
    assert played_paths[-1].endswith('pomodoro_focus_start_001.wav')

    view.toggle_pomodoro_pause()
    assert view.pomodoro_status_label.value == '一時停止中'
    assert _button_label(view.pomodoro_pause_button) == '再開'

    view.toggle_pomodoro_pause()
    view.tick_pomodoro()
    assert view.pomodoro_timer_label.value == '00:01'

    view.tick_pomodoro()
    assert view.pomodoro_phase_label.value == '休憩 1 / 2'
    assert played_paths[-1].endswith('pomodoro_break_start_001.wav')

    view.skip_pomodoro()
    assert view.pomodoro_phase_label.value == '集中 2 / 2'
    assert played_paths[-1].endswith('pomodoro_focus_start_001.wav')

    view.tick_pomodoro()
    view.tick_pomodoro()
    assert view.pomodoro_phase_label.value == '完了 2 / 2'
    assert view.pomodoro_status_label.value == '完了'
    assert played_paths[-1].endswith('pomodoro_finish_001.wav')
