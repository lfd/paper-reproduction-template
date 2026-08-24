# =====================================================================
#  Paper reproduction package – top-level build
#
#  make            build the paper PDF        → build/paper/$(JOB).pdf
#  make reproduce  re-run experiments + plots → build/results, build/plots
#  make check      verify a fresh run against the committed reference
#  make help       list all targets
#
#  Rename the paper by setting JOB (or `make JOB=my_paper`).
# =====================================================================
OUTPUT = build
JOB    = paper_template

.PHONY: all help clean repro reproduce repro_docker dev plots compile_plots \
        check hardware fallback

# Programs and paths
COMPOSE = docker/docker-compose.yml
# Pass the host uid/gid through, so the container writes files as the current
# user instead of the image's built-in uid 1000 (see docker-compose.yml).
DC      = DOCKER_UID=$(shell id -u) DOCKER_GID=$(shell id -g) docker compose
# Auto-use ./.venv when it exists *and has the dependencies installed*
# (create it with: python -m venv .venv &&
#  .venv/bin/pip install -r reproduction/requirements.txt).
# The import probe matters inside containers and Nix shells, where a venv
# built for a different interpreter may be visible but unusable.
# Override with `make PY=/path/to/python`.
VENV_PY := $(shell [ -x .venv/bin/python ] && \
                   .venv/bin/python -c 'import numpy' >/dev/null 2>&1 && \
                   echo .venv/bin/python)
PY      ?= $(if $(VENV_PY),$(VENV_PY),python3)
R       = R_LIBS_USER=$(HOME)/R/library Rscript

# Directories
D_RESULTS      = $(OUTPUT)/results
D_PLOTS        = $(OUTPUT)/plots
D_PAPER        = $(OUTPUT)/paper

D_REPRODUCTION = ./reproduction
D_R            = $(D_REPRODUCTION)/R
D_SCRIPTS      = $(D_REPRODUCTION)/scripts
D_DATA         = $(D_REPRODUCTION)/data

OUTDIRS = $(D_RESULTS) $(D_PLOTS) $(D_PAPER)

# ------------------------------------------------------------------ #
# Paper dependencies                                                 #
# One entry per generated figure; see "Adding a figure" in README.md. #
# ------------------------------------------------------------------ #
RAW_PLOTS = example_zne
PLOTS     = $(addprefix $(D_PLOTS)/,$(addsuffix .tex,$(RAW_PLOTS)))

EXAMPLE_RESULTS = $(D_RESULTS)/example_zne.csv \
                  $(D_RESULTS)/example_zne_summary.csv

# ------------------------------------------------------------------ #
# Top-level rules                                                    #
# ------------------------------------------------------------------ #
# NOTE: the paper PDF depends only on main.tex (figures are inlined via
# \includetikz, falling back to paper/plots_precompiled/ when build/plots/
# is absent).  Regenerate figures/data explicitly with `make reproduce`.
all: $(D_PAPER)/$(JOB).pdf

help:
	@printf 'Targets:\n'
	@printf '  %-14s %s\n' \
	  all            'compile the paper PDF (default)' \
	  reproduce      'run experiments, then build all figures' \
	  plots          'rebuild figures from existing CSVs' \
	  check          'compare a fresh run against data/reference/' \
	  repro_docker   'run `make reproduce` inside the Docker image' \
	  dev            'interactive shell in the Docker image' \
	  hardware       'run the experiment on hardware (BACKEND=ibm|mqss|local)' \
	  clean          'delete build/'
	@printf '\nEnvironments: local venv, `docker compose`, or `nix develop`.\n'

$(D_PAPER)/$(JOB).pdf: paper/main.tex | $(OUTDIRS)
	BIBINPUTS=paper:$$BIBINPUTS latexmk -shell-escape -lualatex \
	    -interaction=nonstopmode \
	    -output-directory=$(D_PAPER) -jobname=$(JOB) $<

dev: $(COMPOSE)
	$(DC) -f $^ run --rm $@

repro_docker: $(COMPOSE)
	$(DC) -f $^ build
	$(DC) -f $^ run --rm repro
	$(MAKE) all

# `reproduce` is the canonical name; `repro` is kept as a short alias.
reproduce: plots
	@echo "Reproduction up to date!"

repro: reproduce

$(OUTDIRS):
	mkdir -p $@

plots: $(PLOTS) compile_plots

compile_plots: $(PLOTS) | $(D_PLOTS)
	@if [ -f "$(D_REPRODUCTION)/gen_img.sh" ]; then \
	    $(D_REPRODUCTION)/gen_img.sh $(D_PLOTS); \
	fi

# ------------------------------------------------------------------ #
# Example experiment + figure (replace with your own)                #
# ------------------------------------------------------------------ #
# Simulation: ZNE on a small circuit under depolarising noise.
$(EXAMPLE_RESULTS) &: $(D_SCRIPTS)/example_zne.py \
                      $(D_REPRODUCTION)/core/*.py | $(OUTDIRS)
	$(PY) $< --outdir $(D_RESULTS)

# Figure: E(lambda) curves + extrapolation, drawn from the CSVs above.
$(D_PLOTS)/example_zne.tex: $(D_R)/plot_example_zne.R \
                            $(D_R)/config.R \
                            $(EXAMPLE_RESULTS) | $(OUTDIRS)
	$(R) $<

# Regenerate the committed fallback PDF (used when build/plots/ is absent).
fallback: $(EXAMPLE_RESULTS)
	$(PY) $(D_SCRIPTS)/make_fallback.py

# ------------------------------------------------------------------ #
# Reproducibility check: fresh run vs. committed reference results   #
# ------------------------------------------------------------------ #
check: $(EXAMPLE_RESULTS)
	$(PY) $(D_SCRIPTS)/check_results.py \
	    --reference $(D_DATA)/reference \
	    --results $(D_RESULTS)

# ------------------------------------------------------------------ #
# Optional: run the experiment on real hardware.                      #
# Not part of `reproduce`: needs credentials (reproduction/.env) and   #
# queue time.  BACKEND=local runs the same code path on a simulator.  #
#   make hardware                  (simulator smoke test)             #
#   make hardware BACKEND=ibm      (real device)                      #
# ------------------------------------------------------------------ #
BACKEND ?= local
HW_REPS ?= 10
HW_SHOTS ?= 4096

hardware: | $(OUTDIRS)
	$(PY) $(D_REPRODUCTION)/hardware/run_hardware.py \
	    --backend $(BACKEND) --reps $(HW_REPS) --shots $(HW_SHOTS) \
	    --outdir $(D_RESULTS)

clean:
	rm -rf $(OUTPUT)
