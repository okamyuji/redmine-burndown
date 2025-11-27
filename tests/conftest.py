"""pytest設定とフィクスチャ."""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _configure_logging(caplog: pytest.LogCaptureFixture) -> None:
    """各テスト前にロギングを設定してcaplogでキャプチャ可能にする."""
    caplog.set_level(logging.INFO)


@pytest.fixture
def temp_csv_file() -> Iterator[Path]:
    """一時CSVファイルを作成するフィクスチャ."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", encoding="utf-8") as f:
        temp_path = Path(f.name)
        yield temp_path
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_csv_file(temp_csv_file: Path) -> Path:
    """サンプルCSVファイルを作成するフィクスチャ."""
    content = """id,project,tracker,status,priority,subject,author,assigned_to,category,created_on,updated_on,start_date,due_date,done_ratio,estimated_hours,spent_hours
1,Project A,Bug,新規,高,Issue 1,User A,User B,Category A,2024-01-01T10:00:00Z,2024-01-08T10:00:00Z,2024-01-01,2024-01-10,0,8.0,0.0
2,Project A,Feature,進行中,中,Issue 2,User A,User C,Category B,2024-01-02T10:00:00Z,2024-01-08T10:00:00Z,2024-01-02,2024-01-15,50,16.0,8.0
3,Project B,Bug,完了,高,Issue 3,User B,User A,Category A,2024-01-03T10:00:00Z,2024-01-15T10:00:00Z,2024-01-03,2024-01-12,100,4.0,4.0
4,Project A,Task,終了,低,Issue 4,User C,User B,Category C,2024-01-05T10:00:00Z,2024-01-22T10:00:00Z,2024-01-05,2024-01-20,100,12.0,12.0
"""
    temp_csv_file.write_text(content, encoding="utf-8")
    return temp_csv_file

