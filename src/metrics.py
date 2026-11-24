"""Build the tables the charts and the write-up use.

With the raw CSVs present, this loads SQLite, runs the queries in sql/, and
writes data/processed/. Without the raw CSVs, it reads those processed files.
Both paths hand the same frames to the charts.
"""

from __future__ import annotations

import os
import sqlite3
import statistics
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.classify import classify_pair
from src.constants import (
    CATEGORY_ORDER,
    EXCLUDED_FROM_PER_CAPITA,
    FIRST_WEEK_START,
    LAST_WEEK_END,
    LOCATION_TO_CENSUS_NAME,
    MISSING_WEEKS,
    POST_SNAPSHOT_START,
    SIZE_BINS,
)
from src.formatters import per_person

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
DB_PATH = ROOT / "data" / "meta_ad_library.db"
PROCESSED = ROOT / "data" / "processed"
POPULATION_PATH = ROOT / "data" / "external" / "state_population_2025.csv"
GEOJSON_PATH = ROOT / "data" / "external" / "us_states_20m.geojson"

RAW_FILES = (
    ROOT / "data" / "raw" / "META_AD_LIBRARY.ADVERTISERS.csv",
    ROOT / "data" / "raw" / "META_AD_LIBRARY.LOCATIONS.csv",
    ROOT / "data" / "raw" / "META_AD_LIBRARY.REGIONS.csv",
)


def raw_available() -> bool:
    return all(path.exists() for path in RAW_FILES)


def _read_sql(connection: sqlite3.Connection, name: str) -> pd.DataFrame:
    query = (SQL_DIR / name).read_text()
    return pd.read_sql_query(query, connection)


def _advertiser_extract(connection: sqlite3.Connection) -> pd.DataFrame:
    # The staged script creates temp tables. The extract query joins them.
    # One combined statement is not usable here: SQLite rebuilds the lookups
    # in a loop and does not finish.
    connection.executescript((SQL_DIR / "stage_advertisers.sql").read_text())
    return _read_sql(connection, "extract_advertisers.sql")


def _week_starts(first: str, last: str) -> list[str]:
    current = date.fromisoformat(first)
    stop = date.fromisoformat(last)
    starts = []
    while current <= stop:
        starts.append(current.isoformat())
        current += timedelta(days=7)
    return starts


def _census_name(location_name: str) -> str | None:
    if location_name in EXCLUDED_FROM_PER_CAPITA:
        return None
    return LOCATION_TO_CENSUS_NAME.get(location_name, location_name.title())


def _population() -> pd.DataFrame:
    frame = pd.read_csv(POPULATION_PATH, dtype={"fips": "string"})
    frame["population_2025"] = frame["population_2025"].astype(int)
    return frame


def _postal_by_name() -> dict[str, str]:
    import json

    payload = json.loads(GEOJSON_PATH.read_text())
    return {
        feature["properties"]["name"]: feature["properties"]["stusps"]
        for feature in payload["features"]
    }


def _states(connection: sqlite3.Connection) -> pd.DataFrame:
    spend = _read_sql(connection, "04_states.sql")
    population = _population()
    postal = _postal_by_name()
    rows = []
    for record in spend.itertuples(index=False):
        census_name = _census_name(record.location_name)
        if census_name is None:
            rows.append(
                {
                    "location_name": record.location_name,
                    "census_name": "",
                    "postal": "",
                    "spend_usd": int(record.spend_usd),
                    "population_2025": pd.NA,
                    "per_capita": pd.NA,
                }
            )
            continue
        match = population.loc[population["name"] == census_name]
        if match.empty:
            raise KeyError(f"No Census population row for {census_name!r} ({record.location_name})")
        pop = int(match.iloc[0]["population_2025"])
        rows.append(
            {
                "location_name": record.location_name,
                "census_name": census_name,
                "postal": postal.get(census_name, ""),
                "spend_usd": int(record.spend_usd),
                "population_2025": pop,
                "per_capita": int(record.spend_usd) / pop,
            }
        )
    states = pd.DataFrame(rows)
    total = int(states["spend_usd"].sum())
    states["spend_share"] = states["spend_usd"] / total
    return states.sort_values(["spend_usd", "location_name"], ascending=[False, True]).reset_index(drop=True)


def _missing_location_rows(connection: sqlite3.Connection) -> list[tuple[str, str, int]]:
    frame = pd.read_sql_query(
        """
        SELECT date_start, location_name, amount_spent_usd
        FROM locations
        WHERE window = 'last_7_days'
        """,
        connection,
    )
    present = set(zip(frame["date_start"], frame["location_name"]))
    notes = []
    for week in sorted(frame["date_start"].unique()):
        for location in sorted(frame["location_name"].unique()):
            if (week, location) not in present:
                other = frame.loc[frame["location_name"] == location, "amount_spent_usd"]
                notes.append((week, location, int(other.sum())))
    return notes


def _classify(advertisers: pd.DataFrame) -> pd.DataFrame:
    frame = advertisers.copy()
    frame["category"] = [
        classify_pair(page, disclaimer)
        for page, disclaimer in zip(frame["page_name"], frame["disclaimer"])
    ]
    return frame


def _write_classified(connection: sqlite3.Connection, advertisers: pd.DataFrame) -> None:
    connection.execute("DELETE FROM classified_weekly")
    connection.executemany(
        """
        INSERT INTO classified_weekly (
            page_id, page_name, disclaimer, spend_usd, num_ads, weeks_observed,
            post_snapshot_spend_usd, post_snapshot_num_ads, lifelong_spend_usd,
            lifelong_num_ads, page_lifelong_spend_usd, category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.page_id,
                row.page_name,
                row.disclaimer,
                int(row.spend_usd),
                int(row.num_ads),
                int(row.weeks_observed),
                int(row.post_snapshot_spend_usd),
                int(row.post_snapshot_num_ads),
                int(row.lifelong_spend_usd),
                int(row.lifelong_num_ads),
                int(row.page_lifelong_spend_usd),
                row.category,
            )
            for row in advertisers.itertuples(index=False)
        ],
    )
    connection.commit()


def _concentration(advertisers: pd.DataFrame) -> dict:
    positive = advertisers.loc[advertisers["spend_usd"] > 0].copy()
    positive = positive.sort_values(
        ["spend_usd", "page_id", "disclaimer"], ascending=[False, True, True]
    ).reset_index(drop=True)
    spends = [int(value) for value in positive["spend_usd"]]
    total = sum(spends)
    count = len(spends)
    top_1pct_n = (count + 99) // 100
    cumulative = 0
    n_for_50 = None
    n_for_80 = None
    curve = []
    for rank, spend in enumerate(spends, start=1):
        cumulative += spend
        if n_for_50 is None and cumulative * 2 >= total:
            n_for_50 = rank
        if n_for_80 is None and cumulative * 5 >= total * 4:
            n_for_80 = rank
        curve.append((rank, spend, cumulative))
    return {
        "n_advertisers": count,
        "total_spend": total,
        "top_1pct_n": top_1pct_n,
        "top10_spend": sum(spends[:10]),
        "top1pct_spend": sum(spends[:top_1pct_n]),
        "n_for_50": n_for_50,
        "n_for_80": n_for_80,
        "curve": curve,
        "ranked": positive,
    }


def _assert_concentration(connection: sqlite3.Connection, concentration: dict) -> None:
    sql_row = _read_sql(connection, "03_concentration.sql").iloc[0]
    pairs = {
        "n_advertisers": int(sql_row.n_advertisers),
        "total_spend": int(sql_row.total_spend),
        "top_1pct_n": int(sql_row.top_1pct_n),
        "top10_spend": int(sql_row.top10_spend),
        "top1pct_spend": int(sql_row.top1pct_spend),
        "n_for_50": int(sql_row.n_for_50),
        "n_for_80": int(sql_row.n_for_80),
    }
    for key, value in pairs.items():
        if concentration[key] != value:
            raise RuntimeError(f"Concentration mismatch on {key}: python {concentration[key]} sql {value}")


def _coverage_from_sql(
    connection: sqlite3.Connection,
    weekly: pd.DataFrame,
    states: pd.DataFrame,
    missing_locations: list[tuple[str, str, int]],
) -> dict:
    recon = _read_sql(connection, "09_reconciliation.sql")
    by_source = {row.source: row for row in recon.itertuples(index=False)}
    per_ad = _read_sql(connection, "06_spend_per_ad.sql").iloc[0]
    lifelong = _read_sql(connection, "07_lifelong.sql").iloc[0]
    observed = weekly["date_start"].tolist()
    expected = _week_starts(FIRST_WEEK_START, "2026-04-13")
    missing = [start for start in expected if start not in set(observed)]
    expected_missing = [start for start, _end in MISSING_WEEKS]
    if missing != expected_missing:
        raise RuntimeError(f"Missing weeks {missing} != {expected_missing}")
    if observed[0] != FIRST_WEEK_START or weekly["date_end"].iloc[-1] != LAST_WEEK_END:
        raise RuntimeError("Weekly window does not run from 2025-10-20 to 2026-04-19")
    overlap = int(weekly.loc[weekly["date_start"] == FIRST_WEEK_START, "spend_usd"].iloc[0])
    post = int(weekly.loc[weekly["date_start"] >= POST_SNAPSHOT_START, "spend_usd"].sum())
    if missing_locations:
        location_note = "; ".join(
            f"{week} {name} (that geography sums to ${other:,} in the weeks it is present)"
            for week, name, other in missing_locations
        )
    else:
        location_note = "none"
    return {
        "advertiser_spend_weekly": int(by_source["advertisers"].spend_usd),
        "advertiser_rows_weekly": int(by_source["advertisers"].rows),
        "location_spend_weekly": int(by_source["locations"].spend_usd),
        "location_rows_weekly": int(by_source["locations"].rows),
        "region_spend_weekly": int(by_source["regions"].spend_usd),
        "region_rows": int(by_source["regions"].rows),
        "advertiser_spend_lifelong": int(by_source["lifelong_advertisers"].spend_usd),
        "advertiser_rows_lifelong": int(by_source["lifelong_advertisers"].rows),
        "location_spend_lifelong": int(by_source["lifelong_locations"].spend_usd),
        "num_ads_weekly": int(per_ad.num_ads),
        "zero_rows_weekly": int(per_ad.zero_rows),
        "zero_row_ads": int(per_ad.zero_row_ads),
        "positive_row_spend": int(per_ad.positive_row_spend),
        "positive_row_ads": int(per_ad.positive_row_ads),
        "n_weeks": int(len(weekly)),
        "overlap_week_spend": overlap,
        "post_snapshot_spend": post,
        "lifelong_pairs": int(lifelong.pairs),
        "new_pairs": int(lifelong.new_pairs),
        "new_pair_spend": int(lifelong.new_pair_spend),
        "pairs_with_lifelong_spend": int(lifelong.pairs_with_lifelong_spend),
        "lifelong_spend_with_no_post_activity": int(lifelong.lifelong_spend_with_no_post_activity),
        "state_spend_total": int(states["spend_usd"].sum()),
        "missing_location_note": location_note,
    }
    if int(lifelong.post_spend_usd) != post:
        raise RuntimeError(
            f"Post-snapshot spend mismatch: sql {int(lifelong.post_spend_usd):,} vs weekly {post:,}"
        )


def _write_processed(report: dict) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    weekly = report["weekly"].copy()
    weekly.to_csv(PROCESSED / "weekly_spend.csv", index=False)
    advertisers = report["advertisers"].copy()
    advertisers.to_csv(PROCESSED / "advertisers.csv", index=False)
    states = report["states"].copy()
    states.to_csv(PROCESSED / "states.csv", index=False)
    report["lifelong_top"].to_csv(PROCESSED / "lifelong_top.csv", index=False)
    coverage = pd.DataFrame(
        [{"key": key, "value": value} for key, value in report["coverage"].items()]
    )
    coverage.to_csv(PROCESSED / "coverage.csv", index=False)


def _derive(report: dict) -> dict:
    """Tables that are functions of the processed frames, on either path."""
    advertisers = report["advertisers"]
    weekly = report["weekly"]
    states = report["states"]
    coverage = report["coverage"]
    concentration = _concentration(advertisers)
    positive = concentration["ranked"]

    categories = (
        advertisers.groupby("category", as_index=False)
        .agg(
            advertisers=("page_id", "size"),
            positive_advertisers=("spend_usd", lambda s: int((s > 0).sum())),
            spend_usd=("spend_usd", "sum"),
            num_ads=("num_ads", "sum"),
        )
    )
    categories["spend_usd"] = categories["spend_usd"].astype(int)
    categories["num_ads"] = categories["num_ads"].astype(int)
    categories["spend_share"] = categories["spend_usd"] / int(coverage["advertiser_spend_weekly"])
    categories["_order"] = categories["category"].map({name: index for index, name in enumerate(CATEGORY_ORDER)})
    categories = categories.sort_values(["spend_usd", "_order"], ascending=[False, True]).drop(columns="_order")

    buckets = []
    zero = advertisers.loc[advertisers["spend_usd"] == 0]
    buckets.append(
        {
            "bucket": "$0",
            "advertisers": int(len(zero)),
            "spend_usd": 0,
            "num_ads": int(zero["num_ads"].sum()),
        }
    )
    for label, low, high in SIZE_BINS:
        if high is None:
            mask = positive["spend_usd"] >= low
        else:
            mask = (positive["spend_usd"] >= low) & (positive["spend_usd"] < high)
        part = positive.loc[mask]
        buckets.append(
            {
                "bucket": label,
                "advertisers": int(len(part)),
                "spend_usd": int(part["spend_usd"].sum()),
                "num_ads": int(part["num_ads"].sum()),
            }
        )
    bucket_frame = pd.DataFrame(buckets)
    advertiser_n = int(len(advertisers))
    bucket_frame["advertiser_share"] = bucket_frame["advertisers"] / advertiser_n
    bucket_frame["spend_share"] = bucket_frame["spend_usd"] / int(coverage["advertiser_spend_weekly"])

    new_pages = positive.loc[
        (positive["post_snapshot_spend_usd"] > 0) & (positive["page_lifelong_spend_usd"] == 0)
    ].sort_values(["post_snapshot_spend_usd", "page_id"], ascending=[False, True])
    new_disclaimers = positive.loc[
        (positive["post_snapshot_spend_usd"] > 0)
        & (positive["lifelong_spend_usd"] == 0)
        & (positive["page_lifelong_spend_usd"] > 0)
    ]

    spends = [int(value) for value in positive["spend_usd"]]
    median_spend = statistics.median(spends) if spends else 0

    one_week = positive.loc[positive["weeks_observed"] == 1]
    many_weeks = positive.loc[positive["weeks_observed"] >= 10]
    peak_idx = int(weekly["spend_usd"].idxmax())
    trough_idx = int(weekly["spend_usd"].idxmin())

    per_capita = states.dropna(subset=["population_2025"]).sort_values(
        ["per_capita", "location_name"], ascending=[False, True]
    )

    report.update(
        {
            "concentration": concentration,
            "categories": categories.reset_index(drop=True),
            "buckets": bucket_frame,
            "new_pages": new_pages.reset_index(drop=True),
            "new_disclaimer_spend": int(new_disclaimers["post_snapshot_spend_usd"].sum()),
            "new_disclaimer_pairs": int(len(new_disclaimers)),
            "new_page_spend": int(new_pages["post_snapshot_spend_usd"].sum()),
            "median_positive_spend": median_spend,
            "mean_positive_spend": int(coverage["advertiser_spend_weekly"] // max(len(positive), 1)),
            "one_week_advertisers": int(len(one_week)),
            "one_week_spend": int(one_week["spend_usd"].sum()),
            "many_week_advertisers": int(len(many_weeks)),
            "many_week_spend": int(many_weeks["spend_usd"].sum()),
            "peak_week": weekly.loc[peak_idx],
            "trough_week": weekly.loc[trough_idx],
            "per_capita": per_capita.reset_index(drop=True),
        }
    )
    return report


def build_from_sqlite() -> dict:
    from sql.load_sqlite import build_database

    if os.environ.get("REBUILD_DB", "1") == "1" or not DB_PATH.exists():
        build_database(DB_PATH)
    connection = sqlite3.connect(DB_PATH)
    try:
        weekly = _read_sql(connection, "01_weekly_spend.sql")
        for column in ("spend_usd", "num_ads", "advertiser_rows", "positive_rows", "zero_row_ads"):
            weekly[column] = weekly[column].astype(int)
        location_weekly = pd.read_sql_query(
            """
            SELECT date_start, SUM(amount_spent_usd) AS location_spend_usd
            FROM locations
            WHERE window = 'last_7_days'
            GROUP BY date_start
            """,
            connection,
        )
        weekly = weekly.merge(location_weekly, on="date_start", how="left")
        weekly["location_spend_usd"] = weekly["location_spend_usd"].astype(int)
        advertisers = _classify(_advertiser_extract(connection))
        int_columns = [
            "spend_usd",
            "num_ads",
            "weeks_observed",
            "post_snapshot_spend_usd",
            "post_snapshot_num_ads",
            "lifelong_spend_usd",
            "lifelong_num_ads",
            "page_lifelong_spend_usd",
        ]
        for column in int_columns:
            advertisers[column] = advertisers[column].astype(int)
        if int(advertisers["spend_usd"].sum()) != int(weekly["spend_usd"].sum()):
            raise RuntimeError("Advertiser extract does not sum to the weekly total")
        states = _states(connection)
        missing_locations = _missing_location_rows(connection)
        coverage = _coverage_from_sql(connection, weekly, states, missing_locations)
        concentration = _concentration(advertisers)
        _assert_concentration(connection, concentration)
        _write_classified(connection, advertisers)
        categories_sql = _read_sql(connection, "05_categories.sql")
        if int(categories_sql["spend_usd"].sum()) != coverage["advertiser_spend_weekly"]:
            raise RuntimeError("Category spend does not sum to the weekly total")
        lifelong_top = _read_sql(connection, "10_lifelong_top.sql")
        lifelong_top["lifelong_spend_usd"] = lifelong_top["lifelong_spend_usd"].astype(int)
        lifelong_top["post_snapshot_spend_usd"] = lifelong_top["post_snapshot_spend_usd"].astype(int)
        lifelong_top["page_post_snapshot_spend_usd"] = lifelong_top["page_post_snapshot_spend_usd"].astype(int)
    finally:
        connection.close()

    report = {
        "weekly": weekly,
        "advertisers": advertisers,
        "states": states,
        "lifelong_top": lifelong_top,
        "coverage": coverage,
        "source": "sqlite",
    }
    report = _derive(report)
    _write_processed(report)
    return report


def _coverage_from_csv(frame: pd.DataFrame) -> dict:
    int_keys = {
        "advertiser_spend_weekly",
        "advertiser_rows_weekly",
        "location_spend_weekly",
        "location_rows_weekly",
        "region_spend_weekly",
        "region_rows",
        "advertiser_spend_lifelong",
        "advertiser_rows_lifelong",
        "location_spend_lifelong",
        "num_ads_weekly",
        "zero_rows_weekly",
        "zero_row_ads",
        "positive_row_spend",
        "positive_row_ads",
        "n_weeks",
        "overlap_week_spend",
        "post_snapshot_spend",
        "lifelong_pairs",
        "new_pairs",
        "new_pair_spend",
        "pairs_with_lifelong_spend",
        "lifelong_spend_with_no_post_activity",
        "state_spend_total",
    }
    coverage = {}
    for row in frame.itertuples(index=False):
        coverage[row.key] = int(row.value) if row.key in int_keys else str(row.value)
    return coverage


def build_from_processed() -> dict:
    weekly = pd.read_csv(PROCESSED / "weekly_spend.csv")
    advertisers = pd.read_csv(
        PROCESSED / "advertisers.csv",
        dtype={"page_id": "string", "page_name": "string", "disclaimer": "string", "category": "string"},
    )
    states = pd.read_csv(PROCESSED / "states.csv")
    lifelong_top = pd.read_csv(PROCESSED / "lifelong_top.csv")
    coverage = _coverage_from_csv(pd.read_csv(PROCESSED / "coverage.csv", dtype=str))
    for column in (
        "spend_usd",
        "num_ads",
        "advertiser_rows",
        "positive_rows",
        "zero_row_ads",
        "location_spend_usd",
    ):
        weekly[column] = weekly[column].astype(int)
    for column in (
        "spend_usd",
        "num_ads",
        "weeks_observed",
        "post_snapshot_spend_usd",
        "post_snapshot_num_ads",
        "lifelong_spend_usd",
        "lifelong_num_ads",
        "page_lifelong_spend_usd",
    ):
        advertisers[column] = advertisers[column].astype(int)
    states["spend_usd"] = states["spend_usd"].astype(int)
    states["population_2025"] = pd.to_numeric(states["population_2025"], errors="coerce")
    states["per_capita"] = pd.to_numeric(states["per_capita"], errors="coerce")
    lifelong_top["lifelong_spend_usd"] = lifelong_top["lifelong_spend_usd"].astype(int)
    lifelong_top["post_snapshot_spend_usd"] = lifelong_top["post_snapshot_spend_usd"].astype(int)
    if "page_post_snapshot_spend_usd" in lifelong_top.columns:
        lifelong_top["page_post_snapshot_spend_usd"] = lifelong_top["page_post_snapshot_spend_usd"].astype(int)
    report = {
        "weekly": weekly,
        "advertisers": advertisers,
        "states": states,
        "lifelong_top": lifelong_top,
        "coverage": coverage,
        "source": "processed",
    }
    return _derive(report)


def build_report() -> dict:
    if raw_available():
        return build_from_sqlite()
    if (PROCESSED / "advertisers.csv").exists():
        return build_from_processed()
    raise FileNotFoundError(
        "No raw CSVs in data/raw and no processed tables. Run python scripts/download_data.py"
    )


def per_capita_label(row: pd.Series) -> str:
    return per_person(int(row.spend_usd), int(row.population_2025))
