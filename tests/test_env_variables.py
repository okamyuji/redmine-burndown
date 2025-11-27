"""環境変数による設定機能のテスト."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

from redmine_burndown.redmine_client import main


class TestEnvironmentVariables:
    """環境変数による設定のテスト."""

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_PROJECT_ID": "598",
            "REDMINE_MAX_ISSUES": "500",
            "REDMINE_STATUS_ID": "open",
        },
    )
    def test_env_with_project_and_max_issues(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """環境変数でプロジェクトIDと取得件数を指定（全件取得ではないがページネーション必要）."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        # 500件を取得するためget_all_issuesが呼ばれる
        mock_get_all_issues.return_value = [{"id": str(i), "subject": f"Test{i}"} for i in range(1, 501)]

        # get_issuesとget_all_issuesの両方をモック
        with patch("redmine_burndown.redmine_client.RedmineClient.get_issues") as mock_get_issues:
            mock_get_issues.return_value = {
                "total_count": 500,
                "issues": [{"id": str(i), "subject": f"Test{i}"} for i in range(1, 101)],
            }
            main()

        assert "プロジェクトID: 598" in caplog.text
        assert "取得件数上限: 500" in caplog.text
        assert "ステータス: open" in caplog.text
        # get_all_issuesが呼ばれることを確認
        mock_get_all_issues.assert_called_once()
        call_kwargs = mock_get_all_issues.call_args[1]
        assert call_kwargs["project_id"] == "598"
        assert call_kwargs["status_id"] == "open"
        assert call_kwargs["max_issues"] == 500

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_PROJECT_ID": "",
            "REDMINE_MAX_ISSUES": "",
            "REDMINE_STATUS_ID": "",
        },
    )
    def test_env_empty_means_all(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """環境変数が空の場合は全件取得."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        mock_get_all_issues.return_value = [
            {"id": "1", "subject": "Test1"},
            {"id": "2", "subject": "Test2"},
        ]

        main()

        assert "プロジェクトID: 全プロジェクト" in caplog.text
        assert "取得件数上限: 全件" in caplog.text
        assert "ステータス: *" in caplog.text
        mock_get_all_issues.assert_called_once()
        call_kwargs = mock_get_all_issues.call_args[1]
        assert call_kwargs["project_id"] is None
        assert call_kwargs["status_id"] == "*"
        assert call_kwargs["max_issues"] == 10000

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_PROJECT_ID": "598,631,728",
            "REDMINE_MAX_ISSUES": "1000",
            "REDMINE_STATUS_ID": "1,2,3",
        },
    )
    def test_env_with_multiple_values(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """環境変数で複数の値を指定（カンマ区切り）."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        mock_get_all_issues.return_value = [{"id": "1", "subject": "Test"}]

        main()

        assert "プロジェクトID: 598,631,728" in caplog.text
        assert "取得件数上限: 1000" in caplog.text
        assert "ステータス: 1,2,3" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_MAX_ISSUES": "50",
        },
    )
    def test_env_max_issues_below_api_limit(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """取得件数がAPI上限（100件）未満の場合."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        # get_issuesをモック（get_all_issuesではない）
        with patch("redmine_burndown.redmine_client.RedmineClient.get_issues") as mock_get_issues:
            mock_get_issues.return_value = {
                "total_count": 50,
                "issues": [{"id": str(i), "subject": f"Test{i}"} for i in range(1, 51)],
            }
            main()
            mock_get_issues.assert_called_once()
            call_kwargs = mock_get_issues.call_args[1]
            assert call_kwargs["limit"] == 50  # min(50, 100)

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_MAX_ISSUES": "200",
        },
    )
    def test_env_max_issues_requires_pagination(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """取得件数が100件超でページネーション必要."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        mock_get_issues.return_value = {
            "total_count": 250,
            "issues": [{"id": str(i), "subject": f"Test{i}"} for i in range(1, 101)],
        }
        mock_get_all_issues.return_value = [{"id": str(i), "subject": f"Test{i}"} for i in range(1, 201)]

        main()

        # get_issuesで最初の100件取得
        mock_get_issues.assert_called_once()
        # 100件 < 200件 かつ 100件 < 250件なので get_all_issues が呼ばれる
        mock_get_all_issues.assert_called_once()
        call_kwargs = mock_get_all_issues.call_args[1]
        assert call_kwargs["max_issues"] == 200

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_MAX_ISSUES": "invalid",
        },
    )
    def test_env_invalid_max_issues(
        self,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """取得件数に不正な値を指定した場合."""
        with pytest.raises(ValueError, match="invalid literal for int"):
            main()

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_STATUS_ID": "closed",
        },
    )
    def test_env_status_closed_only(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """ステータスフィルターで完了のみ指定."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        mock_get_all_issues.return_value = [{"id": "1", "subject": "Test"}]

        main()

        assert "ステータス: closed" in caplog.text
        call_kwargs = mock_get_all_issues.call_args[1]
        assert call_kwargs["status_id"] == "closed"

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch.dict(
        os.environ,
        {
            "REDMINE_URL": "https://test.example.com",
            "REDMINE_API_KEY": "test_key",
            "REDMINE_MAX_ISSUES": "   ",  # 空白のみ
        },
    )
    def test_env_whitespace_only_means_all(
        self,
        mock_export: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_get_projects: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """環境変数が空白のみの場合も全件取得."""
        mock_get_projects.return_value = [{"id": "598", "name": "Test Project"}]
        mock_get_all_issues.return_value = [{"id": "1", "subject": "Test"}]

        main()

        assert "取得件数上限: 全件" in caplog.text
        call_kwargs = mock_get_all_issues.call_args[1]
        assert call_kwargs["max_issues"] == 10000

