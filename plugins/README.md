# OpenClaw Node - Plugins

Action plugins that extend the client's capabilities.

## Tasks

- `clawd-p1u.3.4` - Plugin base class and examples (START HERE)
- `clawd-p1u.3.1` - RV Viewer Plugin
- `clawd-p1u.3.2` - DaVinci Resolve Plugin
- `clawd-p1u.3.3` - File Explorer Plugin

## Creating a Plugin

1. Inherit from `BasePlugin`
2. Define `name` and `actions`
3. Implement `execute(action, params)`
4. Place in `plugins/` directory

```python
from plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "myplugin"
    actions = ["do_thing", "do_other_thing"]
    
    async def execute(self, action: str, params: dict) -> dict:
        if action == "do_thing":
            # ... implementation
            return {"status": "done"}
```

## Available Plugins

| Plugin | Platform | Actions |
|--------|----------|---------|
| `rv` | Win/Mac | `open_session`, `open_sources`, `close` |
| `resolve` | Win/Mac | `add_to_media_pool`, `create_timeline`, `render` |
| `explorer` | Windows | `open_folder`, `reveal_file` |
| `finder` | macOS | `open_folder`, `reveal_file` |
