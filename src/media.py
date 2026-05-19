"""画像・音声リソースを扱う補助処理。"""

import winsound
from pathlib import Path

_ROOT = Path(__file__).parent
_TIME_SIGNAL_DIR = _ROOT / 'resource' / 'voice' / 'time_signal'
_CLICKED_DIR = _ROOT / 'resource' / 'voice' / 'clicked'
_IMAGE_DIR = _ROOT / 'resource' / 'image' / 'character'

_IMAGE_EXTS: tuple[str, ...] = ('.gif', '.png', '.jpg', '.jpeg', '.webp')


def _find_character_image() -> Path | None:
    """キャラクター画像ファイルを探す。"""
    if not _IMAGE_DIR.exists():
        return None
    for ext in _IMAGE_EXTS:
        files = sorted(_IMAGE_DIR.rglob(f'*{ext}'))
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


def _clicked_dir_exists(character: str) -> bool:
    """指定キャラクターのクリック音声フォルダが存在するかを確認する。"""
    return (_CLICKED_DIR / character).is_dir()


def _get_clicked_files_for_character(character: str) -> list[Path]:
    """指定キャラクターのクリック時WAVファイル一覧を返す。"""
    char_dir = _CLICKED_DIR / character
    if not char_dir.exists():
        return []
    return sorted(char_dir.rglob('*.wav'))


def _list_characters() -> list[str]:
    """利用可能なキャラクター名一覧を返す。"""
    if not _IMAGE_DIR.exists():
        return []
    return sorted(d.name for d in _IMAGE_DIR.iterdir() if d.is_dir())


def _character_dir_exists(character: str) -> bool:
    """指定キャラクターのフォルダが存在するかを確認する。"""
    return (_IMAGE_DIR / character).is_dir()


def _find_character_image_by_name(character: str) -> Path | None:
    """指定キャラクターの画像ファイルを探す。"""
    char_dir = _IMAGE_DIR / character
    if not char_dir.exists():
        return None
    for ext in _IMAGE_EXTS:
        files = sorted(char_dir.glob(f'*{ext}'))
        if files:
            return files[0]
    return None


def _list_character_images(character: str) -> list[Path]:
    """指定キャラクターの画像ファイルをファイル名昇順で返す。"""
    char_dir = _IMAGE_DIR / character
    if not char_dir.exists():
        return []
    images: list[Path] = []
    for ext in _IMAGE_EXTS:
        images.extend(char_dir.glob(f'*{ext}'))
    return sorted(images, key=lambda p: p.name)
