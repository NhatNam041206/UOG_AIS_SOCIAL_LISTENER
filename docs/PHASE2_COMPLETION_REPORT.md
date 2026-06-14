# Phase 2 Completion Report: Twitter Preprocessing and Filtering

Completion date: 2026-06-14

## Phase Decision

Phase 2 is **complete and approved for closure**.

The selected high-volume activity threshold is:

```text
9 tweets per active day
```

This threshold is retained because it reduces the influence of extremely active
users while preserving more potentially legitimate political discussion than the
stricter threshold of 6.

## Purpose

Phase 2 converts the combined Phase 1 Twitter records into a cleaner dataset for
sentiment analysis. It removes unusually high-volume user activity, exact duplicate
tweet text, and invalid or empty text while preserving sentiment-relevant signals.

The phase does not claim to identify confirmed bots. Its first filter identifies
high-volume activity that could disproportionately influence later analysis.

## Processing Sequence

```text
Phase 1 Twitter records
    |
    v
High-volume user filtering
    |
    v
Exact duplicate filtering
    |
    v
Text cleaning and validation
    |
    v
Cleaned Phase 2 dataset
```

## Method 1: High-Volume User Filtering

### Simple Explanation

The pipeline calculates how frequently each user posts during the days when that
user is active. Users posting at an unusually high average rate are removed,
including all tweets associated with those users.

This limits the influence of unusually active accounts without claiming that every
removed account is a bot.

### Activity Metric

For each user:

```text
tweets per active day = total tweets from user / number of days user posted
```

An active day is any day when the user posted at least one tweet.

Example:

| User | Total tweets | Active days | Tweets per active day |
| --- | ---: | ---: | ---: |
| User A | 10 | 10 | 1 |
| User B | 100 | 10 | 10 |
| User C | 50 | 1 | 50 |

User C has the highest activity rate because all 50 tweets were posted during one
active day.

### Threshold Selection

The threshold was derived from the actual user-activity distribution instead of
using an arbitrary fixed value.

| Candidate method | Threshold |
| --- | ---: |
| P95 | 3.000 |
| P97.5 | 4.000 |
| P99 | 6.000 |
| P99.5 | 9.000 |
| IQR upper fence | 2.667 |
| Extreme IQR fence | 3.667 |
| Log-z threshold | 4.550 |
| MAD threshold | 1.000 |

The selected P99.5 threshold removes users averaging **more than 9 tweets per active
day**.

### Filtering Result

| Measure | Result |
| --- | ---: |
| Users examined | 483,175 |
| Users removed | 2,227 |
| Users removed percentage | 0.46% |
| Tweets removed | 222,366 |
| Tweets removed percentage | 12.72% |
| Tweets retained | 1,525,176 |

The result shows that a small group of highly active users produced a substantial
share of the tweets.

### Limitation

High posting frequency does not prove automated behavior. Removed users could
include real people, journalists, campaign accounts, or news organizations.
Therefore, this method is documented as **high-volume user filtering**, not
confirmed bot removal.

## Method 2: Exact Duplicate Filtering

### Simple Explanation

The pipeline identifies tweets with exactly identical original text. It retains the
first occurrence and removes later occurrences.

Example:

```text
Tweet 1: "Vote today!"   -> retained
Tweet 2: "Vote today!"   -> removed
Tweet 3: "Vote today!!"  -> retained
```

Tweet 3 is retained because its punctuation differs.

### Filtering Result

| Measure | Result |
| --- | ---: |
| Tweets entering stage | 1,525,176 |
| Exact duplicates removed | 193,831 |
| Tweets retained | 1,331,345 |

### Important Detail

Duplicate detection occurs before text cleaning. Tweets that differ only by URL are
not treated as exact duplicates:

```text
"Vote today! https://example.com/a"
"Vote today! https://example.com/b"
```

This conservative behavior avoids deleting records that only become similar after
normalization.

## Method 3: Text Cleaning and Validation

### Simple Explanation

The final stage removes technical noise while preserving text features that may
affect sentiment.

The cleaner removes:

- URLs;
- HTML tags;
- repeated unnecessary whitespace.

It also converts HTML-encoded characters back to normal characters.

Example:

```text
Before: "<b>Great speech!</b> Watch here: https://example.com"
After:  "Great speech! Watch here:"
```

The cleaner intentionally preserves:

- capitalization;
- punctuation;
- emoji.

These signals are preserved because they can affect sentiment intensity:

```text
"good"
"GOOD!!!"
"good 😊"
```

A tweet is removed after cleaning if it becomes empty or contains invalid Unicode
characters.

### Filtering Result

| Measure | Result |
| --- | ---: |
| Tweets entering stage | 1,331,345 |
| Invalid or empty tweets removed | 28 |
| Tweets retained | 1,331,317 |

## Available but Unused Rules

### Account-Age Filtering

The implementation can reject accounts created less than 30 days before the
election. The source dataset does not contain `user_created_at`, so the rule was not
applied and no account age was inferred.

### External Bot-Score Filtering

The implementation can reject records whose `bot_score` exceeds a configured
threshold. The source dataset does not contain bot scores, and no external bot
detection model has been integrated, so this rule was not applied.

## Overall Results

| Stage | Records removed | Records retained |
| --- | ---: | ---: |
| Starting dataset | - | 1,747,542 |
| High-volume user filter | 222,366 | 1,525,176 |
| Exact duplicate filter | 193,831 | 1,331,345 |
| Text cleaning and validation | 28 | 1,331,317 |

Final retention:

```text
1,331,317 / 1,747,542 = 76.18%
```

## Cleaned Dataset Verification

The cleaned dataset has been created successfully:

```text
data/02_interim/twitter_cleaned.parquet
```

Verification performed on 2026-06-14:

| Check | Result |
| --- | --- |
| File exists | Passed |
| Parquet metadata readable | Passed |
| Rows readable from metadata | 1,331,317 |
| Row count matches Phase 2 manifest | Passed |
| File size | 183,667,730 bytes |
| Parquet row groups | 2 |

Verified schema:

| Column | Type |
| --- | --- |
| `id` | string |
| `date` | timestamp with UTC timezone |
| `tweet` | string |
| `user_id` | string |
| `user_loc` | string |
| `retweets` | double |
| `replies` | null because unavailable in source |
| `candidate` | string |
| `source_file` | string |

## Phase Closure

Phase 2 is closed because:

- the filtering and cleaning methods are implemented;
- the complete Phase 1 Twitter dataset was processed;
- the cleaned Parquet dataset exists and is readable;
- its row count matches the Phase 2 manifest;
- Phase 2 reports, results, and graphs exist;
- Phase 2 automated tests pass;
- the selected threshold of `9.0` tweets per active day has been approved.

The cleaned dataset is ready to become the primary Twitter input for Phase 3
sentiment analysis.

