from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_txt() -> Path:
    return FIXTURES / "sample.txt"


@pytest.fixture
def sample_md() -> Path:
    return FIXTURES / "sample.md"


@pytest.fixture
def sample_html() -> Path:
    return FIXTURES / "sample.html"


@pytest.fixture
def sample_digital_pdf() -> Path:
    return FIXTURES / "sample_digital.pdf"


@pytest.fixture
def sample_scanned_pdf() -> Path:
    return FIXTURES / "sample_scanned.pdf"


@pytest.fixture
def sample_csv() -> Path:
    return FIXTURES / "sample.csv"


@pytest.fixture
def sample_json() -> Path:
    return FIXTURES / "sample.json"


@pytest.fixture
def sample_py() -> Path:
    return FIXTURES / "sample.py"
