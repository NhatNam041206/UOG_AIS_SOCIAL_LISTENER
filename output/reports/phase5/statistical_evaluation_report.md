# Phase 5 Statistical Evaluation Report

Run ID: `phase5_statistical_evaluation_20260731`

## Hypothesis 1: Interrupted Time Series Analysis (ITSA)
- Events Evaluated: 4
### Event: 2020 presidential election day
- Immediate Shock (beta_2): `0.0412` (p-value: `0.0000`)
- Slope Change (beta_3): `-0.0022` (p-value: `0.0000`)
- Model R^2: `0.6298`
### Event: AP projects Joe Biden as president-elect
- Immediate Shock (beta_2): `0.1255` (p-value: `0.0000`)
- Slope Change (beta_3): `-0.0059` (p-value: `0.0000`)
- Model R^2: `0.7065`
### Event: Dueling presidential town halls
- Immediate Shock (beta_2): `0.0346` (p-value: `0.0028`)
- Slope Change (beta_3): `-0.0005` (p-value: `0.3966`)
- Model R^2: `0.2471`
### Event: Final presidential debate
- Immediate Shock (beta_2): `0.0102` (p-value: `0.1658`)
- Slope Change (beta_3): `-0.0003` (p-value: `0.2368`)
- Model R^2: `0.2150`

## Hypothesis 2: Stratified OLS Spatial Regression

| Subgroup | Sample Size (N) | Sentiment Slope (beta_1) | p-value | R^2 | Adj R^2 |
|---|---:|---:|---:|---:|---:|
| National | 51 | 83.0380 | 0.0525 | 0.8129 | 0.7874 |
| Battleground States | 10 | -46.7254 | 0.0033 | 0.9735 | 0.9204 |
| Safe States | 41 | 66.1420 | 0.1816 | 0.8380 | 0.8094 |