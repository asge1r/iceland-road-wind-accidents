.PHONY: all panels prototype
all:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build defense.tex
	cp build/defense.pdf defense.pdf

# Optional presentation-only re-layout of existing validated plot outputs.
panels:
	cd ../.. && MPLCONFIGDIR=/private/tmp/defense-mpl .venv/bin/python reports/defense_beamer/export_panels.py

prototype:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build prototype.tex
