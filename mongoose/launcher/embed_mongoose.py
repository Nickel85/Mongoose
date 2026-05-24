"""Generate a C include file containing the mongoose Python CLI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "mongoose" / "mongoose.py"
OUTPUT = ROOT / "mongoose" / "launcher" / "mongoose_py.inc"


def main() -> None:
    data = SOURCE.read_bytes()
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

