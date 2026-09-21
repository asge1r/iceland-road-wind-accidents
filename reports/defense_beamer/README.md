# Icelandic defence — PPTX rebuild

New, independent version of `Meistaravorn_Asgeir_editable (3).pptx`.
The existing `reports/defense/` presentation is preserved.

From the repository root:

```sh
make -C reports/defense_beamer
```

This uses the installed `latexmk` and XeLaTeX, puts auxiliaries in `build/`,
and copies the successful PDF to `reports/defense_beamer/defense.pdf`.
Aptos is used when installed, with Helvetica Neue as the local fallback.
No analysis runs as part of the normal build.

- `defense.tex`: editable slide text, formulas, workflow and tables.
- `theme.tex`: fonts, margins, logo, and seasonal-slide placement.
- `assets/`: presentation-specific vector figures and the original PPTX HÍ logo.
- `speaker_notes.md`: short Icelandic reminders for essential off-slide interpretation.
- `TIMING.md`: slide-by-slide timing, 29 minutes plus one-minute buffer.
- `INVENTORY.md`: availability of all nine method–variable combinations.
- `REVISION_REPORT.md`: order, timing, sources and validation.
- `export_panels.py`: optional layout-only exports from retained results.
- `prototype.tex`: first seasonal layout prototype (`make -C reports/defense_beamer prototype`).

Original figures are linked from `../main/figures/`, so retain the repository
layout when moving or editing this project. Figures remain vector graphics
except the existing raster accident map and logo.

To refresh only the presentation-specific artwork, using existing validated
outputs and the repository's existing Python environment:

```sh
make -C reports/defense_beamer panels
make -C reports/defense_beamer
```

The exporter calls existing plotting/display routines, preserves original
artists' numerical content, and checks bars, colours, counts, bins, y limits
and ticks before and after layout. It writes only inside this presentation.
It does not estimate traffic, allocate weather exposure anew, select a new
accident sample, or write scientific CSV files. Audit snapshots are in
`assets/panel_audit.json` and `assets/traffic_audit.json`.
