"""Download the Meta Ad Library Weekly compilation into data/raw/.

    python scripts/download_data.py

The archive is the public Kaggle dataset ktkehoe/meta-ad-library-weekly
(Apache 2.0). No Kaggle credential is required. The primary URL is the
dataset download endpoint. If that host returns a challenge page instead of
a zip, the same archive is requested from api.kaggle.com.

Raw CSVs are gitignored. They are large (the region file is about 3.3 million
rows) and are rebuilt here rather than committed.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.constants import KAGGLE_DOWNLOAD_FALLBACK_URL, KAGGLE_DOWNLOAD_URL

RAW_DIR = ROOT / "data" / "raw"
EXPECTED = (
    "META_AD_LIBRARY.ADVERTISERS.csv",
    "META_AD_LIBRARY.LOCATIONS.csv",
    "META_AD_LIBRARY.REGIONS.csv",
)
USER_AGENT = "Mozilla/5.0 (compatible; meta-ad-spend-analysis/1.0)"


def _fetch(url: str, dest: Path) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            first = response.read(4)
            if first != b"PK\x03\x04":
                return False
            with dest.open("wb") as handle:
                handle.write(first)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    except urllib.error.HTTPError:
        return False
    return True


def download(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and all((RAW_DIR / name).exists() for name in EXPECTED):
        print(f"Raw files already in {RAW_DIR.relative_to(ROOT)}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "meta-ad-library-weekly.zip"
        print(f"Downloading {KAGGLE_DOWNLOAD_URL}")
        ok = _fetch(KAGGLE_DOWNLOAD_URL, archive)
        if not ok:
            print(f"Primary URL did not return a zip. Trying {KAGGLE_DOWNLOAD_FALLBACK_URL}")
            ok = _fetch(KAGGLE_DOWNLOAD_FALLBACK_URL, archive)
        if not ok:
            raise RuntimeError("Could not download the dataset zip from either URL.")
        print(f"Unzipping {archive.stat().st_size / 1e6:.1f} MB into {RAW_DIR.relative_to(ROOT)}")
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            missing = [name for name in EXPECTED if name not in names]
            if missing:
                raise RuntimeError(f"Zip is missing {missing}. Found {names}")
            zipped.extractall(RAW_DIR)
    for name in EXPECTED:
        path = RAW_DIR / name
        print(f"  {name}: {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    download(force="--force" in sys.argv)
