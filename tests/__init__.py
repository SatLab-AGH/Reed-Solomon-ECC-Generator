import os
from pathlib import Path

import pytest


proj_path = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def setup():
    rtl_path = proj_path / "build/rtl"
    os.rmdir(rtl_path) if os.path.exists(rtl_path) else None
    os.makedirs(rtl_path)
