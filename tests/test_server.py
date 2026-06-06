"""Unit tests for server-side input validation (no API calls)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from server import analyze_skin_image


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        run(analyze_skin_image("/nonexistent/path/face.jpg"))


def test_unsupported_extension(tmp_path):
    f = tmp_path / "image.bmp"
    f.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Unsupported format"):
        run(analyze_skin_image(str(f)))


def test_not_a_file(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        run(analyze_skin_image(str(tmp_path)))


def test_file_too_large(tmp_path):
    f = tmp_path / "large.jpg"
    f.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="10 MB"):
        run(analyze_skin_image(str(f)))


def test_invalid_format(tmp_path):
    f = tmp_path / "face.jpg"
    f.write_bytes(b"fake")
    with pytest.raises(ValueError, match="format"):
        run(analyze_skin_image(str(f), format="xml"))


def test_mixed_dst_actions_rejected(tmp_path):
    f = tmp_path / "face.jpg"
    f.write_bytes(b"fake")
    with pytest.raises(ValueError, match="cannot be mixed"):
        run(analyze_skin_image(str(f), dst_actions=["hd_acne", "acne"]))


def test_success_returns_json(tmp_path):
    """Happy path: mocks the API layer, checks JSON is returned."""
    f = tmp_path / "face.jpg"
    f.write_bytes(b"fake-jpeg-data")

    fake_result = {"task_status": "success", "results": {"hd_acne": {"score": 0.1}}}

    with patch("server.analyze_skin_v21", new=AsyncMock(return_value=fake_result)):
        result = run(analyze_skin_image(str(f), dst_actions=["hd_acne"]))

    import json
    parsed = json.loads(result)
    assert parsed["task_status"] == "success"
    assert "results" in parsed
