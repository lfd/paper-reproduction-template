#!/usr/bin/env python3
"""Emit the project-layout mermaid block for the README.

Nodes of the same rank are padded to the same character count.  With the
monospace font set in the init directive that makes them equally wide, so
every arrow of a rank starts and ends at the same x position -- dagre centres
nodes within a rank, and equal widths turn that into a flush edge.
"""

# (id, label, css class, parent, rank)
ROOT = ("root", "paper-reproduction-template", "rootbox")

FAMILIES = [
    ("paper", "paper/ · LaTeX source", "srcA"),
    ("repro", "reproduction/ · the experiment", "srcA"),
    ("envs", "environment pinning", "envA"),
    ("build", "build/ · generated, gitignored", "genA"),
]

CHILDREN = [
    ("p1", "paper", "main.tex · sections, figures", "srcB"),
    ("p2", "paper", "references.bib", "srcB"),
    ("p3", "paper", "plots_precompiled/ · fallbacks", "srcB"),
    ("p4", "paper", "IEEEtran.cls · IEEEtran.bst", "srcB"),
    ("r1", "repro", "scripts/ · Python, writes CSV", "srcB"),
    ("r2", "repro", "R/ · CSV to TikZ figures", "srcB"),
    ("r3", "repro", "core/ · shared library", "srcB"),
    ("r4", "repro", "hardware/ · QPU runs", "srcB"),
    ("r5", "repro", "data/ · static inputs", "srcB"),
    ("r7", "repro", "requirements.txt · pinned", "srcB"),
    ("r8", "repro", ".env.example · credentials", "srcB"),
    ("e1", "envs", "docker/ · Python + R + TeX", "envB"),
    ("e2", "envs", "flake.nix · nix develop", "envB"),
    ("e3", "envs", ".github/workflows/ · CI", "envB"),
    ("b1", "build", "results/ · CSV data", "genB"),
    ("b2", "build", "plots/ · TikZ + figure PDFs", "genB"),
    ("b3", "build", "paper/ · the compiled PDF", "genB"),
]

GRANDCHILDREN = [
    ("r6", "r5", "reference/ · make check", "srcB"),
]


def pad(labels):
    """Pad every label to the width of the longest one in its rank.

    Padding uses U+00A0 so it survives whitespace collapsing, without
    depending on how the renderer treats HTML entities."""
    width = max(len(t) for t in labels)
    # A trailing zero-width space keeps the padding: mermaid trims its labels,
    # and JS trim() also strips U+00A0, but not U+200B.
    return {t: t + "\u00a0" * (width - len(t)) + "\u200b" for t in labels}


rank1 = pad([lbl for _, lbl, _ in FAMILIES])
rank2 = pad([lbl for _, _, lbl, _ in CHILDREN])
rank3 = pad([lbl for _, _, lbl, _ in GRANDCHILDREN])

lines = [
    # fontFamily is a top-level option; setting it only under themeVariables
    # leaves the default Trebuchet in place.  A monospace font is what makes
    # equal character counts equal box widths.
    "%%{init: {'fontFamily':'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace',"
    "'themeVariables':{'fontFamily':'ui-monospace,SFMono-Regular,Menlo,"
    "Consolas,monospace','fontSize':'14px'},"
    "'flowchart':{'wrappingWidth':600,'nodeSpacing':20,'rankSpacing':70,"
    "'curve':'basis'}}}%%",
    "flowchart LR",
    f'    {ROOT[0]}(["{ROOT[1]}"])',
    "",
]

by_class = {}
by_class.setdefault(ROOT[2], []).append(ROOT[0])

for fid, flabel, fclass in FAMILIES:
    lines.append(f'    {ROOT[0]} --> {fid}(["{rank1[flabel]}"])')
    by_class.setdefault(fclass, []).append(fid)
    for cid, parent, clabel, cclass in CHILDREN:
        if parent != fid:
            continue
        lines.append(f'    {fid} --> {cid}(["{rank2[clabel]}"])')
        by_class.setdefault(cclass, []).append(cid)
        for gid, gparent, glabel, gclass in GRANDCHILDREN:
            if gparent == cid:
                lines.append(f'    {cid} --> {gid}(["{rank3[glabel]}"])')
                by_class.setdefault(gclass, []).append(gid)
    lines.append("")

lines += [
    "    classDef rootbox fill:#272a35,stroke:#272a35,color:#d4d4d4",
    "    classDef srcA fill:#1f5fa8,stroke:#1f5fa8,color:#e8f0ff",
    "    classDef srcB fill:#8ab4ff,stroke:#8ab4ff,color:#10233d",
    "    classDef envA fill:#8e4d8a,stroke:#8e4d8a,color:#fbe9f8",
    "    classDef envB fill:#dfa8db,stroke:#dfa8db,color:#2c1730",
    "    classDef genA fill:#1f8f5a,stroke:#1f8f5a,color:#d4f7e8",
    "    classDef genB fill:#58e3a6,stroke:#58e3a6,color:#272a35",
    "",
    "    linkStyle default stroke-width:2px",
    "",
]
for cls in ("rootbox", "srcA", "srcB", "envA", "envB", "genA", "genB"):
    if by_class.get(cls):
        lines.append(f'    class {",".join(by_class[cls])} {cls}')

print("\n".join(lines))
