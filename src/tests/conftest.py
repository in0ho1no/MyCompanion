"""pytest の共通設定。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / 'src'
TOOL_ROOT = SRC_ROOT / 'tools'


def _prepend_once(path: Path) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_prepend_once(SRC_ROOT)
_prepend_once(TOOL_ROOT / 'check_sound_duplicate')
_prepend_once(TOOL_ROOT / 'generate_voice')
_prepend_once(TOOL_ROOT / 'list_voices')
