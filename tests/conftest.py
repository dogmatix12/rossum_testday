import json
from pathlib import Path

import pytest


def load_file_content(filename: str) -> str | dict:
    with Path.open(Path("tests", filename)) as f:
        return json.loads(f.read()) if filename.endswith(".json") else f.read()


@pytest.fixture(scope="module")
def sample_annotation_payload():
    return load_file_content("export-6394865.json")
