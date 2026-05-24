# Companion - 仕様書

## 概要

毎時話しかけてくれるデスクトップ常駐キャラクターアプリ。
現状は Python + Flet による Windows 向けデスクトップアプリとして実装している。

### 目的

1. 孤独を癒す
2. 愛着が湧いてきたら、徐々に自分の相棒のようにしたい
3. 最終的には自分専用の AI エージェント化を目指す

---

## 現在の実装範囲

- Flet ベースの常駐風 GUI
- Asia/Tokyo 基準のデジタル時計表示
- キャラクター画像の選択・切り替え・状態保存
- 時報音声の自動再生
- キャラクタークリック時音声の再生
- VOICEPEAK CLI を利用した音声生成ツール
- PCM ハッシュによる WAV 重複検出ツール
- VOICEPEAK のナレーター・感情一覧取得ツール
- pytest / Ruff / mypy を前提にしたテスト・静的解析環境

---

## ディレクトリ構成

```text
project root/
├── pyproject.toml
├── uv.lock
├── docs/
│   └── SPEC.md
├── src/
│   ├── config.toml
│   ├── main.py
│   ├── gui.py
│   ├── media.py
│   ├── .mycompanion_state.json        # 実行時に生成される状態ファイル（Git 管理外）
│   ├── resource/
│   │   ├── image/
│   │   │   └── character/
│   │   │       ├── .gitkeep
│   │   │       └── {character_name}/
│   │   └── voice/
│   │       ├── clicked/
│   │       │   ├── .gitkeep
│   │       │   └── {narrator}/
│   │       ├── time_signal/
│   │       │   ├── .gitkeep
│   │       │   └── {narrator}/
│   │       └── voice_manifest.json    # 実行時に生成される台帳（Git 管理外）
│   ├── tests/
│   └── tools/
│       ├── check_sound_duplicate/
│       │   └── check_duplicate.py
│       ├── generate_voice/
│       │   ├── gen_voice.py
│       │   └── input_voices.yaml      # Git 管理外
│       └── list_voices/
│           ├── list_voices.py
│           └── available_voices.json  # Git 管理外
└── git-setup/
```

---

## Git 管理対象外ファイル

`.gitignore` で以下を除外している。

| パス | 区分 | 理由 |
|------|------|------|
| `src/resource/image/character/*` | キャラクター画像 | 実アセットを環境ごとに差し替えるため |
| `src/resource/voice/clicked/*` | クリック音声 | 生成物バイナリのため |
| `src/resource/voice/time_signal/*` | 時報音声 | 生成物バイナリのため |
| `src/.mycompanion_state.json` | UI 状態 | 前回選択したキャラクター・画像を保持するため |
| `src/resource/voice/voice_manifest.json` | 音声生成台帳 | 生成履歴が環境依存のため |
| `src/tools/generate_voice/input_voices.yaml` | 音声生成入力 | ユーザーごとに内容が異なるため |
| `src/tools/list_voices/available_voices.json` | ツール出力 | インストール済み VOICEPEAK 環境に依存するため |

`.gitkeep` のみ管理し、実データ本体は管理しない。

---

## リソース配置規約

### キャラクター画像

```text
src/resource/image/character/{character_name}/{filename}
```

- `{character_name}` は GUI の選択候補としてそのまま表示する
- 画像探索対象拡張子は `.gif`, `.png`, `.jpg`, `.jpeg`, `.webp`
- キャラクター一覧は `character/` 直下のサブディレクトリ名から構成する
- 選択中キャラクターの画像は、そのキャラクターディレクトリ直下のファイルをファイル名昇順で扱う
- 起動時は前回選択画像が残っていればその画像を復元し、見つからなければ先頭画像へフォールバックする

### 時報音声

```text
src/resource/voice/time_signal/{narrator}/hhmm_xxx.wav
```

- `{narrator}` は VOICEPEAK のナレーター名
- `hhmm` は 24 時間表記の 4 桁時刻
- `xxx` は 001 始まりの 3 桁連番で、`hhmm` ごとに独立して採番する
- 再生側は `time_signal/` 配下を再帰的に探索する

### クリック音声

```text
src/resource/voice/clicked/{narrator}/{name}_xxx.wav
```

- `{name}` は入力 YAML の `clicked[].name`
- `xxx` は 001 始まりの 3 桁連番で、`name` ごとに独立して採番する
- 再生側は選択中キャラクター名と同名のナレーター配下を再帰的に探索する

---

## 設定ファイル

設定ファイルは [src/config.toml](src/config.toml) に配置する。
現状の実装で参照している設定は以下。

```toml
[generate_voice]
voicepeak_path = "C:/Program Files/VOICEPEAK/voicepeak.exe"
narrator = "Miyamai Moca"

[check_sound_duplicate]
target_folder = "resource/voice/time_signal"
```

- `gen_voice.py` は `voicepeak_path` と `narrator` を参照する
- `check_duplicate.py` は CLI 引数未指定時に `target_folder` を参照する
- 優先順位は基本的に CLI 引数 > `config.toml`

---

## GUI 仕様

GUI の本体は [src/gui.py](src/gui.py)、起動エントリポイントは [src/main.py](src/main.py) にある。

### 画面構成

- 常時最前面の固定サイズウィンドウ
- 左側に 9:16 比率のキャラクター表示領域
- 右側にデジタル時計と将来拡張用プレースホルダ領域
- タイトルバー左上にキャラクター選択メニュー

### ウィンドウ設定

- タイトル: `MyCompanion`
- 常時最前面: 有効
- サイズ: 720 x 640
- 最大化: 無効
- リサイズ: 無効

### 起動時の挙動

- `src/.mycompanion_state.json` から前回の選択キャラクター・画像名を復元する
- 前回キャラクターが存在しない場合は、名前順先頭のキャラクターへフォールバックする
- フォールバック時は SnackBar で通知する
- 利用可能キャラクターが 1 件もない場合はプレースホルダを表示する

### キャラクター画像領域

- 選択中キャラクターの画像が存在すればその画像を表示する
- 画像がない場合は配置先パスを示すプレースホルダを表示する
- キャラクターディレクトリ自体が存在しない場合は、フォルダ未検出メッセージを表示する

### マウス操作

- 左クリック: 選択中キャラクターの `clicked` 音声をランダム再生する
- 右クリック: 同キャラクター内の次画像へ切り替える
- ホイールクリック: 画像を再読み込みし、先頭画像へ戻す
- クリック音声フォルダが存在しない場合は SnackBar で通知する

### 時計・時報

- タイムゾーンは Asia/Tokyo 固定
- 1 秒ごとに `HH:MM`, `:SS`, 日付表示を更新する
- 現在時刻に一致する `hhmm_*.wav` が存在すれば 1 件をランダム再生する
- 同一セッション内で同じ `hhmm` は再生済み集合で抑止する

---

## media.py 仕様

[src/media.py](src/media.py) は GUI から使う画像・音声リソース操作を担当する。

- `_play_wav(path)`: `winsound.PlaySound(..., SND_FILENAME | SND_ASYNC)` で非同期再生する
- `_get_time_signal_files(hhmm)`: `time_signal/` 配下を再帰探索し、対象時刻の WAV を列挙する
- `_get_clicked_files_for_character(character)`: 指定キャラクター配下のクリック音声を列挙する
- `_list_characters()`: `character/` 直下のサブディレクトリ名をソートして返す
- `_list_character_images(character)`: 指定キャラクター直下の画像をファイル名昇順で返す

---

## 音声生成ツール

対象: [src/tools/generate_voice/gen_voice.py](src/tools/generate_voice/gen_voice.py)

### 入力ファイル

入力は JSON ではなく YAML で、ファイル名は `input_voices.yaml`。

```yaml
voices:
- narrator: SEKAI
  time_signal:
  - hhmm: '0800'
    texts:
    - text: 8時だよ。今日も一緒にがんばろ！
      emotion: happy
  clicked:
  - name: greeting
    text: ん？どうしたの？
    emotion: fun
```

### 入力ルール

- ルートは `voices` 配列
- `voices[].narrator` はその voice セクションの既定ナレーターとして使える
- `time_signal[].texts[]` はオブジェクト配列で、各要素に `text` を必須とする
- `clicked[]` は `name`, `text` を必須とする
- `narrator` はエントリ単位でも指定可能
- ナレーター解決順は エントリ > voice 単位 > CLI / config 既定値
- `emotion` は単独名なら `happy=100` のように自動正規化する
- 明示式 `happy=50,angry=20` はそのまま利用する

### CLI オプション

| オプション | 説明 |
|------------|------|
| `--voicepeak-path` | VOICEPEAK 実行ファイルパス |
| `--narrator` | 既定ナレーター |
| `--emotions` | 既定感情パラメータ |

### 実行フロー

1. `config.toml` を読み込み、CLI 引数で上書きする
2. `input_voices.yaml` を読み込む
3. 入力構造を検証し、必須キー欠落時はエラー終了する
4. `voices` を順に処理し、`time_signal` と `clicked` を生成する
5. 出力先はカテゴリごとに `src/resource/voice/{category}/{narrator}/` を自動作成する
6. 生成直後に同一フォルダ内で PCM ベースの重複チェックを行う
7. 台帳へ追記し、最後に成功件数 / 失敗件数を表示する

### 台帳ファイル

生成履歴は `src/resource/voice/voice_manifest.json` に追記保存する。

```json
[
    {
        "filename": "0800_001.wav",
        "type": "time_signal",
        "hhmm": "0800",
        "text": "8時だよ。今日も一緒にがんばろ！",
        "narrator": "SEKAI",
        "emotions": "happy=100",
        "generated_at": "2026-05-21T08:00:00",
        "pcm_sha256": "a3f2c1...",
        "duplicate_of": null
    }
]
```

- `type` は `time_signal` または `clicked`
- `time_signal` では `hhmm`、`clicked` では `name` を追加記録する
- `duplicate_of` には重複元ファイル名を記録する

---

## 重複チェックツール

対象: [src/tools/check_sound_duplicate/check_duplicate.py](src/tools/check_sound_duplicate/check_duplicate.py)

### 比較方式

- `wave` モジュールで PCM データのみを読み出す
- PCM データの SHA-256 で同一性判定する
- WAV ヘッダ差分は比較対象外

### 利用方法

1. `gen_voice.py` から関数呼び出し
2. 単独 CLI 実行

```bash
uv run python src/tools/check_sound_duplicate/check_duplicate.py
uv run python src/tools/check_sound_duplicate/check_duplicate.py src/resource/voice/time_signal/SEKAI
```

- 引数未指定時は `config.toml` の `check_sound_duplicate.target_folder` を使う
- 重複ありの場合はファイル名ペアを列挙する
- 重複なしの場合は `重複なし` を表示する

---

## VOICEPEAK 一覧取得ツール

対象: [src/tools/list_voices/list_voices.py](src/tools/list_voices/list_voices.py)

### 役割

- VOICEPEAK CLI からナレーター一覧を取得する
- 各ナレーターについて感情一覧を取得する
- 結果を JSON で保存する

### CLI オプション

| オプション | 説明 |
|------------|------|
| `--voicepeak-path` | VOICEPEAK 実行ファイルパス |
| `--output`, `-o` | 出力 JSON パス |

### 出力フォーマット

```json
{
    "generated_at": "2026-05-21T12:00:00",
    "voicepeak_path": "C:/Program Files/VOICEPEAK/voicepeak.exe",
    "narrators_count": 2,
    "voices": [
        {
            "narrator": "Miyamai Moca",
            "emotions": ["happy", "sad", "angry", "surprised"]
        }
    ]
}
```

- `--voicepeak-path` 未指定時は `config.toml` の `generate_voice.voicepeak_path` を使う
- 感情取得に失敗したナレーターは警告表示し、空配列で継続する

---

## テストと品質基準

### テスト対象

- GUI 状態保存と画像切り替え
- 画像 / 音声リソース探索
- VOICEPEAK 呼び出しラッパー
- 音声生成入力バリデーションと出力先決定
- WAV 重複判定

### 品質チェックコマンド

```bash
uv run ruff check src/
uv run ruff format src/
uv run mypy src/
uv run pytest
```

### コーディング規約

`pyproject.toml` に準拠する。

| 項目 | 設定 |
|------|------|
| Python バージョン | 3.12 以上 |
| 型ヒント | 必須 |
| docstring スタイル | Google スタイル |
| クォート | シングルクォート |
| 行長上限 | 150 文字 |
| Linter / Formatter | Ruff |
| 型チェッカー | mypy |

---

## 将来実装予定

- タイマー設定と開始 / 終了通知
- ToDo / カレンダー表示
- 一日の振り返り機能
- より高度なキャラクターアニメーション
- AI エージェント機能の統合
