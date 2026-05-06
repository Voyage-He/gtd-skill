from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def temp_gtd_dir() -> Iterator[Path]:
    old_gtd = os.environ.get("GTD_DIR")
    with tempfile.TemporaryDirectory() as directory:
        os.environ["GTD_DIR"] = directory
        try:
            yield Path(directory)
        finally:
            if old_gtd is None:
                os.environ.pop("GTD_DIR", None)
            else:
                os.environ["GTD_DIR"] = old_gtd


def decode(result: str) -> dict:
    assert isinstance(result, str)
    return json.loads(result)
