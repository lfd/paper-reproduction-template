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

        # Python: only the interpreter comes from Nix; the paper's pinned
        # packages are installed into ./.venv from reproduction/requirements.txt
        # by the shellHook below (Nix has no pinned qiskit set).
        myPython = pkgs.python313.withPackages (p: with p; [
          pip
          virtualenv
        ]);

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

            gnumake
            git
            less
            which
          ];
          shellHook = ''
            export VENV="$PWD/.venv"
            if [ ! -d "$VENV" ]; then
              echo "Creating virtualenv in $VENV ..."
              python -m venv "$VENV"
            fi
            source "$VENV/bin/activate"
            if [ -f reproduction/requirements.txt ]; then
              echo "Installing Python requirements ..."
              pip install --quiet -r reproduction/requirements.txt
            fi
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
