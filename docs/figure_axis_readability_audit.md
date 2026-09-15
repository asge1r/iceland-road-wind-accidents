# Figure axis readability audit

## Scope and measurement

The user's direct steering limits y-axis changes to Figures **4.2–4.4**;
the other restored scales are retained. All thesis bar figures were audited.
Values below were captured from actual Matplotlib bar containers and axes,
with saving intercepted so unchanged assets were not regenerated. For stacks,
maximum is bar bottom + height; for grouped bars it is the tallest individual
bar. Horizontal composition bars use the value x-axis instead of the category
y-axis. Maps and the coverage line panel are not bar plots.

Flags: <.60 LOW; >.95 HIGH. Target normally .75–.90. A flag is a review signal,
not permission to replace recovered supervisor limits or expand the user's
explicit scale-change scope. All bar-value axes start at zero. The coverage
line uses its existing 70–101% range and is not a zero-based bar comparison.

## Every thesis bar panel

| Figure | Panel | Maximum displayed value | Value-axis maximum | Ratio | Flag / disposition |
|---|---|---:|---:|---:|---|
| 4.2 | All year | 2.22386 | 2.6 | 0.855 | — |
| 4.2 | Winter | 1.75727 | 2.2 | 0.799 | — |
| 4.2 | Spring | 7.35072 | 8.6 | 0.855 | — |
| 4.2 | Summer | 2.80924 | 3.4 | 0.826 | — |
| 4.2 | Autumn | 3.51945 | 4.2 | 0.838 | — |
| 4.3 | All year | 3.55912 | 4.2 | 0.847 | — |
| 4.3 | Winter | 2.52811 | 3 | 0.843 | — |
| 4.3 | Spring | 12.1674 | 16 | 0.760 | — |
| 4.3 | Summer | 7.77853 | 9.2 | 0.845 | — |
| 4.3 | Autumn | 5.03677 | 6 | 0.839 | — |
| 4.4 | All year | 1.71475 | 2 | 0.857 | — |
| 4.4 | Winter | 1.28385 | 1.6 | 0.802 | — |
| 4.4 | Spring | 2.18245 | 2.6 | 0.839 | — |
| 4.4 | Summer | 1.69541 | 2 | 0.848 | — |
| 4.4 | Autumn | 1.78976 | 2.2 | 0.814 | — |
| 4.1 | Rural injury accidents by year | 407 | 427.35 | 0.952 | HIGH; existing non-Q1 scale, labels visually checked |
| 4.5 | Mean wind / All year | 101.152 | 120 | 0.843 | — |
| 4.5 | Wind gust / All year | 101.426 | 120 | 0.845 | — |
| 4.5 | Temperature / All year | 101.529 | 120 | 0.846 | — |
| 4.8 | Mean wind / All year | 2.80401 | 5.269220068 | 0.532 | LOW; existing source-family scale retained |
| 4.8 | Wind gust / All year | 4.46544 | 5.269220068 | 0.847 | — |
| 4.6 | ≥20 m/s: 2.15 → 2.71 / All year | 2.71404 | 3.663956331 | 0.741 | — |
| 4.7 | ≥30 m/s: 3.34 → 4.20 / All year | 4.19516 | 5.663459266 | 0.741 | — |
| 3.2 | Accidents by hour | 538 | 564.9 | 0.952 | HIGH; existing non-Q1 scale, labels visually checked |
| 3.2 | Accidents by season | 2387 | 2506.35 | 0.952 | HIGH; existing non-Q1 scale, labels visually checked |
| 3.2 | Accidents by estimated daylight | 4263 | 4476.15 | 0.952 | HIGH; existing non-Q1 scale, labels visually checked |
| 3.2 | Accidents by matched temperature | 1217 | 1277.85 | 0.952 | HIGH; existing non-Q1 scale, labels visually checked |
| A.1 | Vehicles involved in rural injury accidents | 4659 | 5497.62 | 0.847 | — |
| A.2 | Accident types by injury severity | 69.5327 | 73.00930609 | 0.952 | HIGH; existing source-family scale retained |
| 4.12 | All year | 0.666516 | 1.3 | 0.513 | LOW; recovered source scale retained |
| 4.12 | All year | 0.866423 | 1.3 | 0.666 | — |
| 4.13 | Winter | 0.382112 | 0.8 | 0.478 | LOW; recovered source scale retained |
| 4.13 | Spring | 0.680933 | 0.8 | 0.851 | — |
| 4.13 | Summer | 0.348229 | 0.8 | 0.435 | LOW; recovered source scale retained |
| 4.13 | Autumn | 0.217097 | 0.8 | 0.271 | LOW; recovered source scale retained |
| 4.14 | Winter | 0.328477 | 0.5 | 0.657 | — |
| 4.14 | Spring | 0.36218 | 0.5 | 0.724 | — |
| 4.14 | Summer | 0.297976 | 0.5 | 0.596 | LOW; recovered source scale retained |
| 4.14 | Autumn | 0.224394 | 0.5 | 0.449 | LOW; recovered source scale retained |
| 4.15 | All year | 0.925786 | 1.3 | 0.712 | — |
| 4.15 | All year | 1.17834 | 1.3 | 0.906 | — |
| 4.15 | All year | 0.250538 | 0.3 | 0.835 | — |
| 4.16 | Winter | 0.465698 | 0.8 | 0.582 | LOW; recovered source scale retained |
| 4.16 | Spring | 0.738997 | 0.8 | 0.924 | — |
| 4.16 | Summer | 0.385197 | 0.8 | 0.481 | LOW; recovered source scale retained |
| 4.16 | Autumn | 0.257202 | 0.8 | 0.322 | LOW; recovered source scale retained |
| 4.17 | Winter | 0.386687 | 0.5 | 0.773 | — |
| 4.17 | Spring | 0.387496 | 0.5 | 0.775 | — |
| 4.17 | Summer | 0.326738 | 0.5 | 0.653 | — |
| 4.17 | Autumn | 0.245581 | 0.5 | 0.491 | LOW; recovered source scale retained |
| 4.18 | Winter | 0.254888 | 0.6 | 0.425 | LOW; recovered source scale retained |
| 4.18 | Spring | 0.498729 | 0.6 | 0.831 | — |
| 4.18 | Summer | 0.345146 | 0.6 | 0.575 | LOW; recovered source scale retained |
| 4.18 | Autumn | 0.261917 | 0.6 | 0.437 | LOW; recovered source scale retained |
| 4.11 | Mean wind / All year | 2.79987 | 6 | 0.467 | LOW; existing source-family scale retained |
| 4.11 | Wind gust / All year | 5.25052 | 6 | 0.875 | — |
| 4.11 | Temperature / All year | 1.73368 | 2 | 0.867 | — |
| 4.9 | Mean wind / All year | 2.23798 | 4.052499952 | 0.552 | LOW; existing source-family scale retained |
| 4.9 | Wind gust / All year | 3.43432 | 4.052499952 | 0.847 | — |
| 4.9 | Temperature / All year | 1.71594 | 4.052499952 | 0.423 | LOW; existing source-family scale retained |
| 4.10 | Mean wind / All year | 2.22257 | 4.943640148 | 0.450 | LOW; existing source-family scale retained |
| 4.10 | Wind gust / All year | 4.18953 | 4.943640148 | 0.847 | — |
| 4.10 | Temperature / All year | 1.75275 | 4.943640148 | 0.355 | LOW; existing source-family scale retained |

## Changed baseline panels: old → new

Earlier scripts (`a0d4468`, `ee74db4`, `c90f735`) provide no recovered manual
panel-specific baseline limits. They use automatic headroom; later five-panel
figures share a maximum. The current direct instruction allows panel-specific
scales for readability. Each new maximum rounds max(1, maximum O/E)/.86 upward
to a clean increment; this keeps O/E=1 visible and provides count-label room.
Every panel now displays its own y ticks; axes remain zero-based.

| Figure | Panel | Old shared maximum | New maximum | Tallest-bar fraction |
|---|---|---:|---:|---:|
| 4.2 | All year | 8.673847 | 2.6 | 0.855 |
| 4.2 | Winter | 8.673847 | 2.2 | 0.799 |
| 4.2 | Spring | 8.673847 | 8.6 | 0.855 |
| 4.2 | Summer | 8.673847 | 3.4 | 0.826 |
| 4.2 | Autumn | 8.673847 | 4.2 | 0.838 |
| 4.3 | All year | 14.357495 | 4.2 | 0.847 |
| 4.3 | Winter | 14.357495 | 3 | 0.843 |
| 4.3 | Spring | 14.357495 | 16 | 0.760 |
| 4.3 | Summer | 14.357495 | 9.2 | 0.845 |
| 4.3 | Autumn | 14.357495 | 6 | 0.839 |
| 4.4 | All year | 2.575295 | 2 | 0.857 |
| 4.4 | Winter | 2.575295 | 1.6 | 0.802 |
| 4.4 | Spring | 2.575295 | 2.6 | 0.839 |
| 4.4 | Summer | 2.575295 | 2 | 0.848 |
| 4.4 | Autumn | 2.575295 | 2.2 | 0.814 |

No rate-scale setting was changed in this pass. Some rate panels remain below
.60 because the original manually chosen annual/seasonal scale is preserved,
as requested. No global or cross-parameter scale was introduced. The source
rate limits and every final O/E limit are recorded above.
