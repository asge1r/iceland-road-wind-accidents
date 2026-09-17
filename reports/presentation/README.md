# Defense presentation

Build from the repository root:

```bash
make -C reports/presentation
```

This runs XeLaTeX through latexmk and writes all auxiliary files into `build/`.
The source prefers Noto Sans, falls back to DejaVu Sans, then Latin Modern Sans.
The final `defense_slides.pdf` is retained alongside its source, following the
thesis convention; build PDFs, XDV and auxiliary files are ignored.

Figures are loaded from `reports/main/figures/`. Missing assets fail the build.
The slides follow the current thesis: weather-frequency O/E, approximate
traffic-corrected O/E, and monthly-frequency estimated VKT. Backups cover
matching, the preparation/analysis distinction in Section 3.2, and future work.
A document build needs the retained figures and TeX packages, not the restricted
institutional datasets. Regenerating numerical results requires those datasets
and the preparation steps documented in `docs/pipeline.md`.
