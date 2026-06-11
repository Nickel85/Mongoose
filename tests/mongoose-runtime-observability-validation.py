"""Validate v0.6 runtime observability and guided LLM setup."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"
TEST_LOCAL_APP_DATA = REPO_ROOT / ".test-localappdata-mongoose-runtime"
FIXTURE_ROOT = REPO_ROOT / ".test-mongoose-runtime-fixtures"


def remove_tree(path: Path) -> None:
    def handle_error(function, failing_path, _exc_info):
        os.chmod(failing_path, stat.S_IWRITE)
        function(failing_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_error)


def run_mongoose(*args: str, check: bool = True, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "LOCALAPPDATA": str(TEST_LOCAL_APP_DATA),
        **(extra_env or {}),
    }
    result = subprocess.run(
        [sys.executable, str(MONGOOSE_CLI), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"mongoose {' '.join(args)} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


remove_tree(TEST_LOCAL_APP_DATA)
remove_tree(FIXTURE_ROOT)
fixture_agent = FIXTURE_ROOT / "agents" / "observer"
fixture_agent.mkdir(parents=True)
(fixture_agent / "agent.py").write_text(
    """from __future__ import annotations

import os
import sys
from pathlib import Path

context = os.environ.get("MONGOOSE_RUNTIME_CONTEXT", "")
if not context or not Path(context).exists():
    print("missing runtime context", file=sys.stderr)
    raise SystemExit(2)
print("observer args:", " ".join(sys.argv[1:]))
print("job id:", os.environ.get("MONGOOSE_JOB_ID", ""))
raise SystemExit(0)
""",
    encoding="utf-8",
)
(fixture_agent / "agent.json").write_text(
    json.dumps(
        {
            "schemaVersion": 1,
            "id": "observer",
            "commandName": "Observer",
            "displayName": "Observer",
            "version": "0.1.0",
            "entrypointPath": "agent.py",
            "example": "hello",
            "description": "Runtime observability fixture.",
            "taskTypes": ["diagnostic"],
            "capabilities": [
                {
                    "name": "observe",
                    "displayName": "Observe",
                    "description": "Print runtime context details.",
                    "entrypointPath": "agent.py",
                    "taskTypes": ["diagnostic", "observe"],
                    "configuration": {"required": [], "optional": [], "secretRefs": []},
                    "llm": {"mode": "none"},
                }
            ],
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

run_mongoose("setup", "--registry-root", str(REPO_ROOT))
run_mongoose("install", str(fixture_agent))

fake = run_mongoose("llm", "setup", "--provider", "fake", "--name", "fake-main", "--model", "fake-chat", "--default", "--yes")
assert_true("LLM provider reachable" in fake.stdout, "Fake setup did not ping successfully.")

run_mongoose(
    "llm",
    "setup",
    "--provider",
    "openai",
    "--name",
    "openai-main",
    "--model",
    "gpt-test",
    "--api-key-env",
    "OPENAI_API_KEY",
    "--skip-ping",
    "--yes",
    extra_env={"OPENAI_API_KEY": "secret-token-value"},
)
profiles_path = TEST_LOCAL_APP_DATA / "Agents" / "state" / "llm" / "profiles.json"
profiles_text = profiles_path.read_text(encoding="utf-8")
assert_true("OPENAI_API_KEY" in profiles_text, "Profile did not store the API-key environment variable name.")
assert_true("secret-token-value" not in profiles_text, "Profile leaked the API-key value.")

local = run_mongoose(
    "llm",
    "setup",
    "--provider",
    "ollama",
    "--name",
    "ollama-local",
    "--endpoint",
    "http://127.0.0.1:9/api/tags",
    "--skip-ping",
    "--yes",
)
assert_true("ollama pull llama3.2" in local.stdout, "Unreachable Ollama setup did not print the model pull next step.")

run_mongoose("runtime", "start")
runtime_status = json.loads(run_mongoose("runtime", "status", "--json").stdout)
assert_true(runtime_status["runtime"]["status"] == "running", "Runtime start did not update status.")

run_result = run_mongoose("run", "Observer", "hello")
assert_true("observer args: hello" in run_result.stdout, "Fixture agent did not run through mongoose.")

jobs = json.loads(run_mongoose("jobs", "list", "--json").stdout)
assert_true(jobs, "No job record was created.")
latest = jobs[0]
assert_true(latest["status"] == "succeeded", "Latest job did not succeed.")
assert_true(latest["agent"]["commandName"] == "Observer", "Latest job did not record the agent.")
assert_true(Path(latest["contextPath"]).exists(), "Job context path does not exist.")
assert_true(Path(latest["logPath"]).exists(), "Job log path does not exist.")

shown = json.loads(run_mongoose("jobs", "show", latest["id"], "--json").stdout)
assert_true(shown["id"] == latest["id"], "jobs show returned the wrong job.")
assert_true("observer args" in shown["outputSummary"]["combinedPreview"], "Job output summary did not include fixture output.")

status = json.loads(run_mongoose("status", "--json").stdout)
assert_true(status["installedAgents"] == 1, "Status did not count installed agents.")
assert_true(status["jobs"]["total"] >= 1, "Status did not count jobs.")
assert_true(status["llm"]["configuredProfiles"] >= 3, "Status did not count configured LLM profiles.")

run_mongoose("runtime", "stop")
stopped = json.loads(run_mongoose("runtime", "status", "--json").stdout)
assert_true(stopped["runtime"]["status"] == "stopped", "Runtime stop did not update status.")

print("Mongoose runtime observability validation passed.")
