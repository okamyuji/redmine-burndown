#!/bin/bash
set -euo pipefail

# ========================================
# バーンダウンデータ更新スクリプト（Docker版）
# ========================================

echo "========================================="
echo "📊 バーンダウンデータ更新開始"
echo "========================================="
echo ""

# 1. Redmineからチケットデータを取得
echo "1️⃣  Redmineからチケットデータを取得中..."
if ! python -m redmine_burndown.redmine_client; then
    echo "❌ チケット取得に失敗しました"
    exit 1
fi
echo "✅ チケット取得完了"
echo ""

# 2. バーンダウンデータを生成
echo "2️⃣  バーンダウンデータを生成中..."
if ! python -m redmine_burndown.burndown_analyzer; then
    echo "❌ バーンダウンデータ生成に失敗しました"
    exit 1
fi
echo "✅ バーンダウンデータ生成完了"
echo ""

# 3. Excelワークブックを生成
echo "3️⃣  Excelワークブックを生成中..."
if ! python -c "
from redmine_burndown.excel_generator import ExcelGenerator
import glob
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

csv_files = sorted(glob.glob(os.path.join(output_dir, 'redmine_issues_*.csv')))
if not csv_files:
    logger.error('❌ CSVファイルが見つかりません。Redmineからチケットデータを取得してください。')
    exit(1)

latest_csv = csv_files[-1]
output_excel_path = os.path.join(output_dir, 'burndown_workbook.xlsx')
template_path = os.path.join(output_dir, 'burndown_template.xlsx')

logger.info('📄 Excelテンプレートを作成中...')
generator = ExcelGenerator(template_path=template_path)
if not os.path.exists(template_path):
    generator.create_template()

logger.info('📊 CSVデータをExcelにインポート中: %s -> %s', latest_csv, output_excel_path)
generator.copy_csv_to_excel(latest_csv, output_excel_path)
logger.info('✅ Excelワークブック生成完了: %s', output_excel_path)
"; then
    echo "❌ Excelワークブック生成に失敗しました"
    exit 1
fi
echo "✅ Excelワークブック生成完了"
echo ""

# 完了メッセージ
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

