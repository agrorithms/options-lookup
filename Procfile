web: gunicorn app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```| Setting | Why |
| --- | --- |
| `app:server` | Points to the `server = app.server` variable in `app.py` |
| `--bind 0.0.0.0:$PORT` | Render injects the `PORT` environment variable |
| `--workers 2` | Two worker processes — enough for moderate traffic, stays within free tier memory |
| `--timeout 120` | Yahoo Finance API calls can be slow; prevents gunicorn from killing the worker mid-fetch |
---