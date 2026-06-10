# Module: cleaning_heuristics_model

## Architectural Role

Model boundary for deterministic Phase 2 rules. Components have one responsibility:
`BotFilter` identifies bot-like activity, `DuplicateFilter` identifies exact duplicate
text, `TextCleaner` performs conservative normalization, and `CleaningPolicy` owns
configuration.

## Rules

- All records from a user are rejected when their empirically measured
  `tweets_per_active_day` exceeds the threshold injected by the activity audit. The
  cleaning policy has no fixed default activity threshold.
- An account created within 30 days of the November 3, 2020 election is rejected when
  the configured account-created field exists. Missing account-created values are not
  guessed.
- Exact non-null tweet text is deduplicated before normalization.
- HTML and URLs are removed. Capitalization, punctuation, and emoji are preserved.
- Empty text, Unicode replacement characters, and invalid surrogate code points are
  rejected.

Compatibility functions (`filter_bots`, `deduplicate_text`, `verify_syntax`, and
`verify_emoji_integrity`) remain available for record-oriented callers.
