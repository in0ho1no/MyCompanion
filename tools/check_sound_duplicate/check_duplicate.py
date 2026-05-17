"""WAVファイルの重複チェックスクリプト。

gen_voice.py からのモジュール呼び出し、または単独スクリプトとして使用できる。
"""

import hashlib
import sys
import tomllib
import wave
from pathlib import Path


def compute_pcm_sha256(wav_path: Path) -> str:
    """WAVファイルのPCMデータ部分のSHA-256ハッシュを計算する。

    WAVヘッダ（日時・ソフトウェア名など）を除外し、PCMデータのみを比較対象とする。

    Args:
        wav_path: チェック対象のWAVファイルパス。

    Returns:
        PCMデータのSHA-256ハッシュ文字列。
    """
    with wave.open(str(wav_path), 'rb') as w:
        pcm_data = w.readframes(w.getnframes())
    return hashlib.sha256(pcm_data).hexdigest()


def check_file_duplicate(new_file: Path, folder: Path) -> str | None:
    """新しいファイルがフォルダ内の既存ファイルと重複するか確認する。

    Args:
        new_file: チェック対象のWAVファイルパス。
        folder: 比較対象のフォルダ。

    Returns:
        重複元のファイル名。重複なしの場合は None。
    """
    if not new_file.exists():
        return None
    new_hash = compute_pcm_sha256(new_file)
    for existing in sorted(folder.glob('*.wav')):
        if existing.resolve() == new_file.resolve():
            continue
        if compute_pcm_sha256(existing) == new_hash:
            return existing.name
    return None


def check_all_duplicates(folder: Path) -> list[tuple[str, str]]:
    """フォルダ内の全WAVファイルの重複ペアを検出する。

    Args:
        folder: チェック対象フォルダ。

    Returns:
        重複ペアのリスト。各要素は (元ファイル名, 重複ファイル名) のタプル。
    """
    wav_files = sorted(folder.glob('*.wav'))
    hashes: dict[str, str] = {}
    duplicates: list[tuple[str, str]] = []
    for wav_file in wav_files:
        h = compute_pcm_sha256(wav_file)
        if h in hashes:
            duplicates.append((hashes[h], wav_file.name))
        else:
            hashes[h] = wav_file.name
    return duplicates


def main() -> None:
    """コマンドライン実行のエントリポイント。"""
    config_path = Path(__file__).parent.parent.parent.parent / 'config.toml'
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)

    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(config['check_sound_duplicate']['target_folder'])

    if not folder.exists():
        print(f'フォルダが見つかりません: {folder}')
        return

    duplicates = check_all_duplicates(folder)
    if duplicates:
        print('重複ペアが見つかりました:')
        for a, b in duplicates:
            print(f'  {a} ↔ {b}')
    else:
        print('重複なし')


if __name__ == '__main__':
    main()
