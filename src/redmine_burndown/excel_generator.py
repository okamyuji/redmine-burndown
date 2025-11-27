#!/usr/bin/env python3
"""Excel テンプレート生成モジュール.

Redmineバーンダウンチャート用のExcelワークブックを自動生成します。
Requirements.mdに基づいた4シート構成：
1. RAW: CSVインポート用
2. 週次: バーンダウンチャート
3. 月次: 累積フロー図
4. ダッシュボード: KPI一覧
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from openpyxl import Workbook, load_workbook
from openpyxl.chart import AreaChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

# ロガーの設定
logger = logging.getLogger(__name__)

# スタイル定義
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
BORDER_THIN = Side(style="thin", color="000000")
BORDER = Border(left=BORDER_THIN, right=BORDER_THIN, top=BORDER_THIN, bottom=BORDER_THIN)

# セルスタイル
TITLE_FILL = PatternFill(start_color="2F75B5", end_color="2F75B5", fill_type="solid")
TITLE_FONT = Font(bold=True, color="FFFFFF", size=14)
SUBTITLE_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
SUBTITLE_FONT = Font(bold=True, size=11)

# KPI色設定
KPI_GOOD_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
KPI_WARNING_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
KPI_BAD_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")


class ExcelGenerator:
    """Excelワークブック生成クラス."""

    def __init__(self, template_path: str = "templates/burndown_template.xlsx") -> None:
        """初期化.

        Args:
            template_path: テンプレートファイルパス
        """
        self.template_path = Path(template_path)
        self.wb: Workbook | None = None

    def create_template(self) -> None:
        """Excelテンプレートを作成."""
        logger.info("Excelテンプレート作成開始")

        # 新規ワークブック作成
        self.wb = Workbook()

        # デフォルトシート削除
        if "Sheet" in self.wb.sheetnames:
            del self.wb["Sheet"]

        # 4つのシートを作成
        self._create_raw_sheet()
        self._create_weekly_burndown_sheet()
        self._create_monthly_cfd_sheet()
        self._create_dashboard_sheet()

        # テンプレートディレクトリ作成
        self.template_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存
        self.wb.save(self.template_path)
        logger.info("Excelテンプレート作成完了: %s", self.template_path)

    def _create_raw_sheet(self) -> None:
        """シート1: RAWデータシートを作成."""
        if self.wb is None:
            msg = "ワークブックが初期化されていません"
            raise ValueError(msg)

        logger.debug("RAWシート作成開始")
        ws = self.wb.create_sheet("RAW")

        # ヘッダー行
        headers = [
            "#",
            "題名",
            "ステータス",
            "優先度",
            "担当者",
            "作成日",
            "更新日",
            "開始日",
            "期日",
            "進捗率",
            "予定工数",
            "対象バージョン",
            "完了フラグ",  # K列: 計算列
            "週番号",  # L列: 計算列
            "年-週",  # M列: 計算列
            "残作業量",  # N列: 計算列
        ]

        # ヘッダー設定
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = HEADER_ALIGNMENT
            cell.border = BORDER

        # 列幅設定
        ws.column_dimensions["A"].width = 8  # #
        ws.column_dimensions["B"].width = 40  # 題名
        ws.column_dimensions["C"].width = 12  # ステータス
        ws.column_dimensions["D"].width = 10  # 優先度
        ws.column_dimensions["E"].width = 15  # 担当者
        ws.column_dimensions["F"].width = 12  # 作成日
        ws.column_dimensions["G"].width = 12  # 更新日
        ws.column_dimensions["H"].width = 12  # 開始日
        ws.column_dimensions["I"].width = 12  # 期日
        ws.column_dimensions["J"].width = 10  # 進捗率
        ws.column_dimensions["K"].width = 12  # 予定工数
        ws.column_dimensions["L"].width = 15  # 対象バージョン
        ws.column_dimensions["M"].width = 12  # 完了フラグ
        ws.column_dimensions["N"].width = 10  # 週番号
        ws.column_dimensions["O"].width = 12  # 年-週
        ws.column_dimensions["P"].width = 12  # 残作業量

        # サンプルデータ行（数式のテンプレート）
        # K2: 完了フラグ（ステータスが"終了"なら1）
        ws["M2"] = '=IF(C2="終了",1,0)'

        # L2: 週番号（ISO週）- Google Spreadsheet形式
        ws["N2"] = "=WEEKNUM(G2,2)"

        # M2: 年-週
        ws["O2"] = '=YEAR(G2)&"-W"&TEXT(WEEKNUM(G2,2),"00")'

        # N2: 残作業量（予定工数×(100-進捗率)/100）
        ws["P2"] = "=K2*(100-J2)/100"

        # フリーズペイン（ヘッダー行を固定）
        ws.freeze_panes = "A2"

        logger.debug("RAWシート作成完了")

    def _create_weekly_burndown_sheet(self) -> None:
        """シート2: 週次バーンダウンシートを作成."""
        if self.wb is None:
            msg = "ワークブックが初期化されていません"
            raise ValueError(msg)

        logger.debug("週次バーンダウンシート作成開始")
        ws = self.wb.create_sheet("週次バーンダウン")

        # タイトル
        ws["A1"] = "週次バーンダウンチャート"
        ws["A1"].fill = TITLE_FILL
        ws["A1"].font = TITLE_FONT
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells("A1:G1")
        ws.row_dimensions[1].height = 30

        # ヘッダー行
        headers = [
            "週番号",
            "完了チケット数（累積）",
            "残チケット数",
            "完了工数（累積）",
            "残工数",
            "理想残チケット数",
            "理想残工数",
        ]

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=2, column=col_idx, value=header)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = HEADER_ALIGNMENT
            cell.border = BORDER

        # 列幅設定
        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 18
        ws.column_dimensions["G"].width = 15

        # サンプル数式（3行目）
        # A3: 週番号（RAWシートから取得 - ユニーク値）
        ws["A3"] = "2025-W01"  # プレースホルダー

        # B3: 完了チケット数（累積）
        ws["B3"] = '=COUNTIFS(RAW!$O:$O,"<="&A3,RAW!$M:$M,1)'
        # C3: 残チケット数
        ws["C3"] = "=COUNTA(RAW!$A:$A)-B3-1"
        # D3: 完了工数（累積）
        ws["D3"] = '=SUMIFS(RAW!$K:$K,RAW!$O:$O,"<="&A3,RAW!$M:$M,1)'
        # E3: 残工数
        ws["E3"] = "=SUM(RAW!$K:$K)-D3"

        # F3: 理想残チケット数（線形減少）
        ws["F3"] = "=$C$3*(1-ROW()/COUNTA($A:$A))"

        # G3: 理想残工数（線形減少）
        ws["G3"] = "=$E$3*(1-ROW()/COUNTA($A:$A))"

        # バーンダウンチャートを追加
        chart = LineChart()
        chart.title = "バーンダウンチャート"
        chart.style = 2
        chart.y_axis.title = "残作業量（チケット数）"
        chart.x_axis.title = "週番号"
        chart.height = 10
        chart.width = 20

        # データ範囲（3行目から20行目まで想定）
        data = Reference(ws, min_col=3, min_row=2, max_col=7, max_row=20)
        cats = Reference(ws, min_col=1, min_row=3, max_row=20)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)

        # 系列のスタイル設定
        if len(chart.series) >= 2:
            # 残チケット数（実績）: 青色、太線
            chart.series[0].graphicalProperties.line.solidFill = "4472C4"
            chart.series[0].graphicalProperties.line.width = 25000

            # 理想残チケット数: 灰色、点線
            chart.series[3].graphicalProperties.line.solidFill = "CCCCCC"
            chart.series[3].graphicalProperties.line.width = 20000
            chart.series[3].graphicalProperties.line.dashStyle = "dash"

        # グラフを配置（I列、2行目から）
        ws.add_chart(chart, "I2")

        # フリーズペイン
        ws.freeze_panes = "A3"

        logger.debug("週次バーンダウンシート作成完了")

    def _create_monthly_cfd_sheet(self) -> None:
        """シート3: 月次累積フロー図シートを作成."""
        if self.wb is None:
            msg = "ワークブックが初期化されていません"
            raise ValueError(msg)

        logger.debug("月次累積フロー図シート作成開始")
        ws = self.wb.create_sheet("月次累積フロー図")

        # タイトル
        ws["A1"] = "累積フロー図（CFD: Cumulative Flow Diagram）"
        ws["A1"].fill = TITLE_FILL
        ws["A1"].font = TITLE_FONT
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells("A1:F1")
        ws.row_dimensions[1].height = 30

        # ヘッダー行
        headers = [
            "日付",
            "新規",
            "進行中",
            "レビュー中",
            "完了",
            "合計",
        ]

        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=2, column=col_idx, value=header)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = HEADER_ALIGNMENT
            cell.border = BORDER

        # 列幅設定
        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 15
        ws.column_dimensions["E"].width = 10
        ws.column_dimensions["F"].width = 10

        # サンプルデータ（週次スナップショット）
        sample_data = [
            ["2025-11-01", 20, 15, 5, 10, 50],
            ["2025-11-08", 18, 12, 8, 12, 50],
            ["2025-11-15", 15, 10, 7, 18, 50],
            ["2025-11-22", 12, 8, 5, 25, 50],
        ]

        for row_idx, row_data in enumerate(sample_data, start=3):
            for col_idx, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = BORDER

        # 累積フロー図（積み上げ面グラフ）を追加
        chart = AreaChart()
        chart.title = "累積フロー図（CFD）"
        chart.style = 13
        chart.grouping = "stacked"
        chart.y_axis.title = "チケット数"
        chart.x_axis.title = "日付"
        chart.height = 12
        chart.width = 20

        # データ範囲
        data = Reference(ws, min_col=2, min_row=2, max_col=6, max_row=6)
        cats = Reference(ws, min_col=1, min_row=3, max_row=6)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)

        # グラフを配置（H列、2行目から）
        ws.add_chart(chart, "H2")

        # フリーズペイン
        ws.freeze_panes = "A3"

        logger.debug("月次累積フロー図シート作成完了")

    def _create_dashboard_sheet(self) -> None:
        """シート4: KPIダッシュボードシートを作成."""
        if self.wb is None:
            msg = "ワークブックが初期化されていません"
            raise ValueError(msg)

        logger.debug("KPIダッシュボードシート作成開始")
        ws = self.wb.create_sheet("ダッシュボード")

        # タイトル
        ws["A1"] = "プロジェクトKPIダッシュボード"
        ws["A1"].fill = TITLE_FILL
        ws["A1"].font = TITLE_FONT
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells("A1:E1")
        ws.row_dimensions[1].height = 30

        # 更新日時
        ws["A2"] = "最終更新:"
        ws["B2"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S JST")
        ws["A2"].font = Font(bold=True)

        # KPIヘッダー
        ws["A4"] = "指標名"
        ws["B4"] = "現在値"
        ws["C4"] = "目標値"
        ws["D4"] = "達成率"
        ws["E4"] = "ステータス"

        for col in ["A", "B", "C", "D", "E"]:
            ws[f"{col}4"].fill = HEADER_FILL
            ws[f"{col}4"].font = HEADER_FONT
            ws[f"{col}4"].alignment = HEADER_ALIGNMENT
            ws[f"{col}4"].border = BORDER

        # KPI定義
        kpis = [
            ("完了率", '=COUNTIF(RAW!$C:$C,"終了")/COUNTA(RAW!$A:$A)', 0.80, "≥80%"),
            ("平均ベロシティ", 0, "安定", "±20%以内"),
            ("バグ率", '=COUNTIF(RAW!$C:$C,"バグ")/COUNTA(RAW!$A:$A)', 0.15, "≤15%"),
            ("リードタイム（日）", 14, 14, "≤14日"),
            ("サイクルタイム（日）", 7, 7, "≤7日"),
            ("ブロック率", 0.05, 0.10, "≤10%"),
        ]

        # 列幅設定
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 15
        ws.column_dimensions["E"].width = 15

        # KPIデータ
        for row_idx, (name, current, target, _target_desc) in enumerate(kpis, start=5):
            ws[f"A{row_idx}"] = name
            ws[f"B{row_idx}"] = current
            ws[f"C{row_idx}"] = target

            # 達成率（完了率の場合のみ計算）
            if name == "完了率":
                ws[f"D{row_idx}"] = "=B5/C5"
                ws[f"D{row_idx}"].number_format = "0%"
            else:
                ws[f"D{row_idx}"] = "-"

            # ステータス（条件付き書式用プレースホルダー）
            ws[f"E{row_idx}"] = "分析中"

            # 罫線
            for col in ["A", "B", "C", "D", "E"]:
                ws[f"{col}{row_idx}"].border = BORDER

        # 説明セクション
        ws["A12"] = "KPI説明"
        ws["A12"].font = SUBTITLE_FONT
        ws["A12"].fill = SUBTITLE_FILL
        ws.merge_cells("A12:E12")

        descriptions = [
            "・完了率: 終了チケット数 ÷ 総チケット数",
            "・ベロシティ: 週間完了ストーリーポイント数",
            "・バグ率: バグチケット数 ÷ 総チケット数",
            "・リードタイム: 完了日 - 作成日の平均",
            "・サイクルタイム: 完了日 - 開始日の平均",
            "・ブロック率: ブロック日数 ÷ 総日数",
        ]

        for idx, desc in enumerate(descriptions, start=13):
            ws[f"A{idx}"] = desc

        logger.debug("KPIダッシュボードシート作成完了")

    def copy_csv_to_excel(
        self,
        csv_path: str,
        output_path: str,
        sheet_name: str = "RAW",
    ) -> None:
        """CSVデータをExcelにコピー.

        Args:
            csv_path: CSVファイルパス
            output_path: 出力Excelファイルパス
            sheet_name: コピー先シート名
        """
        logger.info("CSV→Excel変換開始: %s → %s", csv_path, output_path)

        # 出力ファイルが既に存在する場合は削除（グラフ重複防止）
        output_file = Path(output_path)
        if output_file.exists():
            logger.debug("既存のExcelファイルを削除してグラフ重複を防止: %s", output_path)
            output_file.unlink()

        # テンプレートをコピー
        if not self.template_path.exists():
            logger.info("テンプレートが存在しないため作成します")
            self.create_template()

        # テンプレート読み込み
        wb = load_workbook(self.template_path)

        if sheet_name not in wb.sheetnames:
            msg = f"シート '{sheet_name}' が見つかりません"
            raise ValueError(msg)

        ws = wb[sheet_name]

        # CSVデータ読み込み
        csv_file = Path(csv_path)
        if not csv_file.exists():
            msg = f"CSVファイルが見つかりません: {csv_path}"
            raise FileNotFoundError(msg)

        with csv_file.open(encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            logger.warning("CSVファイルが空です")
            return

        # 既存データクリア（ヘッダーは保持）
        self._clear_sheet_data(ws, keep_header=True)

        # CSVヘッダーとExcelヘッダーのマッピングを作成
        csv_header = rows[0]

        # 標準フィールドのマッピング（A-L列: 固定）
        standard_excel_headers = {
            "#": "A",
            "題名": "B",
            "ステータス": "C",
            "優先度": "D",
            "担当者": "E",
            "作成日": "F",
            "更新日": "G",
            "開始日": "H",
            "期日": "I",
            "進捗率": "J",
            "予定工数": "K",
            "対象バージョン": "L",
        }

        # CSVの列名を標準フィールドとカスタムフィールドに分類
        standard_csv_to_excel = {
            "id": "#",
            "subject": "題名",
            "status": "ステータス",
            "priority": "優先度",
            "assigned_to": "担当者",
            "created_on": "作成日",
            "updated_on": "更新日",
            "start_date": "開始日",
            "due_date": "期日",
            "done_ratio": "進捗率",
            "estimated_hours": "予定工数",
            "version": "対象バージョン",
        }

        # カスタムフィールドを検出してExcelヘッダーを追加
        custom_fields = [csv_col_name for csv_col_name in csv_header if csv_col_name not in standard_csv_to_excel]

        # カスタムフィールド用の列を追加（Q列から開始、M-P列は計算列として予約済み）
        custom_field_headers: dict[str, str] = {}
        for idx, field_name in enumerate(custom_fields):
            col_letter = get_column_letter(17 + idx)  # Q=17列目
            custom_field_headers[field_name] = col_letter

        # CSVとExcelのマッピングを作成
        csv_to_excel_map = {}
        for csv_col_idx, csv_col_name in enumerate(csv_header):
            if csv_col_name in standard_csv_to_excel:
                excel_col_name = standard_csv_to_excel[csv_col_name]
                if excel_col_name in standard_excel_headers:
                    csv_to_excel_map[csv_col_idx] = standard_excel_headers[excel_col_name]
            elif csv_col_name in custom_field_headers:
                csv_to_excel_map[csv_col_idx] = custom_field_headers[csv_col_name]

        # カスタムフィールドのヘッダーをRAWシートに追加
        if custom_fields:
            logger.info("カスタムフィールド検出: %d個", len(custom_fields))
            for field_name, col_letter in custom_field_headers.items():
                cell = ws[f"{col_letter}1"]
                cell.value = field_name
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
                cell.alignment = HEADER_ALIGNMENT
                cell.border = BORDER

        # データ行をコピー（2行目から）
        for row_idx, row_data in enumerate(rows[1:], start=2):
            for csv_col_idx, value in enumerate(row_data):
                if csv_col_idx in csv_to_excel_map:
                    excel_col = csv_to_excel_map[csv_col_idx]
                    cell = ws[f"{excel_col}{row_idx}"]
                    cell.border = BORDER

                    # CSVのヘッダーに基づいて数値フォーマット
                    csv_col_name = csv_header[csv_col_idx]

                    if csv_col_name == "done_ratio" and value:  # 進捗率
                        try:
                            cell.value = float(value) / 100
                            cell.number_format = "0%"
                        except (ValueError, TypeError):
                            cell.value = value
                    elif csv_col_name == "estimated_hours" and value:  # 予定工数
                        try:
                            cell.value = float(value)
                            cell.number_format = "0.0"
                        except (ValueError, TypeError):
                            cell.value = value
                    elif csv_col_name in ("created_on", "updated_on", "start_date", "due_date") and value:  # 日付
                        # JST形式の日付を解析してExcel日付型に変換
                        try:
                            # "2025-11-27 09:42:03 JST" または "2025-11-27" 形式を解析
                            # JST サフィックスを除去
                            date_str = re.sub(r"\s+JST$", "", value.strip())

                            # 日付を解析（Excelは内部的にnaive datetimeを使用するため、ここではnaiveのまま）
                            if " " in date_str:
                                # "2025-11-27 09:42:03" 形式
                                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
                            else:
                                # "2025-11-27" 形式
                                dt = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: DTZ007

                            cell.value = dt
                            cell.number_format = "yyyy-mm-dd hh:mm:ss"
                        except (ValueError, TypeError):
                            cell.value = value
                    else:
                        cell.value = value

        # 計算列の数式をコピー（M-P列）
        if len(rows) > 1:
            for row_idx in range(2, len(rows) + 1):
                # M列: 完了フラグ（ステータスが"終了"なら1）
                ws[f"M{row_idx}"] = f'=IF(C{row_idx}="終了",1,0)'
                # N列: 週番号（ISO週）- 更新日（G列）が日付の場合のみ
                ws[f"N{row_idx}"] = f'=IFERROR(WEEKNUM(G{row_idx},2),"")'
                # O列: 年-週
                ws[f"O{row_idx}"] = f'=IFERROR(YEAR(G{row_idx})&"-W"&TEXT(WEEKNUM(G{row_idx},2),"00"),"")'
                # P列: 残作業量（予定工数×(100-進捗率)/100）
                ws[f"P{row_idx}"] = f'=IFERROR(K{row_idx}*(1-J{row_idx}),"")'

        # 出力ディレクトリ作成
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 保存
        wb.save(output_file)
        logger.info("Excel保存完了: %s（%d行）", output_file, len(rows) - 1)

    def _clear_sheet_data(self, ws: Worksheet, keep_header: bool = True) -> None:
        """シートのデータをクリア.

        Args:
            ws: ワークシート
            keep_header: ヘッダー行を保持するか
        """
        start_row = 2 if keep_header else 1
        max_row = ws.max_row
        max_col = ws.max_column

        for row in range(start_row, max_row + 1):
            for col in range(1, max_col + 1):
                ws.cell(row=row, column=col).value = None


def main() -> None:
    """メイン処理（テンプレート生成のみ）."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    generator = ExcelGenerator()
    generator.create_template()
    logger.info("✅ テンプレート生成完了")


if __name__ == "__main__":
    main()

