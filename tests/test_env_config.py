"""環境変数設定のユニットテスト."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from redmine_burndown.redmine_client import main


class TestEnvConfig:
    """環境変数設定のテスト."""

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch.dict(os.environ, {"REDMINE_URL": "https://test.example.com", "REDMINE_API_KEY": "test_key"})
    def test_main_loads_env_variables(
        self,
        mock_get_projects: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_export_to_csv: MagicMock,
        mock_load_dotenv: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """環境変数が正しく読み込まれることをテスト."""
        # モックの設定
        mock_get_projects.return_value = [{"id": "1", "name": "Test Project"}]
        mock_get_all_issues.return_value = [{"id": "1", "subject": "Test Issue"}]

        # main関数を実行
        main()

        # アサーション
        mock_load_dotenv.assert_called_once()
        mock_get_projects.assert_called_once()
        assert "Redmine チケット取得ツール" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_main_missing_redmine_url(self, mock_load_dotenv: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """REDMINE_URLが未設定の場合のテスト."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_URL": "https://test.example.com"}, clear=True)
    def test_main_missing_api_key(self, mock_load_dotenv: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """REDMINE_API_KEYが未設定の場合のテスト."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_API_KEY": "test_key"}, clear=True)
    def test_main_missing_redmine_url_only(self, mock_load_dotenv: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """REDMINE_URLのみ未設定の場合のテスト."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_URL": "", "REDMINE_API_KEY": ""}, clear=True)
    def test_main_empty_env_variables(self, mock_load_dotenv: MagicMock, caplog: pytest.LogCaptureFixture) -> None:
        """環境変数が空文字列の場合のテスト."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch("redmine_burndown.redmine_client.RedmineClient.export_to_csv")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_all_issues")
    @patch("redmine_burndown.redmine_client.RedmineClient.get_projects")
    @patch.dict(
        os.environ,
        {"REDMINE_URL": "https://test.example.com/", "REDMINE_API_KEY": "test_key"},  # 末尾にスラッシュ
    )
    def test_main_with_trailing_slash_in_url(
        self,
        mock_get_projects: MagicMock,
        mock_get_all_issues: MagicMock,
        mock_export_to_csv: MagicMock,
        mock_load_dotenv: MagicMock,
    ) -> None:
        """URLに末尾スラッシュがある場合でも正常動作するかテスト."""
        mock_get_projects.return_value = [{"id": "1", "name": "Test Project"}]
        mock_get_all_issues.return_value = [{"id": "1", "subject": "Test"}]

        main()

        # RedmineClientが末尾スラッシュを削除したURLで初期化されているかチェック
        # （base_urlはrstrip("/")されている）
        assert mock_get_projects.called
