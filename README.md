# litellm-patch-codex

Run a patched LiteLLM proxy that bridges Codex CLI's Responses API calls to any OpenAI-compatible provider. Supports multi-tier routing with automatic fallback.

## Why

Codex CLI uses the OpenAI Responses API (`/v1/responses`). When proxying to non-OpenAI providers, several issues arise:

1. **Unsupported tool types** — Codex sends tool types like `image_generation` that only the OpenAI Responses API supports.
2. **Malformed message sequences** — The bridge can produce consecutive assistant messages and orphaned `tool_calls`.
3. **Provider-specific requirements** — e.g. DeepSeek requires `reasoning_content` on every assistant message in multi-turn conversations.
4. **No 404 fallback** — litellm's router skips retry on `NotFoundError`, breaking multi-provider fallback chains.

The patches in this repo fix all of these at the LiteLLM proxy level.

## Quick start

1. Clone and configure:

```bash
cp .env.example .env
# edit .env with your API keys and base URLs
```

2. Build and start:

```bash
docker compose up -d
```

The proxy runs on `http://localhost:4000`.

3. Point Codex at it — in `~/.codex/config.toml`:

```toml
profile = "cliproxyapi"

[model_providers.cliproxyapi]
name = "CliProxyAPI"
base_url = "http://localhost:4000/v1"
env_key = "LITELLM_API_KEY"

[profiles.cliproxyapi]
model = "gpt-5.5"
model_provider = "cliproxyapi"
model_reasoning_effort = "xhigh"
```

Set `LITELLM_API_KEY` to `LITELLM_MASTER_KEY` from `.env`.

## Routing

Model aliases map Codex model names to upstream providers:

| Codex model | Routing (primary → fallback → fallback) |
|---|---|
| `gpt-5.5` / `gpt-5.4` | cliproxyapi → DeepSeek v4-pro → Gemini 3.1 pro |
| `gpt-5.5-mini` / `gpt-5.4-mini` | cliproxyapi → DeepSeek v4-flash → Gemini 3.1 flash-lite |
| (empty) | defaults to `gpt-5.5` |

All provider URLs and keys are configured via environment variables in `.env`.

## Patches

| File | What it fixes | Scope |
|---|---|---|
| `patch_main.py` | Filters unsupported tool types (`image_generation`, etc.) | All non-OpenAI providers |
| `patch_transformation.py` | Skips unknown tool types in the bridge's else-branch | All providers |
| `patch_handler.py` | Merges consecutive assistant messages, truncates orphaned `tool_calls`, injects `reasoning_content` for DeepSeek | All providers |
| `patch_endpoints.py` | Defaults empty model name to `gpt-5.5` | All providers |
| `patch_router.py` | Allows `NotFoundError` (404) to trigger deployment retry/fallback | All providers |

## Updating

```bash
docker compose build --no-cache
docker compose up -d --force-recreate
```
