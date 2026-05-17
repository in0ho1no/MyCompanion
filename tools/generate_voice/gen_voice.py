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

_SRC_ROOT = Path(__file__).parent.parent.parent
_PROJECT_ROOT = _SRC_ROOT.parent
_RESOURCE_VOICE_DIR = _SRC_ROOT / 'resource' / 'voice'
_MANIFEST_PATH = _RESOURCE_VOICE_DIR / 'voice_manifest.json'
_INPUT_JSON_PATH = Path(__file__).parent / 'input_voices.json'
_CONFIG_PATH = _PROJECT_ROOT / 'config.toml'


def _load_config(voicepeak_path_arg: str | None, narrator_arg: str | None) -> tuple[str, str]:
    with open(_CONFIG_PATH, 'rb') as f:
        config = tomllib.load(f)
    section = config['generate_voice']
    voicepeak_path: str = voicepeak_path_arg or section['voicepeak_path']
    narrator: str = narrator_arg or section.get('narrator', '')
    if not narrator:
        print('エラー: narrator が指定されていません。--narrator オプションか config.toml の narrator を設定してください。')
        sys.exit(1)
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


def _generate_voice(voicepeak: str, narrator: str, text: str, output: Path, emotions: str | None = None) -> bool:
    cmd = [voicepeak, '--say', text, '--out', str(output), '--narrator', narrator]
    if emotions:
        cmd += ['--emotion', emotions]
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
    narrator: str,
    emotions: str | None,
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
        'narrator': narrator,
        'emotions': emotions,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'pcm_sha256': dup_checker.compute_pcm_sha256(output_path),
        'duplicate_of': dup_of,
    }
    manifest.append(record)


def _validate_input(input_data: dict[str, object]) -> bool:
    for entry in input_data.get('clicked', []):  # type: ignore[attr-defined]
        if 'name' not in entry:  # type: ignore[operator]
            print(f'エラー: clickedエントリに "name" キーがありません: {entry}')
            return False
    return True


def main() -> None:
    """コマンドライン実行のエントリポイント。"""
    parser = argparse.ArgumentParser(description='VOICEPEAKで音声ファイルを生成する')
    parser.add_argument('--voicepeak-path', help='VOICEPEAKの実行ファイルパス（config.tomlより優先）')
    parser.add_argument('--narrator', help='ナレーター名（config.tomlより優先）')
    parser.add_argument('--emotions', help='感情パラメータ（例: happy=50,angry=20）')
    args = parser.parse_args()

    voicepeak, narrator = _load_config(args.voicepeak_path, args.narrator)
    emotions: str | None = args.emotions or None

    with open(_INPUT_JSON_PATH, encoding='utf-8') as f:
        input_data: dict[str, object] = json.load(f)

    if not _validate_input(input_data):
        sys.exit(1)

    time_signal_dir = _RESOURCE_VOICE_DIR / 'time_signal' / narrator
    clicked_dir = _RESOURCE_VOICE_DIR / 'clicked' / narrator
    time_signal_dir.mkdir(parents=True, exist_ok=True)
    clicked_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    total_success = 0
    total_failure = 0

    for entry in input_data.get('time_signal', []):  # type: ignore[attr-defined]
        hhmm: str = entry['hhmm']  # type: ignore[index]
        for text in entry['texts']:  # type: ignore[index]
            num = _get_next_number(time_signal_dir, hhmm)
            filename = f'{hhmm}_{num:03d}.wav'
            output_path = time_signal_dir / filename
            print(f'生成中: {filename}')
            if _generate_voice(voicepeak, narrator, text, output_path, emotions):
                _record_to_manifest(manifest, filename, 'time_signal', {'hhmm': hhmm}, text, narrator, emotions, output_path, time_signal_dir)
                total_success += 1
            else:
                total_failure += 1

    for entry in input_data.get('clicked', []):  # type: ignore[attr-defined]
        name: str = entry['name']  # type: ignore[index]
        text = entry['text']  # type: ignore[index]
        num = _get_next_number(clicked_dir, name)
        filename = f'{name}_{num:03d}.wav'
        output_path = clicked_dir / filename
        print(f'生成中: {filename}')
        if _generate_voice(voicepeak, narrator, text, output_path, emotions):
            _record_to_manifest(manifest, filename, 'clicked', {'name': name}, text, narrator, emotions, output_path, clicked_dir)
            total_success += 1
        else:
            total_failure += 1

    _save_manifest(manifest)
    print(f'\n完了: {total_success} 件成功 / {total_failure} 件失敗')


if __name__ == '__main__':
    main()
