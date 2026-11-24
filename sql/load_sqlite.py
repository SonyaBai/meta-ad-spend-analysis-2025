"""Load the three raw CSVs into data/meta_ad_library.db.

    python sql/load_sqlite.py

Reads in batches and inserts into SQLite. The region file is about 3.3 million
rows; it is never held in memory as one dataframe. The database is gitignored
and can be rebuilt after scripts/download_data.py.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
DB_PATH = ROOT / "data" / "meta_ad_library.db"

ADVERTISERS = RAW_DIR / "META_AD_LIBRARY.ADVERTISERS.csv"
LOCATIONS = RAW_DIR / "META_AD_LIBRARY.LOCATIONS.csv"
REGIONS = RAW_DIR / "META_AD_LIBRARY.REGIONS.csv"

BATCH = 20_000


def dollars(text: str) -> int:
    value = Decimal(text)
    if value != value.to_integral_value():
        raise ValueError(f"expected whole dollars, got {text}")
    return int(value)


def _connect(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA locking_mode = EXCLUSIVE")
    connection.execute("PRAGMA temp_store = FILE")
    connection.executescript(SCHEMA_PATH.read_text())
    return connection


def _load(connection: sqlite3.Connection, path: Path, sql: str, adapt) -> tuple[int, int]:
    rows = 0
    total = 0
    batch: list[tuple] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for record in csv.DictReader(handle):
            batch.append(adapt(record))
            total += dollars(record["AMOUNT_SPENT_USD"])
            if len(batch) >= BATCH:
                connection.executemany(sql, batch)
                rows += len(batch)
                batch.clear()
                if rows % 500_000 == 0:
                    print(f"  {path.name}: {rows:,} rows")
        if batch:
            connection.executemany(sql, batch)
            rows += len(batch)
    connection.commit()
    print(f"  {path.name}: {rows:,} rows, ${total:,}")
    return rows, total


def _advertiser(record: dict) -> tuple:
    return (
        record["ID"],
        record["DATE_START"],
        record["DATE_END"],
        record["WINDOW"],
        record["PAGE_ID"],
        record["PAGE_NAME"],
        record["DISCLAIMER"],
        dollars(record["AMOUNT_SPENT_USD"]),
        int(record["NUM_ADS"]),
    )


def _location(record: dict) -> tuple:
    return (
        record["ID"],
        record["DATE_START"],
        record["DATE_END"],
        record["WINDOW"],
        record["LOCATION_NAME"],
        dollars(record["AMOUNT_SPENT_USD"]),
    )


def _region(record: dict) -> tuple:
    return (
        record["ID"],
        record["DATE_START"],
        record["DATE_END"],
        record["WINDOW"],
        record["REGION"],
        record["PAGE_ID"],
        record["PAGE_NAME"],
        record["DISCLAIMER"],
        dollars(record["AMOUNT_SPENT_USD"]),
    )


def build_database(db_path: Path = DB_PATH) -> Path:
    for path in (ADVERTISERS, LOCATIONS, REGIONS):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path.relative_to(ROOT)}. Run python scripts/download_data.py"
            )
    print(f"Loading {db_path.relative_to(ROOT)}")
    connection = _connect(db_path)
    try:
        advertiser_sql = """
            INSERT INTO advertisers (
                id, date_start, date_end, window, page_id, page_name,
                disclaimer, amount_spent_usd, num_ads
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        location_sql = """
            INSERT INTO locations (
                id, date_start, date_end, window, location_name, amount_spent_usd
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        region_sql = """
            INSERT INTO regions (
                id, date_start, date_end, window, region, page_id, page_name,
                disclaimer, amount_spent_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        loaded = {
            "advertisers": _load(connection, ADVERTISERS, advertiser_sql, _advertiser),
            "locations": _load(connection, LOCATIONS, location_sql, _location),
            "regions": _load(connection, REGIONS, region_sql, _region),
        }
        checks = {
            "advertisers": "SELECT COUNT(*), COALESCE(SUM(amount_spent_usd), 0) FROM advertisers",
            "locations": "SELECT COUNT(*), COALESCE(SUM(amount_spent_usd), 0) FROM locations",
            "regions": "SELECT COUNT(*), COALESCE(SUM(amount_spent_usd), 0) FROM regions",
        }
        for name, query in checks.items():
            count, total = connection.execute(query).fetchone()
            expect_count, expect_total = loaded[name]
            if count != expect_count or total != expect_total:
                raise RuntimeError(
                    f"{name} load check failed: sqlite {count:,} ${total:,} "
                    f"vs file {expect_count:,} ${expect_total:,}"
                )
        print("Indexing")
        connection.executescript(
            """
            CREATE INDEX idx_advertisers_window_week ON advertisers (window, date_start);
            CREATE INDEX idx_advertisers_page ON advertisers (page_id, disclaimer, window);
            CREATE INDEX idx_locations_window ON locations (window, location_name);
            CREATE INDEX idx_regions_window ON regions (window, region);
            """
        )
        connection.commit()
    finally:
        connection.close()
    print(f"Wrote {db_path.relative_to(ROOT)}")
    return db_path


if __name__ == "__main__":
    build_database()
