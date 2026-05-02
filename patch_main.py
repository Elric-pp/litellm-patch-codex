#!/usr/bin/env python3
"""Patch litellm responses/main.py to filter unsupported tool types."""
import sys

TARGET = """        local_vars.update(kwargs)
        # Map reasoning_effort (from litellm_params/proxy config) to reasoning when not set"""

INSERT = """
        # Filter unsupported tool types. Only "function", "mcp",
        # "web_search_preview", "web_search" are standard types supported
        # by all OpenAI-compatible providers. Codex may send types like
        # "image_generation" that only the OpenAI Responses API supports.
        _native_supported = {"function", "mcp", "web_search_preview", "web_search"}
        _tools = local_vars.get("tools")
        if _tools:
            _filtered = [t for t in _tools if (t.get("type") if isinstance(t, dict) else None) in _native_supported]
            if len(_filtered) != len(_tools):
                local_vars["tools"] = _filtered
"""

path = sys.argv[1] if len(sys.argv) > 1 else "/app/litellm/responses/main.py"
with open(path) as f:
    content = f.read()

if INSERT in content:
    print("Already patched")
    sys.exit(0)

if TARGET not in content:
    print(f"ERROR: target not found in {path}")
    sys.exit(1)

# Insert AFTER the target line
content = content.replace(TARGET, TARGET + INSERT)
with open(path, "w") as f:
    f.write(content)
print("Patched successfully")
