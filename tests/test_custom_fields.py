"""カスタムフィールド機能のテスト."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from redmine_burndown.redmine_client import RedmineClient


class TestCustomFields:
    """カスタムフィールド機能のテストクラス."""

    def test_get_issues_with_custom_fields(self) -> None:
        """カスタムフィールドを含むチケット取得のテスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [
                {
                    "id": 1,
                    "subject": "テストチケット",
                    "custom_fields": [
                        {"id": 1, "name": "部署", "value": "開発部"},
                        {"id": 2, "name": "工数見積", "value": "8.0"},
                    ],
                }
            ],
            "total_count": 1,
        }
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = client.get_issues(include_custom_fields=True)

            # APIリクエストにinclude=custom_fieldsが含まれていることを確認
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["include"] == "custom_fields"

            # カスタムフィールドが取得できていることを確認
            assert len(result["issues"]) == 1
            assert "custom_fields" in result["issues"][0]
            assert len(result["issues"][0]["custom_fields"]) == 2

    def test_get_issues_without_custom_fields(self) -> None:
        """カスタムフィールドなしでチケット取得のテスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        mock_response = Mock()
        mock_response.json.return_value = {"issues": [{"id": 1, "subject": "テストチケット"}], "total_count": 1}
        mock_response.raise_for_status = Mock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            _ = client.get_issues(include_custom_fields=False)

            # APIリクエストにincludeが含まれていないことを確認
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "include" not in call_args[1]["params"]

    def test_extract_custom_fields(self) -> None:
        """カスタムフィールド名の抽出テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issues = [
            {
                "id": 1,
                "custom_fields": [
                    {"id": 1, "name": "部署", "value": "開発部"},
                    {"id": 2, "name": "工数見積", "value": "8.0"},
                ],
            },
            {
                "id": 2,
                "custom_fields": [
                    {"id": 1, "name": "部署", "value": "営業部"},
                    {"id": 3, "name": "優先度補足", "value": "緊急対応"},
                ],
            },
        ]

        custom_field_names = client._extract_custom_fields(issues)

        assert custom_field_names == {"部署", "工数見積", "優先度補足"}

    def test_extract_custom_fields_empty(self) -> None:
        """カスタムフィールドなしの抽出テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issues: list[dict[str, Any]] = [{"id": 1, "custom_fields": []}, {"id": 2}]

        custom_field_names = client._extract_custom_fields(issues)

        assert custom_field_names == set()

    def test_extract_custom_fields_invalid_format(self) -> None:
        """不正な形式のカスタムフィールドの抽出テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issues: list[dict[str, Any]] = [
            {"id": 1, "custom_fields": "invalid"},  # 文字列（不正）
            {"id": 2, "custom_fields": [{"id": 1}]},  # nameがない（不正）
            {"id": 3, "custom_fields": [{"id": 2, "name": "部署", "value": "開発部"}]},  # 正常
        ]

        custom_field_names = client._extract_custom_fields(issues)

        assert custom_field_names == {"部署"}

    def test_get_custom_field_value(self) -> None:
        """カスタムフィールド値の取得テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issue = {
            "id": 1,
            "custom_fields": [
                {"id": 1, "name": "部署", "value": "開発部"},
                {"id": 2, "name": "工数見積", "value": "8.0"},
            ],
        }

        assert client._get_custom_field_value(issue, "部署") == "開発部"
        assert client._get_custom_field_value(issue, "工数見積") == "8.0"
        assert client._get_custom_field_value(issue, "存在しないフィールド") == ""

    def test_get_custom_field_value_list(self) -> None:
        """リスト形式のカスタムフィールド値の取得テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issue = {"id": 1, "custom_fields": [{"id": 1, "name": "タグ", "value": ["タグ1", "タグ2", "タグ3"]}]}

        assert client._get_custom_field_value(issue, "タグ") == "タグ1, タグ2, タグ3"

    def test_get_custom_field_value_none(self) -> None:
        """None値のカスタムフィールド取得テスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issue = {"id": 1, "custom_fields": [{"id": 1, "name": "空フィールド", "value": None}]}

        assert client._get_custom_field_value(issue, "空フィールド") == ""

    def test_export_to_csv_with_custom_fields(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """カスタムフィールドを含むCSVエクスポートのテスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issues = [
            {
                "id": 1,
                "subject": "チケット1",
                "status": {"name": "進行中"},
                "priority": {"name": "高"},
                "project": {"name": "プロジェクトA"},
                "tracker": {"name": "バグ"},
                "author": {"name": "田中"},
                "assigned_to": {"name": "鈴木"},
                "category": {"name": "開発"},
                "created_on": "2025-01-01T10:00:00Z",
                "updated_on": "2025-01-02T15:30:00Z",
                "start_date": "2025-01-01",
                "due_date": "2025-01-31",
                "done_ratio": 50,
                "estimated_hours": 8,
                "spent_hours": 4,
                "custom_fields": [
                    {"id": 1, "name": "部署", "value": "開発部"},
                    {"id": 2, "name": "工数見積", "value": "8.0"},
                ],
            },
            {
                "id": 2,
                "subject": "チケット2",
                "status": {"name": "終了"},
                "priority": {"name": "低"},
                "project": {"name": "プロジェクトB"},
                "tracker": {"name": "機能"},
                "author": {"name": "佐藤"},
                "assigned_to": {"name": "高橋"},
                "category": {"name": "テスト"},
                "created_on": "2025-01-05T09:00:00Z",
                "updated_on": "2025-01-10T18:00:00Z",
                "start_date": "2025-01-05",
                "due_date": "2025-02-28",
                "done_ratio": 100,
                "estimated_hours": 16,
                "spent_hours": 16,
                "custom_fields": [
                    {"id": 1, "name": "部署", "value": "営業部"},
                    {"id": 3, "name": "優先度補足", "value": "通常対応"},
                ],
            },
        ]

        output_file = tmp_path / "test_custom_fields.csv"

        with caplog.at_level(logging.INFO):
            client.export_to_csv(issues, str(output_file.name), str(tmp_path))

        # ファイルが作成されていることを確認
        assert output_file.exists()

        # ログにカスタムフィールド数が記録されていることを確認
        assert "カスタムフィールド数: 3" in caplog.text

        # CSVの内容を検証
        with output_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 2行のデータがあることを確認
            assert len(rows) == 2

            # ヘッダーにカスタムフィールドが含まれていることを確認
            fieldnames = reader.fieldnames
            assert fieldnames is not None
            assert "部署" in fieldnames
            assert "工数見積" in fieldnames
            assert "優先度補足" in fieldnames

            # 1行目のデータを検証
            assert rows[0]["id"] == "1"
            assert rows[0]["subject"] == "チケット1"
            assert rows[0]["部署"] == "開発部"
            assert rows[0]["工数見積"] == "8.0"
            assert rows[0]["優先度補足"] == ""  # チケット1にはこのフィールドがない

            # 2行目のデータを検証
            assert rows[1]["id"] == "2"
            assert rows[1]["subject"] == "チケット2"
            assert rows[1]["部署"] == "営業部"
            assert rows[1]["工数見積"] == ""  # チケット2にはこのフィールドがない
            assert rows[1]["優先度補足"] == "通常対応"

    def test_export_to_csv_no_custom_fields(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """カスタムフィールドなしのCSVエクスポートのテスト."""
        client = RedmineClient("https://redmine.example.com", "test_api_key")

        issues = [
            {
                "id": 1,
                "subject": "チケット1",
                "status": {"name": "進行中"},
                "priority": {"name": "高"},
                "project": {"name": "プロジェクトA"},
                "tracker": {"name": "バグ"},
                "author": {"name": "田中"},
                "assigned_to": {"name": "鈴木"},
                "category": {"name": "開発"},
                "created_on": "2025-01-01T10:00:00Z",
                "updated_on": "2025-01-02T15:30:00Z",
                "start_date": "2025-01-01",
                "due_date": "2025-01-31",
                "done_ratio": 50,
                "estimated_hours": 8,
                "spent_hours": 4,
            }
        ]

        output_file = tmp_path / "test_no_custom_fields.csv"

        with caplog.at_level(logging.INFO):
            client.export_to_csv(issues, str(output_file.name), str(tmp_path))

        # ファイルが作成されていることを確認
        assert output_file.exists()

        # ログにカスタムフィールド数0が記録されていることを確認
        assert "カスタムフィールド数: 0" in caplog.text

        # CSVの内容を検証
        with output_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 1行のデータがあることを確認
            assert len(rows) == 1

            # ヘッダーは標準フィールドのみであることを確認
            fieldnames = reader.fieldnames
            assert fieldnames is not None
            assert len(fieldnames) == 16  # 標準フィールドのみ

