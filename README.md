# Tactica | غرف التحليل المشترك

A bilingual Arabic/English football tactics workspace with a real Python WebSocket backend. Move 22 players and the ball, draw tactical arrows, name players, and discuss the plan in a shared room.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 8192
```

Open http://localhost:8000. Enter your name, leave Server address blank, and click **Create shared room**. Copy the link and open it in a second browser; enter a second name and click **Join**. Every accepted move, arrow, rename, and chat message is broadcast to everyone in the room.

On the same Wi-Fi, open `http://YOUR_COMPUTER_LAN_IP:8000` on both devices. Allow port 8000 in your firewall. A localhost link only works on the computer running the server.

Alternatively:

```bash
docker compose up --build
```

## Features

- Arabic RTL and English LTR, responsive desktop/mobile interface.
- Pointer/touch movement, keyboard arrow movement for focused pieces.
- Server-authoritative ordering; last accepted edit wins when two users move the same piece.
- 24-character unguessable room links, up to 20 connected analysts per room.
- Persistent SQLite board and latest 100 chat messages; join again to restore state.
- Member presence, clear connection status, explicit reconnection via Join.
- JSON export of the complete plan. Export is for backup/inspection; import is not implemented.
- Input bounds, message size limits, event rate limits, and WebSocket origin checks.
- Client-only local practice when opening `static/index.html`; multiplayer requires Python.

## Hosting

Deploy this repository on a Python/Docker host that supports long-lived WebSockets. Run **one worker and one replica**. Mount persistent storage and set `DATABASE_PATH` to its writable SQLite path. Use HTTPS/WSS through a reverse proxy with WebSocket upgrade support. See `DEPLOYMENT.md` for an Nginx example.

GitHub stores the source. **GitHub Pages cannot run the Python server.** The easiest complete deployment serves the interface and WebSocket API together from Python. The separately published static preview provides local practice and can connect to a deployed Python server.

If using a separate frontend origin, set `ALLOWED_ORIGINS=https://your-frontend.example` on the Python server and enter its HTTPS server URL in the interface. Multiple origins are comma-separated. The server applies the same explicit list to CORS and WebSocket access. Localhost and remote origins must match exactly, including scheme and port.

## GitHub

Create an empty GitHub repository, then run these commands inside this extracted folder:

```bash
git init
git add .
git commit -m "Build Tactica shared analysis rooms"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/tactica.git
git push -u origin main
```

A GitHub Actions workflow tests two analysts editing one room, chat, persistence, and origin rejection. This package does not create a GitHub repository on your behalf.

## Tests

```bash
pip install pytest httpx
python -m pytest -q
```

## Project structure

- `server.py`: FastAPI HTTP/WebSocket server and SQLite persistence.
- `static/`: complete website (`index.html`, `style.css`, `app.js`).
- `tests/`: two-client synchronization and origin tests.
- `Dockerfile`, `compose.yaml`: container startup and persistent volume.
- `.github/workflows/tests.yml`: CI checks.
- `README.ar.md`: Arabic setup guide.

## Scope and room privacy

This is a small-team MVP, not an enterprise access system. Anyone who possesses a room link can edit and read its messages. There are no accounts, passwords, roles, voice calls, or per-user undo. Do not put confidential match data in publicly shared rooms. Disconnected edits are blocked; click Join to fetch current state. Rooms persist until an operator removes their database records. `MAX_ROOMS` defaults to 1000; production public deployments should add authentication and edge rate limits for room creation. SQLite and the in-memory connection registry intentionally support a single process only; horizontal scaling requires a shared message broker and distributed room ownership.

MIT licensed.
