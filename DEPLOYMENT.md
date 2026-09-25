# Deployment

Use one Python process, a persistent writable database volume, and a TLS reverse proxy. The container listens on port 8000. With a native Python host, use:

```sh
uvicorn server:app --host 0.0.0.0 --port "$PORT" --workers 1 --ws-max-size 8192
```

`PORT` must be supplied by your hosting provider. For manual deployment use `8000`.

Environment:

| Variable | Default | Meaning |
| --- | --- | --- |
| DATABASE_PATH | rooms.sqlite3 beside server.py | Persistent writable SQLite file |
| ALLOWED_ORIGINS | empty | Comma-separated additional frontend origins; same-origin is accepted |
| MAX_ROOMS | 1000 | Stored room creation limit |

Nginx location inside an HTTPS server block (configure your own domain and TLS certificate):

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

Back up the SQLite file while the app is stopped, or use SQLite's backup API. Do not enable multiple workers or replicas. Existing rooms are not automatically deleted. Add authentication and per-IP room-creation limits before opening an unrestricted public service. A room URL is an editing capability, not a login.
