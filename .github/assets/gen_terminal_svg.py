#!/usr/bin/env python3
"""Generate the animated terminal SVGs for the README.

One card per environment (local make, Docker, Nix).  Typed lines get a
steps() width animation, which needs the exact character count as a `ch`
width -- that is why these files are generated rather than hand-edited.
Output lines fade in shortly after the command that produced them.

Run from anywhere:  python .github/assets/gen_terminal_svg.py
Regenerate after editing the text, so widths and timings stay in sync.
"""
import html
from pathlib import Path

MUT = "mut"     # muted output
OK = "ok"       # green success
PATH = "path"   # blue-ish paths
NUM = "num"     # numbers
PROMPT = "pr"   # green $
SHELL = "sh"    # prompt of a nested shell (nix develop)
CMD = "cmd"     # white command

TYPE_SPEED = 0.055      # seconds per character
OUT_STEP = 0.16         # delay between consecutive output lines
OUT_FADE = 0.28
PAUSE_AFTER_OUT = 0.45  # think time before the next command is typed

WIDTH = 660
MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace"

# ── the three sessions: (kind, [(text, class), ...]); kind: type | out | gap ──

MAKE = [
    ("type", [("$ ", PROMPT), ("make reproduce", CMD)]),
    ("out",  [("  lambda =  1.0   depth =    7   E = ", MUT), ("+0.7280", NUM)]),
    ("out",  [("  lambda =  5.0   depth =   35   E = ", MUT), ("+0.5562", NUM)]),
    ("out",  [("  wrote ", MUT), ("build/results/example_zne.csv", PATH), ("  (150 rows)", MUT)]),
    ("out",  [("  Wrote ", MUT), ("build/plots/example_zne.tex", PATH)]),
    ("out",  [("Reproduction up to date!", OK)]),
    ("gap",  []),
    ("type", [("$ ", PROMPT), ("make check", CMD)]),
    ("out",  [("OK", OK), ("    example_zne.csv", MUT)]),
    ("out",  [("OK", OK), ("    example_zne_summary.csv", MUT)]),
    ("out",  [("All results match the committed reference.", OK)]),
    ("gap",  []),
    ("type", [("$ ", PROMPT), ("make", CMD)]),
    ("out",  [("Output written on ", MUT), ("build/paper/paper_template.pdf", PATH), (" (1 page)", MUT)]),
]

# No local R or TeX Live needed: everything runs in the pinned image.
DOCKER = [
    ("type", [("$ ", PROMPT), ("make repro_docker", CMD)]),
    ("out",  [("docker compose -f docker/docker-compose.yml build", MUT)]),
    ("out",  [(" Image ", MUT), ("paper_repro", PATH), (" Built", OK)]),
    ("out",  [("docker compose ... run --rm repro", MUT)]),
    ("out",  [("  wrote ", MUT), ("build/results/example_zne.csv", PATH), ("  (150 rows)", MUT)]),
    ("out",  [("  Compiling: example_zne.tex ", MUT), ("→", MUT), (" example_zne.pdf", MUT)]),
    ("out",  [("Reproduction up to date!", OK)]),
    ("out",  [("Output written on ", MUT), ("build/paper/paper_template.pdf", PATH), (" (1 page)", MUT)]),
]

# Nix pins the compilers and system libraries as well, not just the packages.
NIX = [
    ("type", [("$ ", PROMPT), ("nix develop", CMD)]),
    ("out",  [("Creating virtualenv in ./.venv ...", MUT)]),
    ("out",  [("Installing Python requirements ...", MUT)]),
    ("out",  [("Environment ready:  make reproduce  &&  make", OK)]),
    ("gap",  []),
    ("type", [("bash-5.2$ ", SHELL), ("make reproduce && make", CMD)]),
    ("out",  [("  wrote ", MUT), ("build/results/example_zne.csv", PATH), ("  (150 rows)", MUT)]),
    ("out",  [("Reproduction up to date!", OK)]),
    ("out",  [("Output written on ", MUT), ("build/paper/paper_template.pdf", PATH), (" (1 page)", MUT)]),
]

GRAPHICS = {"terminal.svg": MAKE, "terminal_docker.svg": DOCKER, "terminal_nix.svg": NIX}


def build(lines):
    """Return (svg, end_of_animation)."""
    keyframes, rules, body = [], [], []
    t = 0.0
    for i, (kind, spans) in enumerate(lines, start=1):
        cls = f"l{i:02d}"
        if kind == "gap":
            body.append("<br/>")
            continue
        text = "".join(s for s, _ in spans)
        inner = "".join(
            f'<span class="{c}">{html.escape(s)}</span>' for s, c in spans
        )
        if kind == "type":
            n = len(text)
            dur = round(n * TYPE_SPEED, 2)
            keyframes.append(
                f"@keyframes type-{cls}{{from{{width:0ch;}}to{{width:{n}ch;}}}}"
            )
            rules.append(
                f".{cls}{{width:0;animation:type-{cls} {dur}s {round(t, 2)}s "
                f"steps({n},end) forwards,cursor {dur}s linear {round(t, 2)}s 1;}}"
            )
            t = round(t + dur + 0.1, 2)
        else:
            rules.append(
                f".{cls}{{animation:fade {OUT_FADE}s {round(t, 2)}s ease forwards;}}"
            )
            t = round(t + OUT_STEP, 2)
            if i < len(lines) and lines[i][0] in ("gap", "type"):
                t = round(t + PAUSE_AFTER_OUT, 2)
        body.append(
            f'<span class="line {"typed" if kind == "type" else "out"} {cls}">'
            f'{inner}</span><br/>'
        )

    # The card grows with the number of rows; 22px is the measured rhythm of the
    # inline-block lines (overflow:hidden shifts their baseline).
    height = 100 + len(lines) * 22

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}">
  <style>
    /* Terminal card: same look as the qml-essentials code graphic. */
    body {{ padding: 22px; }}

    .container {{
      margin: auto;
      border-radius: 12px;
      box-shadow: 5px 5px 25px #111;
      font-family: {MONO};
      font-size: 14px;
      line-height: 1.45;
      color: #d4d4d4;
      background: #272a35;
    }}

    /* window controls */
    .top {{ padding: 10px; }}
    .button-l,.button-m,.button-r {{ display:inline-block;width:12px;height:12px;
                                    border-radius:50%;margin-left:5px; }}
    .button-l {{ background:#ff5f56; }}
    .button-m {{ background:#ffbd2e; }}
    .button-r {{ background:#27c93f; }}

    .content {{ padding: 0 18px 14px 18px; }}
    .content p {{ margin: 0; }}

    /* white-space:pre keeps the alignment of the real command output */
    .line {{ display:inline-block;white-space:pre;overflow:hidden;
            vertical-align:top;line-height:1.5;
            border-right:0.12em solid transparent; }}
    .out  {{ opacity: 0; }}

    /* syntax colours, matching the website scheme */
    .pr   {{ color:#27c93f; }}
    .sh   {{ color:#7e869c; }}
    .cmd  {{ color:#ffffff; }}
    .mut  {{ color:#8b93a7; }}
    .ok   {{ color:#2fb170; }}
    .path {{ color:#447bdd; }}
    .num  {{ color:#e15a46; }}

    @keyframes cursor {{ 0%,49%{{border-right-color:transparent;}}
                        50%,100%{{border-right-color:#d4d4d4;}} }}
    @keyframes fade {{ from{{opacity:0;}} to{{opacity:1;}} }}

    /* one keyframe set per typed line: the width must match its length in ch */
    {chr(10).join("    " + k for k in keyframes).strip()}
    {chr(10).join("    " + r for r in rules).strip()}
  </style>

  <foreignObject x="0" y="0" width="100%" height="100%">
    <body xmlns="http://www.w3.org/1999/xhtml">
      <div class="container">
        <div class="top">
          <span class="button-l"></span>
          <span class="button-m"></span>
          <span class="button-r"></span>
        </div>
        <div class="content">
          <p>
            {chr(10).join("            " + b for b in body).strip()}
          </p>
        </div>
      </div>
    </body>
  </foreignObject>
</svg>
'''
    return svg, t


here = Path(__file__).resolve().parent
for name, lines in GRAPHICS.items():
    svg, end = build(lines)
    (here / name).write_text(svg, encoding="utf-8")
    print(f"wrote {name}  ({len(svg)} bytes, animation ends at {end}s)")
