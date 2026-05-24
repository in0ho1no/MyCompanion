"""Flet GUI の構築とイベント処理。"""

import asyncio
import json
import random
import tomllib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import flet as ft

from media import (
    _character_dir_exists,
    _clicked_dir_exists,
    _get_clicked_files_for_character,
    _get_pomodoro_files_for_character,
    _get_time_signal_files,
    _list_character_images,
    _list_characters,
    _play_wav,
)

_TZ_TOKYO = timezone(timedelta(hours=9))

# ウィンドウ・レイアウト定数
_WIN_W: int = 720
_WIN_H: int = 640
_TITLEBAR_H: int = 36
_PADDING: int = 14
_GAP: int = 14
_BODY_H: int = _WIN_H - _TITLEBAR_H - _PADDING * 2
_CHAR_W: int = int(_BODY_H * 9 / 16)

# カラーパレット（ライト・ウォームクリーム）
_C_BG_WINDOW = '#faf6ef'
_C_BG_PANEL = '#f3ede2'
_C_BG_IMAGE = '#e8e1d3'
_C_LINE = '#d8cfbe'
_C_LINE_STRONG = '#b8ad97'
_C_INK = '#2a2620'
_C_INK_SOFT = '#6e6657'
_C_INK_MUTE = '#9d937e'
_C_ACCENT = '#b5722d'

_WEEKDAY_JA = ['月', '火', '水', '木', '金', '土', '日']
_MONO = 'Consolas'
_STATE_FILE = Path(__file__).with_name('.mycompanion_state.json')
_CONFIG_PATH = Path(__file__).with_name('config.toml')


@dataclass(frozen=True)
class _PomodoroConfig:
    """ポモドーロタイマー設定。"""

    focus_seconds: int = 25 * 60
    break_seconds: int = 5 * 60
    sets: int = 4
    auto_start_break: bool = True
    auto_start_focus: bool = True


@dataclass
class _GuiView:
    """テストから主要コントロールへアクセスするための GUI 参照。"""

    root: ft.Control
    startup_message: str | None
    clock_loop: Callable[[], Awaitable[None]]
    char_container: ft.GestureDetector
    char_menu: ft.PopupMenuButton
    char_image_area: ft.Container
    selected_char_label: ft.Text
    select_character: Callable[[str], None]
    reload_image: Callable[[], None]
    cycle_image: Callable[[], None]
    pomodoro_phase_label: ft.Text
    pomodoro_timer_label: ft.Text
    pomodoro_status_label: ft.Text
    pomodoro_start_button: ft.OutlinedButton
    pomodoro_pause_button: ft.OutlinedButton
    pomodoro_skip_button: ft.OutlinedButton
    todo_input: ft.TextField
    todo_list_column: ft.Column
    select_todo: Callable[[int], None]
    start_new_todo: Callable[[], None]
    commit_todo: Callable[[], None]
    move_todo_up: Callable[[int], None]
    move_todo_down: Callable[[int], None]
    start_pomodoro: Callable[[], None]
    toggle_pomodoro_pause: Callable[[], None]
    skip_pomodoro: Callable[[], None]
    tick_pomodoro: Callable[[], None]


@dataclass
class _TodoItem:
    """1 件分の Todo 項目。"""

    text: str
    done: bool = False


def _load_pomodoro_config(config_path: Path = _CONFIG_PATH) -> _PomodoroConfig:
    """config.toml からポモドーロ設定を読み込む。"""

    def _coerce_positive_int(value: object, default: int) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int) and value > 0:
            return value
        return default

    def _coerce_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        return default

    try:
        with config_path.open('rb') as config_file:
            config = tomllib.load(config_file)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return _PomodoroConfig()

    section = config.get('pomodoro')
    if not isinstance(section, dict):
        return _PomodoroConfig()

    focus_minutes = _coerce_positive_int(section.get('focus_minutes'), 25)
    break_minutes = _coerce_positive_int(section.get('break_minutes'), 5)
    sets = _coerce_positive_int(section.get('sets'), 4)
    auto_start_break = _coerce_bool(section.get('auto_start_break'), True)
    auto_start_focus = _coerce_bool(section.get('auto_start_focus'), True)
    return _PomodoroConfig(
        focus_seconds=focus_minutes * 60,
        break_seconds=break_minutes * 60,
        sets=sets,
        auto_start_break=auto_start_break,
        auto_start_focus=auto_start_focus,
    )


def _format_mmss(total_seconds: int) -> str:
    """秒数を MM:SS 形式へ変換する。"""
    minutes, seconds = divmod(max(total_seconds, 0), 60)
    return f'{minutes:02d}:{seconds:02d}'


def _make_button(label: str, *, disabled: bool = False) -> ft.OutlinedButton:
    """ラベル付きボタンを返す。"""
    return ft.OutlinedButton(content=ft.Text(label, font_family=_MONO, size=11), disabled=disabled)


def _set_button_label(button: ft.OutlinedButton, label: str) -> None:
    """ボタンラベルを更新する。"""
    if isinstance(button.content, ft.Text):
        button.content.value = label


def _make_panel_badge(label: str) -> ft.Row:
    """カード左上の小さな見出しを返す。"""
    return ft.Row(
        [
            ft.Container(width=6, height=6, bgcolor=_C_ACCENT, border_radius=3),
            ft.Text(label, size=10, color=_C_INK_MUTE, font_family=_MONO),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _read_state_payload(state_file: Path = _STATE_FILE) -> dict[str, Any]:
    """状態ファイル全体を辞書として返す。"""
    try:
        raw = json.loads(state_file.read_text(encoding='utf-8'))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}

    if isinstance(raw, str):
        return {'selected_character': raw or None}
    if not isinstance(raw, dict):
        return {}

    return raw


def _load_ui_state(state_file: Path = _STATE_FILE) -> dict[str, str | None]:
    """保存済み UI 状態を返す。"""
    raw = _read_state_payload(state_file)

    selected_character = raw.get('selected_character')
    selected_image = raw.get('selected_image')
    return {
        'selected_character': selected_character if isinstance(selected_character, str) and selected_character else None,
        'selected_image': selected_image if isinstance(selected_image, str) and selected_image else None,
    }


def _load_selected_character(state_file: Path = _STATE_FILE) -> str | None:
    """保存済みの選択キャラクター名を返す。"""
    return _load_ui_state(state_file)['selected_character']


def _load_selected_image(state_file: Path = _STATE_FILE) -> str | None:
    """保存済みの選択画像ファイル名を返す。"""
    return _load_ui_state(state_file)['selected_image']


def _today_key(now: datetime | None = None) -> str:
    """Todo を区切る当日キーを返す。"""
    current = now if now is not None else datetime.now(_TZ_TOKYO)
    return current.strftime('%Y-%m-%d')


def _normalize_todos(raw: object) -> list[_TodoItem]:
    """保存データから有効な Todo 項目だけを復元する。"""
    if not isinstance(raw, list):
        return []

    items: list[_TodoItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        text = entry.get('text')
        done = entry.get('done', False)
        if not isinstance(text, str):
            continue
        trimmed = text.strip()
        if not trimmed:
            continue
        items.append(_TodoItem(text=trimmed, done=bool(done)))
    return items[:10]


def _load_today_todos(state_file: Path = _STATE_FILE, today: str | None = None) -> list[_TodoItem]:
    """Todo 一覧を返す。日付が変わっても未整理分を持ち越す。"""
    raw = _read_state_payload(state_file)
    return _normalize_todos(raw.get('todos'))


def _save_state_payload(payload: dict[str, Any], state_file: Path = _STATE_FILE) -> None:
    """状態ファイル全体を書き戻す。"""
    try:
        state_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    except OSError:
        return


def _save_today_todos(
    todos: list[_TodoItem],
    state_file: Path = _STATE_FILE,
    today: str | None = None,
) -> None:
    """Todo 一覧を状態ファイルへ保存する。"""
    payload = _read_state_payload(state_file)
    payload['todo_date'] = today if today is not None else _today_key()
    payload['todos'] = [{'text': item.text, 'done': item.done} for item in todos[:10]]
    _save_state_payload(payload, state_file)


def _save_ui_state(
    character: str | None,
    image_name: str | None,
    state_file: Path = _STATE_FILE,
) -> None:
    """選択中の UI 状態を状態ファイルへ保存する。"""
    payload = _read_state_payload(state_file)
    payload['selected_character'] = character
    payload['selected_image'] = image_name
    _save_state_payload(payload, state_file)


def _save_selected_character(character: str | None, state_file: Path = _STATE_FILE) -> None:
    """選択中キャラクター名を状態ファイルへ保存する。"""
    selected_image = _load_selected_image(state_file)
    _save_ui_state(character, selected_image, state_file)


def _resolve_initial_character(characters: list[str], previous_character: str | None) -> tuple[str | None, str | None]:
    """起動時の選択キャラクターと必要な通知メッセージを返す。"""
    if not characters:
        return None, None
    if previous_character is None:
        return characters[0], None
    if previous_character in characters:
        return previous_character, None

    fallback_character = characters[0]
    message = f'前回選択していた「{previous_character}」が存在しません。代わりに「{fallback_character}」を選択しました'
    return fallback_character, message


def _resolve_image_path(images: list[Path], previous_image_name: str | None) -> Path | None:
    """起動時または再描画時に表示すべき画像を返す。"""
    if not images:
        return None
    if previous_image_name is None:
        return images[0]

    for image in images:
        if image.name == previous_image_name:
            return image
    return images[0]


def _configure_page(page: Any) -> None:
    """ページの基本設定を適用する。"""
    page.title = 'MyCompanion'
    page.window.always_on_top = True
    page.window.width = _WIN_W
    page.window.height = _WIN_H
    page.window.maximizable = False
    page.window.resizable = False
    page.bgcolor = _C_BG_WINDOW
    page.padding = 0


def _build_gui(page: Any) -> _GuiView:
    """GUI を構築し、主要コントロール参照を返す。"""
    hhmm_text = ft.Text('00:00', size=56, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO)
    ss_text = ft.Text(':00', size=28, color=_C_INK_MUTE, font_family=_MONO)
    date_text = ft.Text('---- -- -- (--)', size=12, weight=ft.FontWeight.W_500, color=_C_INK_SOFT)
    pomodoro_config = _load_pomodoro_config()

    characters = _list_characters()
    ui_state = _load_ui_state()
    todo_items: list[_TodoItem] = _load_today_todos()
    previous_character = ui_state['selected_character']
    previous_image_name = ui_state['selected_image']
    current_character, startup_message = _resolve_initial_character(characters, previous_character)
    image_found: list[bool] = [False]
    current_image_path: list[Path | None] = [None]
    selected_image_name: list[str | None] = [previous_image_name if current_character == previous_character else None]

    def _reload_hint() -> ft.Text:
        return ft.Text('wheel click · 再読み込み', size=10, color=_C_INK_MUTE, font_family=_MONO, opacity=0.5)

    def _make_char_content(character: str | None, preferred_image_name: str | None = None) -> ft.Control:
        if character is None:
            image_found[0] = False
            current_image_path[0] = None
            selected_image_name[0] = None
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text('9 : 16', size=13, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO),
                        ft.Text('キャラクターを選択してください', size=12, color=_C_INK_MUTE, font_family=_MONO),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )

        if not _character_dir_exists(character):
            image_found[0] = False
            current_image_path[0] = None
            selected_image_name[0] = None
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f'「{character}」のフォルダが\n見つかりません',
                            size=12,
                            color=_C_INK_MUTE,
                            font_family=_MONO,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            f'resource/image/character/{character}/',
                            size=11,
                            color=_C_INK_MUTE,
                            font_family=_MONO,
                            opacity=0.6,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        _reload_hint(),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )

        images = _list_character_images(character)
        img = _resolve_image_path(images, preferred_image_name)
        if img:
            image_found[0] = True
            current_image_path[0] = img
            selected_image_name[0] = img.name
            return ft.Image(src=str(img), fit=ft.BoxFit.COVER)

        image_found[0] = False
        current_image_path[0] = None
        selected_image_name[0] = None
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text('9 : 16', size=13, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO),
                    ft.Text('drop character image here', size=12, color=_C_INK_MUTE, font_family=_MONO),
                    ft.Text(
                        f'resource/image/character/{character}/<name>.png',
                        size=11,
                        color=_C_INK_MUTE,
                        font_family=_MONO,
                        opacity=0.7,
                    ),
                    _reload_hint(),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )

    char_image_area = ft.Container(
        content=_make_char_content(current_character, selected_image_name[0]),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
    _save_ui_state(current_character, selected_image_name[0])

    played_hhmm: set[str] = set()
    pomodoro_phase: list[str] = ['idle']
    pomodoro_set: list[int] = [0]
    pomodoro_remaining: list[int] = [pomodoro_config.focus_seconds]
    pomodoro_paused: list[bool] = [False]

    pomodoro_phase_label = ft.Text('未開始', size=11, color=_C_INK_SOFT, font_family=_MONO)
    pomodoro_timer_label = ft.Text(
        _format_mmss(pomodoro_config.focus_seconds),
        size=34,
        weight=ft.FontWeight.W_500,
        color=_C_INK,
        font_family=_MONO,
    )
    pomodoro_status_label = ft.Text('開始待ち', size=12, color=_C_INK_MUTE, font_family=_MONO)
    pomodoro_start_button = _make_button('開始')
    pomodoro_pause_button = _make_button('一時停止', disabled=True)
    pomodoro_skip_button = _make_button('スキップ', disabled=True)
    todo_input = ft.TextField(
        hint_text='Enter で確定',
        text_size=12,
        expand=True,
        border_color=_C_LINE_STRONG,
        focused_border_color=_C_ACCENT,
        cursor_color=_C_ACCENT,
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        dense=True,
    )
    todo_list_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
    selected_todo_index: list[int | None] = [None]

    def _show_snack(msg: str) -> None:
        snack = ft.SnackBar(content=ft.Text(msg, color='white'), bgcolor=_C_INK, duration=1800)
        page.overlay.append(snack)
        snack.open = True

    def _persist_todos() -> None:
        _save_today_todos(todo_items)

    def _delete_todo(index: int) -> None:
        if not (0 <= index < len(todo_items)):
            return
        todo_items.pop(index)
        _persist_todos()
        _clear_todo_selection()
        _render_todos()
        page.update()

    def _clear_todo_selection(clear_input: bool = True) -> None:
        selected_todo_index[0] = None
        if clear_input:
            todo_input.value = ''

    def _set_selected_todo(index: int | None) -> None:
        if index is None or not (0 <= index < len(todo_items)):
            _clear_todo_selection()
            return
        selected_todo_index[0] = index
        todo_input.value = todo_items[index].text

    def _cancel_todo_edit() -> None:
        selected_index = selected_todo_index[0]
        if selected_index is None:
            return
        if selected_index < len(todo_items):
            todo_input.value = todo_items[selected_index].text
        _clear_todo_selection()
        _render_todos()
        page.update()

    def start_new_todo() -> None:
        if len(todo_items) >= 10:
            _show_snack('Todo は最大10件までです')
            return
        selected_todo_index[0] = len(todo_items)
        todo_input.value = ''
        _render_todos()
        page.update()

    def _toggle_todo(index: int, value: bool) -> None:
        if index >= len(todo_items):
            return
        todo_items[index].done = value
        _persist_todos()
        _render_todos()
        page.update()

    def _move_todo(index: int, offset: int) -> None:
        target = index + offset
        if not (0 <= index < len(todo_items) and 0 <= target < len(todo_items)):
            return
        item = todo_items.pop(index)
        todo_items.insert(target, item)
        if selected_todo_index[0] == index:
            _set_selected_todo(target)
        elif selected_todo_index[0] == target:
            selected_todo_index[0] = index
        _persist_todos()
        _render_todos()
        page.update()

    def move_todo_up(index: int) -> None:
        _move_todo(index, -1)

    def move_todo_down(index: int) -> None:
        _move_todo(index, 1)

    def select_todo(index: int) -> None:
        _set_selected_todo(index)
        _render_todos()
        page.update()

    def _is_editing_existing(index: int) -> bool:
        return selected_todo_index[0] == index and index < len(todo_items)

    def _is_editing_new() -> bool:
        return selected_todo_index[0] == len(todo_items) and len(todo_items) < 10

    def _render_todos() -> None:
        if not todo_items:
            if _is_editing_new():
                todo_list_column.controls = [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(width=22),
                                todo_input,
                            ],
                            spacing=1,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                        border_radius=8,
                        bgcolor=_C_BG_PANEL,
                    ),
                ]
            else:
                todo_list_column.controls = [
                    ft.Container(
                        content=ft.TextButton(
                            content=ft.Text('＋ 新しいTodo', size=12, color=_C_INK_MUTE, font_family=_MONO),
                            on_click=lambda _e: start_new_todo(),
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=6, vertical=0),
                                alignment=ft.Alignment.CENTER_LEFT,
                            ),
                        ),
                        alignment=ft.Alignment.CENTER_LEFT,
                    ),
                ]
            return

        controls: list[ft.Control] = []
        for index, item in enumerate(todo_items):
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Checkbox(
                                value=item.done,
                                active_color=_C_ACCENT,
                                on_change=lambda e, idx=index: _toggle_todo(idx, bool(e.control.value)),
                                scale=0.68,
                            ),
                            (
                                todo_input
                                if _is_editing_existing(index)
                                else ft.Container(
                                    content=ft.Text(
                                        item.text,
                                        size=12,
                                        color=_C_INK if selected_todo_index[0] == index else _C_INK_SOFT,
                                        font_family=_MONO,
                                        text_align=ft.TextAlign.LEFT,
                                        style=ft.TextStyle(
                                            decoration=ft.TextDecoration.LINE_THROUGH if item.done else ft.TextDecoration.NONE,
                                        ),
                                    ),
                                    on_click=lambda _e, idx=index: select_todo(idx),
                                    expand=True,
                                    alignment=ft.Alignment.CENTER_LEFT,
                                    padding=ft.Padding.symmetric(horizontal=4, vertical=1),
                                    border_radius=6,
                                    bgcolor=_C_BG_PANEL if selected_todo_index[0] == index else _C_BG_WINDOW,
                                )
                            ),
                            ft.IconButton(
                                icon=ft.Icons.KEYBOARD_ARROW_UP,
                                icon_size=10,
                                tooltip='上へ',
                                disabled=index == 0,
                                on_click=lambda _e, idx=index: move_todo_up(idx),
                                width=18,
                                height=18,
                                style=ft.ButtonStyle(padding=0),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.KEYBOARD_ARROW_DOWN,
                                icon_size=10,
                                tooltip='下へ',
                                disabled=index == len(todo_items) - 1,
                                on_click=lambda _e, idx=index: move_todo_down(idx),
                                width=18,
                                height=18,
                                style=ft.ButtonStyle(padding=0),
                            ),
                        ],
                        spacing=1,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.only(left=1, right=12, top=0, bottom=0),
                    border_radius=8,
                    bgcolor=_C_BG_PANEL if _is_editing_existing(index) else None,
                )
            )

        if len(todo_items) < 10:
            controls.append(
                ft.Container(
                    content=(
                        ft.Row(
                            [
                                ft.Container(width=22),
                                todo_input,
                            ],
                            spacing=1,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        )
                        if _is_editing_new()
                        else ft.TextButton(
                            content=ft.Text('＋ 新しいTodo', size=12, color=_C_INK_MUTE, font_family=_MONO),
                            on_click=lambda _e: start_new_todo(),
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                alignment=ft.Alignment.CENTER_LEFT,
                            ),
                        )
                    ),
                    padding=ft.Padding.only(left=1, right=12, top=0, bottom=0),
                    border_radius=8,
                    alignment=ft.Alignment.CENTER_LEFT,
                    bgcolor=_C_BG_PANEL if _is_editing_new() else None,
                )
            )

        todo_list_column.controls = controls

    def commit_todo() -> None:
        text = todo_input.value.strip()
        if not text:
            return
        if selected_todo_index[0] is not None and selected_todo_index[0] < len(todo_items):
            todo_items[selected_todo_index[0]].text = text
        else:
            todo_items.append(_TodoItem(text=text))
        _persist_todos()
        _clear_todo_selection()
        _render_todos()
        page.update()

    def on_page_keyboard_event(event: ft.KeyboardEvent) -> None:
        if selected_todo_index[0] is None:
            return
        if event.key == 'Escape':
            _cancel_todo_edit()
            return
        if event.key == 'Enter':
            commit_todo()
            return
        if todo_input.value.strip():
            return
        if event.key not in {'Backspace', 'Delete'}:
            return
        if selected_todo_index[0] < len(todo_items):
            _delete_todo(selected_todo_index[0])
            return
        _clear_todo_selection()
        _render_todos()
        page.update()

    def _is_pomodoro_active() -> bool:
        return pomodoro_phase[0] in {'focus', 'break'}

    def _is_pomodoro_running() -> bool:
        return _is_pomodoro_active() and not pomodoro_paused[0]

    def _play_pomodoro_voice(name: str) -> None:
        if current_character is None:
            return
        files = _get_pomodoro_files_for_character(current_character, name)
        if files:
            _play_wav(random.choice(files))

    def _refresh_pomodoro_ui() -> None:
        phase = pomodoro_phase[0]
        if phase == 'focus':
            pomodoro_phase_label.value = f'集中 {pomodoro_set[0]} / {pomodoro_config.sets}'
            pomodoro_status_label.value = '一時停止中' if pomodoro_paused[0] else '実行中'
        elif phase == 'break':
            pomodoro_phase_label.value = f'休憩 {pomodoro_set[0]} / {pomodoro_config.sets}'
            pomodoro_status_label.value = '一時停止中' if pomodoro_paused[0] else '実行中'
        elif phase == 'completed':
            pomodoro_phase_label.value = f'完了 {pomodoro_config.sets} / {pomodoro_config.sets}'
            pomodoro_status_label.value = '完了'
        elif phase == 'interrupted':
            pomodoro_phase_label.value = '中止'
            pomodoro_status_label.value = '中止後'
        else:
            pomodoro_phase_label.value = '未開始'
            pomodoro_status_label.value = '開始待ち'

        pomodoro_timer_label.value = _format_mmss(pomodoro_remaining[0])
        _set_button_label(pomodoro_start_button, '中止' if _is_pomodoro_active() else '開始')
        _set_button_label(pomodoro_pause_button, '再開' if _is_pomodoro_active() and pomodoro_paused[0] else '一時停止')
        pomodoro_pause_button.disabled = not _is_pomodoro_active()
        pomodoro_skip_button.disabled = not _is_pomodoro_active()

    def _set_focus_phase(set_number: int, auto_start: bool, play_voice: bool = True) -> None:
        pomodoro_phase[0] = 'focus'
        pomodoro_set[0] = set_number
        pomodoro_remaining[0] = pomodoro_config.focus_seconds
        pomodoro_paused[0] = not auto_start
        if play_voice:
            _play_pomodoro_voice('pomodoro_focus_start')
        _refresh_pomodoro_ui()

    def _set_break_phase(set_number: int, auto_start: bool, play_voice: bool = True) -> None:
        pomodoro_phase[0] = 'break'
        pomodoro_set[0] = set_number
        pomodoro_remaining[0] = pomodoro_config.break_seconds
        pomodoro_paused[0] = not auto_start
        if play_voice:
            _play_pomodoro_voice('pomodoro_break_start')
        _refresh_pomodoro_ui()

    def _finish_pomodoro(interrupted: bool) -> None:
        pomodoro_phase[0] = 'interrupted' if interrupted else 'completed'
        pomodoro_remaining[0] = 0
        pomodoro_paused[0] = False
        _play_pomodoro_voice('pomodoro_interrupt' if interrupted else 'pomodoro_finish')
        _refresh_pomodoro_ui()

    def _advance_pomodoro_phase() -> None:
        if pomodoro_phase[0] == 'focus':
            if pomodoro_set[0] >= pomodoro_config.sets:
                _finish_pomodoro(interrupted=False)
                return
            _set_break_phase(pomodoro_set[0], pomodoro_config.auto_start_break)
            return
        if pomodoro_phase[0] == 'break':
            _set_focus_phase(pomodoro_set[0] + 1, pomodoro_config.auto_start_focus)

    def start_pomodoro() -> None:
        if _is_pomodoro_active():
            _finish_pomodoro(interrupted=True)
            page.update()
            return
        _set_focus_phase(1, True)
        page.update()

    def toggle_pomodoro_pause() -> None:
        if not _is_pomodoro_active():
            return
        pomodoro_paused[0] = not pomodoro_paused[0]
        _refresh_pomodoro_ui()
        page.update()

    def skip_pomodoro() -> None:
        if not _is_pomodoro_active():
            return
        _advance_pomodoro_phase()
        page.update()

    def tick_pomodoro() -> None:
        if not _is_pomodoro_running():
            return
        pomodoro_remaining[0] -= 1
        if pomodoro_remaining[0] <= 0:
            _advance_pomodoro_phase()
            return
        _refresh_pomodoro_ui()

    pomodoro_start_button.on_click = lambda _e: start_pomodoro()
    pomodoro_pause_button.on_click = lambda _e: toggle_pomodoro_pause()
    pomodoro_skip_button.on_click = lambda _e: skip_pomodoro()
    todo_input.on_submit = lambda _e: commit_todo()
    page.on_keyboard_event = on_page_keyboard_event
    _refresh_pomodoro_ui()
    _render_todos()

    def on_character_click(_: ft.TapEvent) -> None:
        if current_character is None:
            return
        if not _clicked_dir_exists(current_character):
            _show_snack(f'「{current_character}」の音声フォルダが見つかりません')
            return
        files = _get_clicked_files_for_character(current_character)
        if files:
            _play_wav(random.choice(files))

    def reload_image() -> None:
        if current_character is None:
            return
        char_image_area.content = _make_char_content(current_character)
        _save_ui_state(current_character, selected_image_name[0])
        msg = '再読み込みしました' if image_found[0] else '再読み込みしました — 画像は見つかりませんでした'
        _show_snack(msg)
        page.update()

    def on_middle_click(_: ft.TapEvent) -> None:
        reload_image()

    def cycle_image() -> None:
        if current_character is None or not image_found[0] or current_image_path[0] is None:
            return
        images = _list_character_images(current_character)
        if len(images) <= 1:
            return
        try:
            idx = images.index(current_image_path[0])
        except ValueError:
            idx = 0
        next_img = images[(idx + 1) % len(images)]
        current_image_path[0] = next_img
        selected_image_name[0] = next_img.name
        _save_ui_state(current_character, selected_image_name[0])
        char_image_area.content = ft.Image(src=str(next_img), fit=ft.BoxFit.COVER)
        page.update()

    def on_right_click(_: ft.Event[ft.GestureDetector]) -> None:
        cycle_image()

    char_container = ft.GestureDetector(
        content=ft.Container(
            content=ft.Stack(
                [
                    char_image_area,
                ],
                expand=True,
            ),
            width=_CHAR_W,
            height=_BODY_H,
            bgcolor=_C_BG_IMAGE,
            border_radius=10,
            border=ft.Border.all(1, _C_LINE),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ),
        on_tap=on_character_click,
        on_secondary_tap=on_right_click,
        on_tertiary_tap_down=on_middle_click,
    )

    clock_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        _make_panel_badge('Asia / Tokyo'),
                        ft.Text('24-hour', size=10, color=_C_INK_MUTE, font_family=_MONO),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [hhmm_text, ss_text],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                date_text,
            ],
            spacing=6,
        ),
        padding=ft.Padding.only(left=20, right=20, top=18, bottom=20),
        bgcolor=_C_BG_PANEL,
        border_radius=10,
        border=ft.Border.all(1, _C_LINE),
        expand=True,
    )

    pomodoro_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        _make_panel_badge('pomodoro'),
                        ft.Text(
                            f'{pomodoro_config.focus_seconds // 60:02d}/{pomodoro_config.break_seconds // 60:02d} min · {pomodoro_config.sets} sets',
                            size=10,
                            color=_C_INK_MUTE,
                            font_family=_MONO,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=pomodoro_status_label,
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(
                                content=pomodoro_timer_label,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Container(
                                content=pomodoro_phase_label,
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Row(
                    [pomodoro_start_button, pomodoro_pause_button, pomodoro_skip_button],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            expand=True,
        ),
        bgcolor=_C_BG_PANEL,
        border_radius=10,
        border=ft.Border.all(1, _C_LINE_STRONG),
        expand=True,
        padding=ft.Padding.only(left=20, right=20, top=18, bottom=26),
    )

    todo_card = ft.Container(
        content=ft.Column(
            [
                _make_panel_badge('Todo'),
                ft.Container(
                    content=todo_list_column,
                    height=120,
                    padding=ft.Padding.only(left=3, right=14, top=2, bottom=2),
                    bgcolor=_C_BG_WINDOW,
                    border_radius=8,
                    border=ft.Border.all(1, _C_LINE),
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=8,
        ),
        bgcolor=_C_BG_PANEL,
        border_radius=10,
        border=ft.Border.all(1, _C_LINE),
        expand=True,
        padding=ft.Padding.only(left=12, right=12, top=12, bottom=12),
    )

    right_col = ft.Container(
        content=ft.Column(
            [clock_card, pomodoro_card, todo_card],
            spacing=_GAP,
            expand=True,
        ),
        height=_BODY_H,
        expand=True,
    )

    selected_char_label = ft.Text(
        current_character if current_character else 'キャラクター',
        size=11,
        color=_C_INK_SOFT,
        font_family=_MONO,
    )

    def on_char_select(name: str) -> None:
        nonlocal current_character
        current_character = name
        selected_char_label.value = name
        char_image_area.content = _make_char_content(name)
        _save_ui_state(current_character, selected_image_name[0])
        page.update()

    if characters:
        menu_items: list[ft.PopupMenuItem] = [ft.PopupMenuItem(content=name, on_click=lambda e, n=name: on_char_select(n)) for name in characters]
    else:
        menu_items = [ft.PopupMenuItem(content='(キャラクターなし)', disabled=True)]

    char_menu = ft.PopupMenuButton(
        content=ft.Row(
            [
                selected_char_label,
                ft.Text(' ▾', size=11, color=_C_INK_MUTE),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        items=menu_items,
    )

    titlebar = ft.Container(
        content=ft.Row(
            [
                ft.Container(content=char_menu, padding=ft.Padding.only(left=4)),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=_TITLEBAR_H,
        padding=ft.Padding.symmetric(horizontal=12),
        bgcolor=_C_BG_WINDOW,
        border=ft.Border.only(bottom=ft.BorderSide(1, _C_LINE)),
    )

    root = ft.Column(
        [
            titlebar,
            ft.Container(
                content=ft.Row(
                    [
                        char_container,
                        ft.Container(width=_GAP),
                        right_col,
                    ],
                    spacing=0,
                ),
                padding=ft.Padding.only(left=_PADDING, right=_PADDING, top=_PADDING, bottom=_PADDING),
                expand=True,
            ),
        ],
        spacing=0,
        expand=True,
    )

    async def clock_loop() -> None:
        while True:
            now = datetime.now(_TZ_TOKYO)
            hhmm_str = now.strftime('%H%M')
            hhmm_text.value = now.strftime('%H:%M')
            ss_text.value = f':{now.strftime("%S")}'
            date_text.value = f'{now.strftime("%Y.%m.%d")} ({_WEEKDAY_JA[now.weekday()]})'
            tick_pomodoro()
            page.update()
            if hhmm_str not in played_hhmm and not _is_pomodoro_running():
                files = _get_time_signal_files(hhmm_str)
                if files:
                    played_hhmm.add(hhmm_str)
                    chosen = random.choice(files)
                    _play_wav(chosen)
            await asyncio.sleep(1)

    return _GuiView(
        root=root,
        startup_message=startup_message,
        clock_loop=clock_loop,
        char_container=char_container,
        char_menu=char_menu,
        char_image_area=char_image_area,
        selected_char_label=selected_char_label,
        select_character=on_char_select,
        reload_image=reload_image,
        cycle_image=cycle_image,
        pomodoro_phase_label=pomodoro_phase_label,
        pomodoro_timer_label=pomodoro_timer_label,
        pomodoro_status_label=pomodoro_status_label,
        pomodoro_start_button=pomodoro_start_button,
        pomodoro_pause_button=pomodoro_pause_button,
        pomodoro_skip_button=pomodoro_skip_button,
        todo_input=todo_input,
        todo_list_column=todo_list_column,
        select_todo=select_todo,
        start_new_todo=start_new_todo,
        commit_todo=commit_todo,
        move_todo_up=move_todo_up,
        move_todo_down=move_todo_down,
        start_pomodoro=start_pomodoro,
        toggle_pomodoro_pause=toggle_pomodoro_pause,
        skip_pomodoro=skip_pomodoro,
        tick_pomodoro=tick_pomodoro,
    )


def main(page: ft.Page) -> None:
    """Fletアプリのエントリポイント。"""
    _configure_page(page)
    gui_view = _build_gui(page)
    page.add(gui_view.root)

    if gui_view.startup_message is not None:
        snack = ft.SnackBar(content=ft.Text(gui_view.startup_message, color='white'), bgcolor=_C_INK, duration=1800)
        page.overlay.append(snack)
        snack.open = True

    page.run_task(gui_view.clock_loop)
