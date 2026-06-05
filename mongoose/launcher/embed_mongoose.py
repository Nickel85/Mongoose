"""Generate a C include file containing the mongoose Python CLI."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "mongoose" / "mongoose.py"
OUTPUT = ROOT / "mongoose" / "launcher" / "mongoose_py.inc"


def release_metadata() -> tuple[str, str]:
    ref_type = os.environ.get("GITHUB_REF_TYPE", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")
    if ref_type == "tag" and re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.-]+)?", ref_name):
        return "official", ref_name
    return "development", ""


def source_with_release_metadata() -> bytes:
    source = SOURCE.read_text(encoding="utf-8")
    release_kind, release_tag = release_metadata()
    source = re.sub(
        r'^MONGOOSE_RELEASE_KIND\s*=\s*"[^"]*"',
        f'MONGOOSE_RELEASE_KIND = "{release_kind}"',
        source,
        flags=re.MULTILINE,
    )
    source = re.sub(
        r'^MONGOOSE_RELEASE_TAG\s*=\s*"[^"]*"',
        f'MONGOOSE_RELEASE_TAG = "{release_tag}"',
        source,
        flags=re.MULTILINE,
    )
    return source.encode("utf-8")


def main() -> None:
    data = source_with_release_metadata()
    values = ", ".join(str(byte) for byte in data)
    OUTPUT.write_text(
        "static const unsigned char MONGOOSE_PY[] = {"
        + values
        + "};\n"
        + f"static const unsigned int MONGOOSE_PY_LEN = {len(data)};\n",
        encoding="ascii",
    )


if __name__ == "__main__":
    main()

