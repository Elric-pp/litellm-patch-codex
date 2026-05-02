# litellm-patch-codex

Run a patched LiteLLM proxy that bridges Codex CLI's Responses API calls to any OpenAI-compatible provider (DeepSeek, etc.).

## Why

Codex CLI uses the OpenAI Responses API (`/v1/responses`) which LiteLLM proxies to the Chat Completions API via an internal bridge. Three categories of issues arise with non-OpenAI providers:

1. **Unsupported tool types** — Codex sends tool types like `image_generation` that only the OpenAI Responses API supports. These must be filtered before reaching the upstream provider.
2. **Malformed message sequences** — The bridge can produce consecutive assistant messages and orphaned `tool_calls` that strict providers reject.
3. **Provider-specific requirements** — e.g. DeepSeek requires `reasoning_content` on every assistant message in multi-turn conversations.

The patches in this repo fix all three at the LiteLLM proxy level, making any OpenAI-compatible provider usable with Codex.

## Quick start

1. Clone this repo and copy `.env.example` to `.env`, filling in your upstream API key:

```bash
cp .env.example .env
# edit .env and set UPSTREAM_API_KEY=sk-your-key
```

2. Build and start:

```bash
docker compose up -d
```

The proxy runs on `http://localhost:4000`.

3. Point Codex at it — in `~/.codex/config.toml`:

```toml
model = "deepseek-v4-pro"
profile = "cliproxyapi"

[model_providers.cliproxyapi]
name = "CliProxyAPI"
base_url = "http://localhost:4000/v1"
env_key = "LITELLM_API_KEY"

[profiles.cliproxyapi]
model = "deepseek-v4-pro"
model_provider = "cliproxyapi"
model_reasoning_effort = "xhigh"
```

Set `LITELLM_API_KEY` to the `LITELLM_MASTER_KEY` value from your `.env`.

## What's patched

| File | What it fixes | Scope |
|---|---|---|
| `patch_main.py` | Filters unsupported tool types (`image_generation`, etc.) | All non-OpenAI providers |
| `patch_transformation.py` | Skips unknown tool types in the bridge's else-branch | All providers |
| `patch_handler.py` | Merges consecutive assistant messages, truncates orphaned `tool_calls`, injects `reasoning_content` for DeepSeek | All providers + DeepSeek |

## Customizing providers

Edit `config.yaml` to add any OpenAI-compatible provider. Example for another provider:

```yaml
model_list:
  - model_name: my-model
    litellm_params:
      model: openai/my-model
      api_base: https://your-provider.com
      api_key: os.environ/UPSTREAM_API_KEY
      use_chat_completions_api: true
```

The `use_chat_completions_api: true` flag is recommended for all non-OpenAI providers.

## Updating

To update the base LiteLLM image, rebuild:

```bash
docker compose build --no-cache
docker compose up -d --force-recreate
```
