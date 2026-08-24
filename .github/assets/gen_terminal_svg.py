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

# A shared beat grid keeps the three cards in step: every row starts on a beat,
# a typed command occupies two beats, an output line or a blank one beat.  The
# cards therefore advance in lockstep for as long as their sessions agree, and
# they all restart together every CYCLE seconds.
BEAT = 0.34             # seconds per row
TYPE_BEATS = 2          # beats a typed command occupies
TYPE_DUR = 0.6          # typing itself, independent of the command length
OUT_FADE = 0.26
CYCLE = 15.0            # loop length; the finished frame is held until then

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
    ("type", [("$ ", PROMPT), ("make", CMD)]),
    ("out",  [("Output written on ", MUT), ("build/paper/paper_template.pdf", PATH), (" (1 page)", MUT)]),
    ("gap",  []),
    ("type", [("$ ", PROMPT), ("make check", CMD)]),
    ("out",  [("OK", OK), ("    example_zne.csv", MUT)]),
    ("out",  [("OK", OK), ("    example_zne_summary.csv", MUT)]),
    ("out",  [("All results match the committed reference.", OK)]),
]

# No local R or TeX Live needed: everything runs in the pinned image.  The row
# count is chosen so that the closing PDF line lands on the same beat as in the
# other two sessions.
DOCKER = [
    ("type", [("$ ", PROMPT), ("make repro_docker", CMD)]),
    ("out",  [("docker compose -f docker/docker-compose.yml build", MUT)]),
    ("out",  [(" Image ", MUT), ("paper_repro", PATH), (" Built", OK)]),
    ("out",  [("docker compose ... run --rm repro", MUT)]),
    ("out",  [("python3 reproduction/scripts/example_zne.py", MUT)]),
    ("out",  [("  wrote ", MUT), ("build/results/example_zne.csv", PATH), ("  (150 rows)", MUT)]),
    ("out",  [("  wrote ", MUT), ("build/results/example_zne_summary.csv", PATH), ("  (3 rows)", MUT)]),
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


def pct(seconds):
    """Position of *seconds* inside the loop, in percent of the cycle."""
    return round(min(seconds, CYCLE) / CYCLE * 100, 2)


def build(lines):
    """Return (svg, end_of_animation)."""
    keyframes, rules, body = [], [], []
    beat = 0
    end = 0.0
    for i, (kind, spans) in enumerate(lines, start=1):
        cls = f"l{i:02d}"
        start = round(beat * BEAT, 2)
        if kind == "gap":
            beat += 1
            body.append("<br/>")
            continue
        text = "".join(s for s, _ in spans)
        inner = "".join(
            f'<span class="{c}">{html.escape(s)}</span>' for s, c in spans
        )
        if kind == "type":
            n = len(text)
            p0 = pct(start)
            p1 = pct(start + TYPE_DUR)
            keyframes.append(
                f"@keyframes type-{cls}{{"
                f"0%,{p0}%{{width:0;border-right-color:transparent;}}"
                f"{p0 + 0.01}%{{border-right-color:#d4d4d4;}}"
                f"{p1}%{{width:{n}ch;}}"
                f"{p1 + 0.01}%,100%{{width:{n}ch;border-right-color:transparent;}}}}"
            )
            rules.append(
                f".{cls}{{width:0;animation:type-{cls} {CYCLE}s steps({n},end) infinite;}}"
            )
            beat += TYPE_BEATS
            end = max(end, start + TYPE_DUR)
        else:
            p0 = pct(start)
            p1 = pct(start + OUT_FADE)
            keyframes.append(
                f"@keyframes fade-{cls}{{0%,{p0}%{{opacity:0;}}"
                f"{p1}%,100%{{opacity:1;}}}}"
            )
            rules.append(
                f".{cls}{{animation:fade-{cls} {CYCLE}s linear infinite;}}"
            )
            beat += 1
            end = max(end, start + OUT_FADE)
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

    /* One keyframe set per line, expressed in percent of the {CYCLE}s loop:
       typed lines animate their width in `ch` (hence the generated character
       counts), output lines fade in.  The finished frame is held until the
       cycle restarts, so a reader arriving late still sees the session play. */
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
    return svg, end


here = Path(__file__).resolve().parent
for name, lines in GRAPHICS.items():
    svg, end = build(lines)
    (here / name).write_text(svg, encoding="utf-8")
    print(f"wrote {name}  ({len(svg)} bytes, animation ends at {end}s)")
