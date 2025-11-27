#!/usr/bin/env python3
"""バーンダウンチャート用データ整形ツール.

CSVデータを週次で集計してバーンダウンチャート用のデータを作成
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ロガーの設定
logger = logging.getLogger(__name__)

# 日本時間（JST）のタイムゾーン
JST = timezone(timedelta(hours=9))


class BurndownAnalyzer:
    """バーンダウンチャート用データ分析."""

    def __init__(self, csv_filename: str) -> None:
        """初期化.

        Args:
            csv_filename: 入力CSVファイル名
        """
        self.csv_filename = csv_filename
        self.issues: list[dict[str, str]] = []
        self.load_csv()

    def load_csv(self) -> None:
        """CSVファイルを読み込み（BOM付きUTF-8対応）."""
        try:
            # BOM付きUTF-8にも対応
            with Path(self.csv_filename).open(encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.issues = list(reader)
            logger.info("CSVファイルを読み込みました: %d件", len(self.issues))
        except FileNotFoundError:
            logger.warning("ファイルが見つかりません: %s", self.csv_filename)
            self.issues = []

    def get_week_number(self, date_str: str) -> str:
        """日付文字列から週番号を取得.

        Args:
            date_str: 日付文字列（ISO形式 or "YYYY-MM-DD HH:MM:SS JST" 形式）

        Returns:
            'YYYY-WW' 形式の週番号
        """
        if not date_str:
            return ""

        try:
            # JST形式の場合（例: "2025-11-26 14:07:43 JST"）
            if " JST" in date_str:
                date_part = date_str.replace(" JST", "").strip()
                date = datetime.strptime(date_part, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
            # ISO形式の日付をパース（タイムゾーン付き）
            elif "T" in date_str:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # 日付のみ（YYYY-MM-DD）
            else:
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)

            # ISO週番号を取得
            iso_calendar = date.isocalendar()
            return f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
        except (ValueError, AttributeError) as e:
            logger.debug("日付パースエラー: %s (%s)", date_str, e)
            return ""

    def analyze_weekly_progress(self) -> dict[str, dict[str, Any]]:
        """週次進捗を分析.

        Returns:
            週ごとの集計データ
        """
        weekly_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_issues": 0,
                "closed_issues": 0,
                "total_estimated_hours": 0.0,
                "closed_estimated_hours": 0.0,
                "issues_detail": [],
            }
        )

        # 全チケットを集計
        for issue in self.issues:
            # 更新日で週番号を取得
            week = self.get_week_number(issue.get("updated_on", ""))
            if not week:
                week = self.get_week_number(issue.get("created_on", ""))

            if not week:
                continue

            # 予定工数
            estimated_hours = 0.0
            try:
                if issue.get("estimated_hours"):
                    estimated_hours = float(issue["estimated_hours"])
            except ValueError:
                pass

            # 進捗率
            done_ratio = 0
            try:
                if issue.get("done_ratio"):
                    done_ratio = int(issue["done_ratio"])
            except ValueError:
                pass

            # ステータス
            status = issue.get("status", "")
            is_closed = status in {"終了", "完了", "Closed", "Resolved"}

            # 集計
            weekly_data[week]["total_issues"] += 1
            weekly_data[week]["total_estimated_hours"] += estimated_hours

            if is_closed or done_ratio == 100:
                weekly_data[week]["closed_issues"] += 1
                weekly_data[week]["closed_estimated_hours"] += estimated_hours

            # 詳細情報を保存
            weekly_data[week]["issues_detail"].append({
                "id": issue.get("id"),
                "subject": issue.get("subject"),
                "status": status,
                "done_ratio": done_ratio,
                "estimated_hours": estimated_hours,
            })

        return dict(weekly_data)

    def create_burndown_csv(self, output_filename: str = "burndown_weekly.csv", output_dir: str = "output") -> None:
        """バーンダウンチャート用CSVを作成（累積形式）.

        Args:
            output_filename: 出力ファイル名
            output_dir: 出力ディレクトリ（デフォルト: output）
        """
        weekly_data = self.analyze_weekly_progress()

        if not weekly_data:
            logger.warning("集計データがありません")
            return

        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 完全なファイルパス
        full_path = output_path / output_filename

        # 週を時系列でソート
        weeks = sorted(weekly_data.keys())

        # 累積データを計算
        cumulative_closed_issues = 0
        cumulative_closed_hours = 0.0

        # 初期値（最初の週の総数）
        total_issues = sum(data["total_issues"] for data in weekly_data.values())
        total_hours = sum(data["total_estimated_hours"] for data in weekly_data.values())

        # BOM付きUTF-8で書き込み（Excelで文字化けしない）
        with full_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                "週番号",
                "完了チケット数（累積）",
                "残チケット数",
                "完了工数（累積）",
                "残工数",
                "理想残チケット数",
                "理想残工数",
            ])

            # データ行
            for i, week in enumerate(weeks):
                data = weekly_data[week]

                # 累積計算
                cumulative_closed_issues += data["closed_issues"]
                cumulative_closed_hours += data["closed_estimated_hours"]

                # 残数計算
                remaining_issues = total_issues - cumulative_closed_issues
                remaining_hours = total_hours - cumulative_closed_hours

                # 理想線計算（線形減少）
                progress_ratio = (i + 1) / len(weeks)
                ideal_remaining_issues = total_issues * (1 - progress_ratio)
                ideal_remaining_hours = total_hours * (1 - progress_ratio)

                writer.writerow([
                    week,
                    cumulative_closed_issues,
                    remaining_issues,
                    f"{cumulative_closed_hours:.2f}",
                    f"{remaining_hours:.2f}",
                    f"{ideal_remaining_issues:.1f}",
                    f"{ideal_remaining_hours:.1f}",
                ])

        logger.info("バーンダウン用CSVを作成しました: %s（集計週数: %d週、総チケット数: %d件、総工数: %.1f時間）", full_path, len(weeks), total_issues, total_hours)

    def create_status_summary_csv(self, output_filename: str = "status_summary_weekly.csv", output_dir: str = "output") -> None:
        """ステータス別の週次サマリーCSVを作成.

        Args:
            output_filename: 出力ファイル名
            output_dir: 出力ディレクトリ（デフォルト: output）
        """
        weekly_data = self.analyze_weekly_progress()

        if not weekly_data:
            logger.warning("集計データがありません")
            return

        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 完全なファイルパス
        full_path = output_path / output_filename

        weeks = sorted(weekly_data.keys())

        # ステータスごとに集計
        status_weekly: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for week in weeks:
            for issue in weekly_data[week]["issues_detail"]:
                status = issue["status"]
                status_weekly[week][status] += 1

        # 全ステータスを収集
        all_statuses_set: set[str] = set()
        for week_statuses in status_weekly.values():
            all_statuses_set.update(week_statuses.keys())
        all_statuses = sorted(all_statuses_set)

        # BOM付きUTF-8で書き込み（Excelで文字化けしない）
        with full_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # ヘッダー
            header = ["週番号", *all_statuses, "合計"]
            writer.writerow(header)

            # データ行
            for week in weeks:
                row: list[str | int] = [week]
                total = 0
                for status in all_statuses:
                    count = status_weekly[week].get(status, 0)
                    row.append(count)
                    total += count
                row.append(total)
                writer.writerow(row)

        logger.info("ステータス別サマリーCSVを作成しました: %s（ステータス種類: %d種類）", full_path, len(all_statuses))

    def print_summary(self) -> None:
        """サマリー情報を表示."""
        if not self.issues:
            logger.warning("データがありません")
            return

        logger.info("=" * 60)
        logger.info("【データサマリー】")
        logger.info("=" * 60)

        # 基本統計
        total = len(self.issues)
        logger.info("総チケット数: %d件", total)

        # ステータス別集計
        status_count: dict[str, int] = defaultdict(int)
        for issue in self.issues:
            status = issue.get("status", "不明")
            status_count[status] += 1

        logger.info("【ステータス別内訳】")
        for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
            percentage = (count / total) * 100
            logger.info("  %s: %d件 (%.1f%%)", status, count, percentage)

        # プロジェクト別集計
        project_count: dict[str, int] = defaultdict(int)
        for issue in self.issues:
            project = issue.get("project", "不明")
            project_count[project] += 1

        logger.info("【プロジェクト別内訳】")
        for project, count in sorted(project_count.items(), key=lambda x: -x[1])[:10]:
            percentage = (count / total) * 100
            logger.info("  %s: %d件 (%.1f%%)", project, count, percentage)

        # 工数統計
        total_estimated = 0.0
        estimated_count = 0
        for issue in self.issues:
            try:
                if issue.get("estimated_hours"):
                    hours = float(issue["estimated_hours"])
                    total_estimated += hours
                    estimated_count += 1
            except ValueError:
                pass

        if estimated_count > 0:
            logger.info("【工数統計】")
            logger.info("  工数入力済: %d件", estimated_count)
            logger.info("  総予定工数: %.1f時間", total_estimated)
            logger.info("  平均工数: %.1f時間/件", total_estimated / estimated_count)


def main() -> None:
    """メイン処理."""
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 60)
    logger.info("バーンダウンチャート用データ整形ツール")
    logger.info("=" * 60)

    # 最新のCSVファイルを探す（outputディレクトリ内）
    output_dir = Path("output")
    if not output_dir.exists():
        logger.warning("outputディレクトリが見つかりません")
        logger.info("  先に redmine_client.py を実行してください")
        return

    csv_files = [f for f in output_dir.iterdir() if f.name.startswith("redmine_issues_") and f.name.endswith(".csv")]

    if not csv_files:
        logger.warning("output/redmine_issues_*.csv ファイルが見つかりません")
        logger.info("  先に redmine_client.py を実行してください")
        return

    # 最新のファイルを使用
    latest_csv = sorted(csv_files)[-1]
    logger.info("使用するCSVファイル: %s", latest_csv)

    # 分析実行
    analyzer = BurndownAnalyzer(str(latest_csv))

    # サマリー表示
    analyzer.print_summary()

    logger.info("=" * 60)
    logger.info("【バーンダウン用データ作成】")
    logger.info("=" * 60)

    # バーンダウン用CSV作成（outputディレクトリに出力）
    analyzer.create_burndown_csv(output_dir="output")

    # ステータス別サマリーCSV作成（outputディレクトリに出力）
    analyzer.create_status_summary_csv(output_dir="output")

    logger.info("=" * 60)
    logger.info("処理が完了しました！")
    logger.info("=" * 60)
    logger.info("作成されたファイル:")
    logger.info("  1. output/burndown_weekly.csv - バーンダウンチャート用データ")
    logger.info("  2. output/status_summary_weekly.csv - ステータス別週次サマリー")
    logger.info("次のステップ:")
    logger.info("  1. Excel/Google Spreadsheetで burndown_weekly.csv を開く")
    logger.info("  2. 折れ線グラフを作成（残チケット数 vs 理想残チケット数）")
    logger.info("  3. 週次ミーティングで進捗確認に活用")


if __name__ == "__main__":
    main()

