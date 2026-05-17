"""音声生成スクリプト。

VOICEPEAKを呼び出して音声ファイルを生成し、voice_manifest.jsonに記録する。
"""

import argparse
import contextlib
import json
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'check_sound_duplicate'))
import check_duplicate as dup_checker

_ROOT = Path(__file__).parent.parent.parent
_RESOURCE_VOICE_DIR = _ROOT / 'resource' / 'voice'
_TIME_SIGNAL_DIR = _RESOURCE_VOICE_DIR / 'time_signal'
_CLICKED_DIR = _RESOURCE_VOICE_DIR / 'clicked'
_MANIFEST_PATH = _RESOURCE_VOICE_DIR / 'voice_manifest.json'
_INPUT_JSON_PATH = Path(__file__).parent / 'input_voices.json'
_CONFIG_PATH = _ROOT / 'config.toml'


def _load_config(voicepeak_path_arg: str | None) -> tuple[str, str]:
    with open(_CONFIG_PATH, 'rb') as f:
        config = tomllib.load(f)
    section = config['generate_voice']
    voicepeak_path: str = voicepeak_path_arg or section['voicepeak_path']
    narrator: str = section['narrator']
    return voicepeak_path, narrator


def _load_manifest() -> list[dict[str, object]]:
    if not _MANIFEST_PATH.exists():
        return []
    with open(_MANIFEST_PATH, encoding='utf-8') as f:
        return json.load(f)  # type: ignore[no-any-return]


def _save_manifest(manifest: list[dict[str, object]]) -> None:
    with open(_MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)


def _get_next_number(folder: Path, prefix: str) -> int:
    existing = list(folder.glob(f'{prefix}_*.wav'))
    if not existing:
        return 1
    numbers = []
    for wav in existing:
        with contextlib.suppress(ValueError):
            numbers.append(int(wav.stem.split('_')[-1]))
    return max(numbers, default=0) + 1


def _generate_voice(voicepeak: str, narrator: str, text: str, output: Path) -> bool:
    cmd = [voicepeak, '--say', text, '--out', str(output), '--narrator', narrator]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'  エラー: {e.stderr.strip()}')
        return False
    except FileNotFoundError:
        print(f'  エラー: VOICEPEAKが見つかりません: {voicepeak}')
        return False


def _record_to_manifest(
    manifest: list[dict[str, object]],
    filename: str,
    entry_type: str,
    type_specific: dict[str, object],
    text: str,
    output_path: Path,
    dup_folder: Path,
) -> None:
    dup_of = dup_checker.check_file_duplicate(output_path, dup_folder)
    if dup_of:
        print(f'  重複検出: {filename} は {dup_of} と同一')
    record: dict[str, object] = {
        'filename': filename,
        'type': entry_type,
        **type_specific,
        'text': text,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'pcm_sha256': dup_checker.compute_pcm_sha256(output_path),
        'duplicate_of': dup_of,
    }
    manifest.append(record)


def _validate_input(input_data: dict[str, object]) -> bool:
    for entry in input_data.get('clicked', []):  # type: ignore[union-attr]
        if 'name' not in entry:  # type: ignore[operator]
            print(f'エラー: clickedエントリに "name" キーがありません: {entry}')
            return False
    return True


def main() -> None:
    """コマンドライン実行のエントリポイント。"""
    parser = argparse.ArgumentParser(description='VOICEPEAKで音声ファイルを生成する')
    parser.add_argument('--voicepeak-path', help='VOICEPEAKの実行ファイルパス（config.tomlより優先）')
    args = parser.parse_args()

    voicepeak, narrator = _load_config(args.voicepeak_path)

    with open(_INPUT_JSON_PATH, encoding='utf-8') as f:
        input_data: dict[str, object] = json.load(f)

    if not _validate_input(input_data):
        sys.exit(1)

    _TIME_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    _CLICKED_DIR.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    total_success = 0
    total_failure = 0

    for entry in input_data.get('time_signal', []):  # type: ignore[union-attr]
        hhmm: str = entry['hhmm']  # type: ignore[index]
        for text in entry['texts']:  # type: ignore[index]
            num = _get_next_number(_TIME_SIGNAL_DIR, hhmm)
            filename = f'{hhmm}_{num:03d}.wav'
            output_path = _TIME_SIGNAL_DIR / filename
            print(f'生成中: {filename}')
            if _generate_voice(voicepeak, narrator, text, output_path):
                _record_to_manifest(manifest, filename, 'time_signal', {'hhmm': hhmm}, text, output_path, _TIME_SIGNAL_DIR)
                total_success += 1
            else:
                total_failure += 1

    for entry in input_data.get('clicked', []):  # type: ignore[union-attr]
        name: str = entry['name']  # type: ignore[index]
        text = entry['text']  # type: ignore[index]
        num = _get_next_number(_CLICKED_DIR, name)
        filename = f'{name}_{num:03d}.wav'
        output_path = _CLICKED_DIR / filename
        print(f'生成中: {filename}')
        if _generate_voice(voicepeak, narrator, text, output_path):
            _record_to_manifest(manifest, filename, 'clicked', {'name': name}, text, output_path, _CLICKED_DIR)
            total_success += 1
        else:
            total_failure += 1

    _save_manifest(manifest)
    print(f'\n完了: {total_success} 件成功 / {total_failure} 件失敗')


if __name__ == '__main__':
    main()
