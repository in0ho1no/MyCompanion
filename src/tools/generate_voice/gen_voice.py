"""音声生成スクリプト。

VOICEPEAKを呼び出して音声ファイルを生成し、voice_manifest.jsonに記録する。
"""

import argparse
import contextlib
import json
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / 'check_sound_duplicate'))
import check_duplicate as dup_checker

_SRC_ROOT = Path(__file__).parent.parent.parent
_RESOURCE_VOICE_DIR = _SRC_ROOT / 'resource' / 'voice'
_MANIFEST_PATH = _RESOURCE_VOICE_DIR / 'voice_manifest.json'
_INPUT_JSON_PATH = Path(__file__).parent / 'input_voices.json'
_CONFIG_PATH = _SRC_ROOT / 'config.toml'


def _display_output_path(output_path: Path) -> str:
    with contextlib.suppress(ValueError):
        return output_path.relative_to(_RESOURCE_VOICE_DIR).as_posix()
    return output_path.as_posix()


def _load_config(voicepeak_path_arg: str | None, narrator_arg: str | None) -> tuple[str, str | None]:
    with open(_CONFIG_PATH, 'rb') as f:
        config = tomllib.load(f)
    section = config['generate_voice']
    voicepeak_path: str = voicepeak_path_arg or section['voicepeak_path']
    narrator = narrator_arg or section.get('narrator')
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


def _resolve_narrator(entry: dict[str, object], default_narrator: str | None) -> str | None:
    narrator = entry.get('narrator', default_narrator)
    if isinstance(narrator, str) and narrator:
        return narrator
    return None


def _normalize_input_data(input_data: Mapping[str, object]) -> dict[str, object]:
    voices = input_data.get('voices')
    if not isinstance(voices, list):
        return dict(input_data)

    normalized_time_signal: list[object] = []
    normalized_clicked: list[object] = []

    for voice in voices:
        if not isinstance(voice, dict):
            continue

        narrator = voice.get('narrator')

        time_signal_entries = voice.get('time_signal', [])
        if isinstance(time_signal_entries, list):
            for entry in time_signal_entries:
                if not isinstance(entry, dict):
                    normalized_time_signal.append(entry)
                    continue

                normalized_entry = dict(entry)
                texts = entry.get('texts', [])
                if isinstance(texts, list):
                    normalized_texts: list[object] = []
                    for text_entry in texts:
                        if not isinstance(text_entry, dict):
                            normalized_texts.append(text_entry)
                            continue

                        normalized_text_entry = dict(text_entry)
                        if narrator is not None and 'narrator' not in normalized_text_entry:
                            normalized_text_entry['narrator'] = narrator
                        normalized_texts.append(normalized_text_entry)
                    normalized_entry['texts'] = normalized_texts

                normalized_time_signal.append(normalized_entry)

        clicked_entries = voice.get('clicked', [])
        if isinstance(clicked_entries, list):
            for entry in clicked_entries:
                if not isinstance(entry, dict):
                    normalized_clicked.append(entry)
                    continue

                normalized_entry = dict(entry)
                if narrator is not None and 'narrator' not in normalized_entry:
                    normalized_entry['narrator'] = narrator
                normalized_clicked.append(normalized_entry)

    return {
        'time_signal': normalized_time_signal,
        'clicked': normalized_clicked,
    }


def _normalize_emotions(emotions: str | None) -> str | None:
    if emotions is None:
        return None
    if '=' in emotions or ',' in emotions:
        return emotions
    return f'{emotions}=100'


def _resolve_emotions(entry: dict[str, object], default_emotions: str | None) -> str | None:
    emotion = entry.get('emotion')
    if isinstance(emotion, str) and emotion:
        return _normalize_emotions(emotion)
    return _normalize_emotions(default_emotions)


def _get_output_dir(category: str, narrator: str, dir_cache: dict[str, Path]) -> Path:
    output_dir = dir_cache.get(narrator)
    if output_dir is None:
        output_dir = _RESOURCE_VOICE_DIR / category / narrator
        output_dir.mkdir(parents=True, exist_ok=True)
        dir_cache[narrator] = output_dir
    return output_dir


def _validate_input(input_data: dict[str, object], default_narrator: str | None) -> bool:
    clicked_entries = input_data.get('clicked', [])
    if not isinstance(clicked_entries, list):
        print('エラー: clicked は配列である必要があります。')
        return False

    for entry in clicked_entries:
        if not isinstance(entry, dict):
            print(f'エラー: clicked エントリが不正です: {entry}')
            return False
        if 'name' not in entry:
            print(f'エラー: clickedエントリに "name" キーがありません: {entry}')
            return False
        if 'text' not in entry:
            print(f'エラー: clickedエントリに "text" キーがありません: {entry}')
            return False
        if _resolve_narrator(entry, default_narrator) is None:
            print(f'エラー: clickedエントリに narrator がありません: {entry}')
            return False

    time_signal_entries = input_data.get('time_signal', [])
    if not isinstance(time_signal_entries, list):
        print('エラー: time_signal は配列である必要があります。')
        return False

    for entry in time_signal_entries:
        if not isinstance(entry, dict):
            print(f'エラー: time_signal エントリが不正です: {entry}')
            return False
        if 'hhmm' not in entry:
            print(f'エラー: time_signalエントリに "hhmm" キーがありません: {entry}')
            return False

        texts = entry.get('texts')
        if not isinstance(texts, list):
            print(f'エラー: time_signalエントリの "texts" は配列である必要があります: {entry}')
            return False

        for text_entry in texts:
            if not isinstance(text_entry, dict):
                print(f'エラー: time_signal の text エントリが不正です: {text_entry}')
                return False
            if 'text' not in text_entry:
                print(f'エラー: time_signal の text エントリに "text" キーがありません: {text_entry}')
                return False
            if _resolve_narrator(text_entry, default_narrator) is None:
                print(f'エラー: time_signal の text エントリに narrator がありません: {text_entry}')
                return False

    return True


def _get_required_str(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f'必須文字列 {key} が不足しています: {entry}')
    return value


def main() -> None:
    """コマンドライン実行のエントリポイント。"""
    parser = argparse.ArgumentParser(description='VOICEPEAKで音声ファイルを生成する')
    parser.add_argument('--voicepeak-path', help='VOICEPEAKの実行ファイルパス（config.tomlより優先）')
    parser.add_argument('--narrator', help='ナレーター名（config.tomlより優先）')
    parser.add_argument('--emotions', help='感情パラメータ（例: happy=50,angry=20）')
    args = parser.parse_args()

    voicepeak, default_narrator = _load_config(args.voicepeak_path, args.narrator)
    default_emotions: str | None = args.emotions or None

    with open(_INPUT_JSON_PATH, encoding='utf-8') as f:
        input_data: dict[str, Any] = _normalize_input_data(json.load(f))

    if not _validate_input(input_data, default_narrator):
        sys.exit(1)

    time_signal_dirs: dict[str, Path] = {}
    clicked_dirs: dict[str, Path] = {}

    manifest = _load_manifest()
    total_success = 0
    total_failure = 0

    for entry in input_data.get('time_signal', []):
        if not isinstance(entry, dict):
            continue
        hhmm = _get_required_str(entry, 'hhmm')
        texts = entry.get('texts', [])
        if not isinstance(texts, list):
            continue
        for text_entry in texts:
            if not isinstance(text_entry, dict):
                continue
            narrator = _resolve_narrator(text_entry, default_narrator)
            if narrator is None:
                continue
            text = _get_required_str(text_entry, 'text')
            emotions = _resolve_emotions(text_entry, default_emotions)
            time_signal_dir = _get_output_dir('time_signal', narrator, time_signal_dirs)
            num = _get_next_number(time_signal_dir, hhmm)
            filename = f'{hhmm}_{num:03d}.wav'
            output_path = time_signal_dir / filename
            print(f'生成中: narrator={narrator}, file={_display_output_path(output_path)}')
            if _generate_voice(voicepeak, narrator, text, output_path, emotions):
                _record_to_manifest(manifest, filename, 'time_signal', {'hhmm': hhmm}, text, narrator, emotions, output_path, time_signal_dir)
                total_success += 1
            else:
                total_failure += 1

    for entry in input_data.get('clicked', []):
        if not isinstance(entry, dict):
            continue
        narrator = _resolve_narrator(entry, default_narrator)
        if narrator is None:
            continue
        name = _get_required_str(entry, 'name')
        text = _get_required_str(entry, 'text')
        emotions = _resolve_emotions(entry, default_emotions)
        clicked_dir = _get_output_dir('clicked', narrator, clicked_dirs)
        num = _get_next_number(clicked_dir, name)
        filename = f'{name}_{num:03d}.wav'
        output_path = clicked_dir / filename
        print(f'生成中: narrator={narrator}, file={_display_output_path(output_path)}')
        if _generate_voice(voicepeak, narrator, text, output_path, emotions):
            _record_to_manifest(manifest, filename, 'clicked', {'name': name}, text, narrator, emotions, output_path, clicked_dir)
            total_success += 1
        else:
            total_failure += 1

    _save_manifest(manifest)
    print(f'\n完了: {total_success} 件成功 / {total_failure} 件失敗')


if __name__ == '__main__':
    main()
