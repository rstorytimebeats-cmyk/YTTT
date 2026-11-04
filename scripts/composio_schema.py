"""Prints Composio's current YOUTUBE_UPLOAD_VIDEO schema so you can confirm argument names used in factory/youtube.py."""
import json, os
from composio import Composio
c = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
print(json.dumps(c.tools.get_raw_composio_tool_by_slug("YOUTUBE_UPLOAD_VIDEO").model_dump(), indent=2, default=str)[:4000])
