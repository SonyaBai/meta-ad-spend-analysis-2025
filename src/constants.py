"""Dates, geography, and sources shared by the loader, metrics, and charts.

The weekly file is a set of Monday–Sunday windows. Three of those weeks were
not in the Kaggle compilation. The lifelong file is a separate cumulative
snapshot and is not added to the weekly totals. The first observed week
(20–26 October 2025) overlaps that snapshot through 25 October.
"""

from __future__ import annotations

# First week that sits entirely after the lifelong snapshot date.
POST_SNAPSHOT_START = "2025-10-27"
LIFELONG_END = "2025-10-25"
FIRST_WEEK_START = "2025-10-20"
LAST_WEEK_END = "2026-04-19"

# Monday–Sunday windows absent from the compilation.
MISSING_WEEKS: tuple[tuple[str, str], ...] = (
    ("2025-11-10", "2025-11-16"),
    ("2025-11-17", "2025-11-23"),
    ("2025-11-24", "2025-11-30"),
)

NO_DISCLAIMER = "these ads ran without a disclaimer"

# Meta's location report uses these names. Population is joined only where
# the Census vintage below has a July 1, 2025 resident-population figure.
# The other four geographies stay in the spend tables and drop out of per capita.
EXCLUDED_FROM_PER_CAPITA: frozenset[str] = frozenset(
    {
        "unknown",
        "american samoa",
        "guam",
        "northern mariana islands",
        "virgin islands (u.s.)",
    }
)

LOCATION_TO_CENSUS_NAME: dict[str, str] = {
    "washington, district of columbia": "District of Columbia",
}

# U.S. Census Bureau, Population Division.
# Annual estimates of the resident population for the United States, regions,
# states, the District of Columbia, and Puerto Rico: April 1, 2020 to July 1, 2025.
# File NST-EST2025-ALLDATA, column POPESTIMATE2025, SUMLEV 040.
# https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv
# Table page: https://www.census.gov/data/tables/time-series/demo/popest/2020s-state-total.html
CENSUS_POPULATION_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/"
    "NST-EST2025-ALLDATA.csv"
)
CENSUS_POPULATION_VINTAGE = "Vintage 2025, July 1, 2025 resident population"

# U.S. Census Bureau, 2024 Cartographic Boundary File, 1:20,000,000.
# https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_20m.zip
# data/external/us_states_20m.geojson keeps the coordinates and the name,
# postal abbreviation, and GEOID. Public domain.
CENSUS_CARTOGRAPHY_URL = (
    "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_20m.zip"
)

# Kaggle compilation used by this project.
KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/ktkehoe/meta-ad-library-weekly"
KAGGLE_DOWNLOAD_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/ktkehoe/meta-ad-library-weekly"
)
KAGGLE_DOWNLOAD_FALLBACK_URL = (
    "https://api.kaggle.com/v1/datasets/download/ktkehoe/meta-ad-library-weekly"
)
META_REPORT_URL = "https://www.facebook.com/ads/library/report/?country=US"

CATEGORY_LABELS: dict[str, str] = {
    "party": "Party",
    "candidate": "Candidate or officeholder",
    "government": "Government",
    "media": "Media",
    "advocacy": "Advocacy",
    "company": "Company",
    "other": "Unclassified",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "party",
    "candidate",
    "government",
    "advocacy",
    "company",
    "media",
    "other",
)

# Priority when the page name and the disclaimer disagree.
# Unclassified never outranks a matched label.
CATEGORY_PRIORITY: tuple[str, ...] = (
    "party",
    "candidate",
    "government",
    "media",
    "advocacy",
    "company",
    "other",
)

SIZE_BINS: tuple[tuple[str, int, int | None], ...] = (
    ("$1–$99", 1, 100),
    ("$100–$999", 100, 1_000),
    ("$1,000–$9,999", 1_000, 10_000),
    ("$10,000–$99,999", 10_000, 100_000),
    ("$100,000–$999,999", 100_000, 1_000_000),
    ("$1,000,000 or more", 1_000_000, None),
)
