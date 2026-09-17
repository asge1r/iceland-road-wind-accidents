# Wind, Temperature, and Rural Injury Accidents in Iceland

This MSc thesis studies rural injury accidents using three retained analyses:

1. Weather-frequency observed/expected (O/E), 2007–2025: occurrence relative to local station–season weather frequency.
2. Approximate traffic-corrected O/E, 2007–2025: the same sample, with expected counts reweighted using the 2019–2024 counter response.
3. Monthly-frequency VKT, 2019–2024: accidents per estimated vehicle-kilometre in a smaller counter-linked sample.

The joint wind–temperature heatmap is a descriptive extension of the first
analysis, not a formal interaction model. The analyses use different denominators
and do not establish causal effects or a national vehicle-specific risk.
Historical methods remain in some source modules for audit but are not retained
thesis analyses. Use the current entry point below, not the historical `src.analyze`.

## Reproduction and access

The repository provides code, selected numerical results, figures and document
sources. Original institutional register extracts, weather, traffic and geographic
inputs are not redistributed. A checkout can rebuild the documents from retained
figures and generated LaTeX, but cannot reproduce the numerical results from raw
data without the required institutional deliveries.

[Section 3.2 of the thesis](reports/thesis/content.tex) explains the workflow;
[docs/pipeline.md](docs/pipeline.md) gives the exact preparation order, input paths
and analysis commands. `requirements.txt` pins direct analysis dependencies;
`requirements-dev.txt` adds the test runner. Python 3.13 is the validated local
runtime. Document builds additionally require TeX Live with pdfLaTeX, XeLaTeX,
Beamer, latexmk and the packages declared by the document sources.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
# After obtaining and preparing the documented institutional inputs:
.venv/bin/python -m src.thesis_pipeline
.venv/bin/python -m src.validate
.venv/bin/python -m pytest tests -q
```

## Documents

- [Current thesis PDF](reports/thesis/Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf)
- [Thesis build instructions](reports/thesis/TEMPLATE.md)
- [Defense presentation source and build instructions](reports/presentation/README.md)

## Repository layout

- `src/`: preparation, matching, analysis, rendering and validation modules.
- `tests/`: calculation and document-consistency tests.
- `docs/`: pipeline documentation and review evidence.
- `reports/main/`: retained figures and numerical results.
- `reports/thesis/`: thesis source, generated fragments and final PDF.
- `reports/presentation/`: Beamer source and final PDF; `build/` is disposable and ignored.
- `data/raw/`, `data/processed/`, `data/analysis/`: local inputs and intermediate products; institutional deliveries are not included.
- `reports/working/`, `reports/reproduced/`, `archive/`: local validation evidence and history; preserved separately from the retained deliverables.
