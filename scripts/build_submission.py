"""Build code-only and complete candidate submission ZIP archives."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "submission"
CODE_ZIP = OUTPUT / "trust-first-carenote-code.zip"
FINAL_ZIP = OUTPUT / "Li_Peiheng_Nightingale_Submission.zip"
FIXED_TIME = (2026, 8, 26, 12, 0, 0)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def code_files() -> list[Path]:
    patterns = [
        ".gitignore",
        "ATTRIBUTION.txt",
        "README.md",
        "pyproject.toml",
        "app/**/*.py",
        "app/**/*.html",
        "app/**/*.css",
        "app/**/*.js",
        "tests/**/*.py",
        "scripts/*.py",
        "docs/*.md",
        "docs/diagrams/*.png",
        "output/pdf/trust-first-carenote-technical-brief.pdf",
    ]
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in ROOT.glob(pattern) if path.is_file())
    private_or_candidate_only = {
        ROOT / "scripts/build_resume.py",
        ROOT / "docs/RESUME_FINAL_CONTENT.md",
        ROOT / "docs/SUBMISSION_CHECKLIST.md",
    }
    files.difference_update(private_or_candidate_only)
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def build_code_zip() -> tuple[bytes, str]:
    file_payloads = []
    for path in code_files():
        name = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        if name == "README.md":
            readme = data.decode("utf-8")
            readme = "\n".join(
                line
                for line in readme.splitlines()
                if "Tailored one-page resume" not in line
                and "Tailored resume content source" not in line
            )
            data = (readme + "\n").encode("utf-8")
        file_payloads.append((name, data))
    manifest_lines = [f"{digest(data)}  {name}" for name, data in file_payloads]
    manifest_lines.append("")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in file_payloads:
            write_bytes(archive, f"trust-first-carenote/{name}", data)
        write_bytes(
            archive,
            "trust-first-carenote/SUBMISSION_MANIFEST.txt",
            "\n".join(manifest_lines).encode("utf-8"),
        )
    payload = buffer.getvalue()
    CODE_ZIP.write_bytes(payload)
    return payload, digest(payload)


def build_final_zip(code_payload: bytes, code_sha: str) -> None:
    attachments = {
        "Li_Peiheng_Nightingale_Resume.pdf": ROOT
        / "output/pdf/Li_Peiheng_Nightingale_Resume.pdf",
        "Trust-first_CareNote_Technical_Brief.pdf": ROOT
        / "output/pdf/trust-first-carenote-technical-brief.pdf",
        "architecture.png": ROOT / "docs/diagrams/architecture.png",
        "data-model.png": ROOT / "docs/diagrams/data-model.png",
        "DEMO_SCRIPT.md": ROOT / "docs/DEMO_SCRIPT.md",
        "RECORDING_RUNBOOK.md": ROOT / "docs/RECORDING_RUNBOOK.md",
        "ATTRIBUTION.txt": ROOT / "ATTRIBUTION.txt",
    }
    missing = [str(path) for path in attachments.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required submission files: " + ", ".join(missing))

    payloads = {name: path.read_bytes() for name, path in attachments.items()}
    manifest = [
        "Nightingale 72HR Build - submission bundle",
        "Candidate: Li Peiheng",
        "",
        f"{code_sha}  trust-first-carenote-code.zip",
        *[f"{digest(data)}  {name}" for name, data in sorted(payloads.items())],
        "",
        "Pending outside this archive: final demo video or hosted video link.",
        "No email has been sent and no external upload has been performed.",
        "",
    ]
    with zipfile.ZipFile(FINAL_ZIP, "w") as archive:
        write_bytes(archive, "trust-first-carenote-code.zip", code_payload)
        for name, data in sorted(payloads.items()):
            write_bytes(archive, name, data)
        write_bytes(archive, "SUBMISSION_MANIFEST.txt", "\n".join(manifest).encode("utf-8"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    code_payload, code_sha = build_code_zip()
    build_final_zip(code_payload, code_sha)
    print(f"Code archive: {CODE_ZIP} ({CODE_ZIP.stat().st_size} bytes)")
    print(f"Submission bundle: {FINAL_ZIP} ({FINAL_ZIP.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
