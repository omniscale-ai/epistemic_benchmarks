"""Builds saturation_drop.png for the slide 'Saturation and the drop when memory support is removed'.

Data: ../literature/saturation/slices.jsonl (best-model values per slice, same model within a pair).
Run: ../.venv/bin/python make_saturation_chart.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
S = [json.loads(l) for l in open(HERE / "../literature/saturation/slices.jsonl", encoding="utf-8")]


def val(bench, sl, model):
    for r in S:
        if r["type"] == "slice" and r["bench"] == bench and r["slice"] == sl:
            return r["values"][model]
    raise KeyError((bench, sl, model))


rows = [
    ("Synthetic Universes", "famous law → synthetic twin",
     val("synthetic-universes", "Famous · predictive", "Claude Code sub-agent"),
     val("synthetic-universes", "Twin · predictive", "Claude Code sub-agent")),
    ("EGA", "gene names → anonymised, no data",
     val("evidence-grounded-accuracy", "Гены названы · без данных", "Sonnet 5"),
     val("evidence-grounded-accuracy", "Гены анонимизированы · без данных", "Sonnet 5")),
    ("BioStudyBench", "with data → without data",
     val("biostudybench", "С данными и инструментами", "GPT-6 Astra"),
     val("biostudybench", "Без данных (априорное знание)", "GPT-6 Astra")),
    ("SciGame", "original → counterfactual law",
     val("scigame", "Historical · Identification · Orig", "DeepSeek-V4 Flash (Fixed)"),
     val("scigame", "Historical · Identification · CF", "DeepSeek-V4 Flash (Fixed)")),
    ("PhysGym", "priors open → hidden",
     val("physgym", "Prior L1", "Gemini-2.5-pro"), val("physgym", "Prior L4", "Gemini-2.5-pro")),
    ("SciR, induction", "natural language → obfuscated",
     val("scir", "Induction · Easy · NL", "o3-mini NS"), val("scir", "Induction · Easy · Obf", "o3-mini NS")),
    ("SciR, causal", "natural language → obfuscated",
     val("scir", "Causal · Easy · NL", "o3-mini NS"), val("scir", "Causal · Easy · Obf", "o3-mini NS")),
]
rows.sort(key=lambda r: r[2] - r[3], reverse=True)
rows = rows[::-1]  # biggest drop on top

NAVY, BLUE, RED, GREY, MUTED = "#00204D", "#008CE3", "#DB4F3D", "#B8C7DD", "#4F6D99"
fig = plt.figure(figsize=(10.6, 5.9), dpi=170, facecolor="white")
ax = fig.add_axes([0.34, 0.25, 0.63, 0.58])

for i, (b, cond, l, r) in enumerate(rows):
    ax.plot([r, l], [i, i], color=GREY, lw=6, zorder=1, solid_capstyle="round")
    ax.scatter([l], [i], s=250, color=BLUE, zorder=3)
    ax.scatter([r], [i], s=250, color=RED, zorder=3)
    ax.text(min(l, 100) + 2.8, i, f"{l:.0f}", va="center", fontsize=15, color=BLUE, fontweight="bold")
    ax.text(r - 2.8, i, f"{r:.0f}", va="center", ha="right", fontsize=15, color=RED, fontweight="bold")
    ax.text(-3, i + 0.06, b, ha="right", va="bottom", fontsize=16, color=NAVY, fontweight="bold")
    ax.text(-3, i + 0.02, cond, ha="right", va="top", fontsize=11.5, color=MUTED)
ax.set_xlim(0, 108)
ax.set_ylim(-0.7, len(rows) - 0.3)
ax.set_yticks([])
ax.set_xlabel("score, % of the scale maximum", fontsize=13, color=NAVY)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.spines["bottom"].set_color(GREY)
ax.tick_params(colors=NAVY, labelsize=12)
ax.grid(axis="x", color="#E6EBF2", zorder=0)

fig.text(0.02, 0.925, "Same model, one change: the memory support is removed", fontsize=18,
         fontweight="bold", color=NAVY)
fig.text(0.02, 0.865, "●", color=BLUE, fontsize=16)
fig.text(0.04, 0.868, "with memory support", color=NAVY, fontsize=13.5)
fig.text(0.25, 0.865, "●", color=RED, fontsize=16)
fig.text(0.27, 0.868, "without it", color=NAVY, fontsize=13.5)
fig.text(0.02, 0.02,
         "Examples chosen to cover obfuscation, hidden priors, counterfactual laws and no data; the bottom row shows\n"
         "that the drop is not universal. Scores are not comparable across rows.",
         fontsize=12, color=MUTED, linespacing=1.5)
fig.savefig(HERE / "saturation_drop.png")
for r in rows[::-1]:
    print(f"{r[0]:22s} {r[2]:5.1f} -> {r[3]:5.1f}  ({r[3]-r[2]:+.1f})")
