"""Charts for the US Meta political and issue ad spend review.

Each figure states the comparison in the title and the reading rule in the
subtitle. Bar labels use the same half-up formatting as the printed tables.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Polygon

from src.formatters import advertiser_label, millions, per_person, pretty_category, rate_pct, usd, usd_compact
from src.metrics import GEOJSON_PATH

INK = "#1C2B33"
TEAL = "#1F7A6B"
CORAL = "#C4493A"
GOLD = "#B5812F"
NAVY = "#1E3A5F"
BLUE = "#3D6F99"
SLATE = "#5C6B73"
SPEND = "#8A8178"
SAND = "#F3E6C8"
GRID = "#E6E0D6"
MUTED = "#C8C2B8"
PALE = "#F7F4EE"

CATEGORY_COLORS = {
    "candidate": TEAL,
    "advocacy": NAVY,
    "party": GOLD,
    "company": SPEND,
    "government": BLUE,
    "media": "#6E5A7D",
    "other": MUTED,
}


def _apply_style() -> None:
    sns.set_theme(style="whitegrid", font="DejaVu Sans")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#E0DACF",
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "regular",
            "axes.labelsize": 10,
            "xtick.color": SLATE,
            "ytick.color": INK,
            "text.color": INK,
            "font.size": 10,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
            "legend.fontsize": 9,
        }
    )


def _finish(fig: plt.Figure, path: Path, source: str) -> None:
    fig.text(0.0, -0.02, source, ha="left", va="top", fontsize=8, color=SLATE)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white", pad_inches=0.35)
    plt.close(fig)


def _source(report: dict) -> str:
    weeks = int(report["coverage"]["n_weeks"])
    return (
        "US Meta Ad Library  ·  political and issue ads only  ·  whole USD  ·  "
        f"{weeks} observed weeks, 20 Oct 2025–19 Apr 2026  ·  "
        "weeks of 10 Nov, 17 Nov, and 24 Nov 2025 are not in the file"
    )


def _week(iso: str) -> str:
    value = datetime.strptime(str(iso), "%Y-%m-%d")
    return f"{value.day} {value.strftime('%b %Y')}"


def _short_week(iso: str) -> str:
    value = datetime.strptime(str(iso), "%Y-%m-%d")
    return f"{value.day} {value.strftime('%b')}"


def plot_weekly(report: dict) -> plt.Figure:
    weekly = report["weekly"].sort_values("date_start")
    observed = {row.date_start: int(row.spend_usd) for row in weekly.itertuples()}
    start = datetime.strptime(weekly["date_start"].iloc[0], "%Y-%m-%d")
    end = datetime.strptime(weekly["date_start"].iloc[-1], "%Y-%m-%d")
    cursor = start
    starts = []
    while cursor <= end:
        starts.append(cursor.strftime("%Y-%m-%d"))
        cursor = cursor + pd.Timedelta(days=7)

    peak = report["peak_week"]
    trough = report["trough_week"]
    fig, ax = plt.subplots(figsize=(12.4, 6.6), constrained_layout=True)
    labeled_gap = False
    for index, week_start in enumerate(starts):
        if week_start not in observed:
            ax.axvspan(index - 0.5, index + 0.5, color=SAND, zorder=0, label="Not in the file" if not labeled_gap else None)
            labeled_gap = True
            continue
        ax.bar(index, millions(observed[week_start]), color=TEAL, width=0.78, zorder=2)
    ax.set_xticks(range(len(starts)))
    ax.set_xticklabels([_short_week(value) for value in starts], rotation=45, ha="right")
    ax.set_ylabel("USD millions")
    ax.set_xlim(-0.6, len(starts) - 0.4)
    ax.legend(loc="upper right")
    ax.set_title(
        f"Highest observed week {usd(int(peak.spend_usd))}, week of {_week(str(peak.date_start))}.\n"
        f"Lowest observed week {usd(int(trough.spend_usd))}, week of {_week(str(trough.date_start))}.",
        loc="left",
        color=SLATE,
        pad=8,
    )
    fig.suptitle(
        "Weekly spend, observed weeks only",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_top_advertisers(report: dict) -> plt.Figure:
    frame = report["concentration"]["ranked"].head(12).iloc[::-1]
    labels = [advertiser_label(row.page_name, row.disclaimer) for row in frame.itertuples()]
    colors = [CATEGORY_COLORS.get(row.category, MUTED) for row in frame.itertuples()]
    values = frame["spend_usd"].map(millions).to_numpy()
    fig, ax = plt.subplots(figsize=(11.4, 6.8), constrained_layout=True)
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=0.72, zorder=2)
    span = float(values.max()) if len(values) else 1
    for ypos, value, row in zip(y, values, frame.itertuples()):
        ax.text(
            value + span * 0.015,
            ypos,
            usd_compact(int(row.spend_usd)),
            va="center",
            ha="left",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD millions, sum of observed weeks")
    ax.set_xlim(0, span * 1.22)
    handles = []
    seen = []
    for code in frame["category"]:
        if code not in seen:
            seen.append(code)
            handles.append(plt.Rectangle((0, 0), 1, 1, color=CATEGORY_COLORS[code], label=pretty_category(code)))
    ax.legend(handles=handles, loc="lower right")
    top = report["concentration"]["ranked"].iloc[0]
    share = rate_pct(int(top.spend_usd), int(report["coverage"]["advertiser_spend_weekly"]))
    ax.set_title(
        f"Largest pair: {advertiser_label(top.page_name, top.disclaimer, 48)}, "
        f"{usd(int(top.spend_usd))} ({share} of observed spend).",
        loc="left",
        color=SLATE,
        pad=10,
    )
    fig.suptitle(
        "Top advertisers by observed weekly spend",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_pareto(report: dict) -> plt.Figure:
    concentration = report["concentration"]
    count = concentration["n_advertisers"]
    total = concentration["total_spend"]
    ranks = np.array([row[0] for row in concentration["curve"]])
    cumulative = np.array([row[2] for row in concentration["curve"]], dtype=float)
    x = ranks / count * 100
    y = cumulative / total * 100
    top10 = rate_pct(concentration["top10_spend"], total)
    top1 = rate_pct(concentration["top1pct_spend"], total)
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.2), constrained_layout=True)
    panels = (
        (axes[0], 100, "All positive advertisers"),
        (axes[1], 15, "First 15% of advertisers, largest first"),
    )
    for ax, xmax, panel_title in panels:
        ax.plot(x, y, color=TEAL, linewidth=2.2, zorder=3)
        ax.axhline(80, color=GOLD, linestyle="--", linewidth=1, label="80% of spend")
        ax.axhline(50, color=NAVY, linestyle=":", linewidth=1, label="50% of spend")
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, 102)
        ax.set_xlabel("Cumulative percent of advertisers")
        ax.set_ylabel("Cumulative share of positive spend")
        ax.set_title(panel_title, loc="left", color=SLATE)
    axes[1].axvline(concentration["n_for_50"] / count * 100, color=NAVY, linestyle=":", linewidth=1)
    axes[1].axvline(concentration["n_for_80"] / count * 100, color=GOLD, linestyle="--", linewidth=1)
    axes[0].legend(loc="lower right")
    fig.suptitle(
        f"Top 10 are {top10}. Top 1% ({concentration['top_1pct_n']:,}) are {top1}. "
        f"{concentration['n_for_50']:,} advertisers reach 50%, {concentration['n_for_80']:,} reach 80%.",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_categories(report: dict) -> plt.Figure:
    frame = report["categories"].sort_values("spend_usd", ascending=True)
    labels = [pretty_category(code) for code in frame["category"]]
    values = frame["spend_usd"].map(millions).to_numpy()
    colors = [CATEGORY_COLORS.get(code, MUTED) for code in frame["category"]]
    total = int(report["coverage"]["advertiser_spend_weekly"])
    fig, ax = plt.subplots(figsize=(11.2, 6.2), constrained_layout=True)
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=0.7, zorder=2)
    span = float(values.max()) if len(values) else 1
    for ypos, row in zip(y, frame.itertuples()):
        ax.text(
            millions(int(row.spend_usd)) + span * 0.015,
            ypos,
            f"{usd_compact(int(row.spend_usd))}   {rate_pct(int(row.spend_usd), total)}",
            va="center",
            ha="left",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD millions")
    ax.set_xlim(0, span * 1.38)
    ax.set_title(
        "Keyword labels from the page name and the disclaimer. Unclassified means no rule matched.",
        loc="left",
        color=SLATE,
        pad=10,
    )
    fig.suptitle(
        "Spend by derived advertiser category",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_size(report: dict) -> plt.Figure:
    frame = report["buckets"].copy()
    short_labels = {
        "$0": "$0",
        "$1–$99": "$1–99",
        "$100–$999": "$100–999",
        "$1,000–$9,999": "$1k–10k",
        "$10,000–$99,999": "$10k–100k",
        "$100,000–$999,999": "$100k–1M",
        "$1,000,000 or more": "$1M+",
    }
    frame["bucket"] = frame["bucket"].map(lambda label: short_labels.get(label, label))
    long = frame.melt(
        id_vars="bucket",
        value_vars=["advertiser_share", "spend_share"],
        var_name="metric",
        value_name="share",
    )
    long["metric"] = long["metric"].map(
        {"advertiser_share": "Share of advertisers", "spend_share": "Share of spend"}
    )
    order = frame["bucket"].tolist()
    advertiser_n = int(len(report["advertisers"]))
    spend_total = int(report["coverage"]["advertiser_spend_weekly"])
    fig, ax = plt.subplots(figsize=(12.2, 6.4), constrained_layout=True)
    sns.barplot(
        data=long,
        x="bucket",
        y="share",
        hue="metric",
        order=order,
        hue_order=["Share of advertisers", "Share of spend"],
        palette=[SPEND, TEAL],
        errorbar=None,
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("Share of the observed weekly file")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{value * 100:.0f}%"))
    ax.set_ylim(0, max(0.05, float(long["share"].max()) * 1.28))
    ax.legend(title="", loc="upper right")
    label_sets = [
        [rate_pct(int(row.advertisers), advertiser_n) for row in frame.itertuples()],
        [rate_pct(int(row.spend_usd), spend_total) for row in frame.itertuples()],
    ]
    for container, labels in zip(ax.containers, label_sets):
        ax.bar_label(container, labels=labels, fontsize=7.5, padding=2, color=INK)
    positive = int(report["concentration"]["n_advertisers"])
    ax.set_title(
        f"{positive:,} advertisers report positive spend. "
        f"The rest report $0 and still have ads in the file.",
        loc="left",
        color=SLATE,
        pad=10,
    )
    fig.suptitle(
        "A few large advertisers, and many small ones",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_states(report: dict) -> plt.Figure:
    frame = report["states"].head(15).iloc[::-1]
    labels = [name.title() for name in frame["location_name"]]
    values = frame["spend_usd"].map(millions).to_numpy()
    total = int(report["coverage"]["location_spend_weekly"])
    fig, ax = plt.subplots(figsize=(11.2, 6.8), constrained_layout=True)
    y = np.arange(len(labels))
    ax.barh(y, values, color=NAVY, height=0.72, zorder=2)
    span = float(values.max())
    for ypos, row in zip(y, frame.itertuples()):
        ax.text(
            millions(int(row.spend_usd)) + span * 0.015,
            ypos,
            f"{usd_compact(int(row.spend_usd))}   {rate_pct(int(row.spend_usd), total)}",
            va="center",
            ha="left",
            fontsize=8,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD millions, location report")
    ax.set_xlim(0, span * 1.32)
    leader = report["states"].iloc[0]
    ax.set_title(
        f"Location-report total {usd(total)}. "
        f"{leader.location_name.title()} is {rate_pct(int(leader.spend_usd), total)}.",
        loc="left",
        color=SLATE,
        pad=10,
    )
    fig.suptitle(
        "Spend by state and territory",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def plot_per_capita(report: dict) -> plt.Figure:
    frame = report["per_capita"].head(15).iloc[::-1]
    labels = [row.census_name for row in frame.itertuples()]
    values = frame["per_capita"].to_numpy()
    fig, ax = plt.subplots(figsize=(11.2, 6.8), constrained_layout=True)
    y = np.arange(len(labels))
    ax.barh(y, values, color=TEAL, height=0.72, zorder=2)
    span = float(values.max())
    for ypos, row in zip(y, frame.itertuples()):
        ax.text(
            row.per_capita + span * 0.02,
            ypos,
            per_person(int(row.spend_usd), int(row.population_2025)),
            va="center",
            ha="left",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD per resident, 1 July 2025 Census population")
    ax.set_xlim(0, span * 1.22)
    leader = report["per_capita"].iloc[0]
    ax.set_title(
        f"{leader.census_name} leads at {per_person(int(leader.spend_usd), int(leader.population_2025))} per resident. "
        "Total-spend rank is a different list.",
        loc="left",
        color=SLATE,
        pad=10,
    )
    fig.suptitle(
        "Spend per resident",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def _rings(geometry: dict):
    kind = geometry["type"]
    coords = geometry["coordinates"]
    if kind == "Polygon":
        yield coords[0]
    elif kind == "MultiPolygon":
        for polygon in coords:
            yield polygon[0]
    else:
        raise ValueError(kind)


def _draw(ax, features, values, norm, cmap) -> None:
    for feature in features:
        postal = feature["properties"]["stusps"]
        color = MUTED if postal not in values or pd.isna(values[postal]) else cmap(norm(values[postal]))
        for ring in _rings(feature["geometry"]):
            ax.add_patch(Polygon(ring, closed=True, facecolor=color, edgecolor="white", linewidth=0.4, zorder=2))
    ax.set_axis_off()
    ax.grid(False)


def plot_choropleth(report: dict) -> plt.Figure:
    payload = json.loads(Path(GEOJSON_PATH).read_text())
    features = payload["features"]
    states = report["per_capita"].copy()
    values = {row.postal: float(row.per_capita) for row in states.itertuples() if row.postal}
    ranked = states.sort_values("per_capita", ascending=False)
    top = ranked.iloc[0]
    second = ranked.iloc[1]
    cap = float(top.per_capita) > 1.4 * float(second.per_capita)
    vmax = float(second.per_capita) if cap else float(top.per_capita)
    vmin = float(ranked["per_capita"].min())
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = LinearSegmentedColormap.from_list("spend", ["#F4EFE4", "#8FCBBE", TEAL, "#0E3D36"])

    by_code = {feature["properties"]["stusps"]: feature for feature in features}
    lower = [feature for feature in features if feature["properties"]["stusps"] not in {"AK", "HI", "PR"}]
    fig = plt.figure(figsize=(12.6, 8.0))
    main = fig.add_axes([0.02, 0.14, 0.78, 0.70])
    alaska = fig.add_axes([0.05, 0.08, 0.20, 0.20])
    hawaii = fig.add_axes([0.28, 0.08, 0.14, 0.16])
    _draw(main, lower, values, norm, cmap)
    main.set_xlim(-128, -66)
    main.set_ylim(23.2, 50.2)
    main.set_aspect(1 / math.cos(math.radians(38)))
    _draw(alaska, [by_code["AK"]], values, norm, cmap)
    alaska.autoscale()
    alaska.set_aspect(1 / math.cos(math.radians(64)))
    alaska.set_title("Alaska", loc="left", fontsize=8, color=SLATE)
    _draw(hawaii, [by_code["HI"]], values, norm, cmap)
    hawaii.autoscale()
    hawaii.set_aspect(1 / math.cos(math.radians(20)))
    hawaii.set_title("Hawaii", loc="left", fontsize=8, color=SLATE)

    colorbar_ax = fig.add_axes([0.84, 0.28, 0.02, 0.42])
    fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=colorbar_ax)
    colorbar_ax.set_ylabel("USD per resident", color=SLATE)
    cap_note = ""
    if cap:
        cap_note = (
            f" {top.census_name} at {per_person(int(top.spend_usd), int(top.population_2025))} "
            f"is above the color scale, which stops at {per_person(int(second.spend_usd), int(second.population_2025))}."
        )
    fig.suptitle(
        "Spend per resident",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.02,
        y=0.98,
        ha="left",
    )
    note = "Color is dollars per resident, not total spend. Puerto Rico is outside this frame."
    if cap:
        note += (
            f"\n{top.census_name} is {per_person(int(top.spend_usd), int(top.population_2025))}"
            f" per resident, above this scale. The scale stops at {second.census_name},"
            f" {per_person(int(second.spend_usd), int(second.population_2025))}."
        )
    fig.text(0.02, 0.93, note, ha="left", va="top", fontsize=9, color=SLATE, linespacing=1.4)
    return fig


def plot_new_vs_lifelong(report: dict) -> plt.Figure:
    fresh = report["new_pages"].head(8).iloc[::-1]
    veterans = report["lifelong_top"].head(8).iloc[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 6.6), constrained_layout=True)

    ax = axes[0]
    labels = [advertiser_label(row.page_name, row.disclaimer, 36) for row in fresh.itertuples()]
    values = fresh["post_snapshot_spend_usd"].map(millions).to_numpy()
    y = np.arange(len(labels))
    ax.barh(y, values, color=TEAL, height=0.7, zorder=2)
    span = float(values.max()) if len(values) else 1
    for ypos, row in zip(y, fresh.itertuples()):
        ax.text(
            millions(int(row.post_snapshot_spend_usd)) + span * 0.02,
            ypos,
            usd_compact(int(row.post_snapshot_spend_usd)),
            va="center",
            ha="left",
            fontsize=8,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD millions after 27 Oct 2025")
    ax.set_xlim(0, span * 1.28)
    post_total = int(report["coverage"]["post_snapshot_spend"])
    fresh_spend = int(report["new_page_spend"])
    ax.set_title(
        f"Pages with no positive lifelong spend: {usd(fresh_spend)} "
        f"({rate_pct(fresh_spend, post_total)} of post-snapshot spend).",
        loc="left",
        color=SLATE,
    )

    ax = axes[1]
    labels = [
        f"{advertiser_label(row.page_name, row.disclaimer, 28)}  ·  {usd_compact(int(row.lifelong_spend_usd))} lifelong"
        for row in veterans.itertuples()
    ]
    values = veterans["post_snapshot_spend_usd"].map(millions).to_numpy()
    y = np.arange(len(labels))
    ax.barh(y, values, color=NAVY, height=0.7, zorder=2)
    span = max(float(values.max()) if len(values) else 1, 0.01)
    for ypos, row in zip(y, veterans.itertuples()):
        recent = int(row.post_snapshot_spend_usd)
        ax.text(
            millions(recent) + span * 0.03,
            ypos,
            usd_compact(recent) if recent else "$0",
            va="center",
            ha="left",
            fontsize=8,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("USD millions after 27 Oct 2025, same disclaimer")
    ax.set_xlim(0, span * 1.28)
    ax.set_title(
        "Largest lifelong pairs. The bar is later spend under that same disclaimer.",
        loc="left",
        color=SLATE,
    )
    fig.suptitle(
        "New spenders and the historical leaders",
        fontsize=16,
        fontweight="bold",
        color=INK,
        x=0.0,
        ha="left",
    )
    return fig


def render_all(report: dict, image_dir: Path) -> list[Path]:
    _apply_style()
    image_dir.mkdir(parents=True, exist_ok=True)
    source = _source(report)
    figures = [
        ("weekly_spend.png", plot_weekly),
        ("top_advertisers.png", plot_top_advertisers),
        ("pareto.png", plot_pareto),
        ("categories.png", plot_categories),
        ("advertiser_size.png", plot_size),
        ("state_spend.png", plot_states),
        ("state_per_capita.png", plot_per_capita),
        ("state_choropleth.png", plot_choropleth),
        ("new_vs_lifelong.png", plot_new_vs_lifelong),
    ]
    paths = []
    for name, builder in figures:
        fig = builder(report)
        path = image_dir / name
        _finish(fig, path, source)
        paths.append(path)
    return paths
