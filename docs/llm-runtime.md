# Mongoose LLM Runtime v1

Mongoose LLM Runtime v1 defines provider-neutral LLM profiles that installed
agents can request without hard-coding a backend or storing credentials in agent
manifests.

## Security Model

LLM profiles are stored in user-local Mongoose state:

```text
%LOCALAPPDATA%\Agents\state\llm\profiles.json
```

Profiles store provider metadata and secret references only. API keys, bearer
tokens, request headers, and secret values must stay in environment variables or
future Mongoose secret/profile storage. Agent manifests may declare that an LLM
is optional or required and may reference a profile name, but they must not
contain raw credentials.

## Commands

Add a fake profile for local validation:

```text
mongoose llm add fake-main --provider fake --model fake-chat --default
mongoose llm ping fake-main
```

Add an OpenAI-compatible profile:

```text
mongoose llm add openai-main --provider openai --model gpt-4.1-mini --api-key-env OPENAI_API_KEY --default
mongoose llm ping openai-main
```

Inspect profiles without printing secrets:

```text
mongoose llm list
mongoose llm show openai-main
mongoose llm use openai-main
```

## Profile Shape

Profiles are provider-neutral:

```json
{
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "endpoint": "",
  "secret": {
    "mode": "env",
    "env": "OPENAI_API_KEY"
  },
  "capabilities": ["chat"]
}
```

Supported provider types:

- `openai`
- `anthropic`
- `local-http`
- `fake`

The `fake` provider is for validation and tests. It returns a deterministic
`pong` response and does not require network access or secrets.

## Agent-Facing Interface

Runtime Contract v1 exposes LLM availability and an invocation command through
the `llm` provider descriptor in `MONGOOSE_RUNTIME_CONTEXT`:

```json
{
  "providers": {
    "llm": {
      "available": true,
      "interface": "mongoose.llm.v1",
      "defaultProfile": "openai-main",
      "profile": {
        "name": "openai-main",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "apiKeyEnv": "OPENAI_API_KEY",
        "secretAvailable": true
      },
      "invokeCommand": [
        "python",
        "C:\\Users\\you\\AppData\\Local\\Agents\\mongoose\\mongoose.py",
        "llm",
        "invoke",
        "--json",
        "--profile",
        "openai-main"
      ],
      "input": "stdin prompt text",
      "output": "json"
    }
  }
}
```

Agents should request an LLM profile by explicit profile name, the default
profile, or manifest-declared requirement. They should treat provider-specific
credentials as opaque and let Mongoose resolve profile readiness.

Installed agents invoke the provider by running the advertised `invokeCommand`
and passing prompt text on stdin. The command returns JSON:

```json
{
  "ok": true,
  "profile": "openai-main",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "response": {
    "role": "assistant",
    "content": "Generated narration..."
  }
}
```

For local validation, the `fake` provider returns deterministic narration and
does not require network access or secrets:

```text
mongoose llm invoke --profile fake-main "Explain these deterministic facts"
```

## Runtime Errors

LLM setup and ping failures use structured runtime error codes:

- `mongoose.llm_profile_missing`
- `mongoose.llm_profile_invalid`
- `mongoose.llm_secret_missing`
- `mongoose.llm_ping_failed`
- `mongoose.llm_invoke_failed`
- `mongoose.provider_unavailable`

Diagnostics are redacted before printing. Missing environment variable names may
be printed because they are references, not secret values.

## Deterministic Agents

Deterministic agents and deterministic capabilities do not need an LLM profile.
They continue to run through the existing Mongoose runtime context and can
ignore the `llm` provider descriptor.
