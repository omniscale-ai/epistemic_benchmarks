#!/usr/bin/env python3
"""Editable draw.io source for the 'classical scientific loop' slide (generic examples) + PNG render.

Writes classical_loop.drawio. PNG is rendered separately (see render step in README of the deck / build notes):
the draw.io viewer in headless Chrome, then cropped to the content -> classical_loop.png.
Cards are groups (card, number, title, question, example): move a group and its arrows follow.
"""
from pathlib import Path
from xml.sax.saxutils import quoteattr

NAVY, BLUE, LIGHT, GREY = "#00204D", "#008CE3", "#B8C7DD", "#5B6B82"
OX, OY = 40, 40
CW, CH = 300, 124
GAPX, GAPY = 90, 54
STAGES = [
    ("1", "Context", "What do we already know?", "e.g. literature, data, earlier results", 0, 0),
    ("2", "Hypothesis", "What could explain it?", "e.g. candidate laws, mechanisms, entities", 1, 0),
    ("3", "Experiment", "How do we test it?", "e.g. a simulation, a measurement, a lab run", 1, 1),
    ("4", "Evidence", "What did we learn?", "e.g. fits, residuals, ranked explanations", 0, 1),
]
cells = []


def vertex(i, value, x, y, w, h, style, parent="1"):
    cells.append(f'<mxCell id="{i}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="{parent}">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def text(size, color, bold=False, italic=False, align="left"):
    return (f"text;html=1;whiteSpace=wrap;fontFamily=Helvetica;fontSize={size};fontColor={color};align={align};"
            f"verticalAlign=middle;fontStyle={(1 if bold else 0) | (2 if italic else 0)};strokeColor=none;fillColor=none;spacing=0;")


for n, title, q, ex, cx, cy in STAGES:
    gid = f"g{n}"
    x, y = OX + cx * (CW + GAPX), OY + cy * (CH + GAPY)
    cells.append(f'<mxCell id="{gid}" value="" style="group;" vertex="1" connectable="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{CW}" height="{CH}" as="geometry"/></mxCell>')
    vertex(f"{gid}_card", "", 0, 0, CW, CH, f"rounded=1;arcSize=7;html=1;fillColor={NAVY};strokeColor=none;", gid)
    vertex(f"{gid}_num", n, 18, 16, 34, 34, f"ellipse;html=1;fillColor={BLUE};strokeColor=none;fontColor=#FFFFFF;fontSize=17;fontStyle=1;fontFamily=Helvetica;", gid)
    vertex(f"{gid}_title", title, 64, 14, 220, 38, text(25, "#FFFFFF", bold=True), gid)
    vertex(f"{gid}_q", q, 18, 60, CW - 30, 26, text(17, "#FFFFFF", italic=True), gid)
    vertex(f"{gid}_ex", ex, 18, 90, CW - 30, 24, text(13, LIGHT), gid)


def edge(i, src, tgt, ex, ey, nx, ny):
    cells.append(f'<mxCell id="{i}" style="endArrow=classic;endFill=1;html=1;strokeColor={BLUE};strokeWidth=2.5;'
                 f'exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;" edge="1" parent="1" source="{src}" target="{tgt}">'
                 f'<mxGeometry relative="1" as="geometry"/></mxCell>')


edge("e12", "g1", "g2", 1, 0.5, 0, 0.5)
edge("e23", "g2", "g3", 0.5, 1, 0.5, 0)
edge("e34", "g3", "g4", 0, 0.5, 1, 0.5)
edge("e41", "g4", "g1", 0.5, 0, 0.5, 1)
vertex("repeat", "repeat", OX + CW + GAPX / 2 - 36 + 0, OY + CH + GAPY / 2 - 12, 72 + 0, 24, text(15, GREY, align="center"))

xml = ('<mxfile host="app.diagrams.net"><diagram name="Classical scientific loop" id="loop">'
       '<mxGraphModel dx="1000" dy="700" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
       'page="1" pageScale="1" pageWidth="1000" pageHeight="500" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>\n'
       + "\n".join(cells) + "\n</root></mxGraphModel></diagram></mxfile>")
(Path(__file__).parent / "classical_loop.drawio").write_text(xml, encoding="utf-8")
print("wrote classical_loop.drawio")
