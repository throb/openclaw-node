# OpenClaw Node - Server

VPS-side WebSocket orchestrator for managing node connections and routing commands.

## Tasks

- `clawd-p1u.1.1` - Design WebSocket message protocol
- `clawd-p1u.1.2` - Implement WebSocket server core
- `clawd-p1u.1.3` - Client registry and multi-node management
- `clawd-p1u.1.4` - Command routing and response handling
- `clawd-p1u.1.5` - Server-side security and authentication
- `clawd-p1u.1.6` - REST API for status and admin

## Tech Stack

- Python 3.10+
- FastAPI + websockets
- Pydantic for message validation

## Quick Start

```bash
cd server
pip install -r requirements.txt
python main.py
```
