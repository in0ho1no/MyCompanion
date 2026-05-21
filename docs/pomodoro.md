# ポモドーロタイマー 仕様書

## 概要

現行の Flet GUI にポモドーロタイマーを追加するための将来仕様。
基盤となるディレクトリ構成、音声配置規約、GUI レイアウト方針は [docs/SPEC.md](docs/SPEC.md) に追従する。

- GUI への組み込み先は [src/main.py](src/main.py) ではなく [src/gui.py](src/gui.py)
- 音声・画像リソースの操作は [src/media.py](src/media.py) の責務に合わせて拡張する
- 音声生成入力は JSON ではなく YAML を前提とする

---

## 追加対象

- [src/gui.py](src/gui.py): ポモドーロ表示領域、操作ボタン、状態遷移、時計ループとの統合
- [src/media.py](src/media.py): ポモドーロ音声の列挙ヘルパー追加
- [src/config.toml](src/config.toml): ポモドーロ設定追加
- [src/tools/generate_voice/gen_voice.py](src/tools/generate_voice/gen_voice.py): `pomodoro` 音声生成対応
- `src/resource/voice/pomodoro/`: ポモドーロ用音声配置先

本書は未実装機能の仕様であり、ここに記載する `pomodoro` 系ディレクトリ・設定・UI は追加対象を示す。

---

## ディレクトリ構成への追加

現行の音声配置規約に合わせ、`src/resource/voice/` 配下に以下を追加する。

- `src/resource/voice/pomodoro/`
- `src/resource/voice/pomodoro/.gitkeep`
- `src/resource/voice/pomodoro/{narrator}/`

- `pomodoro/` も `clicked/` と同様にナレーター別サブディレクトリ構成とする
- 実データは Git 管理対象外、`.gitkeep` のみ管理する想定とする
- `voice_manifest.json` は既存台帳を継続利用し、`type: "pomodoro"` を追加する

---

## config.toml への追加

[src/config.toml](src/config.toml) に以下を追加する。

```toml
[pomodoro]
focus_minutes = 25
break_minutes = 5
sets = 4
auto_start_break = true
auto_start_focus = true
```

- `focus_minutes`: 集中フェーズの分数
- `break_minutes`: 休憩フェーズの分数
- `sets`: 集中フェーズの総セット数
- `auto_start_break`: 集中終了後に自動で休憩へ進むか
- `auto_start_focus`: 休憩終了後に自動で次の集中へ進むか

設定値の優先順位は、既存ツールの方針に合わせて CLI または UI 操作による明示指定 > `config.toml` とする。

---

## 音声生成仕様への追加

対象: [src/tools/generate_voice/gen_voice.py](src/tools/generate_voice/gen_voice.py)

### input_voices.yaml フォーマットへの追加

現行実装の入力ルールに合わせ、`voices` 配列の各要素へ `pomodoro` セクションを追加する。

例:

```yaml
voices:
- narrator: SEKAI
    pomodoro:
    - { name: pomodoro_focus_start, text: "よし、集中していこう！", emotion: happy }
    - { name: pomodoro_focus_start, text: "頑張れ！応援してるよ。", emotion: fun }
    - { name: pomodoro_break_start, text: "お疲れ様。ちゃんと手を止めてね。", emotion: sad }
    - { name: pomodoro_finish, text: "全部終わったよ。お疲れ様でした！", emotion: happy }
    - { name: pomodoro_interrupt, text: "ここまでだね。また再開しよう。", emotion: sad }
```

- 現行の `clicked` と同じく、1 エントリ = 1 出力ファイルとする
- 複数バリエーションは `texts` 配列ではなく、同じ `name` の複数エントリで表現する
- `narrator` は voice 単位またはエントリ単位で継承・上書き可能とする
- `emotion` は既存仕様と同様に省略可能とする

### 出力先と命名規則

出力先は以下とする。

```text
src/resource/voice/pomodoro/{narrator}/{name}_xxx.wav
```

例:

```text
src/resource/voice/pomodoro/SEKAI/pomodoro_focus_start_001.wav
src/resource/voice/pomodoro/SEKAI/pomodoro_break_start_001.wav
src/resource/voice/pomodoro/SEKAI/pomodoro_finish_001.wav
src/resource/voice/pomodoro/SEKAI/pomodoro_interrupt_001.wav
```

- 採番ルールは `clicked` と同一で、`name` ごとに 001 から連番とする
- 同一ナレーター配下で既存最大番号の次を採用する

### gen_voice.py での取り扱い

- `pomodoro` セクションは `clicked` と同等の構造で受け付ける
- 必須キーは `name`, `text`
- 出力カテゴリのみ `pomodoro` に切り替える
- 生成直後に同一フォルダ内で重複チェックを行う
- 台帳には `type: "pomodoro"` と `name` を記録する

---

## GUI 画面構成

対象: [src/gui.py](src/gui.py)

### 現行レイアウトとの関係

現行 GUI では右列が以下の 2 要素で構成される。

- 上段: 時計カード
- 下段: 将来拡張用プレースホルダ領域

ポモドーロタイマーは、この下段プレースホルダ領域を置き換えるか、同領域をポモドーロ専用カードへ差し替える形で追加する。

### 全体イメージ

```text
┌──────────────────────────────────┐
│ [キャラクター画像]  │  時計       │
│                    │            │
│                    │ ポモドーロ  │
│                    │  タイマー   │
│                    │ [操作ボタン] │
└──────────────────────────────────┘
```

### ポモドーロ表示エリア

右列下段に以下を表示する。

| 要素 | 内容 |
|---|---|
| フェーズ表示 | `集中 2 / 4`、`休憩 2 / 4` など現在フェーズとセット数 |
| 残り時間 | `MM:SS` 形式 |
| 状態表示 | `未開始`、`実行中`、`一時停止中`、`完了` など |
| 操作ボタン | 開始 / 中止、一時停止 / 再開、スキップ |

### 操作ボタン

| 位置 | ラベル | 動作 |
|---|---|---|
| 左 | `開始` / `中止` | 未開始時はセッション開始、実行中または一時停止中は全体中止 |
| 中 | `一時停止` / `再開` | 実行中と一時停止中でトグル。未開始時は非活性 |
| 右 | `スキップ` | 現在フェーズを終了して次状態へ進む。未開始時は非活性 |

---

## ポモドーロ動作仕様

### フェーズ遷移

```text
[未開始]
    ↓ 開始
[集中 1 / N] → [休憩 1 / N] → [集中 2 / N] → ... → [全セット完了]
```

- `sets` は集中フェーズの回数を指す
- 最終集中フェーズ完了後、必要な休憩を終えたら `完了` へ遷移する
- `スキップ` 操作でも通常の遷移順に従う
- `中止` はどのフェーズからでも `中止後` 状態へ遷移する

### 自動開始設定

- `auto_start_break = true`: 集中終了後すぐに休憩タイマーを開始する
- `auto_start_break = false`: 休憩フェーズへは遷移するが、残り時間 0 の待機状態で停止し、`再開` を待つ
- `auto_start_focus = true`: 休憩終了後すぐに次の集中タイマーを開始する
- `auto_start_focus = false`: 次の集中フェーズへは遷移するが、待機状態で停止し、`再開` を待つ

### 時間カウント

- 表示は `MM:SS`
- 更新粒度は現行時計ループと同じ 1 秒単位を前提とする
- アプリの時計更新と競合しないよう、[src/gui.py](src/gui.py) の非同期ループへ統合する前提とする

---

## 音声再生ルール

### ポモドーロ用音声カテゴリ

| タイミング | 再生名 | 備考 |
|---|---|---|
| 集中フェーズ開始 | `pomodoro_focus_start` | 選択キャラクターと同名ナレーター配下からランダム再生 |
| 休憩フェーズ開始 | `pomodoro_break_start` | 同上 |
| 全セット完了 | `pomodoro_finish` | 同上 |
| セッション中止 | `pomodoro_interrupt` | 同上 |

- 現行の `clicked` と同様に、選択中キャラクター名と同名のナレーター配下を参照する
- 該当ファイルが複数ある場合はランダムに 1 件再生する
- 該当フォルダまたは該当音声がない場合は無音で継続し、必要なら GUI 側で通知する

### 既存音声との共存ルール

| 種別 | 未開始 | 実行中 | 一時停止中 | 完了 / 中止後 |
|---|---|---|---|---|
| 時報 (`time_signal`) | ○ | × | ○ | ○ |
| クリック (`clicked`) | ○ | ○ | ○ | ○ |
| ポモドーロ音声 (`pomodoro`) | 操作時のみ | フェーズ遷移時のみ | 再開時または遷移時のみ | 完了 / 中止時のみ |

- ここでの「実行中」は、開始後から完了または中止までのうち、一時停止中を除く期間を指す
- スキップ操作時は、遷移先フェーズ開始音声を通常どおり再生する

---

## 状態定義

| 状態 | 説明 | 時報 | クリック音 |
|---|---|---|---|
| 未開始 | セッション未開始 | ○ | ○ |
| 実行中（集中） | 集中タイマー進行中 | × | ○ |
| 実行中（休憩） | 休憩タイマー進行中 | × | ○ |
| 一時停止中 | 現在フェーズの残時間を保持して停止 | ○ | ○ |
| 完了 | 全セット終了 | ○ | ○ |
| 中止後 | ユーザーが中止 | ○ | ○ |

---

## media.py への追加想定

ポモドーロ音声も既存の設計に合わせ、[src/media.py](src/media.py) に補助関数を追加する前提とする。

想定追加関数:

- `_pomodoro_dir_exists(character: str) -> bool`
- `_get_pomodoro_files_for_character(character: str, name: str) -> list[Path]`

仕様:

- ベースディレクトリは `src/resource/voice/pomodoro`
- 選択中キャラクター名と同名ナレーター配下を参照する
- `name_*.wav` パターンで再帰探索する

---

## 実装時の注意

- 既存の UI 状態保存はキャラクターと画像選択のみであり、ポモドーロ状態の永続化は本仕様では必須としない
- 現行の時報抑止は `gui.py` 側のロジックで制御する想定で、`media.py` 側には停止状態を持たせない
- 現行の音声生成入力は YAML のため、旧仕様にある `input_voices.json` 前提は採用しない
- GUI の責務は [src/gui.py](src/gui.py) に集約し、[src/main.py](src/main.py) は起動エントリポイントのままとする
