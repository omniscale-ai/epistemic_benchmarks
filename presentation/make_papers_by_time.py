#!/usr/bin/env python3
"""Chart: number of discovery papers (71 in the atlas) by arXiv submission month. Writes SVG and PNG.

Source: literature/classification/benchmark_classification.json (papers with a defined answer depth A2_max).
Month comes from the arXiv id (YYMM). Papers without an arXiv id are omitted (counted in the caption).
Rendering: SVG built here, PNG via headless Chrome (bundled with Quarto).
"""
import collections
import json
import os
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parent / "literature" / "classification" / "benchmark_classification.json"
CH = os.environ.get("CHROME", str(Path.home() / ".local/share/quarto/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell"))
LAST_MONTH = "2611"  # data collected 17 Nov 2026: this month is partial

W, H = 1168, 470
L, R, T, B = 68, 16, 40, 78
BLUE, NAVY, CONF, GRID = "#008CE3", "#00204D", "#004381", "#E3E8F0"

papers = [j for j in json.loads(SRC.read_text()) if j.get("A2_max") and str(j["A2_max"]) not in ("", "?", "n/a")]
counts, early, no_id = collections.Counter(), 0, 0
for j in papers:
    a = (j.get("arxiv") or "").strip()
    if not a[:4].isdigit():
        no_id += 1
        continue
    m = a[:4]
    if m < "2401":
        early += 1
    else:
        counts[m] += 1
months = [f"{y}{mm:02d}" for y in (24, 25, 26) for mm in range(1, 13) if f"{y}{mm:02d}" <= LAST_MONTH]
total = early + sum(counts.values())
peak = max(counts.values())
top2 = sorted(counts.values())[-2:]

# slots: 0 = early bucket, 1 = gap (axis break), then months
slots = 2 + len(months)
pw, ph = W - L - R, H - T - B
sw = pw / slots
YMAX = 16.5


def X(i):
    return L + i * sw


def Y(v):
    return T + ph - v / YMAX * ph


def bar(i, v, partial=False):
    x, w = X(i) + sw * 0.18, sw * 0.64
    y0, y1, r = Y(0), Y(v), min(4, w / 2)
    h = y0 - y1
    if h <= r:
        r = max(h / 2, 0)
    path = f"M{x:.1f},{y0:.1f} V{y1+r:.1f} Q{x:.1f},{y1:.1f} {x+r:.1f},{y1:.1f} H{x+w-r:.1f} Q{x+w:.1f},{y1:.1f} {x+w:.1f},{y1+r:.1f} V{y0:.1f} Z"
    if partial:
        return f'<path d="{path}" fill="url(#hatch)" stroke="{BLUE}" stroke-width="1.5"/>'
    return f'<path d="{path}" fill="{BLUE}"/>'


svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Liberation Sans, Arial, Helvetica, sans-serif">')
svg.append(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff"/><line x1="0" y1="0" x2="0" y2="6" stroke="{BLUE}" stroke-width="2.5"/></pattern></defs>')
svg.append(f'<rect width="{W}" height="{H}" fill="#fff"/>')
# grid + y labels
for v in (0, 5, 10, 15):
    y = Y(v)
    svg.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{GRID if v else CONF}" stroke-width="{1 if v else 1.5}"/>')
    svg.append(f'<text x="{L-10}" y="{y+4:.1f}" font-size="13" text-anchor="end" fill="{CONF}">{v}</text>')
svg.append(f'<text x="{L-48}" y="{T+ph/2:.1f}" font-size="13" fill="{CONF}" text-anchor="middle" transform="rotate(-90 {L-48} {T+ph/2:.1f})">papers per month</text>')
# bars
svg.append(bar(0, early))
for k, m in enumerate(months):
    v = counts.get(m, 0)
    if v:
        svg.append(bar(2 + k, v, partial=(m == LAST_MONTH)))
# axis break between the early bucket and 2024
bx = X(1) + sw / 2
for dx in (-4, 4):
    svg.append(f'<line x1="{bx+dx-3:.1f}" y1="{Y(0)+6:.1f}" x2="{bx+dx+3:.1f}" y2="{Y(0)-6:.1f}" stroke="{NAVY}" stroke-width="2"/>')
# x labels: early bucket, quarter starts, years
svg.append(f'<text x="{X(0)+sw/2:.1f}" y="{Y(0)+20:.1f}" font-size="12" text-anchor="middle" fill="{CONF}">2019–23</text>')
for k, m in enumerate(months):
    cx = X(2 + k) + sw / 2
    mm = int(m[2:])
    if mm in (1, 4, 7, 10):
        name = ["Jan", "Apr", "Jul", "Oct"][(mm - 1) // 3]
        svg.append(f'<line x1="{cx:.1f}" y1="{Y(0)}" x2="{cx:.1f}" y2="{Y(0)+5}" stroke="{NAVY}" stroke-width="1.2"/>')
        svg.append(f'<text x="{cx:.1f}" y="{Y(0)+20:.1f}" font-size="12" text-anchor="middle" fill="{CONF}">{name}</text>')
    if mm == 1:
        svg.append(f'<text x="{cx-sw*0.5:.1f}" y="{Y(0)+40:.1f}" font-size="14" font-weight="700" text-anchor="start" fill="{NAVY}">20{m[:2]}</text>')
# selective direct labels: the two peak months and the partial month
for k, m in enumerate(months):
    v = counts.get(m, 0)
    if v in top2 or m == LAST_MONTH:
        cx = X(2 + k) + sw / 2
        label = f"{v}" + ("*" if m == LAST_MONTH else "")
        svg.append(f'<text x="{cx:.1f}" y="{Y(v)-7:.1f}" font-size="14" font-weight="700" text-anchor="middle" fill="{NAVY}">{label}</text>')
svg.append(f'<text x="{X(0)+sw/2:.1f}" y="{Y(early)-7:.1f}" font-size="14" font-weight="700" text-anchor="middle" fill="{NAVY}">{early}</text>')
# title + caption
svg.append(f'<text x="{L}" y="22" font-size="17" font-weight="700" fill="{NAVY}">Discovery benchmark papers by arXiv month, n = {total}</text>')
cap = (f"* November 2026 is partial (data to 17 Nov). The two peak months hold {sum(top2)} of {total} papers "
       f"({sum(top2)/total:.0%}). {no_id} paper without an arXiv id omitted.")
svg.append(f'<text x="{L}" y="{H-8}" font-size="12.5" fill="{CONF}">{cap}</text>')
svg.append("</svg>")
svg_text = "\n".join(svg)

(HERE / "papers_by_time.svg").write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg_text)
with tempfile.TemporaryDirectory() as td:
    page = Path(td) / "p.html"
    page.write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#fff}}</style>{svg_text}')
    subprocess.run([CH, "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={W},{H}", f"--screenshot={HERE/'papers_by_time.png'}", f"file://{page}"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
print(f"n={total} (early {early}, no id {no_id}), peak {peak}, top2 {top2}; wrote papers_by_time.svg/png")
