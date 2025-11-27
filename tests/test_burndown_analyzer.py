"""BurndownAnalyzerのユニットテスト."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from redmine_burndown.burndown_analyzer import BurndownAnalyzer, main


class TestBurndownAnalyzer:
    """BurndownAnalyzerクラスのテスト."""

    @pytest.fixture
    def csv_file(self, tmp_path: Any) -> str:
        """テスト用の基本CSVファイルを作成."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
        csv_file.write_text(csv_content)
        return str(csv_file)

    def test_init(self, csv_file: str) -> None:
        """初期化が正しく動作することを確認."""
        analyzer = BurndownAnalyzer(csv_file)
        assert analyzer.csv_filename == csv_file
        assert len(analyzer.issues) == 1

    def test_load_csv_success(self, tmp_path: Any, caplog: Any) -> None:
        """CSVファイルの読み込みが正常に動作することを確認."""
        with caplog.at_level(logging.INFO):
            csv_file = tmp_path / "test.csv"
            csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
2,Issue 2,Project A,Task,Closed,Normal,User C,User D,Category B,2024-01-08,2024-01-15,2024-01-08,2024-01-20,100,16.0,12.0
"""
            csv_file.write_text(csv_content)

            analyzer = BurndownAnalyzer(str(csv_file))

            assert len(analyzer.issues) == 2
            assert analyzer.issues[0]["id"] == "1"
            assert analyzer.issues[1]["id"] == "2"
            assert "CSVファイルを読み込みました: 2件" in caplog.text

    def test_load_csv_file_not_found(self, caplog: Any) -> None:
        """存在しないCSVファイルの読み込みテスト."""
        with caplog.at_level(logging.WARNING):
            analyzer = BurndownAnalyzer("nonexistent.csv")

            assert "ファイルが見つかりません" in caplog.text
            assert len(analyzer.issues) == 0

    def test_load_csv_empty_file(self, tmp_path: Any) -> None:
        """空のCSVファイルの読み込みテスト."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("id,subject,project\n")

        analyzer = BurndownAnalyzer(str(csv_file))

        assert len(analyzer.issues) == 0

    def test_get_week_number(self, csv_file: str) -> None:
        """週番号の取得が正しく動作することを確認."""
        analyzer = BurndownAnalyzer(csv_file)
        date_str = "2024-01-01"
        week = analyzer.get_week_number(date_str)

        assert isinstance(week, str)
        assert week.startswith("2024-W")

    def test_get_week_number_invalid_date(self, csv_file: str) -> None:
        """無効な日付の場合のテスト."""
        analyzer = BurndownAnalyzer(csv_file)
        result = analyzer.get_week_number("invalid-date")

        assert result == ""

    def test_get_week_number_empty_string(self, csv_file: str) -> None:
        """空文字列の場合のテスト."""
        analyzer = BurndownAnalyzer(csv_file)
        result = analyzer.get_week_number("")

        assert result == ""

    def test_analyze_weekly_progress_success(self, tmp_path: Any) -> None:
        """週次進捗分析が正常に動作することを確認."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
2,Issue 2,Project A,Task,Closed,Normal,User C,User D,Category B,2024-01-08,2024-01-15,2024-01-08,2024-01-20,100,16.0,12.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_analyze_weekly_progress_no_data(self, tmp_path: Any, caplog: Any) -> None:
        """データがない場合の週次進捗分析のテスト."""
        with caplog.at_level(logging.WARNING):
            csv_file = tmp_path / "empty.csv"
            csv_file.write_text("id,subject\n")

            analyzer = BurndownAnalyzer(str(csv_file))
            weekly_data = analyzer.analyze_weekly_progress()

            # analyze_weekly_progressはlogger.warningを出さない（空でも正常）
            assert len(weekly_data) == 0

    def test_create_burndown_csv_success(self, tmp_path: Any, caplog: Any) -> None:
        """バーンダウンCSVの作成が成功することを確認."""
        with caplog.at_level(logging.INFO):
            csv_file = tmp_path / "test.csv"
            csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
            csv_file.write_text(csv_content)

            analyzer = BurndownAnalyzer(str(csv_file))
            analyzer.analyze_weekly_progress()

            output_dir = str(tmp_path / "output")
            analyzer.create_burndown_csv("burndown.csv", output_dir=output_dir)

            assert "バーンダウン用CSVを作成しました" in caplog.text
            assert (tmp_path / "output" / "burndown.csv").exists()

    def test_create_burndown_csv_no_data(self, tmp_path: Any) -> None:
        """データがない場合のバーンダウンCSV作成のテスト."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("id,subject\n")

        analyzer = BurndownAnalyzer(str(csv_file))
        analyzer.analyze_weekly_progress()
        # データがなくても正常に実行される
        analyzer.create_burndown_csv(output_dir=str(tmp_path))

    def test_create_status_summary_csv_success(self, tmp_path: Any, caplog: Any) -> None:
        """ステータスサマリCSVの作成が成功することを確認."""
        with caplog.at_level(logging.INFO):
            csv_file = tmp_path / "test.csv"
            csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
2,Issue 2,Project A,Task,Closed,Normal,User C,User D,Category B,2024-01-08,2024-01-15,2024-01-08,2024-01-20,100,16.0,12.0
"""
            csv_file.write_text(csv_content)

            analyzer = BurndownAnalyzer(str(csv_file))
            analyzer.analyze_weekly_progress()

            output_dir = str(tmp_path / "output")
            analyzer.create_status_summary_csv("status.csv", output_dir=output_dir)

            assert "ステータス別サマリーCSVを作成しました" in caplog.text
            assert (tmp_path / "output" / "status.csv").exists()

    def test_create_status_summary_csv_no_data(self, tmp_path: Any) -> None:
        """データがない場合のステータスサマリCSV作成のテスト."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("id,subject\n")

        analyzer = BurndownAnalyzer(str(csv_file))
        analyzer.analyze_weekly_progress()
        # データがなくても正常に実行される
        analyzer.create_status_summary_csv(output_dir=str(tmp_path))

    def test_print_summary(self, tmp_path: Any, caplog: Any) -> None:
        """サマリ出力が正常に動作することを確認."""
        with caplog.at_level(logging.INFO):
            csv_file = tmp_path / "test.csv"
            csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
            csv_file.write_text(csv_content)

            analyzer = BurndownAnalyzer(str(csv_file))
            analyzer.analyze_weekly_progress()
            analyzer.print_summary()

            assert "【データサマリー】" in caplog.text

    def test_print_summary_no_data(self, tmp_path: Any, caplog: Any) -> None:
        """データがない場合のサマリ出力のテスト."""
        with caplog.at_level(logging.WARNING):
            csv_file = tmp_path / "empty.csv"
            csv_file.write_text("id,subject\n")

            analyzer = BurndownAnalyzer(str(csv_file))
            analyzer.analyze_weekly_progress()
            analyzer.print_summary()

            # データがない場合は警告が出る
            assert "データがありません" in caplog.text

    def test_analyze_with_invalid_estimated_hours(self, tmp_path: Any) -> None:
        """不正なestimated_hoursの場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,invalid,4.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_analyze_with_invalid_done_ratio(self, tmp_path: Any) -> None:
        """不正なdone_ratioの場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,invalid,8.0,4.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_analyze_with_empty_start_date(self, tmp_path: Any) -> None:
        """start_dateが空の場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,,2024-01-10,50,8.0,4.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_multiple_statuses_same_week(self, tmp_path: Any) -> None:
        """同一週に複数のステータスがある場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
2,Issue 2,Project A,Task,In Progress,Normal,User C,User D,Category B,2024-01-02,2024-01-03,2024-01-02,2024-01-15,25,16.0,8.0
3,Issue 3,Project A,Feature,Closed,Low,User E,User F,Category C,2024-01-03,2024-01-04,2024-01-03,2024-01-20,100,12.0,12.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_edge_case_year_boundary(self, tmp_path: Any) -> None:
        """年境界のエッジケースのテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2023-12-25,2024-01-05,2023-12-25,2024-01-10,50,8.0,4.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_zero_estimated_hours(self, tmp_path: Any) -> None:
        """見積時間がゼロの場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,0.0,0.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0

    def test_hundred_percent_done_ratio(self, tmp_path: Any) -> None:
        """完了率が100%の場合のテスト."""
        csv_file = tmp_path / "test.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,Closed,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,100,8.0,8.0
"""
        csv_file.write_text(csv_content)

        analyzer = BurndownAnalyzer(str(csv_file))
        weekly_data = analyzer.analyze_weekly_progress()

        assert len(weekly_data) > 0


def test_main_success(tmp_path: Any, caplog: Any, monkeypatch: Any) -> None:
    """main関数の正常実行テスト."""
    with caplog.at_level(logging.INFO):
        monkeypatch.chdir(tmp_path)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        csv_file = output_dir / "redmine_issues_20240101_120000.csv"
        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
2,Issue 2,Project A,Task,Closed,Normal,User C,User D,Category B,2024-01-08,2024-01-15,2024-01-08,2024-01-20,100,16.0,12.0
"""
        csv_file.write_text(csv_content)

        main()

        assert "バーンダウンチャート用データ整形ツール" in caplog.text
        assert "使用するCSVファイル" in caplog.text
        assert "処理が完了しました" in caplog.text


def test_main_no_csv_found(tmp_path: Any, caplog: Any, monkeypatch: Any) -> None:
    """CSVファイルが見つからない場合のテスト."""
    with caplog.at_level(logging.WARNING):
        monkeypatch.chdir(tmp_path)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        main()

        assert "ファイルが見つかりません" in caplog.text


def test_main_multiple_csv_files(tmp_path: Any, caplog: Any, monkeypatch: Any) -> None:
    """複数のCSVファイルがある場合のテスト（最新を使用）."""
    with caplog.at_level(logging.INFO):
        monkeypatch.chdir(tmp_path)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        csv_file1 = output_dir / "redmine_issues_20240101_120000.csv"
        csv_file2 = output_dir / "redmine_issues_20240102_120000.csv"

        csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
        csv_file1.write_text(csv_content)
        csv_file2.write_text(csv_content)

        main()

        assert "使用するCSVファイル" in caplog.text
        assert "redmine_issues_20240102_120000.csv" in caplog.text


def test_main_no_output_dir(tmp_path: Any, caplog: Any, monkeypatch: Any) -> None:
    """outputディレクトリが存在しない場合のテスト."""
    with caplog.at_level(logging.WARNING):
        monkeypatch.chdir(tmp_path)

        main()

        assert "outputディレクトリが見つかりません" in caplog.text


def test_create_burndown_csv_creates_directory(tmp_path: Any) -> None:
    """出力ディレクトリが存在しない場合に作成されることのテスト."""
    csv_file = tmp_path / "test.csv"
    csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
    csv_file.write_text(csv_content)

    analyzer = BurndownAnalyzer(str(csv_file))
    analyzer.analyze_weekly_progress()

    output_dir = str(tmp_path / "new_output" / "subdir")
    analyzer.create_burndown_csv("burndown.csv", output_dir=output_dir)

    assert (tmp_path / "new_output" / "subdir").exists()
    assert (tmp_path / "new_output" / "subdir" / "burndown.csv").exists()


def test_create_status_summary_csv_creates_directory(tmp_path: Any) -> None:
    """出力ディレクトリが存在しない場合に作成されることのテスト."""
    csv_file = tmp_path / "test.csv"
    csv_content = """id,subject,project,tracker,status,priority,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Issue 1,Project A,Bug,New,High,User A,User B,Category A,2024-01-01,2024-01-02,2024-01-01,2024-01-10,50,8.0,4.0
"""
    csv_file.write_text(csv_content)

    analyzer = BurndownAnalyzer(str(csv_file))
    analyzer.analyze_weekly_progress()

    output_dir = str(tmp_path / "new_output" / "subdir")
    analyzer.create_status_summary_csv("status.csv", output_dir=output_dir)

    assert (tmp_path / "new_output" / "subdir").exists()
    assert (tmp_path / "new_output" / "subdir" / "status.csv").exists()
