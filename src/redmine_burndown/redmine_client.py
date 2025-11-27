#!/usr/bin/env python3
"""Redmine API クライアント - シンプルなチケット取得ツール."""

from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)

# 日本時間（JST）のタイムゾーン
JST = timezone(timedelta(hours=9))


class RedmineClient:
    """Redmine API クライアント."""

    def __init__(self, base_url: str, api_key: str) -> None:
        """初期化.

        Args:
            base_url: RedmineのベースURL（例: https://redmine.example.com）
            api_key: Redmine APIキー
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-Redmine-API-Key": api_key, "Content-Type": "application/json"}

    def get_issues(
        self,
        project_id: str | None = None,
        status_id: str = "*",
        limit: int = 100,
        offset: int = 0,
        include_custom_fields: bool = True,
    ) -> dict[str, Any]:
        """チケット一覧を取得.

        Args:
            project_id: プロジェクトID（Noneの場合は全プロジェクト）
            status_id: ステータスID（'*'で全ステータス）
            limit: 取得件数上限
            offset: オフセット
            include_custom_fields: カスタムフィールドを含めるかどうか

        Returns:
            APIレスポンス（辞書形式）
        """
        url = f"{self.base_url}/issues.json"

        params: dict[str, str | int] = {
            "status_id": status_id,
            "limit": limit,
            "offset": offset,
        }

        if project_id:
            params["project_id"] = project_id

        # カスタムフィールドを含める
        if include_custom_fields:
            params["include"] = "custom_fields"

        try:
            response = requests.get(url, headers=self.headers, params=params, verify=True, timeout=30)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                msg = "API response is not a dictionary"
                raise TypeError(msg)
            return result
        except requests.exceptions.RequestException as e:
            logger.error("チケット取得エラー: %s", e)
            return {"issues": [], "total_count": 0}

    def get_all_issues(
        self,
        project_id: str | None = None,
        status_id: str = "*",
        max_issues: int = 1000,
    ) -> list[dict[str, Any]]:
        """全チケットを取得（ページネーション対応）.

        Args:
            project_id: プロジェクトID
            status_id: ステータスID
            max_issues: 最大取得件数

        Returns:
            チケットのリスト
        """
        all_issues: list[dict[str, Any]] = []
        limit = 100
        offset = 0

        logger.info("チケット取得開始（max_issues=%s）", max_issues)

        while len(all_issues) < max_issues:
            logger.debug("取得中... (オフセット: %d)", offset)
            data = self.get_issues(project_id, status_id, limit, offset)

            issues = data.get("issues", [])
            if not issues:
                break

            all_issues.extend(issues)

            total_count = data.get("total_count", 0)
            if not isinstance(total_count, int):
                total_count = 0
            if len(all_issues) >= total_count or len(all_issues) >= max_issues:
                break

            offset += limit

        result = all_issues[:max_issues]
        logger.info("チケット取得完了: %d件", len(result))
        return result

    def get_projects(self) -> list[dict[str, Any]]:
        """プロジェクト一覧を取得.

        Returns:
            プロジェクトのリスト
        """
        url = f"{self.base_url}/projects.json"

        try:
            response = requests.get(url, headers=self.headers, verify=True, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                msg = "API response is not a dictionary"
                raise TypeError(msg)
            projects = data.get("projects", [])
            if not isinstance(projects, list):
                return []
            logger.info("プロジェクト取得完了: %d件", len(projects))
            return projects
        except requests.exceptions.RequestException as e:
            logger.error("プロジェクト取得エラー: %s", e)
            return []

    @staticmethod
    def _convert_to_jst(datetime_str: str) -> str:
        """ISO8601形式の日時文字列をJSTに変換.

        Args:
            datetime_str: ISO8601形式の日時文字列（例: "2024-01-01T10:00:00Z"）

        Returns:
            JST形式の日時文字列（例: "2024-01-01 19:00:00 JST"）

        """
        if not datetime_str:
            return ""
        try:
            # ISO8601形式をパース
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            # JSTに変換
            dt_jst = dt.astimezone(JST)
            # 読みやすい形式で返す
            return dt_jst.strftime("%Y-%m-%d %H:%M:%S JST")
        except (ValueError, AttributeError):
            # パースに失敗した場合は元の値を返す
            return datetime_str

    def _extract_custom_fields(self, issues: list[dict[str, Any]]) -> set[str]:
        """全チケットからカスタムフィールド名を抽出.

        Args:
            issues: チケットのリスト

        Returns:
            カスタムフィールド名のセット
        """
        custom_field_names: set[str] = set()
        for issue in issues:
            custom_fields = issue.get("custom_fields", [])
            if isinstance(custom_fields, list):
                for field in custom_fields:
                    if isinstance(field, dict) and "name" in field:
                        custom_field_names.add(field["name"])
        return custom_field_names

    def _get_custom_field_value(self, issue: dict[str, Any], field_name: str) -> str:
        """チケットから指定されたカスタムフィールドの値を取得.

        Args:
            issue: チケット情報
            field_name: カスタムフィールド名

        Returns:
            カスタムフィールドの値（見つからない場合は空文字列）
        """
        custom_fields = issue.get("custom_fields", [])
        if isinstance(custom_fields, list):
            for field in custom_fields:
                if isinstance(field, dict) and field.get("name") == field_name:
                    value = field.get("value", "")
                    # 値がリストの場合は、カンマ区切りで結合
                    if isinstance(value, list):
                        return ", ".join(str(v) for v in value)
                    return str(value) if value is not None else ""
        return ""

    def export_to_csv(self, issues: list[dict[str, Any]], filename: str = "issues.csv", output_dir: str = "output") -> None:
        """チケットをCSVファイルにエクスポート（BOM付きUTF-8、日時はJST、カスタムフィールド対応）.

        Args:
            issues: チケットのリスト
            filename: 出力ファイル名
            output_dir: 出力ディレクトリ（デフォルト: output）
        """
        if not issues:
            logger.warning("エクスポートするチケットがありません")
            return

        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.debug("出力ディレクトリ作成: %s", output_path)

        # 完全なファイルパス
        full_path = output_path / filename

        # 標準フィールド
        standard_fieldnames = [
            "id",
            "project",
            "tracker",
            "status",
            "priority",
            "subject",
            "author",
            "assigned_to",
            "category",
            "created_on",
            "updated_on",
            "start_date",
            "due_date",
            "done_ratio",
            "estimated_hours",
            "spent_hours",
        ]

        # カスタムフィールド名を抽出（ソート済み）
        custom_field_names = sorted(self._extract_custom_fields(issues))

        # 全フィールド名を結合
        fieldnames = standard_fieldnames + custom_field_names

        logger.info("カスタムフィールド数: %d", len(custom_field_names))
        if custom_field_names:
            logger.debug("カスタムフィールド名: %s", ", ".join(custom_field_names))

        # BOM付きUTF-8で書き込み（Excelで文字化けしない）
        with full_path.open("w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for issue in issues:
                # 標準フィールド
                row: dict[str, Any] = {
                    "id": issue.get("id"),
                    "project": issue.get("project", {}).get("name", ""),
                    "tracker": issue.get("tracker", {}).get("name", ""),
                    "status": issue.get("status", {}).get("name", ""),
                    "priority": issue.get("priority", {}).get("name", ""),
                    "subject": issue.get("subject", ""),
                    "author": issue.get("author", {}).get("name", ""),
                    "assigned_to": issue.get("assigned_to", {}).get("name", ""),
                    "category": issue.get("category", {}).get("name", ""),
                    "created_on": self._convert_to_jst(issue.get("created_on", "")),
                    "updated_on": self._convert_to_jst(issue.get("updated_on", "")),
                    "start_date": issue.get("start_date", ""),
                    "due_date": issue.get("due_date", ""),
                    "done_ratio": issue.get("done_ratio", 0),
                    "estimated_hours": issue.get("estimated_hours", ""),
                    "spent_hours": issue.get("spent_hours", ""),
                }

                # カスタムフィールドを追加
                for field_name in custom_field_names:
                    row[field_name] = self._get_custom_field_value(issue, field_name)

                writer.writerow(row)

        logger.info("CSVファイルに出力しました: %s（%d件、%d列）", full_path, len(issues), len(fieldnames))


def main() -> None:
    """メイン処理."""
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 環境変数を読み込み
    load_dotenv()

    # Redmine接続情報を環境変数から取得
    redmine_url = os.getenv("REDMINE_URL")
    api_key = os.getenv("REDMINE_API_KEY")

    if not redmine_url or not api_key:
        logger.error("環境変数が設定されていません")
        logger.error("REDMINE_URL と REDMINE_API_KEY を .env ファイルに設定してください")
        logger.info("サンプル: .env.example を参照")
        sys.exit(1)

    # オプション設定を環境変数から取得
    project_id = os.getenv("REDMINE_PROJECT_ID", "").strip()
    max_issues_str = os.getenv("REDMINE_MAX_ISSUES", "").strip()
    status_id = os.getenv("REDMINE_STATUS_ID", "").strip() or "*"

    # 取得件数の決定（空なら全件取得）
    max_issues = int(max_issues_str) if max_issues_str else None

    logger.info("=" * 60)
    logger.info("Redmine チケット取得ツール")
    logger.info("=" * 60)
    logger.info("設定:")
    logger.info("  プロジェクトID: %s", project_id if project_id else "全プロジェクト")
    logger.info("  取得件数上限: %s", max_issues if max_issues else "全件")
    logger.info("  ステータス: %s", status_id)

    # クライアント初期化
    client = RedmineClient(redmine_url, api_key)

    # まずプロジェクト一覧を取得
    logger.info("【1】プロジェクト一覧を取得中...")
    projects = client.get_projects()

    if projects:
        logger.info("プロジェクト数: %d件", len(projects))
        for i, project in enumerate(projects[:10], 1):  # 最初の10件のみ表示
            logger.info("  %d. %s (ID: %s)", i, project.get("name"), project.get("id"))
        if len(projects) > 10:
            logger.info("  ... 他 %d件", len(projects) - 10)
    else:
        logger.warning("プロジェクトが取得できませんでした")

    # チケット一覧を取得
    logger.info("【2】チケット一覧を取得中...")

    if max_issues:
        # 件数制限あり
        issues_data = client.get_issues(
            project_id=project_id if project_id else None,
            status_id=status_id,
            limit=min(max_issues, 100),  # APIの1回の上限は100件
        )
        total_count = issues_data.get("total_count", 0)
        issues = issues_data.get("issues", [])

        # max_issuesを超えないように、必要に応じてページネーション
        if len(issues) < max_issues and len(issues) < total_count:
            all_issues = client.get_all_issues(
                project_id=project_id if project_id else None,
                status_id=status_id,
                max_issues=max_issues,
            )
            issues = all_issues
    else:
        # 全件取得
        all_issues = client.get_all_issues(
            project_id=project_id if project_id else None,
            status_id=status_id,
            max_issues=10000,  # 安全のための上限
        )
        issues = all_issues
        total_count = len(issues)

    logger.info("総チケット数: %d件", total_count)
    logger.info("取得件数: %d件", len(issues))

    if issues:
        # 最初の5件を表示
        logger.info("【3】チケットサンプル（最初の5件）")
        for issue in issues[:5]:
            logger.info("チケット #%s", issue.get("id"))
            logger.info("  題名: %s", issue.get("subject"))
            logger.info("  ステータス: %s", issue.get("status", {}).get("name"))
            logger.info("  優先度: %s", issue.get("priority", {}).get("name"))
            logger.info("  担当者: %s", issue.get("assigned_to", {}).get("name", "未割当"))
            logger.info("  進捗率: %d%%", issue.get("done_ratio", 0))
            logger.info("  作成日: %s", issue.get("created_on", ""))
            logger.info("  更新日: %s", issue.get("updated_on", ""))

        # CSVエクスポート
        logger.info("【4】CSVファイルにエクスポート中...")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        csv_filename = f"redmine_issues_{timestamp}.csv"
        client.export_to_csv(issues, csv_filename, output_dir="output")

        logger.info("=" * 60)
        logger.info("処理が完了しました！")
        logger.info("=" * 60)
    else:
        logger.warning("チケットが取得できませんでした")


if __name__ == "__main__":
    main()

