#!/bin/bash
set -euo pipefail  # エラー時に即座に終了

# スクリプトのディレクトリに移動
cd "$(dirname "$0")" || exit 1

# .envファイルの存在確認
if [ ! -f .env ]; then
    echo "❌ エラー: .env ファイルが見つかりません"
    echo ""
    echo "以下のコマンドで .env ファイルを作成してください:"
    echo "  cp .env.example .env"
    echo ""
    echo "その後、.env ファイルを編集して実際のRedmine情報を設定してください"
    exit 1
fi

echo "========================================="
echo "📊 バーンダウンデータ更新開始"
echo "========================================="
echo ""

# チケットデータを取得
echo "1️⃣  Redmineからチケットデータを取得中..."
if ! uv run python -m redmine_burndown.redmine_client; then
    echo "❌ チケット取得に失敗しました"
    exit 1
fi
echo "✅ チケットデータ取得完了"
echo ""

# バーンダウンデータを生成
echo "2️⃣  バーンダウンデータを生成中..."
if ! uv run python -m redmine_burndown.burndown_analyzer; then
    echo "❌ バーンダウンデータ生成に失敗しました"
    exit 1
fi
echo "✅ バーンダウンデータ生成完了"
echo ""

# Excelワークブックを生成
echo "3️⃣  Excelワークブックを生成中..."
if ! uv run python -c "
from redmine_burndown.excel_generator import ExcelGenerator
from pathlib import Path
import glob

# 最新のCSVファイルを検索
csv_files = sorted(glob.glob('output/redmine_issues_*.csv'))
if csv_files:
    latest_csv = csv_files[-1]
    generator = ExcelGenerator()
    
    # テンプレートが存在しない場合は作成
    if not Path('templates/burndown_template.xlsx').exists():
        print('📄 Excelテンプレートを作成中...')
        generator.create_template()
    
    # CSVデータをExcelにインポート
    generator.copy_csv_to_excel(latest_csv, 'output/burndown_workbook.xlsx')
    print(f'✅ Excelワークブック生成完了: output/burndown_workbook.xlsx')
else:
    print('⚠️  CSVファイルが見つかりません')
    exit(1)
"; then
    echo "❌ Excelワークブック生成に失敗しました"
    exit 1
fi
echo "✅ Excelワークブック生成完了"
echo ""

echo "========================================="
echo "🎉 バーンダウンデータ更新完了！"
echo "========================================="
echo ""
echo "📁 出力ファイル:"
echo "  - output/redmine_issues_*.csv"
echo "  - output/burndown_weekly.csv"
echo "  - output/status_summary_weekly.csv"
echo "  - output/burndown_workbook.xlsx"
echo ""
echo "💡 次のステップ:"
echo "  1. output/burndown_workbook.xlsx をExcelで開く"
echo "  2. 「週次バーンダウン」シートでグラフを作成"
echo "  3. 「ダッシュボード」シートでKPIを確認"
echo ""
