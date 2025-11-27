"""環境変数検証のユニットテスト（sys.exit対応）."""

from __future__ import annotations

import logging
import os
from typing import Any
from unittest.mock import patch

import pytest

from redmine_burndown.redmine_client import main


class TestEnvValidation:
    """環境変数検証とsys.exitのテスト."""

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_main_exits_when_env_not_set(self, mock_load_dotenv: Any, caplog: Any) -> None:
        """環境変数未設定時にsys.exit(1)で終了することを確認."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_URL": "https://test.com"}, clear=True)
    def test_main_exits_when_api_key_missing(self, mock_load_dotenv: Any, caplog: Any) -> None:
        """APIキーのみ未設定時にsys.exit(1)で終了することを確認."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_API_KEY": "test_key"}, clear=True)
    def test_main_exits_when_url_missing(self, mock_load_dotenv: Any, caplog: Any) -> None:
        """URLのみ未設定時にsys.exit(1)で終了することを確認."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            assert "環境変数が設定されていません" in caplog.text

    @patch("redmine_burndown.redmine_client.load_dotenv")
    @patch.dict(os.environ, {"REDMINE_URL": "", "REDMINE_API_KEY": ""}, clear=True)
    def test_main_exits_when_env_empty(self, mock_load_dotenv: Any, caplog: Any) -> None:
        """環境変数が空文字列の場合にsys.exit(1)で終了することを確認."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            assert "環境変数が設定されていません" in caplog.text

