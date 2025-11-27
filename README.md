# Redmine バーンダウンチャート

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-93.18%25-brightgreen.svg)](htmlcov/index.html)
[![Tests](https://img.shields.io/badge/tests-103%20passed-brightgreen.svg)](tests/)

Redmine REST APIを使用してチケット情報を取得し、バーンダウンチャート用のデータを生成するモダンなPythonツールです。

## 特徴

- 高速パッケージ管理: `uv`による超高速な依存関係管理
- 厳格なコード品質: `ruff` + `mypy` + `pre-commit`による堅牢な品質管理
- 高カバレッジ: 93%以上のテストカバレッジ（103テスト）
- 環境変数管理: `.env`ファイルで安全な設定管理
- 型安全: 完全な型アノテーションとstrict型チェック
- REST API対応: Redmine API経由でチケット情報を取得
- CSV出力: Excel/Google Spreadsheetで使えるCSV形式でデータ出力
- 週次集計: バーンダウンチャート用の週次進捗データを自動生成
- 適切なディレクトリ構成: `output/`ディレクトリへの整理された出力
- Excelテンプレート生成: 4シート構成の完全なExcelワークブック自動生成

## このツールでできること

プラグインなしのRedmine環境から、週次でバーンダウンチャートを作成するための完全なワークフローです。

- Redmine APIを使った自動チケット取得
- 週次進捗の自動集計
- バーンダウンチャート用データ生成
- Excelワークブック自動生成（RAW/週次/月次/ダッシュボード）
- CSVデータの自動インポート
- Excel/Google Spreadsheetで即座にグラフ化

## クイックスタート

### 実行方法の選択

このツールは3つの方法で実行できます

1. Docker（推奨） - 環境構築不要、最も簡単
2. uv（推奨・ローカル実行） - Python環境があれば高速
3. pip（従来型） - 標準的なPython環境

---

## Docker で実行（推奨）

### 必要環境

- [Docker](https://www.docker.com/get-started)（20.10以上）
- [Docker Compose](https://docs.docker.com/compose/install/)（v2.0以上、オプション）

### セットアップ

#### 1. リポジトリをクローン

```bash
git clone https://github.com/okamyuji/redmine-burndown
cd redmine-burndown
```

#### 2. 環境変数を設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集（エディタで開く）
# REDMINE_URL=https://your-redmine.example.com
# REDMINE_API_KEY=your_api_key_here

# オプション設定（必要に応じて追加）
# REDMINE_PROJECT_ID=598 # 特定プロジェクトのみ取得（空=全プロジェクト）
# REDMINE_MAX_ISSUES= # 取得件数上限（空=全件取得）
# REDMINE_STATUS_ID=open # ステータスフィルター（空=全て）
```

#### 3. Dockerイメージをビルド

```bash
docker compose build
```

#### 4. 実行

```bash
# docker-composeで実行（推奨）
docker compose up

# または、Dockerコマンドで実行
docker run --rm \
-v $(pwd)/.env:/app/.env:ro \
-v $(pwd)/output:/app/output:rw \
redmine-burndown:latest
```

### Docker実行のメリット

- 環境構築不要: Python環境のセットアップ不要
- 依存関係の分離: ホストシステムを汚さない
- 再現性: どの環境でも同じ動作を保証
- CIで実行可能: GitHub ActionsやGitLab CIで使用可能
- cronジョブ化が容易: 定期実行に最適

### Docker使用例

```bash
# 週次実行（cronに登録する場合）
0 9 * * 1 cd /path/to/redmine-burndown && docker compose up

# 環境変数を直接指定して実行
docker run --rm \
-e REDMINE_URL=https://redmine.example.com \
-e REDMINE_API_KEY=your_api_key \
-v $(pwd)/output:/app/output \
redmine-burndown:latest

# 特定のコマンドを実行
docker run --rm \
-v $(pwd)/.env:/app/.env:ro \
-v $(pwd)/output:/app/output:rw \
redmine-burndown:latest \
python -m redmine_burndown.redmine_client
```

---

## uv で実行（ローカル環境）

### uvの必要環境

- Python 3.11以上
- [uv](https://github.com/astral-sh/uv)（推奨）

### uvを使ったセットアップ

```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトのクローン
cd redmine-burndown

# 依存関係のインストール
uv sync

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して、実際のRedmine情報を設定してください

# テストの実行
uv run pytest

# Linterチェック
uv run ruff check .
uv run mypy src/
```

### pipを使ったセットアップ

```bash
# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -e ".[dev]"

# テストの実行
pytest
```

## 使い方ガイド

### 前提条件: 環境変数の設定

- チケットデータを取得する前に、`.env`ファイルを作成して接続情報を設定してください

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集
# REDMINE_URL=https://your-redmine-url.com
# REDMINE_API_KEY=your-api-key-here

# オプション設定（空の場合はデフォルト動作）
# REDMINE_PROJECT_ID= # プロジェクトID（空=全プロジェクト、カンマ区切りで複数指定可）
# REDMINE_MAX_ISSUES= # 取得件数上限（空=全件取得、数値指定で上限設定）
# REDMINE_STATUS_ID= # ステータスフィルター（空=全て、open/closed/ID指定）
```

- APIキーの取得方法
   1. Redmineにログイン
   2. 右上のアカウント名 →「個人設定」
   3. 右側メニューの「APIアクセスキー」→「表示」ボタンをクリック

### 基本ワークフロー（3ステップ）

#### ステップ1: チケットデータを取得

```bash
uv run python -m redmine_burndown.redmine_client
```

- 実行結果
    - `output/redmine_issues_YYYYMMDD_HHMMSS.csv` が生成されます
    - プロジェクト一覧とチケット一覧が表示されます

- エラーが発生した場合
    - 「環境変数が設定されていません」→ `.env`ファイルが作成されているか確認
    - API接続エラー → `.env`のURLとAPIキーが正しいか確認

#### ステップ2: バーンダウン用データを生成

```bash
uv run python -m redmine_burndown.burndown_analyzer
```

- 実行結果
    - `output/burndown_weekly.csv` - バーンダウンチャート用データ
    - `output/status_summary_weekly.csv` - ステータス別週次サマリー

#### ステップ3: Excelワークブックを生成

```bash
# Excelテンプレート生成（初回のみ）
uv run python -m redmine_burndown.excel_generator

# CSVデータをExcelにインポート
uv run python -c "
from redmine_burndown.excel_generator import ExcelGenerator
import glob

# 最新のCSVファイルを検索
csv_files = sorted(glob.glob('output/redmine_issues_*.csv'))
if csv_files:
latest_csv = csv_files[-1]
generator = ExcelGenerator()
generator.copy_csv_to_excel(latest_csv, 'output/burndown_workbook.xlsx')
print(f' Excelワークブック生成完了: output/burndown_workbook.xlsx')
"
```

- 実行結果
    - `templates/burndown_template.xlsx` - Excelテンプレート（初回作成）
    - `output/burndown_workbook.xlsx` - データ入りExcelワークブック

- Excelワークブックの構成

1. RAWシート: Redmineチケットデータ + 自動計算列
   - 完了フラグ、週番号、年-週、残作業量を自動計算
2. 週次バーンダウンシート: バーンダウンチャート用データ
   - 完了チケット数（累積）、残チケット数
   - 完了工数（累積）、残工数
   - 理想線（線形減少）
3. 月次累積フロー図シート: CFD（Cumulative Flow Diagram）
   - 新規、進行中、レビュー中、完了のステータス推移
   - ボトルネック検出に活用
4. ダッシュボードシート: KPI一覧
   - 完了率、平均ベロシティ、バグ率
   - リードタイム、サイクルタイム、ブロック率

#### ステップ4: Excelワークブックの確認

- `update_burndown.sh`スクリプトで自動的にExcelワークブック（グラフ付き）が生成されます

1. `output/burndown_workbook.xlsx` をExcelで開く
2. 以下のシートとグラフを確認：
   - RAWシート: チケットデータ + 自動計算列 + カスタムフィールド
   - 週次バーンダウンシート: バーンダウンチャート（折れ線グラフ自動配置済み）
   - 月次累積フロー図シート: CFD（積み上げ面グラフ自動配置済み）
   - ダッシュボードシート: 6つのKPI指標

グラフは自動生成されているため、手動での作成は不要です。

> Note: 手動でCSVからグラフを作成したい場合は、`output/burndown_weekly.csv`を開いてデータ範囲（A列、C列、F列）を選択し、「挿入」→「折れ線グラフ」を選択してください。

### プログラムから利用

#### 1. Redmineからチケット情報を取得

```python
from redmine_burndown import RedmineClient

# クライアント初期化
client = RedmineClient(
base_url="https://your-redmine.example.com",
api_key="your_api_key_here"
)

# プロジェクト一覧の取得
projects = client.get_projects()

# チケット一覧の取得
issues_data = client.get_issues(limit=100)

# CSVへエクスポート（output/ディレクトリに保存）
client.export_to_csv(issues_data['issues'], 'issues.csv', output_dir='output')
```

#### 2. バーンダウンチャート用データの生成

```python
from redmine_burndown import BurndownAnalyzer

# 分析実行（output/ディレクトリのCSVファイルを読み込む）
analyzer = BurndownAnalyzer('output/issues.csv')

# サマリー表示
analyzer.print_summary()

# バーンダウン用CSV作成（output/ディレクトリに保存）
analyzer.create_burndown_csv('burndown_weekly.csv', output_dir='output')

# ステータス別サマリーCSV作成（output/ディレクトリに保存）
analyzer.create_status_summary_csv('status_summary_weekly.csv', output_dir='output')
```

#### 3. Excelワークブック生成

```python
from redmine_burndown.excel_generator import ExcelGenerator

# Excelジェネレーター初期化
generator = ExcelGenerator()

# テンプレート作成（初回のみ）
generator.create_template()

# CSVデータをExcelにインポート
generator.copy_csv_to_excel(
csv_path='output/redmine_issues_20251127_100000.csv',
output_path='output/burndown_workbook.xlsx',
sheet_name='RAW'
)
```

- 生成されるExcelワークブックの特徴
    - 自動計算列: 完了フラグ、週番号、年-週、残作業量が自動計算
    - 数式埋め込み: Excel関数で動的に集計（COUNTIFS、SUMIFS等）
    - 4シート構成: RAW、週次バーンダウン、月次CFD、ダッシュボード
    - スタイル設定済み: ヘッダーの色、罫線、列幅が最適化
    - BOM付きUTF-8: 日本語が文字化けしない（macOS Excelでも対応）

## ️ プロジェクト構造

```text
redmine-burndown/
├── src/
│ └── redmine_burndown/
│ ├── __init__.py
│ ├── redmine_client.py # Redmine APIクライアント
│ └── burndown_analyzer.py # バーンダウンチャート分析
├── tests/
│ ├── conftest.py # pytestフィクスチャ
│ ├── test_redmine_client.py # redmine_clientのテスト（33テスト）
│ ├── test_burndown_analyzer.py # burndown_analyzerのテスト（28テスト）
│ ├── test_env_config.py # 環境変数設定のテスト（6テスト）
│ ├── test_env_validation.py # 環境変数検証のテスト（4テスト）
│ ├── test_env_variables.py # 環境変数機能のテスト（8テスト）
│ ├── test_custom_fields.py # カスタムフィールドのテスト（10テスト）
│ └── test_excel_generator.py # Excel生成のテスト（19テスト）
├── templates/ # Excelテンプレート
│ └── burndown_template.xlsx # 自動生成されるテンプレート
├── output/ # 生成されるCSVファイル・Excelファイルの出力先
│ ├── redmine_issues_*.csv # 取得した生データ
│ ├── burndown_weekly.csv # バーンダウン用データ
│ ├── status_summary_weekly.csv # ステータス別サマリー
│ └── burndown_workbook.xlsx # 完全なExcelワークブック
├── .env.example # 環境変数設定のサンプル
├── .env # 環境変数設定（Git管理外）
├── pyproject.toml # プロジェクト設定
├── .pre-commit-config.yaml # pre-commit設定
└── README.md
```

## 出力データの詳細

### burndown_weekly.csv の列説明

| 列名 | 説明 | 用途 |
|------|------|------|
| 週番号 | ISO週番号（YYYY-WW形式） | X軸 |
| 完了チケット数（累積） | その週までに完了したチケット数 | 進捗確認 |
| 残チケット数 | 未完了のチケット数 | **バーンダウン実績線** |
| 完了工数（累積） | 完了した工数の合計 | 進捗確認（工数ベース） |
| 残工数 | 未完了の工数 | **バーンダウン実績線（工数）** |
| 理想残チケット数 | 線形に減少した場合の残数 | **理想線** |
| 理想残工数 | 線形に減少した場合の残工数 | **理想線（工数）** |

### status_summary_weekly.csv の列説明

週ごとのステータス別内訳を表示。積み上げグラフで可視化すると効果的です

## Excel/Google Spreadsheetでのグラフ作成

### A. 基本的なバーンダウンチャート

使用データ: `output/burndown_weekly.csv`

1. データ選択
   - A列（週番号）
   - C列（残チケット数）
   - F列（理想残チケット数）
2. グラフ作成
   - Excel: 「挿入」→「折れ線グラフ」→「マーカー付き折れ線」
   - Google Spreadsheet: 「挿入」→「グラフ」→「折れ線グラフ」
3. 書式設定
   - タイトル: 「プロジェクト進捗 - バーンダウンチャート」
   - X軸: 「週番号」
   - Y軸: 「残チケット数」
   - 実績線: 青色・太線
   - 理想線: 灰色・点線

### B. 工数ベースのバーンダウンチャート

同じ手順でD列（残工数）とG列（理想残工数）を使用

### C. ステータス別推移グラフ（積み上げ面グラフ）

使用データ: `output/status_summary_weekly.csv`

1. 全データを選択
2. 「積み上げ面グラフ」を選択
3. 各ステータスが色分けされた推移が表示される

## 週次運用フロー

### 毎週月曜日の作業（約5分）

```bash
# 1. 最新データを取得
uv run python -m redmine_burndown.redmine_client

# 2. バーンダウンデータを生成
uv run python -m redmine_burndown.burndown_analyzer

# 3. ExcelまたはGoogle Spreadsheetで確認
# output/burndown_weekly.csv を開いてグラフ更新
```

### 効率化のヒント

- 方法1: ワンライナーで実行

```bash
uv run python -m redmine_burndown.redmine_client && uv run python -m redmine_burndown.burndown_analyzer
```

- 方法2: シェルスクリプト化

```bash
# プロジェクトに同梱の update_burndown.sh を使用
./update_burndown.sh
```

このスクリプトは以下を自動で実行します：

- `.env`ファイルの存在確認（未設定時はエラーで即座停止）
- エラー時の即座停止（`set -euo pipefail`）
- チケットデータ取得
- バーンダウンデータ生成
- 詳細な進捗表示と成功/失敗の明確な通知

## 設定

### API キーの取得方法

1. Redmineにログイン
2. 右上のアカウント名 → 「個人設定」
3. 「APIアクセスキー」セクションで「表示」をクリック
4. 表示されたキーをコピー

### 環境変数の詳細設定

`.env`ファイルで以下の環境変数を設定できます

```bash
# 必須設定
REDMINE_URL=https://your-redmine.example.com
REDMINE_API_KEY=your_api_key_here

# オプション設定（空の場合はデフォルト動作）
REDMINE_PROJECT_ID= # プロジェクトID（空=全プロジェクト）
REDMINE_MAX_ISSUES= # 取得件数上限（空=全件取得）
REDMINE_STATUS_ID= # ステータスフィルター（空=全ステータス）
```

環境変数の動作。

| 環境変数 | 空の場合 | 設定例 | 説明 |
|---------|---------|--------|------|
| `REDMINE_PROJECT_ID` | 全プロジェクト | `598` または `598,631,728` | 特定プロジェクトまたは複数プロジェクト |
| `REDMINE_MAX_ISSUES` | **全件取得** | `500` | 最大500件まで取得 |
| `REDMINE_STATUS_ID` | 全ステータス | `open`, `closed`, `*`, `1,2,3` | ステータスフィルター |

### 詳細設定

#### 1. 取得件数の変更

環境変数で設定可能（空の場合は全件取得）

```bash
# .envファイルに追加
REDMINE_URL=https://your-redmine.example.com
REDMINE_API_KEY=your_api_key_here

# 全件取得（デフォルト）
REDMINE_MAX_ISSUES=

# または件数制限を設定
REDMINE_MAX_ISSUES=500 # 500件まで取得
```

- 動作仕様
    - `REDMINE_MAX_ISSUES`が空（未設定）の場合 → 全件取得
    - `REDMINE_MAX_ISSUES=500`の場合 → 最大500件まで取得
    - 取得件数が100件を超える場合は自動的にページネーションを実行

#### 2. 特定プロジェクトのみ取得

環境変数で指定（空の場合は全プロジェクト）

```bash
# .envファイルに追加

# 全プロジェクト（デフォルト）
REDMINE_PROJECT_ID=

# 特定プロジェクトのみ
REDMINE_PROJECT_ID=598

# 複数プロジェクト（カンマ区切り）
REDMINE_PROJECT_ID=598,631,728
```

#### 3. ステータスフィルター

環境変数でステータスを指定（空の場合は全ステータス）

```bash
# .envファイルに追加

# 全ステータス（デフォルト）
REDMINE_STATUS_ID=

# オープンのみ
REDMINE_STATUS_ID=open

# 完了のみ
REDMINE_STATUS_ID=closed

# 複数ステータスID（カンマ区切り）
REDMINE_STATUS_ID=1,2,3

# 全て（明示的に指定）
REDMINE_STATUS_ID=*
```

## 分析のポイント

### 1. 実績線が理想線より上にある

→ 遅延している = 対策が必要

- 確認すべきこと
    - ブロッカーとなっているチケットはあるか？
    - リソース不足か？
    - 見積もりが甘かったか？

### 2. 実績線が急激に変化

→ スコープ変更または大量処理

- 確認すべきこと
    - 新規チケットが大量追加されたか？
    - まとめてクローズしたか？

### 3. 実績線が横ばい

→ 作業が停滞

- 確認すべきこと
    - 担当者のアサインは適切か？
    - 技術的な問題で詰まっていないか？

## 開発

### テストの実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=src/redmine_burndown --cov-report=html

# 特定のテストのみ
uv run pytest tests/test_redmine_client.py -v
```

### コード品質チェック

```bash
# Ruffによるlintチェック
uv run ruff check .

# Ruffによる自動修正
uv run ruff check . --fix

# Ruffフォーマット
uv run ruff format .

# mypyによる型チェック
uv run mypy src/

# pre-commitフックのインストール
uv run pre-commit install

# 全ファイルに対してpre-commitを実行
uv run pre-commit run --all-files
```

### 依存関係の管理

```bash
# パッケージの追加
uv add requests

# 開発用パッケージの追加
uv add --dev pytest pytest-cov

# パッケージの削除
uv remove package-name

# 依存関係の更新
uv lock --upgrade
```

## トラブルシューティング

### Q1: "Connection Error" が出る

- 原因: ネットワークまたはAPI設定の問題
- 対処法
    1. RedmineのURLが正しいか確認
    2. APIキーが有効か確認（Redmine個人設定で再生成）
    3. REST APIが有効になっているか確認
    4. VPN接続が必要な場合は接続を確認

### Q2: 取得件数が0件

- 原因: アクセス権限の問題
- 対処法
    1. Redmineにログインしてチケットが閲覧できるか確認
    2. 使用しているAPIキーのユーザーに権限があるか確認
    3. プライベートプロジェクトの場合はメンバーに追加されているか確認

### Q3: 文字化けする

- 原因: エンコーディングの不一致
- 対処法
    - Excelで開く際に以下を実行する
        1. 「データ」→「テキストから」でインポート
        2. エンコーディングを「UTF-8」に設定

### Q4: 週番号がずれる

- 原因: ISO週番号とExcelの週番号の違い
- 対処法
    - そのまま使用（ISO週番号が国際標準）
    - または `burndown_analyzer.py` で週番号計算を変更

### Q5: 工数が0になる

- 原因: Redmineで予定工数が入力されていない
- 対処法
    - チケットに予定工数を入力する
    - または「チケット数」ベースのバーンダウンを使用

## ️ 技術スタック

### コア技術

- Python 3.11+: 最新のPython機能を活用
- requests: HTTP通信ライブラリ
- openpyxl: Excel（.xlsx）ファイルの読み書き

### 開発ツール

- uv: 超高速Pythonパッケージマネージャー
- ruff: Rust製の高速Linter/Formatter
- mypy: 静的型チェッカー
- python-dotenv: 環境変数管理
- pytest: テストフレームワーク
- pytest-cov: カバレッジ測定
- pytest-mock: モックサポート
- pre-commit: Gitフック管理

### 品質管理

- 型安全: 全関数に型アノテーション
- strict型チェック: mypyのstrict mode有効
- 高カバレッジ: 95.62%のテストカバレッジ（87テスト）
- 自動フォーマット: ruffによる統一的なコードスタイル
- CI/CD対応: pre-commitによる自動チェック

## 設定ファイル

### pyproject.toml

プロジェクトの中核設定ファイル。

- パッケージメタデータ
- 依存関係管理
- ruff設定（Linter/Formatter）
- mypy設定（型チェック）
- pytest設定（テスト）
- coverage設定（カバレッジ）

### .pre-commit-config.yaml

- Git commit時の自動チェック
    - ruffによるlintチェック＆フォーマット
    - mypyによる型チェック
    - 標準的なチェック（trailing whitespace等）

## パフォーマンス

### uvによる高速化

- 従来のpipやpoetryと比較して、uvは以下のような性能を発揮します
    - パッケージインストール: 最大10-100倍高速
    - 依存関係解決: 数秒で完了
    - 仮想環境作成: ほぼ瞬時

### ruffによる高速Lint

- blackやflake8と比較して以下が利点です
    - Lintチェック: 最大100倍高速
    - 自動修正: 数ミリ秒で完了
    - 統合: Linter + Formatter一体化

### コーディング規約

- PEP 8準拠（ruffでチェック）
- 型アノテーション必須
- Docstring必須（Google Style）
- テストカバレッジ95%以上維持

## 謝辞

このプロジェクトは以下のオープンソースツールを活用しています。

- [uv](https://github.com/astral-sh/uv) by Astral
- [ruff](https://github.com/astral-sh/ruff) by Astral
- [mypy](https://github.com/python/mypy) by Python
- [pytest](https://github.com/pytest-dev/pytest) by pytest-dev

## 参考リンク

- [uv公式ドキュメント](https://github.com/astral-sh/uv)
- [Ruff公式ドキュメント](https://docs.astral.sh/ruff/)
- [mypy公式ドキュメント](https://mypy.readthedocs.io/)
- [Redmine REST API](https://www.redmine.org/projects/redmine/wiki/Rest_api)
- [uvとRuffで実現する高速で堅牢なPython開発環境の構築](https://zenn.dev/okamyuji/articles/uv-practical-guide)
