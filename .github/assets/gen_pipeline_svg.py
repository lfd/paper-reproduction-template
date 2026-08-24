#!/usr/bin/env python3
"""Generate the animated pipeline SVG for the README.

Three bands, one per make target; every box and arrow fades in in the order
the pipeline actually produces it.

Run from the project root:  python .github/assets/gen_pipeline_svg.py
Regenerate after editing the text, so the animation timings stay in sync.
"""
from pathlib import Path

W, H = 780, 420
CARD = dict(x=20, y=16, w=740, h=388, r=12)
MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace"

SRC, GEN, OUT, REF = "src", "gen", "out", "ref"
BOX_H = 46
CYCLE = 15.0   # loop length, matching gen_terminal_svg.py

parts = {"labels": [], "arrows": [], "nodes": []}
anims, keyframes = [], []
clock = [0.0]
uid = [0]


def tick(inc):
    d = clock[0]
    clock[0] = round(clock[0] + inc, 2)
    return d


def pct(seconds):
    """Position of *seconds* inside the loop, in percent of the cycle."""
    return round(min(seconds, CYCLE) / CYCLE * 100, 2)


def anim(dur, delay):
    """One keyframe set per element, expressed in percent of the cycle.

    Using percentages rather than `animation-delay` matters: with a delay,
    every element restarts its own cycle at its own time and merely blinks in
    place.  Here all elements share one timeline, so the diagram clears at 0%
    and is drawn again in order."""
    uid[0] += 1
    name = f"a{uid[0]}"
    p0, p1 = pct(delay), pct(delay + dur)
    keyframes.append(
        f"@keyframes show-{name}{{0%,{p0}%{{opacity:0;}}{p1}%,100%{{opacity:1;}}}}"
    )
    anims.append(f".{name}{{animation:show-{name} {CYCLE}s linear infinite;}}")
    return name


def box(x, y, w, flavour, name, where):
    cls = anim(0.3, tick(0.34))
    parts["nodes"].append(
        f'  <g class="fx {cls}">\n'
        f'    <rect class="box {flavour}" x="{x}" y="{y}" width="{w}" '
        f'height="{BOX_H}" rx="7"/>\n'
        f'    <text class="t {flavour}" x="{x + w / 2:g}" y="{y + 21}">{name}</text>\n'
        f'    <text class="t sub" x="{x + w / 2:g}" y="{y + 35}">{where}</text>\n'
        f'  </g>'
    )
    return x + w


def arrow(x1, x2, y, caption):
    cls = anim(0.25, tick(0.18))
    parts["arrows"].append(
        f'  <g class="fx {cls}">\n'
        f'    <line class="arw" x1="{x1}" y1="{y}" x2="{x2 - 7}" y2="{y}"/>\n'
        f'    <path class="head" d="M{x2 - 7},{y - 4} L{x2},{y} L{x2 - 7},{y + 4} Z"/>\n'
        f'    <text class="t cap" x="{(x1 + x2) / 2:g}" y="{y - 8}">{caption}</text>\n'
        f'  </g>'
    )


def target(y, text):
    cls = anim(0.3, tick(0.1))
    parts["labels"].append(
        f'  <g class="fx {cls}">\n'
        f'    <text class="t tgt" x="42" y="{y}">$ {text}</text>\n  </g>'
    )


def note(x, y, lines):
    cls = anim(0.3, tick(0.1))
    body = "\n".join(
        f'    <text class="t note" x="{x}" y="{y + 14 * n}">{line}</text>'
        for n, line in enumerate(lines)
    )
    parts["labels"].append(f'  <g class="fx {cls}">\n{body}\n  </g>')


# ── band 1: make reproduce ───────────────────────────────────────────────
target(64, "make reproduce")
y = 78
x = box(42, y, 124, SRC, "example_zne.py", "reproduction/scripts")
arrow(x, x + 66, y + 23, "simulate")
x = box(x + 66, y, 124, GEN, "example_zne.csv", "build/results")
arrow(x, x + 66, y + 23, "tikzDevice")
x = box(x + 66, y, 124, GEN, "example_zne.tex", "build/plots")
arrow(x, x + 66, y + 23, "gen_img.sh")
box(x + 66, y, 124, GEN, "example_zne.pdf", "build/plots")

# ── band 2: make ─────────────────────────────────────────────────────────
target(186, "make")
y = 200
x = box(42, y, 124, SRC, "main.tex", "paper")
arrow(x, x + 66, y + 23, "latexmk")
box(x + 66, y, 300, OUT, "paper_template.pdf", "build/paper")
note(552, y + 18, ["\\includetikz uses build/plots/,", "else plots_precompiled/"])

# ── band 3: make check ───────────────────────────────────────────────────
target(294, "make check")
y = 308
x = box(42, y, 220, GEN, "build/results/*.csv", "fresh run")
cls = anim(0.25, tick(0.18))
parts["arrows"].append(
    f'  <g class="fx {cls}">\n'
    f'    <line class="arw dash" x1="{x + 6}" y1="{y + 23}" x2="{x + 90}" y2="{y + 23}"/>\n'
    f'    <path class="head" d="M{x + 13},{y + 19} L{x + 6},{y + 23} L{x + 13},{y + 27} Z"/>\n'
    f'    <path class="head" d="M{x + 83},{y + 19} L{x + 90},{y + 23} L{x + 83},{y + 27} Z"/>\n'
    f'    <text class="t cap" x="{x + 48}" y="{y + 15}">equal</text>\n'
    f'  </g>'
)
box(x + 96, y, 260, REF, "reproduction/data/reference/*.csv", "committed expectation")

legend_cls = anim(0.3, tick(0.2))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="Pipeline of the reproduction template: make reproduce turns the
       experiment script into CSV results, TikZ figures and figure PDFs; make turns
       main.tex into the paper PDF; make check compares fresh results with the
       committed reference results.">
  <style>
    .card {{ fill:#272a35; filter:drop-shadow(4px 5px 18px rgba(0,0,0,.55)); }}
    .t    {{ font-family:{MONO}; font-size:11px; fill:#d4d4d4; text-anchor:middle; }}
    .sub  {{ font-size:9px; fill:#7e869c; }}
    .cap  {{ font-size:9px; fill:#7e869c; }}
    .tgt  {{ font-size:12px; fill:#27c93f; text-anchor:start; }}
    .note {{ font-size:9px; fill:#7e869c; text-anchor:start; }}

    /* box flavours: committed source, generated artefact, the paper, reference data */
    .box     {{ fill:#2f3341; stroke-width:1.2; }}
    .box.src {{ stroke:#447bdd; }}
    .box.gen {{ stroke:#2fb170; }}
    .box.out {{ stroke:#e15a46; }}
    .box.ref {{ stroke:#c972c1; }}
    text.src {{ fill:#8ab4ff; }}
    text.gen {{ fill:#63d39b; }}
    text.out {{ fill:#ff8b78; }}
    text.ref {{ fill:#dfa8db; }}

    .arw  {{ stroke:#7e869c; stroke-width:1.2; }}
    .dash {{ stroke-dasharray:4 3; }}
    .head {{ fill:#7e869c; }}

    /* each element appears when the pipeline reaches it */
    .fx {{ opacity:0; }}
    /* Each element fades in when the pipeline reaches it and is then held
       until the {CYCLE:g}s cycle restarts, which clears the diagram and draws
       it again.  Opacity only: animating `transform` pushes the group onto
       the compositor, where it renders inconsistently once the SVG is
       embedded as an image. */
    {chr(10).join("    " + k for k in keyframes).strip()}
    {chr(10).join("    " + a for a in anims).strip()}
  </style>

  <rect class="card" x="{CARD['x']}" y="{CARD['y']}" width="{CARD['w']}"
        height="{CARD['h']}" rx="{CARD['r']}"/>

{chr(10).join(parts["labels"])}
{chr(10).join(parts["arrows"])}
{chr(10).join(parts["nodes"])}

  <g class="fx {legend_cls}">
    <rect class="box src" x="42" y="372" width="10" height="10" rx="2"/>
    <text class="t note" x="58" y="381">committed</text>
    <rect class="box gen" x="150" y="372" width="10" height="10" rx="2"/>
    <text class="t note" x="166" y="381">generated (build/, gitignored)</text>
    <rect class="box out" x="392" y="372" width="10" height="10" rx="2"/>
    <text class="t note" x="408" y="381">paper</text>
    <rect class="box ref" x="466" y="372" width="10" height="10" rx="2"/>
    <text class="t note" x="482" y="381">reference results</text>
  </g>
</svg>
'''
out = Path(__file__).resolve().parent / "pipeline.svg"
out.write_text(svg, encoding="utf-8")
print(f"wrote {out} ({len(svg)} bytes, animation ends ~{round(clock[0] + 0.5, 2)}s)")
