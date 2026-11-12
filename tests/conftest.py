"""Test-session setup.

- Prices are synthetic by default: real ENTSO-E price files may exist locally, so without
  SUNDIAL_FORCE_SYNTHETIC the same tests would behave differently on the author's PC and in CI.
  Tests that need the fixture prices clear it with monkeypatch.delenv.
- A tiny deterministic per-zone data directory is built once per session and SUNDIAL_DATA_DIR
  points at it, so the loaders are exercised on per-zone files independent of local data.
"""
import os

import pytest

from tests.fixture_data import make_fixture_dir

os.environ["SUNDIAL_FORCE_SYNTHETIC"] = "1"


@pytest.fixture(scope="session", autouse=True)
def fixture_data_dir(tmp_path_factory):
    """Build the fixture data dir and point SUNDIAL_DATA_DIR at it for the whole session."""
    path = make_fixture_dir(tmp_path_factory.mktemp("sundial_data"))
    previous = os.environ.get("SUNDIAL_DATA_DIR")
    os.environ["SUNDIAL_DATA_DIR"] = str(path)
    yield path
    if previous is None:
        os.environ.pop("SUNDIAL_DATA_DIR", None)
    else:
        os.environ["SUNDIAL_DATA_DIR"] = previous
