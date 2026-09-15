# Archived road-section traffic method

Removed from the thesis presentation in the four-issue review. Analysis code and
all numerical CSV outputs remain unchanged. No result from this model remains
cited in the thesis. This preserves the former mathematical description.

```latex
\subsection{Supporting Road-Section Traffic Comparison}

Annual road-section data provide a supporting exposure analysis for accidents
that can be linked by road section, year, official traffic period, and wind
interval. For road-section--year--traffic-period stratum \(k\) and wind
interval \(j\), estimated vehicle-kilometres are

\[
V_{kj}=q_k L_k D_k p_{kj},
\]

where \(q_k\) is SDU, VDU, or derived VHDU vehicles per day, \(L_k\) is section
length, \(D_k\) is the number of calendar days, and \(p_{kj}\) is the local
share of quality-controlled 10-minute observations in wind interval \(j\).
This construction accounts for road length and differences in published
seasonal traffic, but assumes that traffic within each traffic period is
distributed across wind intervals in proportion to time. It does not observe
traffic at the accident minute.

The station nearest the road-section midpoint with qualifying data supplies
\(p_{kj}\). Accidents in this analysis are matched to that road-section station,
rather than to the accident-nearest station used in the weather-only analysis, and are retained only
when the station is within 20 km and has a valid observation within five
minutes of the accident time.

A conditional Poisson model is fitted as a supporting inferential analysis.
Each road section, year, and traffic period has its own intercept:

\[
\log E(A_{kj}) = \alpha_k + \beta_j + \log V_{kj},
\]

where \(A_{kj}\) is the accident count and \(\log V_{kj}\) is the offset. The
exponentiated coefficient \(\exp(\beta_j)\) is the estimated rate ratio relative
to 0--5 m/s within road-section--year--traffic-period strata. Strata with no
accidents contain no within-stratum information after conditioning and do not
contribute to this model. The model is fitted separately for all injury
accidents and for serious or fatal accidents. A seasonal extension uses
0--10, 10--15, and at least 15 m/s because the finer upper-wind cells are
sparse.

```
