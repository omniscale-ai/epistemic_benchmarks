#!/usr/bin/env python3
"""Editable draw.io source: the classical loop with an LLM agent inside it (generic, not tied to a specific task).

Writes agent_loop.drawio. Same four navy stages as classical_loop.drawio; each card gets a yellow
"Agent:" line saying what the agent does at that stage; a yellow pill in the centre is the agent itself.
PNG: render with the draw.io viewer in headless Chrome and crop (see the commands in the chat / deck notes).
"""
from pathlib import Path
from xml.sax.saxutils import quoteattr

NAVY, BLUE, LIGHT, YELLOW = "#00204D", "#008CE3", "#B8C7DD", "#FFC622"
OX, OY = 40, 40
CW, CH = 330, 154
GAPX, GAPY = 170, 90
STAGES = [
    ("1", "Context", "What do we already know?", "e.g. literature, data, earlier results",
     "reads the task, data and memory", 0, 0),
    ("2", "Hypothesis", "What could explain it?", "e.g. candidate laws, mechanisms, entities",
     "the LLM proposes explanations", 1, 0),
    ("3", "Experiment", "How do we test it?", "e.g. a simulation, a measurement, a lab run",
     "calls tools, acts in the environment", 1, 1),
    ("4", "Evidence", "What did we learn?", "e.g. fits, residuals, ranked explanations",
     "analyses results, updates memory", 0, 1),
]
cells = []


def vertex(i, value, x, y, w, h, style, parent="1"):
    cells.append(f'<mxCell id="{i}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="{parent}">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def text(size, color, bold=False, italic=False, align="left"):
    return (f"text;html=1;whiteSpace=wrap;fontFamily=Helvetica;fontSize={size};fontColor={color};align={align};"
            f"verticalAlign=middle;fontStyle={(1 if bold else 0) | (2 if italic else 0)};strokeColor=none;fillColor=none;spacing=0;")


for n, title, q, ex, ag, cx, cy in STAGES:
    gid = f"g{n}"
    x, y = OX + cx * (CW + GAPX), OY + cy * (CH + GAPY)
    cells.append(f'<mxCell id="{gid}" value="" style="group;" vertex="1" connectable="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{CW}" height="{CH}" as="geometry"/></mxCell>')
    vertex(f"{gid}_card", "", 0, 0, CW, CH, f"rounded=1;arcSize=6;html=1;fillColor={NAVY};strokeColor=none;", gid)
    vertex(f"{gid}_num", n, 18, 16, 34, 34, f"ellipse;html=1;fillColor={BLUE};strokeColor=none;fontColor=#FFFFFF;fontSize=17;fontStyle=1;fontFamily=Helvetica;", gid)
    vertex(f"{gid}_title", title, 64, 14, 240, 38, text(25, "#FFFFFF", bold=True), gid)
    vertex(f"{gid}_q", q, 18, 60, CW - 30, 26, text(17, "#FFFFFF", italic=True), gid)
    vertex(f"{gid}_ex", ex, 18, 88, CW - 30, 22, text(13, LIGHT), gid)
    vertex(f"{gid}_line", "", 18, 116, CW - 36, 1, f"rounded=0;html=1;fillColor={YELLOW};strokeColor=none;opacity=60;", gid)
    vertex(f"{gid}_ag", f"<b>Agent:</b> {ag}", 18, 120, CW - 30, 28, text(14, YELLOW), gid)


def edge(i, src, tgt, ex, ey, nx, ny):
    cells.append(f'<mxCell id="{i}" style="endArrow=classic;endFill=1;html=1;strokeColor={BLUE};strokeWidth=2.5;'
                 f'exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;" edge="1" parent="1" source="{src}" target="{tgt}">'
                 f'<mxGeometry relative="1" as="geometry"/></mxCell>')


edge("e12", "g1", "g2", 1, 0.3, 0, 0.3)
edge("e23", "g2", "g3", 0.5, 1, 0.5, 0)
edge("e34", "g3", "g4", 0, 0.7, 1, 0.7)
edge("e41", "g4", "g1", 0.5, 0, 0.5, 1)
# the agent in the centre: a yellow card with the robot icon (embedded SVG, source: robot_transparent_vector.svg)
import base64
ICON = base64.b64encode((Path(__file__).parent / "robot_transparent_vector.svg").read_bytes()).decode()
AW, AH = 150, 196
ax = OX + CW + GAPX / 2 - AW / 2
ay = OY + (2 * CH + GAPY) / 2 - AH / 2
cells.append(f'<mxCell id="agent" value="" style="group;" vertex="1" connectable="1" parent="1">'
             f'<mxGeometry x="{ax}" y="{ay}" width="{AW}" height="{AH}" as="geometry"/></mxCell>')
vertex("agent_card", "", 0, 0, AW, AH, f"rounded=1;arcSize=12;html=1;fillColor={YELLOW};strokeColor=none;", "agent")
vertex("agent_icon", "", 17, 10, 116, 116,
       f"shape=image;html=1;imageAspect=1;aspect=fixed;verticalLabelPosition=bottom;image=data:image/svg+xml,{ICON};", "agent")
vertex("agent_name", "LLM agent", 5, 128, AW - 10, 28, text(20, NAVY, bold=True, align="center"), "agent")
vertex("agent_sub", "LLM + memory + tools", 5, 158, AW - 10, 28, text(13, NAVY, align="center"), "agent")

xml = ('<mxfile host="app.diagrams.net"><diagram name="Agent in the loop" id="agentloop">'
       '<mxGraphModel dx="1000" dy="700" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
       'page="1" pageScale="1" pageWidth="1100" pageHeight="600" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>\n'
       + "\n".join(cells) + "\n</root></mxGraphModel></diagram></mxfile>")
(Path(__file__).parent / "agent_loop.drawio").write_text(xml, encoding="utf-8")
print("wrote agent_loop.drawio")
