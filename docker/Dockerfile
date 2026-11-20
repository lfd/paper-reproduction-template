FROM python:3.12-slim

ARG USER="repro"

# System deps: LaTeX + R
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        latexmk \
        libcurl4-openssl-dev \
        libfontconfig1-dev \
        libfribidi-dev \
        libharfbuzz-dev \
        libssl-dev \
        libtiff5-dev \
        libuv1-dev \
        libxml2-dev \
        r-base \
        r-base-dev \
        sudo \
        texlive-base \
        texlive-fonts-recommended \
        texlive-latex-extra \
        texlive-luatex \
        texlive-pictures \
        texlive-plain-generic \
        texlive-publishers \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir ~/.R && \
    echo "MAKEFLAGS = -j$(($(nproc)/4))" > ~/.R/Makevars

# R packages (same set as companion paper)
RUN Rscript -e "install.packages(c('tidyverse', 'scales', 'patchwork', 'tikzDevice', 'ggnewscale'), \
    Ncpus=parallel::detectCores(), repos='https://cloud.r-project.org', clean=TRUE)"

# Python dependencies, installed from uv.lock into /opt/venv (first on PATH,
# so `python3` is the locked environment).  uv uses the image's interpreter.
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH
WORKDIR /root
COPY ./reproduction/pyproject.toml ./reproduction/uv.lock ./
RUN uv sync --locked --no-cache && \
    rm pyproject.toml uv.lock

# Unprivileged user
RUN useradd -m ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER ${USER}
WORKDIR /home/${USER}

CMD [ "bash" ]
