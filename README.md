# Paper Reproduction Template

A self-contained project template for reproducible quantum-computing papers.
The horoscope-effect experiment (garbage-folding ZNE falsification) is included
as a working end-to-end example; replace or extend it for new papers.

---

## Project layout

```
paper/                  LaTeX source (IEEEtran, lualatex)
  main.tex              Paper source — title, authors, sections
  references.bib        BibTeX database
  plots_precompiled/    Fallback PDFs used when build/plots/ is absent
  IEEEtran.{cls,bst}   IEEE class and bibliography style

reproduction/
  scripts/              Python simulation scripts
  R/                    R plotting scripts (tikzDevice → TikZ/PDF figures)
  core/                 Shared Python library (circuits, noise, ZNE, stats)
  hardware/             Hardware-execution scripts (require credentials)
  data/                 Static read-only input data committed to the repo
  logs/                 Hardware run logs (.gitignored)
  requirements.txt      Pinned Python dependencies
  .env.example          Credential template — copy to .env, never commit

docker/
  Dockerfile            Python 3.12 + R + LaTeX image
  docker-compose.yml    Services: dev (interactive) and repro (make repro)

build/                  All generated files — gitignored, safe to delete
  paper/                Compiled PDF and LaTeX intermediates
  plots/                TikZ .tex fragments + compiled PDFs
  results/              Generated CSV data
```

---

## Quick start

### 1 — Local (recommended for development)

**Prerequisites:** Python ≥ 3.11, R ≥ 4.5, a TeX Live installation with
`lualatex` / `latexmk`, and the R packages listed below.

```bash
# Python environment
python3 -m venv .venv
.venv/bin/pip install -r reproduction/requirements.txt

# R packages (first time only)
Rscript -e "install.packages(
  c('tidyverse','scales','patchwork','tikzDevice','ggnewscale'),
  repos='https://cloud.r-project.org', type='source')"

# Build paper PDF (uses precompiled fallback figures)
make all

# Regenerate all figures from scratch, then rebuild PDF
make repro        # = simulation + R plots
make all          # rebuild PDF with fresh figures
```

### 2 — Docker (reproducible, no local R/LaTeX needed for repro)

```bash
# Build the image (≈ 5 min, done once)
make repro_docker

# Or step by step:
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm repro  # make repro inside container
make all                                                      # compile PDF locally
```

Interactive development shell inside the container:

```bash
make dev
# inside container:
make repro
```

---

## Make targets

| Target          | What it does |
|-----------------|--------------|
| `make all`      | Compile the paper PDF with latexmk (default). Uses `build/plots/*.tex` if present, otherwise falls back to `paper/plots_precompiled/`. |
| `make repro`    | Run Python simulation → generate CSVs → run R scripts → compile TikZ figures. Does **not** rebuild the PDF. |
| `make plots`    | Run R scripts and compile TikZ figures only (assumes CSVs already exist). |
| `make repro_docker` | Build the Docker image and run `make repro` inside it. |
| `make dev`      | Start an interactive shell in the Docker container. |
| `make hardware_qexa` | Run the EQE1 hardware experiment (requires `MQSS_TOKEN`). |
| `make clean`    | Delete the entire `build/` directory. |

---

## Configuration

### Adding a new figure

1. Write a Python script in `reproduction/scripts/` that produces a CSV under
   `build/results/`.
2. Write an R script in `reproduction/R/` that reads the CSV and writes a TikZ
   file to `build/plots/` via `tikzDevice`.
3. In the `Makefile`, add the figure name to `RAW_PLOTS` and add dependency
   rules (see the existing `horoscope_sweep` rules as a model).
4. In `paper/main.tex`, use `\includetikz{figure_name}`.

### Python environment

The Makefile auto-detects `.venv/bin/python` in the project root and uses it
when present, falling back to `python3`.  Create it with:

```bash
python3 -m venv .venv
.venv/bin/pip install -r reproduction/requirements.txt
```

### R library path

The Makefile sets `R_LIBS_USER=$(HOME)/R/library` when calling `Rscript`, so
packages installed there are always found.  Install with:

```bash
Rscript -e "install.packages('<pkg>', lib='~/R/library', type='source')"
```

### Anonymisation

`paper/main.tex` contains an `anonymous` boolean.  Set it to `true` to censor
author names and institution for double-blind submission:

```latex
\setboolean{anonymous}{true}
```

### Hardware credentials

Copy `reproduction/.env.example` to `reproduction/.env` and fill in your
tokens.  The `.env` file is gitignored — **never commit credentials**.

```
MQSS_TOKEN=...          # IQM Euro-Q-Exa (EQE1) via LRZ MQSS portal
IBM_QUANTUM_TOKEN=...   # optional, for --backend ibm
```

Load them before running a hardware script:

```bash
export $(grep -v '^#' reproduction/.env | xargs)
python reproduction/hardware/horoscope_qexa.py --reps 30 --shots 4096
```

Or on the LRZ server (deploy in a tmux session via the deploy scripts).

---

## Adapting this template for a new paper

1. **Rename** the job: change `JOB = paper_template` in the Makefile and
   update `paper/main.tex`.
2. **Replace** the horoscope experiment: remove or keep the existing scripts
   and add your own in `reproduction/scripts/` and `reproduction/R/`.
3. **Update** `RAW_PLOTS` and dependency rules in the Makefile.
4. **Clear** the example bibliography entries in `paper/references.bib` and
   add your own.  Uncomment `\bstctlcite{BSTcontrol}` and
   `\bibliographystyle{IEEEtran}` / `\bibliography{references}` in `main.tex`
   once you have `\cite{}` commands.
5. **Pin** package versions in `reproduction/requirements.txt` once the
   experimental pipeline is finalised.
