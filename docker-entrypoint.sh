#!/usr/bin/env bash
set -euo pipefail

# ========================================
# Docker Entrypoint for Redmine Burndown Chart Tool
# ========================================

echo "========================================="
echo "🐳 Redmine Burndown Chart Tool (Docker)"
echo "========================================="
echo ""

# .envファイルの存在確認
if [ ! -f .env ]; then
    echo "❌ エラー: .env ファイルが見つかりません"
    echo ""
    echo "Dockerで実行する場合、以下の方法で環境変数を設定してください:"
    echo ""
    echo "方法1: .envファイルをマウント"
    echo "  docker run -v \$(pwd)/.env:/app/.env -v \$(pwd)/output:/app/output redmine-burndown"
    echo ""
    echo "方法2: 環境変数を直接指定"
    echo "  docker run -e REDMINE_URL=<url> -e REDMINE_API_KEY=<key> -v \$(pwd)/output:/app/output redmine-burndown"
    echo ""
    echo "方法3: docker-composeを使用"
    echo "  docker compose up"
    echo ""
    exit 1
fi

# REDMINE_URLとREDMINE_API_KEYの存在確認
if [ -z "${REDMINE_URL:-}" ] || [ -z "${REDMINE_API_KEY:-}" ]; then
    echo "⚠️  警告: 環境変数が設定されていません"
    echo ""
    echo "REDMINE_URL と REDMINE_API_KEY を設定してください"
    echo ""
    
    # .envファイルがある場合は読み込む
    if [ -f .env ]; then
        echo "📄 .env ファイルから環境変数を読み込みます..."
        # shellcheck disable=SC2046
        export $(grep -v '^#' .env | xargs)
    fi
fi

# 環境変数の確認（セキュリティのため値は表示しない）
if [ -n "${REDMINE_URL:-}" ]; then
    echo "✅ REDMINE_URL: 設定済み"
else
    echo "❌ REDMINE_URL: 未設定"
fi

if [ -n "${REDMINE_API_KEY:-}" ]; then
    echo "✅ REDMINE_API_KEY: 設定済み"
else
    echo "❌ REDMINE_API_KEY: 未設定"
fi

echo ""
echo "📁 出力ディレクトリ: /app/output"
echo ""

# 出力ディレクトリの権限を確認
if [ ! -w /app/output ]; then
    echo "⚠️  警告: /app/output に書き込み権限がありません"
    echo "   ボリュームマウントの権限を確認してください"
fi

echo "========================================="
echo "🚀 処理を開始します"
echo "========================================="
echo ""

# 渡されたコマンドを実行
exec "$@"

