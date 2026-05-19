"""Flet GUI の構築とイベント処理。"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import flet as ft

from media import (
    _character_dir_exists,
    _clicked_dir_exists,
    _find_character_image_by_name,
    _get_clicked_files_for_character,
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


def main(page: ft.Page) -> None:
    """Fletアプリのエントリポイント。"""
    page.title = 'MyCompanion'
    page.window.always_on_top = True
    page.window.width = _WIN_W
    page.window.height = _WIN_H
    page.window.maximizable = False
    page.window.resizable = False
    page.bgcolor = _C_BG_WINDOW
    page.padding = 0

    hhmm_text = ft.Text('00:00', size=56, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO)
    ss_text = ft.Text(':00', size=28, color=_C_INK_MUTE, font_family=_MONO)
    date_text = ft.Text('---- -- -- (--)', size=12, weight=ft.FontWeight.W_500, color=_C_INK_SOFT)

    characters = _list_characters()
    current_character: str | None = characters[0] if characters else None
    image_found: list[bool] = [False]
    current_image_path: list[Path | None] = [None]

    def _reload_hint() -> ft.Text:
        return ft.Text('wheel click · 再読み込み', size=10, color=_C_INK_MUTE, font_family=_MONO, opacity=0.5)

    def _make_char_content(character: str | None) -> ft.Control:
        if character is None:
            image_found[0] = False
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

        img = _find_character_image_by_name(character)
        if img:
            image_found[0] = True
            current_image_path[0] = img
            return ft.Image(src=str(img), fit=ft.BoxFit.COVER, expand=True)

        image_found[0] = False
        current_image_path[0] = None
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

    char_image_area = ft.Container(content=_make_char_content(current_character), expand=True)

    played_hhmm: set[str] = set()

    def _show_snack(msg: str) -> None:
        snack = ft.SnackBar(content=ft.Text(msg, color='white'), bgcolor=_C_INK, duration=1800)
        page.overlay.append(snack)
        snack.open = True

    def on_character_click(_: ft.TapEvent) -> None:
        if current_character is None:
            return
        if not _clicked_dir_exists(current_character):
            _show_snack(f'「{current_character}」の音声フォルダが見つかりません')
            return
        files = _get_clicked_files_for_character(current_character)
        if files:
            _play_wav(random.choice(files))

    def on_middle_click(_: ft.TapEvent) -> None:
        if current_character is None:
            return
        char_image_area.content = _make_char_content(current_character)
        msg = '再読み込みしました' if image_found[0] else '再読み込みしました — 画像は見つかりませんでした'
        _show_snack(msg)
        page.update()

    def on_right_click(_: ft.Event[ft.GestureDetector]) -> None:
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
        char_image_area.content = ft.Image(src=str(next_img), fit=ft.BoxFit.COVER, expand=True)
        page.update()

    char_container = ft.GestureDetector(
        content=ft.Container(
            content=ft.Stack(
                [
                    char_image_area,
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text('character', size=11, color=_C_INK_MUTE, font_family=_MONO),
                                ft.Container(width=6, height=6, bgcolor=_C_ACCENT, border_radius=3),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.Padding.all(12),
                        top=0,
                        left=0,
                        right=0,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text('idle', size=11, color=_C_INK_MUTE, font_family=_MONO),
                                ft.Text('v1', size=11, color=_C_INK_MUTE, font_family=_MONO),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.Padding.all(12),
                        bottom=0,
                        left=0,
                        right=0,
                    ),
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
                        ft.Row(
                            [
                                ft.Container(width=6, height=6, bgcolor=_C_ACCENT, border_radius=3),
                                ft.Text('Asia / Tokyo', size=10, color=_C_INK_MUTE, font_family=_MONO),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
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
    )

    future_area = ft.Container(
        content=ft.Column(
            [
                ft.Text('reserved · 拡張領域', size=10, color=_C_INK_MUTE, font_family=_MONO),
                ft.Text('ここに今後追加', size=13, weight=ft.FontWeight.W_500, color=_C_INK_SOFT),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(label, size=10, color=_C_INK_SOFT, font_family=_MONO),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border=ft.Border.all(1, _C_LINE),
                            border_radius=999,
                            bgcolor=_C_BG_WINDOW,
                        )
                        for label in ['ToDo', 'Timer', '...']
                    ],
                    spacing=6,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        bgcolor=_C_BG_PANEL,
        border_radius=10,
        border=ft.Border.all(1, _C_LINE_STRONG),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )

    right_col = ft.Container(
        content=ft.Column(
            [clock_card, future_area],
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

    def on_char_select(e: ft.ControlEvent, name: str) -> None:
        nonlocal current_character
        current_character = name
        selected_char_label.value = name
        char_image_area.content = _make_char_content(name)
        page.update()

    if characters:
        menu_items: list[ft.PopupMenuItem] = [
            ft.PopupMenuItem(content=name, on_click=lambda e, n=name: on_char_select(e, n))
            for name in characters
        ]
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
                ft.Container(
                    content=ft.Text(
                        'MyCompanion  ·  minimal v1',
                        size=12,
                        color=_C_INK_SOFT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(width=80),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=_TITLEBAR_H,
        padding=ft.Padding.symmetric(horizontal=12),
        bgcolor=_C_BG_WINDOW,
        border=ft.Border.only(bottom=ft.BorderSide(1, _C_LINE)),
    )

    page.add(
        ft.Column(
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
    )

    async def clock_loop() -> None:
        while True:
            now = datetime.now(_TZ_TOKYO)
            hhmm_str = now.strftime('%H%M')
            hhmm_text.value = now.strftime('%H:%M')
            ss_text.value = f':{now.strftime("%S")}'
            date_text.value = f'{now.strftime("%Y.%m.%d")} ({_WEEKDAY_JA[now.weekday()]})'
            page.update()
            if hhmm_str not in played_hhmm:
                files = _get_time_signal_files(hhmm_str)
                if files:
                    played_hhmm.add(hhmm_str)
                    chosen = random.choice(files)
                    _play_wav(chosen)
            await asyncio.sleep(1)

    page.run_task(clock_loop)
