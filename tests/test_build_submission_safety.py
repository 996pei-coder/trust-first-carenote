import io
import zipfile
from pathlib import Path

import pytest

from scripts.build_submission import write_bytes


def test_archive_member_name_is_data_not_a_shell_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    marker_dollar = tmp_path / "marker-dollar"
    marker_backtick = tmp_path / "marker-backtick"
    marker_semicolon = tmp_path / "marker-semicolon"
    untrusted_name = "evidence-$(touch marker-dollar)-`touch marker-backtick`;touch marker-semicolon"
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        write_bytes(archive, untrusted_name, b"safe payload")

    with zipfile.ZipFile(buffer) as archive:
        assert archive.namelist() == [untrusted_name]
        assert archive.read(untrusted_name) == b"safe payload"

    assert not marker_dollar.exists()
    assert not marker_backtick.exists()
    assert not marker_semicolon.exists()
