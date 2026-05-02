#!/usr/bin/env python3
"""Patch transformation.py to skip unsupported tool types."""
import sys

OLD = """            else:
                chat_completion_tools.append(
                    cast(Union[ChatCompletionToolParam, OpenAIMcpServerTool], tool)
                )"""
NEW = """            else:
                pass  # skip unsupported tool types (e.g. image_generation)"""

path = sys.argv[1] if len(sys.argv) > 1 else "/app/litellm/responses/litellm_completion_transformation/transformation.py"
with open(path) as f:
    content = f.read()

if NEW in content:
    print("Already patched")
    sys.exit(0)

if OLD not in content:
    print(f"ERROR: target not found in {path}")
    sys.exit(1)

content = content.replace(OLD, NEW)
with open(path, "w") as f:
    f.write(content)
print("Patched successfully")
