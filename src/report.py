"""Print the figures the write-up quotes.

Amounts are whole dollars, as Meta reported them. Rates and per-person
figures are half-up, from src/formatters.py.
"""

from __future__ import annotations

import pandas as pd

from src.formatters import advertiser_label, per_ad, per_person, pretty_category, rate_pct, usd


def _week(iso: str) -> str:
    year, month, day = str(iso).split("-")
    months = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }
    return f"{int(day)} {months[month]} {year}"


def _usd_median(value: float) -> str:
    if float(value).is_integer():
        return usd(int(value))
    return f"${value:,.2f}"


def key_figures(report: dict) -> list[str]:
    """Formatted figures the README must contain, verbatim."""
    coverage = report["coverage"]
    concentration = report["concentration"]
    total = coverage["advertiser_spend_weekly"]
    positive_n = concentration["n_advertisers"]
    top = concentration["ranked"].iloc[0]
    peak = report["peak_week"]
    trough = report["trough_week"]
    state = report["states"].iloc[0]
    per_capita_leader = report["per_capita"].iloc[0]
    unknown = report["states"].loc[report["states"]["location_name"] == "unknown"]
    unknown_spend = int(unknown["spend_usd"].iloc[0]) if len(unknown) else 0
    other = report["categories"].loc[report["categories"]["category"] == "other"].iloc[0]
    new_spend = int(report["new_page_spend"])
    post = coverage["post_snapshot_spend"]
    location_gap = coverage["location_spend_weekly"] - total
    region_gap = coverage["location_spend_weekly"] - coverage["region_spend_weekly"]
    lifelong_top = report["lifelong_top"].iloc[0]
    fresh = report["new_pages"].iloc[0]
    million_bucket = report["buckets"].loc[report["buckets"]["bucket"] == "$1,000,000 or more"].iloc[0]
    zero_bucket = report["buckets"].loc[report["buckets"]["bucket"] == "$0"].iloc[0]
    return [
        usd(total),
        usd(coverage["advertiser_spend_lifelong"]),
        usd(coverage["location_spend_weekly"]),
        usd(coverage["region_spend_weekly"]),
        usd(abs(location_gap)),
        usd(region_gap),
        usd(int(top.spend_usd)),
        advertiser_label(top.page_name, top.disclaimer, 80),
        rate_pct(concentration["top10_spend"], concentration["total_spend"]),
        rate_pct(concentration["top1pct_spend"], concentration["total_spend"]),
        f"{concentration['top_1pct_n']:,}",
        f"{positive_n:,}",
        f"{concentration['n_for_50']:,}",
        f"{concentration['n_for_80']:,}",
        per_ad(total, coverage["num_ads_weekly"]),
        per_ad(coverage["positive_row_spend"], coverage["positive_row_ads"]),
        rate_pct(coverage["zero_row_ads"], coverage["num_ads_weekly"]),
        f"{coverage['zero_rows_weekly']:,}",
        f"{coverage['advertiser_rows_weekly']:,}",
        _usd_median(report["median_positive_spend"]),
        per_ad(total, positive_n),
        usd(int(state.spend_usd)),
        state.location_name.title(),
        per_person(int(per_capita_leader.spend_usd), int(per_capita_leader.population_2025)),
        per_capita_leader.census_name,
        usd(unknown_spend),
        rate_pct(int(other.spend_usd), total),
        pretty_category("other"),
        usd(new_spend),
        rate_pct(new_spend, post),
        usd(post),
        usd(coverage["overlap_week_spend"]),
        usd(int(peak.spend_usd)),
        _week(peak.date_start),
        usd(int(trough.spend_usd)),
        _week(trough.date_start),
        advertiser_label(fresh.page_name, fresh.disclaimer, 80),
        usd(int(fresh.post_snapshot_spend_usd)),
        advertiser_label(lifelong_top.page_name, lifelong_top.disclaimer, 80),
        usd(int(lifelong_top.lifelong_spend_usd)),
        usd(int(lifelong_top.post_snapshot_spend_usd)),
        rate_pct(int(million_bucket.spend_usd), total),
        rate_pct(int(million_bucket.advertisers), int(len(report["advertisers"]))),
        f"{int(zero_bucket.advertisers):,}",
        rate_pct(coverage["lifelong_spend_with_no_post_activity"], coverage["advertiser_spend_lifelong"]),
        usd(coverage["new_pair_spend"]),
        f"{coverage['new_pairs']:,}",
        f"{int(report['new_pages'].shape[0]):,}",
        usd(int(report["one_week_spend"])),
        rate_pct(int(report["one_week_spend"]), total),
    ]


def print_report(report: dict) -> None:
    coverage = report["coverage"]
    total = coverage["advertiser_spend_weekly"]
    print("US Meta political and issue ad spend")
    print(f"Source path: {report['source']}")
    print(f"Observed weekly spend (advertisers): {usd(total)}")
    print(f"Lifelong spend through 25 Oct 2025 (advertisers): {usd(coverage['advertiser_spend_lifelong'])}")
    print(f"Observed weeks: {coverage['n_weeks']}")
    print(f"Overlap week of 20 Oct 2025: {usd(coverage['overlap_week_spend'])}")
    print(f"Post-snapshot spend (weeks starting 27 Oct 2025 or later): {usd(coverage['post_snapshot_spend'])}")
    print(f"Location-report weekly spend: {usd(coverage['location_spend_weekly'])}")
    print(f"Region-file weekly spend: {usd(coverage['region_spend_weekly'])}")
    print(f"Location minus advertisers: {usd(coverage['location_spend_weekly'] - total)}")
    print(f"Location minus regions: {usd(coverage['location_spend_weekly'] - coverage['region_spend_weekly'])}")
    print(f"Lifelong location spend: {usd(coverage['location_spend_lifelong'])}")
    print(f"Missing location rows: {coverage['missing_location_note']}")
    print(f"Weekly advertiser rows: {coverage['advertiser_rows_weekly']:,}")
    print(f"Rows with $0 spend: {coverage['zero_rows_weekly']:,}")
    print(f"Ad-weeks: {coverage['num_ads_weekly']:,}")
    print(f"Ad-weeks on $0 rows: {coverage['zero_row_ads']:,} ({rate_pct(coverage['zero_row_ads'], coverage['num_ads_weekly'])})")
    print(f"Spend per ad-week: {per_ad(total, coverage['num_ads_weekly'])}")
    print(
        "Spend per ad-week on rows with positive spend: "
        f"{per_ad(coverage['positive_row_spend'], coverage['positive_row_ads'])}"
    )

    print("\nWeekly")
    print(f"{'start':<12} {'end':<12} {'spend':>16} {'ads':>12} {'rows':>8} {'location':>16}")
    for row in report["weekly"].itertuples(index=False):
        print(
            f"{row.date_start:<12} {row.date_end:<12} {usd(int(row.spend_usd)):>16} "
            f"{int(row.num_ads):>12,} {int(row.advertiser_rows):>8,} {usd(int(row.location_spend_usd)):>16}"
        )
    peak = report["peak_week"]
    trough = report["trough_week"]
    print(f"Peak: {_week(peak.date_start)} {usd(int(peak.spend_usd))}")
    print(f"Trough: {_week(trough.date_start)} {usd(int(trough.spend_usd))}")

    concentration = report["concentration"]
    print("\nConcentration, positive spend only")
    print(f"Advertisers: {concentration['n_advertisers']:,}")
    print(f"Top 10 spend: {usd(concentration['top10_spend'])} ({rate_pct(concentration['top10_spend'], concentration['total_spend'])})")
    print(
        f"Top 1% ({concentration['top_1pct_n']:,}) spend: {usd(concentration['top1pct_spend'])} "
        f"({rate_pct(concentration['top1pct_spend'], concentration['total_spend'])})"
    )
    print(f"Advertisers to reach 50% of positive spend: {concentration['n_for_50']:,}")
    print(f"Advertisers to reach 80% of positive spend: {concentration['n_for_80']:,}")
    print(f"Median positive advertiser: {_usd_median(report['median_positive_spend'])}")
    print(f"Mean positive advertiser: {per_ad(total, concentration['n_advertisers'])}")
    print(
        f"One observed week: {report['one_week_advertisers']:,} advertisers, "
        f"{usd(report['one_week_spend'])} ({rate_pct(report['one_week_spend'], total)})"
    )
    print(
        f"10 or more observed weeks: {report['many_week_advertisers']:,} advertisers, "
        f"{usd(report['many_week_spend'])} ({rate_pct(report['many_week_spend'], total)})"
    )

    print("\nTop 15 weekly advertisers")
    print(f"{'spend':>14} {'lifelong':>14} {'post':>14} {'ads':>8} {'weeks':>5} {'category':<28} name")
    for row in concentration["ranked"].head(15).itertuples():
        print(
            f"{usd(int(row.spend_usd)):>14} {usd(int(row.lifelong_spend_usd)):>14} "
            f"{usd(int(row.post_snapshot_spend_usd)):>14} {int(row.num_ads):>8,} {int(row.weeks_observed):>5} "
            f"{pretty_category(row.category):<28} {advertiser_label(row.page_name, row.disclaimer, 70)}"
        )

    print("\nCategories")
    for row in report["categories"].itertuples():
        print(
            f"{pretty_category(row.category):<28} {usd(int(row.spend_usd)):>14} "
            f"{rate_pct(int(row.spend_usd), total):>8} "
            f"positive {int(row.positive_advertisers):>6,}  ads {int(row.num_ads):>10,}"
        )

    print("\nSize buckets, all weekly advertisers")
    advertiser_n = len(report["advertisers"])
    for row in report["buckets"].itertuples():
        print(
            f"{row.bucket:<22} advertisers {int(row.advertisers):>7,} ({rate_pct(int(row.advertisers), advertiser_n):>8})  "
            f"spend {usd(int(row.spend_usd)):>14} ({rate_pct(int(row.spend_usd), total):>8})  "
            f"spend/ad {per_ad(int(row.spend_usd), int(row.num_ads))}"
        )

    print("\nStates, location report")
    location_total = coverage["location_spend_weekly"]
    for row in report["states"].head(15).itertuples():
        per = "n/a" if pd.isna(row.population_2025) else per_person(int(row.spend_usd), int(row.population_2025))
        print(
            f"{row.location_name:<32} {usd(int(row.spend_usd)):>14} "
            f"{rate_pct(int(row.spend_usd), location_total):>8}  {per:>10}"
        )
    print("...")
    print("Per capita leaders")
    for row in report["per_capita"].head(10).itertuples():
        print(
            f"{row.census_name:<28} {per_person(int(row.spend_usd), int(row.population_2025)):>10}  "
            f"spend {usd(int(row.spend_usd))}"
        )
    print("Per capita, lowest 5")
    for row in report["per_capita"].tail(5).itertuples():
        print(
            f"{row.census_name:<28} {per_person(int(row.spend_usd), int(row.population_2025)):>10}  "
            f"spend {usd(int(row.spend_usd))}"
        )

    print("\nNew pages (no positive lifelong spend), top 10 by post-snapshot spend")
    print(
        f"Pairs: {len(report['new_pages']):,}  post-snapshot spend {usd(report['new_page_spend'])} "
        f"({rate_pct(report['new_page_spend'], coverage['post_snapshot_spend'])})"
    )
    print(
        f"New disclaimer on a page that already had lifelong spend: "
        f"{report['new_disclaimer_pairs']:,} pairs, {usd(report['new_disclaimer_spend'])}"
    )
    print(
        f"SQL pair-level new (lifelong pair spend is $0): {coverage['new_pairs']:,} pairs, "
        f"{usd(coverage['new_pair_spend'])}"
    )
    print(
        f"Lifelong spend on pairs with no positive post-snapshot spend: "
        f"{usd(coverage['lifelong_spend_with_no_post_activity'])} "
        f"({rate_pct(coverage['lifelong_spend_with_no_post_activity'], coverage['advertiser_spend_lifelong'])})"
    )
    for row in report["new_pages"].head(10).itertuples():
        print(
            f"{usd(int(row.post_snapshot_spend_usd)):>14}  {pretty_category(row.category):<28} "
            f"{advertiser_label(row.page_name, row.disclaimer, 70)}"
        )

    print("\nLifelong top 15")
    for row in report["lifelong_top"].itertuples():
        print(
            f"lifelong {usd(int(row.lifelong_spend_usd)):>14}  recent {usd(int(row.post_snapshot_spend_usd)):>12}  "
            f"page {usd(int(row.page_post_snapshot_spend_usd)):>12}  "
            f"{advertiser_label(row.page_name, row.disclaimer, 70)}"
        )
