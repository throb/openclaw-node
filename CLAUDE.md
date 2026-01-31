# OpenClaw Node

Remote execution framework for VFX/post-production pipeline automation.

## Beads Workflow
- Beads live in this repo: `.beads/`
- Prefix: `clawd-p1u`
- Start work: `bd start clawd-p1u.X.X`
- Complete: `bd close clawd-p1u.X.X`
- List tasks: `bd list`

## Git Workflow
- Commit after completing each bead
- Push to GitHub regularly
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`

## Code Standards
- Python 3.10+
- async/await for all I/O
- Type hints everywhere
- pytest for tests
- Use `logging` module, not print statements

## Project Structure
```
openclaw-node/
├── server/         # WebSocket server (VPS)
├── client/         # Python client (workstations)
└── plugins/        # Plugin implementations
```

## Running

### Server
```bash
cd server && uvicorn main:app --host 0.0.0.0 --port 8765
```

### Client
```bash
cd client && python main.py --config node_config.yaml
```

## Testing
```bash
pytest tests/
```
