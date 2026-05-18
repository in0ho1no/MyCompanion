"""Companion デスクトップアプリ。

毎時話しかけてくれるデスクトップ常駐キャラクターアプリ。
"""

import asyncio
import random
import winsound
from datetime import datetime
from pathlib import Path

import flet as ft

_ROOT = Path(__file__).parent
_TIME_SIGNAL_DIR = _ROOT / 'resource' / 'voice' / 'time_signal'
_CLICKED_DIR = _ROOT / 'resource' / 'voice' / 'clicked'
_IMAGE_DIR = _ROOT / 'resource' / 'image' / 'character'


def _find_character_image() -> Path | None:
    if not _IMAGE_DIR.exists():
        return None
    for ext in ('.gif', '.png', '.jpg', '.jpeg'):
        files = list(_IMAGE_DIR.glob(f'*{ext}'))
        if files:
            return files[0]
    return None


def _play_wav(path: Path) -> None:
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def _get_time_signal_files(hhmm: str) -> list[Path]:
    if not _TIME_SIGNAL_DIR.exists():
        return []
    return sorted(_TIME_SIGNAL_DIR.rglob(f'{hhmm}_*.wav'))


def _get_clicked_files() -> list[Path]:
    if not _CLICKED_DIR.exists():
        return []
    return sorted(_CLICKED_DIR.rglob('*.wav'))


def main(page: ft.Page) -> None:
    """Fletアプリのエントリポイント。"""
    page.title = 'Companion'
    page.window.always_on_top = True
    page.window.width = 320
    page.window.height = 420
    page.window.resizable = False

    clock_text = ft.Text(datetime.now().strftime('%H:%M'), size=36, weight=ft.FontWeight.BOLD)
    subtitle_text = ft.Text('', size=11, color=ft.Colors.GREY_500)

    image_path = _find_character_image()
    if image_path:
        char_control: ft.Control = ft.Image(
            src=str(image_path),
            width=220,
            height=220,
            fit=ft.BoxFit.CONTAIN,
        )
    else:
        char_control = ft.Text('（キャラクター画像なし）', size=14)

    played_hhmm: set[str] = set()

    def on_character_click(_: ft.TapEvent) -> None:
        files = _get_clicked_files()
        if not files:
            return
        chosen = random.choice(files)
        subtitle_text.value = chosen.name
        page.update()
        _play_wav(chosen)

    char_gesture = ft.GestureDetector(
        content=char_control,
        on_tap=on_character_click,
    )

    page.add(
        ft.Column(
            [
                clock_text,
                char_gesture,
                subtitle_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )
    )

    async def clock_loop() -> None:
        while True:
            now = datetime.now()
            hhmm = now.strftime('%H%M')
            clock_text.value = now.strftime('%H:%M')
            page.update()
            if hhmm not in played_hhmm:
                files = _get_time_signal_files(hhmm)
                if files:
                    played_hhmm.add(hhmm)
                    chosen = random.choice(files)
                    subtitle_text.value = chosen.name
                    page.update()
                    _play_wav(chosen)
            await asyncio.sleep(1)

    page.run_task(clock_loop)


if __name__ == '__main__':
    ft.run(main)
