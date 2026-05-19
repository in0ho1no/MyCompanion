"""Flet GUI の構築とイベント処理。"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

import flet as ft

from media import (
    _character_dir_exists,
    _find_character_image_by_name,
    _get_clicked_files,
    _get_time_signal_files,
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

    def _make_char_content(character: str | None) -> ft.Control:
        if character is None:
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
            return ft.Image(src=str(img), fit=ft.BoxFit.COVER, expand=True)

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

    def on_character_click(_: ft.TapEvent) -> None:
        files = _get_clicked_files()
        if not files:
            return
        chosen = random.choice(files)
        _play_wav(chosen)

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
