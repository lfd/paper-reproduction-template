{
  description = "Reproduction environment for a paper reproduction package (R + Python + TeX Live)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowBroken = true;
        };

        # Python: only the interpreter comes from Nix (the minor version must
        # match requires-python in reproduction/pyproject.toml); the paper's
        # locked packages are installed into reproduction/.venv from uv.lock
        # by the shellHook below (Nix has no pinned qiskit set).
        myPython = pkgs.python312;

        # R: plotting stack used by reproduction/R/*.R
        myR = pkgs.rWrapper.override {
          packages = with pkgs.rPackages; [
            ggnewscale
            patchwork
            scales
            tidyverse
            tikzDevice
          ];
        };

        # TeX Live: collections rather than individual packages, so that
        # adding a LaTeX package to paper/main.tex rarely means touching
        # this file.  Swap for `pkgs.texliveFull` if something is missing.
        myTex = pkgs.texliveBasic.withPackages (ps: with ps; [
          latexmk

          collection-bibtexextra    # biber, biblatex, bst files
          collection-fontsrecommended
          collection-latexextra     # censor, cleveref, glossaries-extra, standalone
          collection-latexrecommended
          collection-luatex         # lualatex
          collection-pictures       # tikz/pgf (also needed by R's tikzDevice)
          collection-plaingeneric
          collection-publishers     # IEEEtran

          preprint                  # balance.sty (IEEE two-column balancing)
        ]);

        shell = pkgs.mkShell {
          NIX_HARDENING_ENABLE = "";
          buildInputs = with pkgs; [
            myTex
            myR
            myPython
            uv

            gnumake
            git
            less
            which
          ];
          shellHook = ''
            # uv must use Nix's interpreter, never download its own.
            export UV_PYTHON="${myPython}/bin/python3"
            export UV_PYTHON_DOWNLOADS=never
            if [ ! -d reproduction/.venv ]; then
              echo "Creating virtualenv in reproduction/.venv ..."
            fi
            echo "Syncing Python packages from uv.lock ..."
            uv sync --locked --quiet --directory reproduction
            source reproduction/.venv/bin/activate
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ]}:$LD_LIBRARY_PATH"
            echo "Environment ready:  make reproduce  &&  make"
          '';
        };

      in
      {
        devShells.default = shell;
        # `nix develop` on older Nix versions
        devShell = shell;
      }
    );
}
