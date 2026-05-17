"""VoicePeak のナレーター・感情一覧を取得して JSON に出力するスクリプト。

Usage:
    python list_voices.py
    python list_voices.py --voicepeak-path "C:/Program Files/VOICEPEAK/voicepeak.exe"
    python list_voices.py --output available_voices.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / 'config.toml'
DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'available_voices.json'


def load_voicepeak_path() -> str | None:
    """config.toml から voicepeak_path を読み込む。

    Returns:
        設定値が存在すれば文字列、なければ None。
    """
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH, 'rb') as f:
        config = tomllib.load(f)
    return config.get('generate_voice', {}).get('voicepeak_path')


def run_voicepeak(exe: str, args: list[str]) -> str:
    """VoicePeak CLI を実行して stdout を返す。

    Args:
        exe: voicepeak.exe のパス。
        args: 追加の CLI 引数。

    Returns:
        標準出力の文字列。

    Raises:
        RuntimeError: プロセスが非ゼロで終了した場合。
    """
    cmd = [exe, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f'voicepeak exited with code {result.returncode}: {result.stderr.strip()}')
    return result.stdout.strip()


def get_narrators(exe: str) -> list[str]:
    """利用可能なナレーター一覧を取得する。

    Args:
        exe: voicepeak.exe のパス。

    Returns:
        ナレーター名のリスト。
    """
    output = run_voicepeak(exe, ['--list-narrator'])
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_emotions(exe: str, narrator: str) -> list[str]:
    """指定ナレーターの感情一覧を取得する。

    Args:
        exe: voicepeak.exe のパス。
        narrator: ナレーター名。

    Returns:
        感情名のリスト。
    """
    output = run_voicepeak(exe, ['--list-emotion', narrator])
    return [line.strip() for line in output.splitlines() if line.strip()]


def build_voices_data(exe: str) -> dict:
    """全ナレーターと感情情報を収集して辞書にまとめる。

    Args:
        exe: voicepeak.exe のパス。

    Returns:
        ナレーター・感情一覧を含む辞書。
    """
    narrators = get_narrators(exe)
    print(f'ナレーター {len(narrators)} 件を検出')

    voices: list[dict[str, str | list[str]]] = []
    for narrator in narrators:
        print(f'  {narrator} の感情を取得中...')
        try:
            emotions = get_emotions(exe, narrator)
        except RuntimeError as e:
            print(f'    [WARN] 感情取得に失敗: {e}')
            emotions = []
        voices.append(
            {
                'narrator': narrator,
                'emotions': emotions,
            }
        )

    return {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'voicepeak_path': exe,
        'narrators_count': len(voices),
        'voices': voices,
    }


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする。

    Returns:
        パース結果の Namespace。
    """
    parser = argparse.ArgumentParser(description='VoicePeak ナレーター・感情一覧を JSON に出力')
    parser.add_argument('--voicepeak-path', type=str, default=None, help='voicepeak.exe のパス（省略時は config.toml から読み込み）')
    parser.add_argument('--output', '-o', type=Path, default=DEFAULT_OUTPUT, help=f'出力先 JSON ファイル（デフォルト: {DEFAULT_OUTPUT}）')
    return parser.parse_args()


def main() -> None:
    """エントリーポイント。"""
    args = parse_args()

    # VoicePeak パスの解決: CLI引数 > config.toml
    exe = args.voicepeak_path or load_voicepeak_path()
    if not exe:
        print('[ERROR] voicepeak_path が指定されていません。--voicepeak-path 引数または config.toml で設定してください。', file=sys.stderr)
        sys.exit(1)

    print(f'VoicePeak: {exe}')
    print()

    try:
        data = build_voices_data(exe)
    except RuntimeError as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        sys.exit(1)

    # JSON 出力
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print(f'完了: {output_path} に出力しました')
    print(f'  ナレーター数: {data["narrators_count"]}')
    for voice in data['voices']:
        print(f'  - {voice["narrator"]}: {", ".join(voice["emotions"]) or "(感情なし)"}')


if __name__ == '__main__':
    main()
