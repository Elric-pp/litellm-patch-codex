#!/usr/bin/env python3
"""
Patch handler.py to fix message compatibility for OpenAI-compatible providers.

Fixes (provider-agnostic unless noted):
  1. Merge consecutive assistant messages (bridge can produce back-to-back
     assistant messages that confuse strict providers like DeepSeek)
  2. Truncate tool_calls that lack matching tool messages (session history
     may include tool_calls whose results were dropped)
  3. Ensure every assistant message has content when tool_calls are removed
  4. DeepSeek-specific: inject empty reasoning_content for multi-turn compat
"""
import sys

FIX_CODE = """{indent}# Message cleanup for OpenAI-compatible providers.
{indent}# Merges consecutive assistant messages, truncates orphaned tool_calls,
{indent}# and ensures reasoning_content for DeepSeek multi-turn compatibility.
{indent}_model = _completion_args.get("model") or _litellm_req.get("model", "")
{indent}_is_deepseek = "deepseek" in str(_model).lower()
{indent}_messages = _completion_args.get("messages") or _litellm_req.get("messages")
{indent}if _messages and isinstance(_messages, list):
{indent}    # Step 1: merge consecutive assistant messages (provider-agnostic)
{indent}    _merged = []
{indent}    for _m in _messages:
{indent}        if isinstance(_m, dict) and _m.get("role") == "assistant" and _merged and isinstance(_merged[-1], dict) and _merged[-1].get("role") == "assistant":
{indent}            _prev = _merged[-1]
{indent}            _prev_tcs = _prev.get("tool_calls") or []
{indent}            _cur_tcs = _m.get("tool_calls") or []
{indent}            _prev_ct = _prev.get("content") if isinstance(_prev.get("content"), str) else ""
{indent}            _cur_ct = _m.get("content") if isinstance(_m.get("content"), str) else ""
{indent}            _prev_rc = _prev.get("reasoning_content") if isinstance(_prev.get("reasoning_content"), str) else ""
{indent}            _cur_rc = _m.get("reasoning_content") if isinstance(_m.get("reasoning_content"), str) else ""
{indent}            _merged[-1] = {{**_prev,
{indent}                "tool_calls": _prev_tcs + _cur_tcs,
{indent}                "content": ("\\n".join(p for p in [_prev_ct, _cur_ct] if p)) or "",
{indent}                "reasoning_content": ("\\n".join(p for p in [_prev_rc, _cur_rc] if p)) or "",
{indent}            }}
{indent}        else:
{indent}            _merged.append(_m)
{indent}    # Step 2: collect resolved tool_call_ids (provider-agnostic)
{indent}    _resolved_ids = set()
{indent}    for _m in _merged:
{indent}        if isinstance(_m, dict) and _m.get("role") == "tool":
{indent}            _tc_id = _m.get("tool_call_id")
{indent}            if _tc_id:
{indent}                _resolved_ids.add(str(_tc_id))
{indent}    # Step 3: fix messages (provider-agnostic + DeepSeek reasoning_content)
{indent}    _fixed = []
{indent}    for _m in _merged:
{indent}        if isinstance(_m, dict) and _m.get("role") == "assistant":
{indent}            # DeepSeek requires reasoning_content in multi-turn conversation history
{indent}            if _is_deepseek and "reasoning_content" not in _m:
{indent}                _m = {{**_m, "reasoning_content": ""}}
{indent}            _tcs = _m.get("tool_calls")
{indent}            if _tcs:
{indent}                _valid_tcs = [tc for tc in _tcs if str(tc.get("id", "")) in _resolved_ids]
{indent}                if not _valid_tcs:
{indent}                    _m = {{k: v for k, v in _m.items() if k != "tool_calls"}}
{indent}                    if not _m.get("content"):
{indent}                        _m["content"] = ""
{indent}                elif len(_valid_tcs) != len(_tcs):
{indent}                    _m = {{**_m, "tool_calls": _valid_tcs}}
{indent}            if not _m.get("content") and not _m.get("tool_calls"):
{indent}                _m["content"] = ""
{indent}        _fixed.append(_m)
{indent}    _completion_args["messages"] = _fixed"""

ASYNC_TARGET = """        acompletion_args = {}
        acompletion_args.update(kwargs)
        acompletion_args.update(litellm_completion_request)"""

ASYNC_PRELUDE = """
        _completion_args = acompletion_args
        _litellm_req = litellm_completion_request"""
ASYNC_INSERT = ASYNC_PRELUDE + FIX_CODE.format(indent="        ") + "\n"

SYNC_TARGET = """    ] = litellm.completion(
            **litellm_completion_request,
            **kwargs,
        )"""

SYNC_HELPER = FIX_CODE.format(indent="    ")

SYNC_HELPER_FUNC = """
# Injected: message cleanup for OpenAI-compatible providers
def _litellm_completion_with_message_cleanup(litellm_completion_request, kwargs):
    _completion_args = {}
    _completion_args.update(kwargs)
    _completion_args.update(litellm_completion_request)
    _litellm_req = litellm_completion_request
""" + SYNC_HELPER + """
    return litellm.completion(**litellm_completion_request, **kwargs)
"""

SYNC_REPLACE = """    ] = _litellm_completion_with_message_cleanup(
            litellm_completion_request=litellm_completion_request,
            kwargs=kwargs,
        )"""

path = sys.argv[1] if len(sys.argv) > 1 else "/app/.venv/lib/python3.13/site-packages/litellm/responses/litellm_completion_transformation/handler.py"
with open(path) as f:
    content = f.read()

if "_litellm_completion_with_message_cleanup" in content:
    print("Already patched")
    sys.exit(0)

ok = 0

if ASYNC_TARGET in content:
    content = content.replace(ASYNC_TARGET, ASYNC_TARGET + ASYNC_INSERT)
    ok += 1
    print("Async path patched")
else:
    print("WARNING: async target not found")

if SYNC_TARGET in content:
    content = content.replace(SYNC_TARGET, SYNC_REPLACE)
    helper_pos = content.find("class LiteLLMCompletionTransformationHandler:")
    if helper_pos > 0:
        content = content[:helper_pos] + SYNC_HELPER_FUNC + "\n" + content[helper_pos:]
    ok += 1
    print("Sync path patched")
else:
    print("WARNING: sync target not found")

if ok == 0:
    print("ERROR: no patches applied")
    sys.exit(1)

with open(path, "w") as f:
    f.write(content)
print(f"Done ({ok} paths)")
