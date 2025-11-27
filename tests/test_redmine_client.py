"""RedmineClientのユニットテスト."""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar
from unittest.mock import Mock, patch

import pytest
import requests

from redmine_burndown.redmine_client import RedmineClient, main


class TestRedmineClient:
    """RedmineClientクラスのテスト."""

    base_url: ClassVar[str] = "https://example.com"
    api_key: ClassVar[str] = "test_api_key"
    headers: ClassVar[dict[str, str]] = {"X-Redmine-API-Key": "test_api_key", "Content-Type": "application/json"}

    @pytest.fixture
    def client(self) -> RedmineClient:
        """テスト用のRedmineClientインスタンスを作成."""
        return RedmineClient(self.base_url, self.api_key)

    def test_init(self, client: RedmineClient) -> None:
        """初期化が正しく動作することを確認."""
        assert client.base_url == self.base_url
        assert client.api_key == self.api_key
        assert client.headers["X-Redmine-API-Key"] == self.api_key
        assert client.headers["Content-Type"] == "application/json"

    def test_init_strips_trailing_slash(self) -> None:
        """URLの末尾のスラッシュが削除されることを確認."""
        client = RedmineClient("https://example.com/", "test_key")
        assert client.base_url == "https://example.com"

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_success(self, mock_get: Mock, client: RedmineClient) -> None:
        """get_issuesが正常にAPIレスポンスを返すことを確認（カスタムフィールド含む）."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [{"id": 1, "subject": "Test"}],
            "total_count": 1,
        }
        mock_get.return_value = mock_response

        result = client.get_issues()

        assert result == {"issues": [{"id": 1, "subject": "Test"}], "total_count": 1}
        mock_get.assert_called_once_with(
            f"{self.base_url}/issues.json",
            headers=self.headers,
            params={"status_id": "*", "limit": 100, "offset": 0, "include": "custom_fields"},
            verify=True,
            timeout=30,
        )

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_with_project_id(self, mock_get: Mock, client: RedmineClient) -> None:
        """project_idを指定した場合のテスト."""
        mock_response = Mock()
        mock_response.json.return_value = {"issues": [], "total_count": 0}
        mock_get.return_value = mock_response

        client.get_issues(project_id="test_project")

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["project_id"] == "test_project"

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_with_custom_params(self, mock_get: Mock, client: RedmineClient) -> None:
        """カスタムパラメータでの呼び出しテスト."""
        mock_response = Mock()
        mock_response.json.return_value = {"issues": [], "total_count": 0}
        mock_get.return_value = mock_response

        client.get_issues(status_id="open", limit=50, offset=10)

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["status_id"] == "open"
        assert call_kwargs["params"]["limit"] == 50
        assert call_kwargs["params"]["offset"] == 10

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_request_exception(self, mock_get: Mock, client: RedmineClient, caplog: Any) -> None:
        """リクエスト例外が発生した場合のテスト."""
        with caplog.at_level(logging.ERROR):
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")

            result = client.get_issues()

            assert result == {"issues": [], "total_count": 0}
            assert "チケット取得エラー" in caplog.text

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_http_error(self, mock_get: Mock, client: RedmineClient) -> None:
        """HTTPエラーが発生した場合のテスト."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = client.get_issues()

        assert result == {"issues": [], "total_count": 0}

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_issues_invalid_response(self, mock_get: Mock, client: RedmineClient) -> None:
        """無効なレスポンスの場合のテスト."""
        mock_response = Mock()
        mock_response.json.return_value = "invalid"
        mock_get.return_value = mock_response

        with pytest.raises(TypeError):
            client.get_issues()

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_all_issues_single_page(self, mock_get: Mock, client: RedmineClient) -> None:
        """単一ページでの全チケット取得テスト."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [{"id": i} for i in range(50)],
            "total_count": 50,
        }
        mock_get.return_value = mock_response

        result = client.get_all_issues(max_issues=100)

        assert len(result) == 50

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_all_issues_multiple_pages(self, mock_get: Mock, caplog: Any) -> None:
        """全チケット取得（複数ページ）のテスト."""
        with caplog.at_level(logging.INFO):
            client = RedmineClient(self.base_url, self.api_key)
            responses = [
                {"issues": [{"id": i} for i in range(100)], "total_count": 250},
                {"issues": [{"id": i} for i in range(100, 200)], "total_count": 250},
                {"issues": [{"id": i} for i in range(200, 250)], "total_count": 250},
            ]

            def side_effect(*args: Any, **kwargs: Any) -> Mock:
                mock_response = Mock()
                mock_response.json.return_value = responses.pop(0) if responses else {"issues": [], "total_count": 250}
                return mock_response

            mock_get.side_effect = side_effect

            result = client.get_all_issues(max_issues=1000)

            assert len(result) == 250
            assert mock_get.call_count == 3
            assert "チケット取得開始" in caplog.text
            assert "チケット取得完了" in caplog.text

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_all_issues_with_max_limit(self, mock_get: Mock) -> None:
        """max_issuesで制限される場合のテスト."""
        client = RedmineClient(self.base_url, self.api_key)
        mock_response_page1 = Mock()
        mock_response_page1.json.return_value = {
            "issues": [{"id": i} for i in range(100)],
            "total_count": 500,
        }
        mock_response_page2 = Mock()
        mock_response_page2.json.return_value = {
            "issues": [{"id": i} for i in range(100, 200)],
            "total_count": 500,
        }
        mock_get.side_effect = [mock_response_page1, mock_response_page2]

        result = client.get_all_issues(max_issues=150)

        assert len(result) == 150
        assert mock_get.call_count == 2

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_all_issues_empty_response(self, mock_get: Mock) -> None:
        """空のレスポンスの場合のテスト."""
        client = RedmineClient(self.base_url, self.api_key)
        mock_response = Mock()
        mock_response.json.return_value = {"issues": [], "total_count": 0}
        mock_get.return_value = mock_response

        result = client.get_all_issues(max_issues=100)

        assert len(result) == 0

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_all_issues_invalid_total_count(self, mock_get: Mock) -> None:
        """total_countが不正な値の場合のテスト."""
        client = RedmineClient(self.base_url, self.api_key)
        mock_response = Mock()
        mock_response.json.return_value = {
            "issues": [{"id": 1}],
            "total_count": "invalid",
        }
        mock_get.return_value = mock_response

        result = client.get_all_issues(max_issues=100)

        assert len(result) == 1

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_projects_success(self, mock_get: Mock, client: RedmineClient) -> None:
        """get_projectsが正常にプロジェクト一覧を返すことを確認."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "projects": [{"id": 1, "name": "Test Project"}],
        }
        mock_get.return_value = mock_response

        result = client.get_projects()

        assert result == [{"id": 1, "name": "Test Project"}]

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_projects_request_exception(self, mock_get: Mock, client: RedmineClient, caplog: Any) -> None:
        """get_projectsでリクエスト例外が発生した場合のテスト."""
        with caplog.at_level(logging.ERROR):
            mock_get.side_effect = requests.exceptions.RequestException("Network error")

            result = client.get_projects()

            assert result == []
            assert "プロジェクト取得エラー" in caplog.text

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_projects_invalid_response_type(self, mock_get: Mock, client: RedmineClient) -> None:
        """get_projectsで無効なレスポンスタイプの場合のテスト."""
        mock_response = Mock()
        mock_response.json.return_value = "invalid"
        mock_get.return_value = mock_response

        with pytest.raises(TypeError):
            client.get_projects()

    @patch("redmine_burndown.redmine_client.requests.get")
    def test_get_projects_invalid_projects_type(self, mock_get: Mock, client: RedmineClient) -> None:
        """get_projectsでprojectsが不正な型の場合のテスト."""
        mock_response = Mock()
        mock_response.json.return_value = {"projects": "invalid"}
        mock_get.return_value = mock_response

        result = client.get_projects()

        assert result == []

    def test_export_to_csv_success(self, tmp_path: Any, client: RedmineClient, caplog: Any) -> None:
        """CSVエクスポートが成功する場合のテスト."""
        with caplog.at_level(logging.INFO):
            issues = [
                {
                    "id": 1,
                    "subject": "Test Issue",
                    "project": {"name": "Project A"},
                    "tracker": {"name": "Bug"},
                    "status": {"name": "New"},
                    "priority": {"name": "High"},
                    "author": {"name": "User A"},
                    "assigned_to": {"name": "User B"},
                    "category": {"name": "Category A"},
                    "created_on": "2024-01-01",
                    "updated_on": "2024-01-02",
                    "start_date": "2024-01-01",
                    "due_date": "2024-01-10",
                    "done_ratio": 50,
                    "estimated_hours": 8.0,
                    "spent_hours": 4.0,
                }
            ]

            output_dir = str(tmp_path / "output")
            client.export_to_csv(issues, "test.csv", output_dir=output_dir)

            assert "CSVファイルに出力しました" in caplog.text
            assert "1件" in caplog.text
            assert (tmp_path / "output" / "test.csv").exists()

    def test_export_to_csv_with_missing_fields(self, tmp_path: Any, client: RedmineClient) -> None:
        """フィールドが不足しているissuesのCSVエクスポートのテスト."""
        issues = [{"id": 1, "subject": "Test Issue"}]

        output_dir = str(tmp_path / "output")
        client.export_to_csv(issues, "test.csv", output_dir=output_dir)

        assert (tmp_path / "output" / "test.csv").exists()

    def test_export_to_csv_empty_issues(self, client: RedmineClient, caplog: Any) -> None:
        """空のissuesリストの場合のテスト."""
        with caplog.at_level(logging.WARNING):
            client.export_to_csv([])

            assert "エクスポートするチケットがありません" in caplog.text

    def test_export_to_csv_default_filename(self, tmp_path: Any, client: RedmineClient, caplog: Any) -> None:
        """デフォルトのファイル名でのエクスポートテスト."""
        with caplog.at_level(logging.INFO):
            issues = [{"id": 1}]

            output_dir = str(tmp_path / "output")
            client.export_to_csv(issues, output_dir=output_dir)

            assert "CSVファイルに出力しました" in caplog.text
            assert (tmp_path / "output" / "issues.csv").exists()


@patch.dict(os.environ, {"REDMINE_URL": "https://test.com", "REDMINE_API_KEY": "test_key"})
@patch("redmine_burndown.redmine_client.RedmineClient")
def test_main_success(mock_client_class: Mock, caplog: Any) -> None:
    """main関数の正常実行テスト."""
    with caplog.at_level(logging.INFO):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get_projects.return_value = [
            {"id": i, "name": f"Project {i}"} for i in range(1, 12)
        ]

        mock_client.get_all_issues.return_value = [{"id": i, "subject": f"Issue {i}"} for i in range(1, 6)]

        main()

        assert "Redmine チケット取得ツール" in caplog.text
        assert "プロジェクト数: 11件" in caplog.text
        assert "総チケット数: 5件" in caplog.text
        assert "取得件数: 5件" in caplog.text
        assert "処理が完了しました" in caplog.text


@patch.dict(os.environ, {"REDMINE_URL": "https://test.com", "REDMINE_API_KEY": "test_key"})
@patch("redmine_burndown.redmine_client.RedmineClient")
def test_main_no_projects(mock_client_class: Mock, caplog: Any) -> None:
    """プロジェクトが取得できない場合のテスト."""
    with caplog.at_level(logging.WARNING):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_projects.return_value = []
        mock_client.get_all_issues.return_value = []

        main()

        assert "プロジェクトが取得できませんでした" in caplog.text


@patch.dict(os.environ, {"REDMINE_URL": "https://test.com", "REDMINE_API_KEY": "test_key"})
@patch("redmine_burndown.redmine_client.RedmineClient")
def test_main_no_issues(mock_client_class: Mock, caplog: Any) -> None:
    """チケットが取得できない場合のテスト."""
    with caplog.at_level(logging.WARNING):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get_projects.return_value = [{"id": 1, "name": "Project 1"}]
        mock_client.get_all_issues.return_value = []

        main()

        assert "チケットが取得できませんでした" in caplog.text


@patch.dict(os.environ, {"REDMINE_URL": "https://test.com", "REDMINE_API_KEY": "test_key"})
@patch("redmine_burndown.redmine_client.RedmineClient")
def test_main_few_projects(mock_client_class: Mock, caplog: Any) -> None:
    """プロジェクトが10件以下の場合のテスト."""
    with caplog.at_level(logging.INFO):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get_projects.return_value = [
            {"id": i, "name": f"Project {i}"} for i in range(1, 6)
        ]
        mock_client.get_all_issues.return_value = []

        main()

        assert "プロジェクト数: 5件" in caplog.text
        assert "... 他" not in caplog.text


@patch("redmine_burndown.redmine_client.requests.get")
def test_get_all_issues_reaches_total_count_exactly(mock_get: Mock) -> None:
    """total_countに到達して停止する場合のテスト."""
    client = RedmineClient("https://example.com", "test_key")

    mock_response = Mock()
    mock_response.json.return_value = {
        "issues": [{"id": i} for i in range(100)],
        "total_count": 100,
    }
    mock_get.return_value = mock_response

    result = client.get_all_issues(max_issues=200)

    assert len(result) == 100
    assert mock_get.call_count == 1


@patch("redmine_burndown.redmine_client.requests.get")
def test_get_all_issues_stops_at_total_before_max(mock_get: Mock) -> None:
    """total_countによる停止条件のテスト（分岐カバレッジ100%達成）."""
    client = RedmineClient("https://example.com", "test_key")

    responses = [
        {"issues": [{"id": i} for i in range(100)], "total_count": 150},
        {"issues": [{"id": i} for i in range(100, 150)], "total_count": 150},
    ]

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        mock_response = Mock()
        mock_response.json.return_value = responses.pop(0) if responses else {"issues": [], "total_count": 150}
        return mock_response

    mock_get.side_effect = side_effect

    result = client.get_all_issues(max_issues=500)

    assert len(result) == 150
    assert mock_get.call_count == 2


def test_export_to_csv_creates_directory(tmp_path: Any) -> None:
    """出力ディレクトリが存在しない場合に作成されることのテスト."""
    client = RedmineClient("https://example.com", "test_key")
    issues = [{"id": 1, "subject": "Test"}]

    output_dir = str(tmp_path / "new_output" / "subdir")
    client.export_to_csv(issues, "test.csv", output_dir=output_dir)

    assert (tmp_path / "new_output" / "subdir").exists()
    assert (tmp_path / "new_output" / "subdir" / "test.csv").exists()

