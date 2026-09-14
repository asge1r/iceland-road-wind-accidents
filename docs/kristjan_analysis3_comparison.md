# Analysis 3: which denominator adds traffic to O/E?

> **Status:** This comparison records the 13 September review of the former
> 613-accident coverage-threshold design. The later same-day rural VKT
> implementation uses 694 accidents, rural section lengths, time-specific
> station selection, and excludes unobserved minutes; its results supersede
> the 613-case production description.

**For discussion with Kristján — methodological comparison, not a proposed thesis change.**

All three designs estimate the same type of descriptive quantity: observed accidents in wind bin \(j\), divided by accidents expected if each stratum's accident total were distributed proportionally to its chosen exposure. With \(A_{kj}\) observed accidents, \(A_k=\sum_jA_{kj}\), and exposure \(X_{kj}\):

\[
e_{kj}=\frac{X_{kj}}{\sum_hX_{kh}},\qquad
E_{kj}=A_ke_{kj},\qquad
\mathrm{OE}_j=\frac{\sum_kA_{kj}}{\sum_kE_{kj}}.
\]

Thus O/E compares with an **exposure-proportional null within the specified strata**, not with the calm bin or a causal counterfactual. All designs use bins 0–5, 5–10, 10–15, 15–20 and ≥20 m/s.

| | 1. Primary weather O/E | 2. Annual estimated-VKT O/E | 3. Strict same-day traffic-weighted O/E |
|---|---|---|---|
| **Stratum and exact comparison** | Station × season: accidents relative to local weather-time composition. | Road section × year × traffic period: accidents relative to estimated period-VKT composition. | Section × year × season: accidents relative to accumulated same-day allocated VKT. |
| **Exposure \(X_{kj}\)** | Valid local weather observations \(n_{kj}\), used as a time proxy. | \(q_kL_kD_kp_{kj}\). | \(\sum_{d\in k}Q_dL_kp_{dj}\), over **all eligible days**, including accident-free days. |
| **What varies** | Weather frequency by wind bin and station/season. | Local period weather fractions vary by bin; daily traffic estimate, length and duration vary between strata. | Both measured daily traffic and same-day weather composition vary across days. |
| **What cancels** | Total observation scale within a stratum. | **All of \(q_kL_kD_k\)** within each stratum. | Constant section length; a common multiplier on all daily counts. **Relative daily traffic variation remains.** |
| **Main assumption** | Weather-record shares adequately represent local weather time and the null distribution of accident opportunities. | Period-average traffic can be allocated using weather fractions, without observed wind-specific traffic. | Full daily traffic can be allocated using that day's weather fractions; allocated VKT represents relative accident opportunities within the season. |
| **All-injury sample** | **6,259**, 2007–2025. | **5,125**, 2007–2025; 4,135 accident-bearing strata. | **613**, 2019–2024; 530 accident-bearing strata. |
| **≥20 m/s: observed / expected / O/E** | **68 / 31.596 / 2.152** | **61 / 25.810 / 2.363** | **10 / 2.109 / 4.742** |
| **Does traffic magnitude affect O/E?** | No traffic input. | No, holding eligibility and weather fractions fixed; traffic availability still selects the sample. | **Yes:** daily traffic weights weather exposure across days. |
| **“O/E with traffic injected”?** | Baseline design. | Formally VKT-based, but no additional traffic-volume weighting survives. | **Yes**, with observed daily totals and estimated wind-bin allocation. |

**Why the cancellation differs.** Here \(q\) is VDU, SDU or derived VHDU vehicles/day, \(L\) is section length, \(D\) is period duration, and \(p\) is the local weather-bin fraction:

\[
e^{\mathrm{annual}}_{kj}
=\frac{q_kL_kD_kp_{kj}}{q_kL_kD_k\sum_hp_{kh}}
=p_{kj},\qquad
e^{\mathrm{strict}}_{kj}
=\frac{\sum_dQ_dL_kp_{dj}}{\sum_dQ_dL_k}
=\frac{\sum_dQ_dp_{dj}}{\sum_dQ_d}.
\]

Because \(Q_d\) varies across days, it cannot generally be factored out of the weighted sum. On the same strict sample and seasonal strata, equal-day weighting instead gives ≥20 O/E **3.150**, confirming that traffic weighting materially affects the estimate. Conditioning separately on each day would cancel \(Q_d\) again.

**Recommendation.** If Kristján means that traffic variation should actually influence the denominator, **design 3 is the closest methodological match**: it preserves the O/E structure while retaining daily traffic weighting. Choose it for that reason, not its larger estimate. Its smaller, more restricted sample and ten high-wind accidents limit precision and generalisability. Design 2 remains a useful broader-sample descriptive comparison, but its difference from primary O/E cannot be attributed to traffic magnitudes. Confirm that seasonal, rather than within-day, conditioning matches the intended question.

**Conditional Poisson: demote to supporting annual analysis.** The existing annual model estimates reference-relative RRs through \(\pi_{kj}(\beta)\propto X_{kj}\exp(\beta_j)\); O/E uses the null allocation \(\beta=0\). Keep it as inferential support for the **annual** comparison, not as uncertainty for the 613-case result: it uses another sample and its \(qLD\) also cancels. Direct inference for design 3 would require the same strict panel/strata and an appropriate dependence assessment. Do not omit useful annual evidence, but avoid presenting it as proof of daily traffic adjustment.

*Provenance and limits:* [verified review](../reports/reproduced/traffic_oe_concept_review_20260913/README.md). Annual results use the corrected annual model panel; strict results use the audited fresh 613-case panel. Samples differ, so these are not isolated traffic-adjustment contrasts. Full 24-hour traffic allocated using 07:00–24:00 weather, ≤5-minute cross-midnight matching, and record-weighted weather fractions remain modelling assumptions for discussion. No production or thesis changes.
