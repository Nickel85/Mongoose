"""Validate Mongoose CLI self-update helpers without live network access."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import stat
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_LOCAL_APP_DATA = REPO_ROOT / ".test-localappdata-mongoose-self-update"
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"


def remove_tree(path: Path) -> None:
    def handle_error(function, failing_path, _exc_info):
        os.chmod(failing_path, stat.S_IWRITE)
        function(failing_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_error)


def run_update(mongoose, releases, download=None, replace=None, include_prerelease=False):
    output = io.StringIO()
    downloads: list[Path] = []
    replacements: list[tuple[Path, Path]] = []

    def fake_fetch():
        return releases

    def fake_download(_asset, destination):
        downloads.append(destination)
        if download is not None:
            return download(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake exe")
        return None

    def fake_replace(staged, target):
        replacements.append((staged, target))
        if replace is not None:
            return replace(staged, target)
        return "replaced"

    mongoose.fetch_release_metadata = fake_fetch
    mongoose.download_release_asset = fake_download
    mongoose.replace_installed_executable = fake_replace

    with contextlib.redirect_stdout(output):
        code = mongoose.update_mongoose_cli(include_prerelease=include_prerelease)
    return code, output.getvalue(), downloads, replacements


def run_scoped_update(mongoose, *, registry_only=False, self_only=False, include_prerelease=False):
    output = io.StringIO()
    calls: list[tuple[str, bool | None]] = []

    def fake_registry():
        calls.append(("registry", None))
        print("registry phase ran")
        return 0

    def fake_self_update(include_prerelease=False):
        calls.append(("self", include_prerelease))
        print("self phase ran")
        return 0

    mongoose.update_registry = fake_registry
    mongoose.update_mongoose_cli = fake_self_update

    args = type(
        "Args",
        (),
        {
            "registry_only": registry_only,
            "self_only": self_only,
            "include_prerelease": include_prerelease,
        },
    )()
    with contextlib.redirect_stdout(output):
        code = mongoose.cmd_update(args)
    return code, output.getvalue(), calls


remove_tree(TEST_LOCAL_APP_DATA)
TEST_LOCAL_APP_DATA.mkdir(parents=True)
os.environ["LOCALAPPDATA"] = str(TEST_LOCAL_APP_DATA)

spec = importlib.util.spec_from_file_location("mongoose_cli", MONGOOSE_CLI)
assert_true(spec is not None and spec.loader is not None, "Could not load mongoose.py.")
mongoose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mongoose)

assert_true(mongoose.compare_release_versions("0.1.3", "0.1.2") > 0, "Newer patch did not compare higher.")
assert_true(mongoose.compare_release_versions("0.1.2", "0.1.2") == 0, "Equal versions did not compare equal.")
assert_true(mongoose.compare_release_versions("0.1.2", "0.1.3") < 0, "Older patch did not compare lower.")
assert_true(
    mongoose.compare_release_versions("0.1.2", "0.1.2-alpha") > 0,
    "Stable release should compare higher than prerelease.",
)
assert_true(mongoose.parse_release_version("not-a-version") is None, "Invalid release tag parsed successfully.")

release_current = {
    "tag_name": f"v{mongoose.MONGOOSE_VERSION}",
    "draft": False,
    "prerelease": False,
    "assets": [{"name": "mongoose.exe", "browser_download_url": "https://example.invalid/mongoose.exe"}],
}
release_next = {
    "tag_name": "v0.3.1",
    "draft": False,
    "prerelease": False,
    "assets": [{"name": "mongoose.exe", "browser_download_url": "https://example.invalid/mongoose.exe"}],
}
release_prerelease = {
    "tag_name": "v0.3.2-alpha",
    "draft": False,
    "prerelease": True,
    "assets": [{"name": "mongoose.exe", "browser_download_url": "https://example.invalid/mongoose.exe"}],
}
release_without_asset = {
    "tag_name": "v0.3.1",
    "draft": False,
    "prerelease": False,
    "assets": [],
}

assert_true(
    mongoose.latest_eligible_release([release_prerelease, release_next]) == release_next,
    "Stable self-update should ignore prereleases.",
)
assert_true(
    mongoose.latest_eligible_release([release_prerelease, release_next], include_prerelease=True) == release_prerelease,
    "Prerelease self-update did not choose the newest allowed prerelease.",
)

code, output, downloads, replacements = run_update(mongoose, [release_current])
assert_true(code == 0, f"Already-current update failed: {output}")
assert_true("already current" in output, "Already-current output did not explain the state.")
assert_true(not downloads, "Already-current update should not download an asset.")
assert_true(not replacements, "Already-current update should not replace the executable.")

code, output, downloads, replacements = run_update(mongoose, [release_next])
assert_true(code == 0, f"Update-available path failed: {output}")
assert_true(downloads, "Update-available path did not download the release asset.")
assert_true(replacements, "Update-available path did not replace the executable.")
assert_true(replacements[0][1] == mongoose.installed_mongoose_exe_path(), "Self-update targeted the wrong executable.")
assert_true("Updated Mongoose to 0.3.1" in output, "Successful update output did not report the new version.")

code, output, _downloads, replacements = run_update(mongoose, [release_without_asset])
assert_true(code == 1, "Missing release asset did not fail.")
assert_true("does not include mongoose.exe" in output, "Missing asset output was not actionable.")
assert_true(not replacements, "Missing asset path should not replace the executable.")


def fail_download(_destination):
    raise mongoose.SelfUpdateError("simulated download failure")


code, output, downloads, replacements = run_update(mongoose, [release_next], download=fail_download)
assert_true(code == 1, "Failed download did not fail self-update.")
assert_true(downloads, "Failed download path did not attempt a download.")
assert_true(not replacements, "Failed download path should not replace the executable.")
assert_true("simulated download failure" in output, "Failed download output did not include the error.")


def fail_replace(_staged, _target):
    raise mongoose.SelfUpdateError("simulated replacement failure")


code, output, _downloads, replacements = run_update(mongoose, [release_next], replace=fail_replace)
assert_true(code == 1, "Failed replacement did not fail self-update.")
assert_true(replacements, "Failed replacement path did not attempt replacement.")
assert_true("simulated replacement failure" in output, "Failed replacement output did not include the error.")

code, output, calls = run_scoped_update(mongoose)
assert_true(code == 0, f"Default update orchestration failed: {output}")
assert_true(calls == [("registry", None), ("self", False)], "Default update did not run registry then CLI phases.")
assert_true("Update summary" in output, "Default update did not print a summary.")
assert_true("Registry:" in output and "Mongoose CLI:" in output, "Default update summary missed phase labels.")

code, _output, calls = run_scoped_update(mongoose, registry_only=True)
assert_true(code == 0, "Registry-only update failed.")
assert_true(calls == [("registry", None)], "Registry-only update should not run the CLI phase.")

code, _output, calls = run_scoped_update(mongoose, self_only=True, include_prerelease=True)
assert_true(code == 0, "Self-only update failed.")
assert_true(calls == [("self", True)], "Self-only update did not pass prerelease allowance.")

code, output, calls = run_scoped_update(mongoose, registry_only=True, include_prerelease=True)
assert_true(code == 1, "Registry-only update with prerelease flag should fail.")
assert_true(not calls, "Invalid registry-only prerelease flag should not run update phases.")
assert_true("--include-prerelease" in output, "Invalid flag output did not name the flag.")

parser = mongoose.build_parser()
self_only_args = parser.parse_args(["update", "--self-only"])
assert_true(self_only_args.self_only and not self_only_args.registry_only, "--self-only did not parse as self-only.")
self_alias_args = parser.parse_args(["update", "--self"])
assert_true(self_alias_args.self_only and not self_alias_args.registry_only, "--self did not remain a self-only alias.")

print("Mongoose self-update validation passed.")
