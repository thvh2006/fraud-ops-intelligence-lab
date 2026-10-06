# Delayed-label and monitoring backtest

## Feedback is selected, not representative

The simulated top-100 investigator stream has an observed fraud rate of **33.85%**, versus **2.33%** outside the reviewed queue—a **14.5×** rate ratio. Fast feedback therefore cannot be treated as a random training sample.

## Point-in-time recalibration

At the start of each OOT elapsed week, a Platt calibrator is refit using only labels available by that snapshot: immediate labels for previously reviewed alerts plus delayed labels for the remaining population. No current/future-week label enters the fit.

- **7-day delay:** rolling calibration improves mean Brier by **0.00007** versus the fixed calibrator; mean rolling ECE **0.005**; mean historical label coverage **97.0%**.
- **14-day delay:** rolling calibration improves mean Brier by **0.00007** versus the fixed calibrator; mean rolling ECE **0.005**; mean historical label coverage **93.4%**.
- **30-day delay:** rolling calibration improves mean Brier by **0.00008** versus the fixed calibrator; mean rolling ECE **0.005**; mean historical label coverage **85.3%**.

Rolling recalibration is not automatically promoted. Its value depends on delay and selected-feedback bias; the fixed development/calibration model remains the fallback whenever rolling Brier deteriorates.

The Brier differences across delay scenarios are only **0.00007–0.00008**. No delay setting is declared a winner from this short six-week OOT horizon.

## Drift monitoring

- Locked OOT covers **6 elapsed weeks**.
- Maximum weekly score PSI versus development is **0.063**.
- The rules emit **0 red alerts** across score PSI, amount PSI, and ECE checks.
- Thresholds are portfolio operating assumptions: PSI amber/red at 0.10/0.20 and ECE amber/red at 0.02/0.04. They require production calibration before operational use.

## Governance decision

Monitor score distribution, amount distribution, calibration, identity coverage, and alert precision weekly. Keep fast investigator feedback and delayed population outcomes as separate labelled streams; record label provenance and availability time. Trigger diagnosis before retraining because drift may reflect calibration, population, coverage, or policy selection rather than model ranking failure.
