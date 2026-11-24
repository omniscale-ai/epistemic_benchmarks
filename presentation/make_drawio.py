#!/usr/bin/env python3
"""Export the slide-2 timeline (same geometry and texts as make_timeline.py, five stages only) to an editable .drawio file.

Cards, bars, dots and labels are separate shapes; leader lines are connectors glued to the dots and
labels, so moving a card or a label drags its line along. One file per language.
"""
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import make_timeline as mt

OX, OY = 20, 20  # canvas margin
FONT = "Helvetica"


class Doc:
    def __init__(self):
        self.cells = []
        self.n = 1

    def nid(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def vertex(self, prefix, value, x, y, w, h, style):
        i = self.nid(prefix)
        self.cells.append(
            f'<mxCell id="{i}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="1">'
            f'<mxGeometry x="{x+OX:.1f}" y="{y+OY:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry"/></mxCell>'
        )
        return i

    def edge(self, style, source=None, target=None, p0=None, p1=None):
        i = self.nid("e")
        a = f' source="{source}"' if source else ""
        b = f' target="{target}"' if target else ""
        pts = ""
        if p0:
            pts += f'<mxPoint x="{p0[0]+OX:.1f}" y="{p0[1]+OY:.1f}" as="sourcePoint"/>'
        if p1:
            pts += f'<mxPoint x="{p1[0]+OX:.1f}" y="{p1[1]+OY:.1f}" as="targetPoint"/>'
        self.cells.append(
            f'<mxCell id="{i}" style={quoteattr(style)} edge="1" parent="1"{a}{b}>'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return i

    def xml(self, name):
        body = "\n".join(self.cells)
        return (
            '<mxfile host="app.diagrams.net">'
            f'<diagram name={quoteattr(name)} id="timeline">'
            '<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
            'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1280" pageHeight="720" math="0" shadow="0">'
            f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>\n{body}\n</root></mxGraphModel></diagram></mxfile>'
        )


def text_style(size=13, color="#00204D", align="center", bold=False, italic=False, valign="middle"):
    f = (1 if bold else 0) | (2 if italic else 0)
    return (f"text;html=1;whiteSpace=wrap;fontFamily={FONT};fontSize={size};fontColor={color};align={align};"
            f"verticalAlign={valign};fontStyle={f};strokeColor=none;fillColor=none;spacing=2;")


def build(lang):
    t = mt.TXT[lang]
    d = Doc()
    W, CARD_H, GANT_Y, ROW, AXIS_Y = mt.W, mt.CARD_H, mt.GANT_Y, mt.ROW, mt.AXIS_Y
    NAVY = mt.NAVY
    xl, xr, X2021 = mt.xl, mt.xr, mt.X2021

    # axis (left part, break, right part with arrow)
    d.edge(f"endArrow=none;html=1;strokeColor={NAVY};strokeWidth=2;", p0=(20, AXIS_Y), p1=(758, AXIS_Y))
    d.edge(f"endArrow=classic;endFill=1;html=1;strokeColor={NAVY};strokeWidth=2;", p0=(X2021 - 14, AXIS_Y), p1=(W - 2, AXIS_Y))
    for dx in (764, 776):
        d.edge(f"endArrow=none;html=1;strokeColor={NAVY};strokeWidth=2;", p0=(dx, AXIS_Y - 6), p1=(dx + 8, AXIS_Y + 6))

    # ticks and year labels
    def tick(x, label, bold=False, left=False):
        d.edge(f"endArrow=none;html=1;strokeColor={NAVY};strokeWidth=1.5;", p0=(x, AXIS_Y - 4), p1=(x, AXIS_Y + 4))
        w = 50
        d.vertex("t", str(label), x - (4 if left else w / 2), AXIS_Y + 6, w, 18,
                 text_style(12, "#004381", "left" if left else "center", bold))
    for yr in (1950, 1975, 2000):
        tick(xl(yr), yr, left=(yr == 1950))
    for yr in range(2021, 2027):
        tick(xr(yr), yr, bold=True)

    # stage cards (top row)
    gap = 12
    cw = (W - 4 * gap) / 5
    card_ids = []
    for i, (name, yrs, ex, inp, outp, sc, ju) in enumerate(t["stages"]):
        body = "<br><br>".join(f'<b>{escape(t[k])}</b>{escape(v)}' for k, v in
                               (("k_in", inp), ("k_out", outp), ("k_sc", sc), ("k_ju", ju)))
        val = (f'<b>{i+1} · {escape(name)}</b><br><font style="font-size:12px" color="#004381">{escape(yrs)}</font>'
               f'<br><i><font color="#004381">{escape(ex)}</font></i><br><br><font style="font-size:13px">{body}</font>')
        style = (f"rounded=1;arcSize=4;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontFamily={FONT};fontSize=14;"
                 f"fontColor={NAVY};fillColor=#F9F9F9;strokeColor={mt.STAGE_COL[i]};strokeWidth=2;spacingLeft=8;spacingTop=6;spacingRight=6;")
        card_ids.append(d.vertex("card", val, i * (cw + gap), 0, cw, CARD_H, style))

    # period bars + dots + leaders to cards
    spans = mt.SPANS
    for i, (a, b) in enumerate(spans):
        y = GANT_Y + (4 - i) * ROW
        h = ROW - 4
        txt = f"{i+1}"
        d.vertex("bar", txt, a, y, b - a, h,
                 f"rounded=1;arcSize=30;html=1;fontFamily={FONT};fontSize=11;fontStyle=1;align=right;spacingRight=8;"
                 f"fillColor={mt.STAGE_COL[i]};strokeColor=none;fontColor={mt.STAGE_TXT[i]};")
        dot = d.vertex("dot", "", a + 4, y + (h - 8) / 2, 8, 8, "ellipse;html=1;fillColor=#FFFFFF;strokeColor=none;")
        d.edge(f"endArrow=none;html=1;strokeColor={mt.STAGE_COL[i]};strokeWidth=1.3;strokeOpacity=75;"
               "entryX=0.5;entryY=1;entryDx=0;entryDy=0;", source=dot, target=card_ids[i])

    return d.xml("Slide 2: " + lang)


if __name__ == "__main__":
    here = Path(__file__).parent
    for lang in ("en", "ru"):
        out = here / f"slide2_timeline_v2_{lang}.drawio"
        out.write_text(build(lang), encoding="utf-8")
        print("wrote", out.name)
