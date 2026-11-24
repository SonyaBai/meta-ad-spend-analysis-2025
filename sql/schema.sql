-- US Meta Ad Library weekly compilation.
-- Source: Kaggle "Meta Ad Library Weekly" (ktkehoe), Apache 2.0.
-- https://www.kaggle.com/datasets/ktkehoe/meta-ad-library-weekly
-- Upstream reports: https://www.facebook.com/ads/library/report/?country=US
--
-- Scope: ads about social issues, elections, or politics, United States, USD.
-- amount_spent_usd is Meta's reported whole dollars. This compilation has no
-- cents. num_ads is the count of ads in the library for that row's window.
--
-- window = 'last_7_days' is one Monday–Sunday report. Summing those weeks
-- totals the observed weeks. It does not fill the three missing November
-- weeks, and it does not count distinct ads: an ad that runs for four weeks
-- is in four numerators.
-- window = 'lifelong' is a separate cumulative snapshot through 2025-10-25.
-- date_start is blank on those rows. Do not add lifelong dollars to weekly
-- dollars. The week of 2025-10-20 overlaps the snapshot through 2025-10-25.
-- The region file has no lifelong rows.

DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS advertisers;

CREATE TABLE advertisers (
    id TEXT PRIMARY KEY,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    window TEXT NOT NULL CHECK (window IN ('last_7_days', 'lifelong')),
    page_id TEXT NOT NULL,
    page_name TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    amount_spent_usd INTEGER NOT NULL CHECK (amount_spent_usd >= 0),
    num_ads INTEGER NOT NULL CHECK (num_ads >= 0),
    CHECK (
        (
            window = 'lifelong'
            AND date_start = ''
            AND date_end = '2025-10-25'
        )
        OR (
            window = 'last_7_days'
            AND date_start GLOB '????-??-??'
            AND date_end GLOB '????-??-??'
            AND date_start < date_end
        )
    )
);

CREATE TABLE locations (
    id TEXT PRIMARY KEY,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    window TEXT NOT NULL CHECK (window IN ('last_7_days', 'lifelong')),
    location_name TEXT NOT NULL,
    amount_spent_usd INTEGER NOT NULL CHECK (amount_spent_usd >= 0),
    CHECK (
        (
            window = 'lifelong'
            AND date_start = ''
            AND date_end = '2025-10-25'
        )
        OR (
            window = 'last_7_days'
            AND date_start GLOB '????-??-??'
            AND date_end GLOB '????-??-??'
            AND date_start < date_end
        )
    )
);

CREATE TABLE regions (
    id TEXT PRIMARY KEY,
    date_start TEXT NOT NULL,
    date_end TEXT NOT NULL,
    window TEXT NOT NULL CHECK (window = 'last_7_days'),
    region TEXT NOT NULL,
    page_id TEXT NOT NULL,
    page_name TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    amount_spent_usd INTEGER NOT NULL CHECK (amount_spent_usd >= 0),
    CHECK (
        date_start GLOB '????-??-??'
        AND date_end GLOB '????-??-??'
        AND date_start < date_end
    )
);

-- Indexes are created in sql/load_sqlite.py after the insert. Building them
-- on the empty tables and updating them row by row is much slower on the
-- region file.

-- Rebuilt by src/metrics.py after names are classified. sql/05_categories.sql
-- reads this table. It is not part of the raw load.
DROP TABLE IF EXISTS classified_weekly;
CREATE TABLE classified_weekly (
    page_id TEXT NOT NULL,
    page_name TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    spend_usd INTEGER NOT NULL,
    num_ads INTEGER NOT NULL,
    weeks_observed INTEGER NOT NULL,
    post_snapshot_spend_usd INTEGER NOT NULL,
    post_snapshot_num_ads INTEGER NOT NULL,
    lifelong_spend_usd INTEGER NOT NULL,
    lifelong_num_ads INTEGER NOT NULL,
    page_lifelong_spend_usd INTEGER NOT NULL,
    category TEXT NOT NULL CHECK (
        category IN (
            'party', 'candidate', 'government', 'media', 'advocacy', 'company', 'other'
        )
    ),
    PRIMARY KEY (page_id, disclaimer)
);
