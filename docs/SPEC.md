# Companion - 仕様書

## 概要

毎時話しかけてくれるデスクトップ常駐キャラクターアプリ。
Python + Flet によるデスクトップアプリとして実装する。

### 目的

1. 孤独を癒す
2. 愛着が湧いてきたら、徐々に自分の相棒のようにしたい
3. 最終的には自分専用のAIエージェント化を目指す（段階的に実現）

---

## ディレクトリ構成

```
project root/
├── config.toml                          # 全ツール共通設定（プロジェクトルート）
├── main.py                              # Flet アプリ本体
├── SPEC.md                              # 本仕様書
├── pyproject.toml
├── requirements.txt
├── resource/
│   ├── voice/
│   │   ├── voice_manifest.json          # 音声ファイル ↔ テキスト対応記録
│   │   ├── time_signal/                 # 時報ボイス置き場
│   │   └── clicked/                     # クリック反応ボイス置き場
│   └── image/
│       └── character/                   # キャラクター画像置き場
└── tools/
    ├── generate_voice/
    │   ├── gen_voice.py                 # 音声生成スクリプト
    │   └── input_voices.json            # 生成テキスト定義
    └── check_sound_duplicate/
        └── check_duplicate.py           # 重複チェックスクリプト
```

> `resource/voice/` 以下の音声ファイルは Git 管理対象外（`.gitignore` で除外）。

---

## ファイル命名規則

### time_signal

```
hhmm_xxx.wav
```

- `hhmm`：時分（例：`0800`、`2300`）
- `xxx`：採番。`001` 始まりの3桁、`hhmm` ごとに独立してカウント
- 例：`0800_001.wav`、`0800_002.wav`、`2300_001.wav`

### clicked

```
{name}_xxx.wav
```

- `name`：`input_voices.json` の `"name"` キーで指定した文字列
- `xxx`：採番。`001` 始まりの3桁、`name` ごとに独立してカウント
- 例：`greeting_001.wav`、`greeting_002.wav`

> 採番はスキップなし・上書なし。実行のたびに既存の最大番号の次から生成する。

---

## config.toml

プロジェクトルートに1ファイルとして配置。ツールごとにセクション分け。
CLI 引数での指定が優先され、なければ config.toml から読み込む（各ツール共通ルール）。

```toml
[generate_voice]
voicepeak_path = "C:/Program Files/VOICEPEAK/voicepeak.exe"
narrator = "宮舞モカ"

[check_sound_duplicate]
target_folder = "resource/voice/time_signal"
```

---

## tools/generate_voice/

### input_voices.json フォーマット

```json
{
    "time_signal": [
        {
            "hhmm": "0800",
            "texts": ["8時だよ。お仕事頑張ってね！", "8時。今日のタスク、確認した？"]
        }
    ],
    "clicked": [
        {"name": "greeting", "text": "なに？呼んだ？"},
        {"name": "shy",      "text": "えへへ、くすぐったいよ。"}
    ]
}
```

- `time_signal.texts`：複数指定で複数ファイルを生成
- `clicked.name`：出力ファイル名の基底（必須キー）

### gen_voice.py 仕様

#### 実行フロー

1. `config.toml` を読み込む（CLI 引数 `--voicepeak-path` があれば優先）
2. `input_voices.json` を読み込む
3. **事前バリデーション**：`clicked` エントリに `"name"` キーが存在しなければエラーを出力して処理を中断
4. 全エントリを一括生成（`time_signal` → `clicked` の順）
5. 1ファイル生成するたびに重複チェックを実行（`check_duplicate.py` を呼び出し）
6. 生成完了後、成功・失敗件数をサマリ表示

#### 採番ロジック

- 対象フォルダを走査し、同一プレフィクスの既存ファイルの最大番号を取得
- `最大番号 + 1` を出力番号とする
- 既存ファイルがなければ `_001` から開始

#### エラー処理

- 1件の生成失敗はログに出力して次の処理を続行
- 最終サマリ：`完了: X 件成功 / Y 件失敗`

#### voice_manifest.json への記録

生成のたびに `resource/voice/voice_manifest.json` へ追記。
重複が検出された場合も記録し、`duplicate_of` フィールドに重複元ファイル名を記載。

```json
[
    {
        "filename": "0800_001.wav",
        "type": "time_signal",
        "hhmm": "0800",
        "text": "8時だよ。お仕事頑張ってね！",
        "generated_at": "2025-05-17T10:30:00",
        "pcm_sha256": "a3f2c1...",
        "duplicate_of": null
    },
    {
        "filename": "greeting_001.wav",
        "type": "clicked",
        "name": "greeting",
        "text": "なに？呼んだ？",
        "generated_at": "2025-05-17T10:30:05",
        "pcm_sha256": "b7e4d2...",
        "duplicate_of": null
    }
]
```

---

## tools/check_sound_duplicate/

### check_duplicate.py 仕様

#### 比較方式

Python 標準ライブラリ `wave` モジュールで PCM データ部分のみを読み出し、SHA-256 で比較する。
WAV ヘッダに含まれる日時・ソフトウェア名などのメタデータは比較対象外。

> VoicePeak で感情パラメータを意図的に変えた場合は PCM が変化するため、別ファイルとして扱われる。

#### 実行モード

1. **`gen_voice.py` からのモジュール呼び出し**：生成直後に1ファイルを対象フォルダ内と照合
2. **単独スクリプト実行**：対象フォルダを指定してフォルダ内全件を照合

```bash
# CLI 引数で指定
python check_duplicate.py resource/voice/time_signal/

# 引数なし → config.toml の [check_sound_duplicate] target_folder を使用
python check_duplicate.py
```

#### 出力

- 重複ペアが存在する場合：ファイル名のペアをログ出力
- 重複なしの場合：その旨を出力

---

## main.py（Flet アプリ）

### 画面構成

- 常時最前面（`always_on_top`）
- デジタル時計（HH:MM 表示）
- キャラクター画像（中央）
- 字幕テキスト（再生中のファイル名を表示）

### キャラクター画像

- `resource/image/character/` 内の画像を1枚表示
- GIF は無限ループ再生
- 対応形式：`.png` / `.jpg` / `.jpeg` / `.gif`（GIF 優先）

### 時報再生

- 毎分、現在時刻の `hhmm` に一致するファイルを `resource/voice/time_signal/` から探索
- 一致するファイルが複数あればランダムに1つ再生
- 同一 `hhmm` 内での二重再生は行わない

### クリック反応

- キャラクター画像をクリックすると `resource/voice/clicked/` からランダムに1つ再生

---

## コーディング規約

`pyproject.toml` に準拠。

| 項目 | 設定 |
|------|------|
| Python バージョン | 3.12 |
| 型ヒント | 必須（`disallow_untyped_defs = true`） |
| docstring スタイル | Google スタイル |
| クォート | シングルクォート |
| 行長上限 | 150 文字 |
| Linter / Formatter | ruff |
| 型チェッカー | mypy |

---

## 将来実装予定（現時点では対象外）

- タイマー設定と開始・終了の通知
- 口パク・目パチなどのアニメーション
- TodoList 表示
- カレンダー管理
- 一日の振り返り KPT 管理
- ブラウザ / スマートフォンアプリ化
