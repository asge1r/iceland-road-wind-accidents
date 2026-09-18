# University of Iceland thesis template

The cover retains the supplied University of Iceland banner. The revised thesis
uses one-sided A4 pages, 2 cm margins, centred page numbers, 12-point Times body
text and sans-serif headings. No blank recto/verso pages or appendix are included.
`draft_en.tex` loads `content.tex` and the retained generated tables. The examiner
is rendered using the existing `thesisexaminer` field.

Build in a separate output directory to preserve the unrelated untracked
`draft_en.pdf`. The final deliverable retains its existing long PDF filename.

## Current isolated build

In Emacs with AUCTeX, open `content.tex` and press `C-c C-c`. Its
`TeX-master` setting selects `draft_en.tex`, and the local `.latexmkrc` writes
`Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf` directly.
The same command works from `draft_en.tex`. `latexmk` may leave ignored
auxiliary files here, but it does not overwrite `draft_en.pdf`.

For an isolated command-line build, use the following procedure.

From `reports/thesis`, create an empty output directory and run pdfLaTeX three
times, keeping all auxiliary files out of the source directory:

```bash
mkdir -p /private/tmp/thesis-build
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/private/tmp/thesis-build draft_en.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/private/tmp/thesis-build draft_en.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=/private/tmp/thesis-build draft_en.tex
```

Review the PDF and log, then copy only the PDF to
`Meteorological_Conditions_and_Rural_Injury_Accidents_in_Iceland.pdf`. Preserve
local `draft_en.pdf` backups. Python dependencies are pinned at the repository
root; preparation and retained analysis commands are in `docs/pipeline.md`.
