#!/usr/bin/env python3
"""Add a native (editable) bar chart to slide2_timeline_v2_en.drawio, x-aligned with its time axis.

Bars are calendar years (width = the year's span on the axis above, so they stay in sync with the ticks).
All chart shapes sit in one group.
Idempotent: removes the embedded PNG (if any) and an earlier chart group before adding.
Only the chart cells are touched; the rest of the file (your edits) is left as is.
"""
import collections
import json
import re
import sys
from pathlib import Path

import make_timeline as mt

HERE = Path(__file__).parent
FILE = HERE / "slide2_timeline_v2_en.drawio"
SRC = HERE.parent / "literature" / "classification" / "benchmark_classification.json"
OFF = 20  # canvas offset used by make_drawio.py (axis ticks: x = mt.x + OFF)
NAVY, CONF, BLUE, LIGHT, GRID = "#00204D", "#004381", "#008CE3", "#99D1F4", "#E3E8F0"
BASE_Y, UNIT, VMAX = 680, 2.4, 60  # baseline y, px per paper, top gridline value
GX, GY, GW, GH = 0, 500, 1200, 214  # group box (absolute)

# ---- data ------------------------------------------------------------------
papers = [j for j in json.loads(SRC.read_text()) if j.get("A2_max") and str(j["A2_max"]) not in ("", "?", "n/a")]
yearly = collections.Counter()
no_id = 0
for j in papers:
    a = (j.get("arxiv") or "").strip()
    if a[:4].isdigit():
        yearly[2000 + int(a[:2])] += 1
    elif str(j.get("year") or "").isdigit():  # no arXiv id: use the year given in the classification
        yearly[int(j["year"])] += 1
        no_id += 1
    else:
        no_id += 1
total = sum(yearly.values())
PARTIAL = 2026  # data to 23 Nov 2026

# ---- cells -----------------------------------------------------------------
cells = []
n = [0]


def nid():
    n[0] += 1
    return f"pc_{n[0]}"


def rel(x, y):
    return x - GX, y - GY


def vertex(value, x, y, w, h, style):
    rx, ry = rel(x, y)
    i = nid()
    from xml.sax.saxutils import quoteattr
    cells.append(f'                <mxCell id="{i}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="pc_group">'
                 f'<mxGeometry x="{rx:.1f}" y="{ry:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry"/></mxCell>')


def line(x1, y1, x2, y2, style):
    i = nid()
    from xml.sax.saxutils import quoteattr
    (a, b), (c, d) = rel(x1, y1), rel(x2, y2)
    cells.append(f'                <mxCell id="{i}" style={quoteattr(style)} edge="1" parent="pc_group">'
                 f'<mxGeometry relative="1" as="geometry"><mxPoint x="{a:.1f}" y="{b:.1f}" as="sourcePoint"/>'
                 f'<mxPoint x="{c:.1f}" y="{d:.1f}" as="targetPoint"/></mxGeometry></mxCell>')


def tstyle(size=12, color=CONF, align="center", bold=False, extra=""):
    return (f"text;html=1;whiteSpace=wrap;fontFamily=Helvetica;fontSize={size};fontColor={color};align={align};"
            f"verticalAlign=middle;fontStyle={1 if bold else 0};strokeColor=none;fillColor=none;spacing=0;{extra}")


def X(year):  # year is a float, e.g. 2024.25
    return (mt.xl(year) if year < 2021 else mt.xr(year)) + OFF


def Yv(v):
    return BASE_Y - v * UNIT


AX0, AX1 = 40, 1186  # axis extent
# horizontal grid + labels
for v in (20, 40, 60):
    line(AX0, Yv(v), AX1, Yv(v), f"endArrow=none;html=1;strokeColor={GRID};strokeWidth=1;")
for v in (0, 20, 40, 60):
    vertex(str(v), AX0 - 34, Yv(v) - 9, 28, 18, tstyle(12, CONF, "right"))
# guides from the time-axis ticks down to the baseline (this is what ties the chart to the axis)
for yr in (1975, 2000, 2021, 2022, 2023, 2024, 2025, 2026):
    x = X(yr)
    line(x, 500, x, BASE_Y, f"endArrow=none;html=1;strokeColor={GRID};strokeWidth=1;dashed=1;dashPattern=2 3;")
line(AX0, BASE_Y, AX1, BASE_Y, f"endArrow=none;html=1;strokeColor={NAVY};strokeWidth=1.5;")


def bar(x0, x1, v, label=None, partial=False):
    w = max(x1 - x0 - 4, 2)
    style = (f"rounded=1;absoluteArcSize=1;arcSize=5;html=1;strokeColor={BLUE};strokeWidth={1.5 if partial else 0};dashed={1 if partial else 0};"
             f"fillColor={LIGHT if partial else BLUE};")
    vertex("", x0 + 2, Yv(v), w, v * UNIT, style)
    if label:
        vertex(label, x0 + 2 + w / 2 - 20, Yv(v) - 20, 40, 18, tstyle(13, NAVY, "center", True))


for yr, v in sorted(yearly.items()):
    bar(X(yr), X(yr + 1), v, label=f"{v}" + ("*" if yr == PARTIAL else ""), partial=(yr == PARTIAL))
# title and caption
vertex(f"Discovery benchmark papers per year, n = {total}", 50, 548, 420, 20,
       tstyle(14, NAVY, "left", True, "labelBackgroundColor=#FFFFFF;"))
vertex(f"* 2026 is year to date (data to 23 Nov). Bar width = the year's span on the time axis above (2011 and 2019 sit on the compressed part). "
       f"{no_id} papers without an arXiv id are placed by the year in the classification.", AX0, BASE_Y + 8, 1146, 20, tstyle(11, CONF, "left"))

group = (f'                <mxCell id="pc_group" value="" style="group;" vertex="1" connectable="0" parent="1">'
         f'<mxGeometry x="{GX}" y="{GY}" width="{GW}" height="{GH}" as="geometry"/></mxCell>')

s = FILE.read_text(encoding="utf-8")
s = re.sub(r'[ \t]*<mxCell id="chart_papers_by_time".*?</mxCell>\n', "", s, flags=re.S)  # embedded PNG
s = re.sub(r'[ \t]*<mxCell id="pc_[^"]*".*?</mxCell>\n?', "", s, flags=re.S)
i = s.rindex("</root>")
# keep the closing tag's indentation
j = s.rfind("\n", 0, i) + 1
s = s[:j] + group + "\n" + "\n".join(cells) + "\n" + s[j:]
FILE.write_text(s, encoding="utf-8")
print("yearly:", dict(sorted(yearly.items())), "n =", total)
