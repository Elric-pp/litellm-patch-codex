#!/usr/bin/env python3
"""Patch endpoints.py to default empty model to gpt-5.5."""
import sys

OLD = """    data = await _read_request_body(request=request)

    # Check if polling via cache should be used for this request"""

NEW = """    data = await _read_request_body(request=request)

    # Default empty model to gpt-5.5 so Codex requests without an explicit
    # model still route correctly through the model group.
    if not data.get("model"):
        data["model"] = "gpt-5.5"

    # Check if polling via cache should be used for this request"""

path = sys.argv[1] if len(sys.argv) > 1 else "/app/.venv/lib/python3.13/site-packages/litellm/proxy/response_api_endpoints/endpoints.py"
with open(path) as f:
    content = f.read()

if "Default empty model" in content:
    print("Already patched")
    sys.exit(0)

if OLD not in content:
    print(f"ERROR: target not found in {path}")
    sys.exit(1)

content = content.replace(OLD, NEW)
with open(path, "w") as f:
    f.write(content)
print("Patched successfully")
