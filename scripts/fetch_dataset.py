"""Deploy helper: download the raw dataset from a private URL. Used by scripts/start.sh.

The dataset never goes in git (public repo; hackathon terms). On Railway it is
fetched once into the persistent volume from SIKHNET_DATA_URL, which should be
a private, expiring link (e.g. a signed URL). Never print the URL: it is a secret.

Usage: python3 scripts/fetch_dataset.py <out_path>
Env: SIKHNET_DATA_URL (required), SIKHNET_DATA_TOKEN (optional, sent as a Bearer token).
"""
import os
import sys
import urllib.request


def main() -> int:
    url = os.environ.get("SIKHNET_DATA_URL")
    if not url:
        print("fetch_dataset: SIKHNET_DATA_URL not set; skipping", file=sys.stderr)
        return 1
    out = sys.argv[1]
    req = urllib.request.Request(url, headers={"User-Agent": "sikhnet-deploy"})
    if os.environ.get("SIKHNET_DATA_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['SIKHNET_DATA_TOKEN']}")
    tmp = out + ".part"
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
    except Exception as e:  # don't echo the URL
        print(f"fetch_dataset: download failed ({type(e).__name__})", file=sys.stderr)
        return 1
    if os.path.getsize(tmp) == 0:
        print("fetch_dataset: downloaded file is empty", file=sys.stderr)
        return 1
    os.replace(tmp, out)
    print(f"fetch_dataset: saved {os.path.getsize(out):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
