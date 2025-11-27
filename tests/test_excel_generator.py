#!/usr/bin/env python3
"""Excel生成モジュールのユニットテスト."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest
from openpyxl import load_workbook

from redmine_burndown.excel_generator import ExcelGenerator


class TestExcelGenerator:
    """ExcelGeneratorクラスのテスト."""

    template_path: ClassVar[str] = "templates/test_burndown_template.xlsx"
    output_path: ClassVar[str] = "output/test_burndown.xlsx"

    def test_init(self) -> None:
        """初期化テスト."""
        generator = ExcelGenerator()
        assert generator.template_path == Path("templates/burndown_template.xlsx")
        assert generator.wb is None

    def test_init_custom_path(self) -> None:
        """カスタムパスでの初期化テスト."""
        generator = ExcelGenerator("custom/path.xlsx")
        assert generator.template_path == Path("custom/path.xlsx")

    def test_create_template(self, tmp_path: Path) -> None:
        """テンプレート作成テスト."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # ファイルが作成されたか確認
        assert template_file.exists()

        # ワークブックを読み込んで確認
        wb = load_workbook(template_file)

        # 4つのシートが存在するか確認
        assert "RAW" in wb.sheetnames
        assert "週次バーンダウン" in wb.sheetnames
        assert "月次累積フロー図" in wb.sheetnames
        assert "ダッシュボード" in wb.sheetnames

    def test_create_raw_sheet(self, tmp_path: Path) -> None:
        """RAWシート作成テスト."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["RAW"]

        # ヘッダー確認
        expected_headers = [
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
            "完了フラグ",
            "週番号",
            "年-週",
            "残作業量",
        ]

        for col_idx, expected_header in enumerate(expected_headers, start=1):
            actual_header = ws.cell(row=1, column=col_idx).value
            assert actual_header == expected_header

        # 計算式確認
        assert ws["M2"].value == '=IF(C2="終了",1,0)'
        assert ws["N2"].value == "=WEEKNUM(G2,2)"
        assert 'YEAR(G2)&"-W"&TEXT(WEEKNUM(G2,2),"00")' in str(ws["O2"].value)
        assert ws["P2"].value == "=K2*(100-J2)/100"

    def test_create_weekly_burndown_sheet(self, tmp_path: Path) -> None:
        """週次バーンダウンシート作成テスト."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["週次バーンダウン"]

        # タイトル確認
        assert ws["A1"].value == "週次バーンダウンチャート"

        # ヘッダー確認
        expected_headers = [
            "週番号",
            "完了チケット数（累積）",
            "残チケット数",
            "完了工数（累積）",
            "残工数",
            "理想残チケット数",
            "理想残工数",
        ]

        for col_idx, expected_header in enumerate(expected_headers, start=1):
            actual_header = ws.cell(row=2, column=col_idx).value
            assert actual_header == expected_header

        # サンプル数式確認
        assert ws["A3"].value == "2025-W01"
        assert 'COUNTIFS(RAW!$O:$O,"<="&A3,RAW!$M:$M,1)' in str(ws["B3"].value)
        assert "COUNTA(RAW!$A:$A)-B3-1" in str(ws["C3"].value)

    def test_create_monthly_cfd_sheet(self, tmp_path: Path) -> None:
        """月次累積フロー図シート作成テスト."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["月次累積フロー図"]

        # タイトル確認
        assert "累積フロー図" in str(ws["A1"].value)

        # ヘッダー確認
        expected_headers = [
            "日付",
            "新規",
            "進行中",
            "レビュー中",
            "完了",
            "合計",
        ]

        for col_idx, expected_header in enumerate(expected_headers, start=1):
            actual_header = ws.cell(row=2, column=col_idx).value
            assert actual_header == expected_header

        # サンプルデータ確認
        assert ws["A3"].value == "2025-11-01"
        assert ws["B3"].value == 20

    def test_create_dashboard_sheet(self, tmp_path: Path) -> None:
        """ダッシュボードシート作成テスト."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["ダッシュボード"]

        # タイトル確認
        assert ws["A1"].value == "プロジェクトKPIダッシュボード"

        # 更新日時確認
        assert ws["A2"].value == "最終更新:"
        assert ws["B2"].value is not None

        # KPIヘッダー確認
        expected_headers = ["指標名", "現在値", "目標値", "達成率", "ステータス"]
        for col_idx, expected_header in enumerate(expected_headers, start=1):
            actual_header = ws.cell(row=4, column=col_idx).value
            assert actual_header == expected_header

        # KPI項目確認
        kpi_names = [
            ws[f"A{row}"].value for row in range(5, 11)
        ]
        assert "完了率" in kpi_names
        assert "平均ベロシティ" in kpi_names
        assert "バグ率" in kpi_names
        assert "リードタイム（日）" in kpi_names
        assert "サイクルタイム（日）" in kpi_names
        assert "ブロック率" in kpi_names

    def test_copy_csv_to_excel_success(self, tmp_path: Path) -> None:
        """CSV→Excel変換成功テスト."""
        # テンプレート作成
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # テストCSVデータ作成
        csv_file = tmp_path / "test_data.csv"
        csv_data = [
            [
                "id",
                "subject",
                "status",
                "priority",
                "assigned_to",
                "created_on",
                "updated_on",
                "start_date",
                "due_date",
                "done_ratio",
                "estimated_hours",
                "version",
            ],
            [
                "1",
                "テスト機能実装",
                "進行中",
                "高",
                "田中",
                "2025-11-01",
                "2025-11-27",
                "2025-11-01",
                "2025-12-01",
                "50",
                "8",
                "v1.0",
            ],
            [
                "2",
                "バグ修正",
                "終了",
                "緊急",
                "鈴木",
                "2025-11-15",
                "2025-11-20",
                "2025-11-15",
                "2025-11-18",
                "100",
                "4",
                "v1.0",
            ],
        ]

        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)

        # 出力先ファイル
        output_file = tmp_path / "output.xlsx"

        # CSV→Excel変換
        generator.copy_csv_to_excel(str(csv_file), str(output_file))

        # 検証
        assert output_file.exists()

        wb = load_workbook(output_file)
        ws = wb["RAW"]

        # データ行確認（ヘッダー除く2行）
        assert ws["A2"].value == "1"
        assert ws["B2"].value == "テスト機能実装"
        assert ws["C2"].value == "進行中"
        assert ws["A3"].value == "2"
        assert ws["B3"].value == "バグ修正"
        assert ws["C3"].value == "終了"

        # 計算列の数式確認
        assert '=IF(C2="終了",1,0)' in str(ws["M2"].value)
        assert "WEEKNUM(G2,2)" in str(ws["N2"].value)  # IFERRORでラップされている

    def test_copy_csv_to_excel_file_not_found(self, tmp_path: Path) -> None:
        """CSV→Excel変換失敗テスト（ファイルなし）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        output_file = tmp_path / "output.xlsx"
        non_existent_csv = tmp_path / "non_existent.csv"

        with pytest.raises(FileNotFoundError, match="CSVファイルが見つかりません"):
            generator.copy_csv_to_excel(str(non_existent_csv), str(output_file))

    def test_copy_csv_to_excel_empty_csv(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """CSV→Excel変換テスト（空CSV）."""
        # テンプレート作成
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # 空CSVファイル作成
        csv_file = tmp_path / "empty.csv"
        csv_file.touch()

        output_file = tmp_path / "output.xlsx"

        with caplog.at_level(logging.WARNING):
            generator.copy_csv_to_excel(str(csv_file), str(output_file))

        assert "CSVファイルが空です" in caplog.text

    def test_copy_csv_to_excel_sheet_not_found(self, tmp_path: Path) -> None:
        """CSV→Excel変換失敗テスト（シートなし）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # テストCSVデータ作成
        csv_file = tmp_path / "test_data.csv"
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "subject"])
            writer.writerow(["1", "test"])

        output_file = tmp_path / "output.xlsx"

        with pytest.raises(ValueError, match=r"シート .* が見つかりません"):
            generator.copy_csv_to_excel(
                str(csv_file), str(output_file), sheet_name="NonExistent"
            )

    def test_copy_csv_to_excel_creates_output_dir(self, tmp_path: Path) -> None:
        """CSV→Excel変換テスト（出力ディレクトリ自動作成）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # テストCSVデータ作成
        csv_file = tmp_path / "test_data.csv"
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "subject"])
            writer.writerow(["1", "test"])

        # 存在しないディレクトリを指定
        output_file = tmp_path / "new_dir" / "output.xlsx"

        generator.copy_csv_to_excel(str(csv_file), str(output_file))

        # 出力ディレクトリとファイルが作成されたか確認
        assert output_file.parent.exists()
        assert output_file.exists()

    def test_copy_csv_to_excel_numeric_formatting(self, tmp_path: Path) -> None:
        """CSV→Excel変換テスト（数値フォーマット）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # テストCSVデータ作成（進捗率と予定工数に数値）
        csv_file = tmp_path / "test_data.csv"
        csv_data = [
            [
                "id",
                "subject",
                "status",
                "priority",
                "assigned_to",
                "created_on",
                "updated_on",
                "start_date",
                "due_date",
                "done_ratio",
                "estimated_hours",
                "version",
            ],
            [
                "1",
                "テスト",
                "進行中",
                "高",
                "田中",
                "2025-11-01",
                "2025-11-27",
                "2025-11-01",
                "2025-12-01",
                "75",
                "12.5",
                "v1.0",
            ],
        ]

        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)

        output_file = tmp_path / "output.xlsx"
        generator.copy_csv_to_excel(str(csv_file), str(output_file))

        wb = load_workbook(output_file)
        ws = wb["RAW"]

        # 進捗率（J列）が0.75（75%）になっているか確認
        assert ws["J2"].value == 0.75
        assert ws["J2"].number_format == "0%"

        # 予定工数（K列）が12.5になっているか確認
        assert ws["K2"].value == 12.5
        assert ws["K2"].number_format == "0.0"

    def test_copy_csv_to_excel_invalid_numeric_values(self, tmp_path: Path) -> None:
        """CSV→Excel変換テスト（無効な数値）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        # テストCSVデータ作成（無効な数値）
        csv_file = tmp_path / "test_data.csv"
        csv_data = [
            [
                "id",
                "subject",
                "status",
                "priority",
                "assigned_to",
                "created_on",
                "updated_on",
                "start_date",
                "due_date",
                "done_ratio",
                "estimated_hours",
                "version",
            ],
            [
                "1",
                "テスト",
                "進行中",
                "高",
                "田中",
                "2025-11-01",
                "2025-11-27",
                "2025-11-01",
                "2025-12-01",
                "invalid",
                "not_a_number",
                "v1.0",
            ],
        ]

        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)

        output_file = tmp_path / "output.xlsx"

        # エラーにならずに文字列としてそのまま格納されることを確認
        generator.copy_csv_to_excel(str(csv_file), str(output_file))

        wb = load_workbook(output_file)
        ws = wb["RAW"]

        assert ws["J2"].value == "invalid"
        assert ws["K2"].value == "not_a_number"

    def test_copy_csv_to_excel_with_template_auto_creation(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """CSV→Excel変換テスト（テンプレート自動作成）."""
        # テンプレートが存在しない状態でExcelGenerator作成
        template_file = tmp_path / "auto_created_template.xlsx"
        generator = ExcelGenerator(str(template_file))

        # テストCSVデータ作成
        csv_file = tmp_path / "test_data.csv"
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "subject"])
            writer.writerow(["1", "test"])

        output_file = tmp_path / "output.xlsx"

        with caplog.at_level(logging.INFO):
            generator.copy_csv_to_excel(str(csv_file), str(output_file))

        # テンプレートが自動作成されたことを確認
        assert "テンプレートが存在しないため作成します" in caplog.text
        assert template_file.exists()
        assert output_file.exists()

    def test_clear_sheet_data_keep_header(self, tmp_path: Path) -> None:
        """シートデータクリアテスト（ヘッダー保持）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["RAW"]

        # テストデータ追加
        ws["A2"] = "test1"
        ws["A3"] = "test2"

        # クリア実行
        generator._clear_sheet_data(ws, keep_header=True)

        # ヘッダーは残る
        assert ws["A1"].value == "#"
        # データは消える
        assert ws["A2"].value is None
        assert ws["A3"].value is None

    def test_clear_sheet_data_without_header(self, tmp_path: Path) -> None:
        """シートデータクリアテスト（ヘッダー含む）."""
        template_file = tmp_path / "test_template.xlsx"
        generator = ExcelGenerator(str(template_file))
        generator.create_template()

        wb = load_workbook(template_file)
        ws = wb["RAW"]

        # テストデータ追加
        ws["A1"] = "header"
        ws["A2"] = "test1"

        # クリア実行
        generator._clear_sheet_data(ws, keep_header=False)

        # ヘッダーも消える
        assert ws["A1"].value is None
        assert ws["A2"].value is None

    def test_main_function(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """main関数テスト."""
        from redmine_burndown import excel_generator  # noqa: PLC0415

        # ExcelGeneratorをモック
        mock_generator_instance = ExcelGenerator(str(tmp_path / "test.xlsx"))
        mock_generator_instance.create_template()

        def mock_excel_generator_init(template_path: str = "templates/burndown_template.xlsx") -> ExcelGenerator:
            return mock_generator_instance

        with (
            patch.object(excel_generator, "ExcelGenerator", side_effect=mock_excel_generator_init),
            caplog.at_level(logging.INFO),
        ):
            excel_generator.main()

        assert "✅ テンプレート生成完了" in caplog.text

    def test_main_function_real(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """main関数実際の動作テスト."""
        # 作業ディレクトリを一時ディレクトリに変更
        monkeypatch.chdir(tmp_path)

        from redmine_burndown import excel_generator  # noqa: PLC0415

        # main実行
        excel_generator.main()

        # テンプレートファイルが作成されたことを確認
        assert (tmp_path / "templates" / "burndown_template.xlsx").exists()

