# Deploying to Railway

Decision 007. The app runs as one long-lived server with a persistent volume,
which is what the community features (SQLite) and background moderation need.

## One-time setup (≈15 min)

1. **New project → Deploy from GitHub repo** → `bhajneeks/sikhnet`, branch `main`.
   Railway reads `railway.json` (start command `sh scripts/start.sh`, health check
   `/api/health`) and `.python-version` (3.12), and installs `requirements.txt`.
2. **Add a volume** to the service, mount path **`/data`**. Railway sets
   `RAILWAY_VOLUME_MOUNT_PATH`; the start script then keeps `community.db` and
   `qa.jsonl` there, so posts, votes and the dataset survive redeploys.
3. **Variables** (service → Variables):

   | Variable | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | the team key (AI answers, Surprise-me hooks, AI moderation) |
   | `SIKHNET_ADMIN_TOKEN` | a long random string, e.g. `openssl rand -hex 24`. **Required**: moderation is locked without it |
   | `SIKHNET_DATA_URL` | a **private, expiring** link to the raw export (`qa-sample-300.jsonl`), see below |
   | `SIKHNET_DATA_SOURCE` | `sikhnet-qa-dataset` (default; keeps record ids identical to local) |
   | optional | `SIKHNET_DATA_TOKEN` (Bearer auth for the URL), `SIKHNET_DATA_FORMAT` (`jsonl` default, or `csv`/`xlsx`/`json`), `SIKHNET_EFFORT=medium` for faster answers |

4. **Settings → Networking → Generate domain.** Open it, then check
   `https://<domain>/api/health`: `records` should be the real count (853 for
   the 300-question export), not 4.

## The dataset (never through git)

The repo is public and the hackathon terms forbid committing the data. On first
boot `scripts/start.sh` downloads `SIKHNET_DATA_URL` into the volume, runs
`ingest/ingest.py`, and never downloads again unless `SIKHNET_REINGEST=1`.

For the URL use something private and short-lived: a presigned S3/R2 link, or a
private file host behind `SIKHNET_DATA_TOKEN`. A public "anyone with the link"
Google Drive share counts as redistribution, so don't use one. **Confirm with
SikhNet (via Jaspreet) that hosting the data on Railway for the demo is OK.**
After the first successful boot you can delete the variable.

**Terms: delete all copies within 30 days.** When the hackathon is over, delete
the Railway volume (it holds `qa.jsonl` and `raw-dataset.*`) or the whole project.

## Moderating

Open `https://<domain>/moderate.html` and paste `SIKHNET_ADMIN_TOKEN`. On a
deployed server the "this computer needs no token" shortcut is off.

## Things to know

- **One worker** on purpose (`--workers 1`): community storage is one SQLite file.
  That's plenty for a demo. Scaling past one replica means moving to Postgres.
- Every push to `main` redeploys. The volume (data, posts, votes) is kept.
- Logs: service → Deployments → View logs. The start script says whether the
  dataset downloaded and ingested.
- Locally nothing changes: `uvicorn backend.app:app --reload --port 8000`.
