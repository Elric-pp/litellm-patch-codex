#!/usr/bin/env python3
"""
Patch router.py to allow retry on NotFoundError (404) when multiple
deployments exist. Enables Gemini → DeepSeek fallback.
"""
import sys

# Fix 1: Allow 404 to proceed past the status_code check (alongside 401/403)
OLD1 = """        if status_code is not None and not litellm._should_retry(status_code):
            # 401/403 are special cases - allow retry if multiple deployments exist (handled below)
            if status_code not in (401, 403):
                raise error"""

NEW1 = """        if status_code is not None and not litellm._should_retry(status_code):
            # 401/403/404 are special cases - allow retry if multiple deployments exist (handled below)
            if status_code not in (401, 403, 404):
                raise error"""

# Fix 2: Allow NotFoundError to be retried when other deployments exist
OLD2 = """        if isinstance(error, litellm.NotFoundError):
            raise error
        # Error we should only retry if there are other deployments"""

NEW2 = """        # Allow NotFoundError retry when multiple deployments exist
        # (e.g. Gemini proxy returns 404, fallback to DeepSeek)
        if isinstance(error, litellm.NotFoundError):
            if _num_all_deployments <= 1:
                raise error
        # Error we should only retry if there are other deployments"""

path = sys.argv[1] if len(sys.argv) > 1 else "/app/.venv/lib/python3.13/site-packages/litellm/router.py"
with open(path) as f:
    content = f.read()

if "401, 403, 404" in content and "Allow NotFoundError retry" in content:
    print("Already patched")
    sys.exit(0)

for old_str, new_str in [(OLD1, NEW1), (OLD2, NEW2)]:
    if old_str not in content:
        print(f"ERROR: target not found in {path}")
        sys.exit(1)
    content = content.replace(old_str, new_str)

with open(path, "w") as f:
    f.write(content)
print("Patched successfully")
