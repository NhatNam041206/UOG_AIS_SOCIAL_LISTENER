# Phase 4 Aggregation Report

Run ID: `phase4_matrix_aggregation_20260731`

## Aggregation Summary
- Temporal Hourly Slices: 599
- Temporal Daily Slices: 25
- Event Window Hourly Slices: 345
- State Spatial Aggregate Rows: 51 (50 States + DC)
- Classified Battleground States (10): AZ, FL, GA, MI, MN, NC, NH, NV, PA, WI
- Classified Safe States (41): AK, AL, AR, CA, CO, CT, DC, DE, HI, IA, ID, IL, IN, KS, KY, LA, MA, MD, ME, MO, MS, MT, ND, NE, NJ, NM, NY, OH, OK, OR, RI, SC, SD, TN, TX, UT, VA, VT, WA, WV, WY

## State Coverage Limitation
- Tweets with valid US state code: 264,095 / 1,280,784 (20.6%)
- The spatial sentiment matrix (Xi) is computed from this subset only.
- **Limitation**: ~79.5% of tweets have missing or non-US state codes. State-level H2 results
  reflect users who chose to provide geocoded location, which may not represent all states equally.
  This selection bias should be acknowledged when interpreting H2 OLS coefficients.