import os
from pathlib import Path

import pytest

proj_path = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def setup():
    rtl_path = proj_path / "build/rtl"
    Path(rtl_path).rmdir() if Path(rtl_path).exists() else None
    Path(rtl_path).mkdir(parents=True)
