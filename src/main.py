"""Companion デスクトップアプリ。

毎時話しかけてくれるデスクトップ常駐キャラクターアプリ。
"""

import asyncio
import random
import winsound
from datetime import datetime, timedelta, timezone
from pathlib import Path

import flet as ft

_ROOT = Path(__file__).parent
_TZ_TOKYO = timezone(timedelta(hours=9))
_TIME_SIGNAL_DIR = _ROOT / 'resource' / 'voice' / 'time_signal'
_CLICKED_DIR = _ROOT / 'resource' / 'voice' / 'clicked'
_IMAGE_DIR = _ROOT / 'resource' / 'image' / 'character'

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


def _find_character_image() -> Path | None:
    """キャラクター画像ファイルを探す。"""
    if not _IMAGE_DIR.exists():
        return None
    for ext in ('.gif', '.png', '.jpg', '.jpeg'):
        files = list(_IMAGE_DIR.glob(f'*{ext}'))
        if files:
            return files[0]
    return None


def _play_wav(path: Path) -> None:
    """WAVファイルを非同期再生する。"""
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def _get_time_signal_files(hhmm: str) -> list[Path]:
    """指定時刻の時報WAVファイル一覧を返す。"""
    if not _TIME_SIGNAL_DIR.exists():
        return []
    return sorted(_TIME_SIGNAL_DIR.rglob(f'{hhmm}_*.wav'))


def _get_clicked_files() -> list[Path]:
    """クリック時WAVファイル一覧を返す。"""
    if not _CLICKED_DIR.exists():
        return []
    return sorted(_CLICKED_DIR.rglob('*.wav'))


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

    # 時計ウィジェット
    hhmm_text = ft.Text('00:00', size=56, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO)
    ss_text = ft.Text(':00', size=28, color=_C_INK_MUTE, font_family=_MONO)
    date_text = ft.Text('---- -- -- (--)', size=12, weight=ft.FontWeight.W_500, color=_C_INK_SOFT)

    # キャラクター画像
    image_path = _find_character_image()
    if image_path:
        char_main: ft.Control = ft.Image(src=str(image_path), fit=ft.BoxFit.COVER, expand=True)
    else:
        char_main = ft.Container(
            content=ft.Column(
                [
                    ft.Text('9 : 16', size=13, weight=ft.FontWeight.W_500, color=_C_INK, font_family=_MONO),
                    ft.Text('drop character image here', size=12, color=_C_INK_MUTE, font_family=_MONO),
                    ft.Text('resource/image/character/', size=11, color=_C_INK_MUTE, font_family=_MONO, opacity=0.7),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )

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
                    char_main,
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

    # 時計カード
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

    # 拡張領域（将来のToDo/タイマー用）
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

    # 右カラム
    right_col = ft.Container(
        content=ft.Column(
            [clock_card, future_area],
            spacing=_GAP,
            expand=True,
        ),
        height=_BODY_H,
        expand=True,
    )

    # タイトルバー
    titlebar = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(width=12, height=12, bgcolor='#e36b5a', border_radius=6),
                        ft.Container(width=12, height=12, bgcolor='#e3b85a', border_radius=6),
                        ft.Container(width=12, height=12, bgcolor='#6ab47b', border_radius=6),
                    ],
                    spacing=7,
                ),
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


if __name__ == '__main__':
    ft.run(main)
