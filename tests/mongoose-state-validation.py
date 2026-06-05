"""Validate Mongoose local state helpers."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_LOCAL_APP_DATA = REPO_ROOT / ".test-localappdata-mongoose-state"
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"


def remove_tree(path: Path) -> None:
    def handle_error(function, failing_path, _exc_info):
        os.chmod(failing_path, stat.S_IWRITE)
        function(failing_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_error)


if TEST_LOCAL_APP_DATA.exists():
    remove_tree(TEST_LOCAL_APP_DATA)
TEST_LOCAL_APP_DATA.mkdir(parents=True)
os.environ["LOCALAPPDATA"] = str(TEST_LOCAL_APP_DATA)

spec = importlib.util.spec_from_file_location("mongoose_cli", MONGOOSE_CLI)
assert_true(spec is not None and spec.loader is not None, "Could not load mongoose.py.")
mongoose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mongoose)

paths = mongoose.ensure_state_layout()
for key in ("root", "bin", "mongoose", "state", "nonSecretConfig", "agentState", "jobs", "logs"):
    assert_true(Path(paths[key]).is_dir(), f"Missing state directory for {key}: {paths[key]}")

state_file = mongoose.NON_SECRET_CONFIG_ROOT / "sample.json"
mongoose.write_json_atomic(state_file, {"name": "sample", "nested": {"enabled": True}})
assert_true(
    mongoose.read_json(state_file) == {"name": "sample", "nested": {"enabled": True}},
    "Atomic JSON read/write did not round trip.",
)

missing_default = mongoose.read_json(mongoose.NON_SECRET_CONFIG_ROOT / "missing.json", {"default": True})
assert_true(missing_default == {"default": True}, "Missing JSON file did not return the default value.")

corrupt_file = mongoose.NON_SECRET_CONFIG_ROOT / "corrupt.json"
corrupt_file.write_text("{", encoding="utf-8")
try:
    mongoose.read_json(corrupt_file)
except ValueError as exc:
    assert_true(str(corrupt_file) in str(exc), "Corrupt JSON error did not include the path.")
else:
    raise AssertionError("Corrupt JSON did not raise ValueError.")

redacted = mongoose.redact_secrets(
    {
        "YNAB_ACCESS_TOKEN": "secret-token",
        "visible": "safe",
        "nested": {"api_key": "secret-key", "name": "Njord"},
    }
)
assert_true(redacted["YNAB_ACCESS_TOKEN"] == "[redacted]", "Token key was not redacted.")
assert_true(redacted["nested"]["api_key"] == "[redacted]", "API key was not redacted.")
assert_true(redacted["visible"] == "safe", "Non-secret key was incorrectly redacted.")

log_path = mongoose.append_log(
    "njord/config",
    "Configured token=secret-token and password:secret-password",
    access_token="secret-token",
    visible="safe",
)
log_record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
assert_true("secret-token" not in json.dumps(log_record), "Log output leaked a token.")
assert_true("secret-password" not in json.dumps(log_record), "Log output leaked a password.")
assert_true(log_record["metadata"]["access_token"] == "[redacted]", "Log metadata was not redacted.")
assert_true(log_record["metadata"]["visible"] == "safe", "Log metadata redacted a safe value.")

old_log = mongoose.LOG_ROOT / "old.jsonl"
old_log.write_text("{}\n", encoding="utf-8")
old_mtime = time.time() - (40 * 24 * 60 * 60)
os.utime(old_log, (old_mtime, old_mtime))
removed = mongoose.cleanup_logs(retention_days=30)
assert_true(old_log in removed, "Expired log file was not reported as removed.")
assert_true(not old_log.exists(), "Expired log file was not removed.")

result = subprocess.run(
    [sys.executable, str(MONGOOSE_CLI), "state", "--init", "--json"],
    check=False,
    capture_output=True,
    text=True,
    env={**os.environ, "LOCALAPPDATA": str(TEST_LOCAL_APP_DATA)},
)
assert_true(result.returncode == 0, f"mongoose state failed: {result.stdout}{result.stderr}")
state_output = json.loads(result.stdout)
assert_true(
    state_output["root"] == str(TEST_LOCAL_APP_DATA / "Agents"),
    "mongoose state reported the wrong root.",
)
assert_true(state_output["version"] == mongoose.MONGOOSE_VERSION, "mongoose state did not report version.")
assert_true(state_output["releaseKind"] == "development", "mongoose state did not report development release kind.")
assert_true(state_output["releaseTag"] == "", "mongoose state should not report a release tag for development builds.")
assert_true(state_output["cliSource"].endswith("mongoose.py"), "mongoose state did not report CLI source.")
assert_true(state_output["registryRevision"] == "missing", "Missing registry revision was not reported cleanly.")
assert_true(state_output["registryStatus"] == "missing", "Missing registry status was not reported cleanly.")

version_result = subprocess.run(
    [sys.executable, str(MONGOOSE_CLI), "--version"],
    check=False,
    capture_output=True,
    text=True,
    env={**os.environ, "LOCALAPPDATA": str(TEST_LOCAL_APP_DATA)},
)
assert_true(version_result.returncode == 0, f"mongoose --version failed: {version_result.stdout}{version_result.stderr}")
assert_true(
    f"mongoose {mongoose.MONGOOSE_VERSION} (development)" in version_result.stdout,
    "mongoose --version did not report the expected version and release kind.",
)

mongoose.CONFIG_PATH.write_text("{", encoding="utf-8")
result = subprocess.run(
    [sys.executable, str(MONGOOSE_CLI), "list"],
    check=False,
    capture_output=True,
    text=True,
    env={**os.environ, "LOCALAPPDATA": str(TEST_LOCAL_APP_DATA)},
)
assert_true(result.returncode != 0, "Corrupted config did not fail.")
assert_true("Could not read JSON file" in result.stderr, "Corrupted config error was not actionable.")
assert_true("Traceback" not in result.stderr, "Corrupted config printed a traceback.")

print("Mongoose state validation passed.")

