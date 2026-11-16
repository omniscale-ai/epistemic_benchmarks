"""Build the data fragments of the episode report (report/episode/episode_report.qmd).

Run from the repository root (after `cli evaluate` / `cli aggregate`):

    PYTHONPATH=src .venv/bin/python report/episode/make_report.py [--runs-root runs_episode]
    quarto render report/episode/episode_report.qmd

Writes, next to this script:
- _anim_world.html    decay world: events, spectrum vs thickness, calorimeter (both mechanisms, same seed)
- _anim_episode.html  step-by-step replay of real agent episodes (A -> B -> C -> D)
- _charts.html        hidden check per episode vs anchors; carrier mass agent vs truth
- _tables.md          episode table and baseline table (markdown, no code execution at render time)
- _kpi.md             headline numbers

Agent models are re-run only inside the bwrap sandbox (via the episode Model wrapper).
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np

from abductbench.episode import baselines as bl
from abductbench.episode import physics as ph
from abductbench.episode.cli import collect_runs
from abductbench.episode.protocol import Session, load_session
from abductbench.episode.world import HIDDEN_CHECK, EpisodeConfig, World

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#8a8f98"
SPEC_EDGES = np.linspace(0.1, 1.3, 49)
CAL_EDGES = np.linspace(-0.1, 1.25, 55)
THICK = (0.25, 0.5, 1.0, 2.0, 3.0)

CSS = """
<style>
.vz { border: 1px solid rgba(127,127,127,.3); border-radius: .6rem; padding: .8rem; margin: 1rem 0 1.6rem; }
.vz svg { width: 100%; height: auto; display: block; color: var(--bs-body-color, #222); }
.vz .vz-bar { display: flex; flex-wrap: wrap; gap: .5rem 1.1rem; align-items: center; font-size: .88rem; margin: 0 0 .6rem; }
.vz .vz-bar label { display: inline-flex; align-items: center; gap: .35rem; }
.vz .vz-bar button, .vz .vz-seg button, .vz select { font: inherit; padding: .2rem .7rem; border: 1px solid rgba(127,127,127,.5); border-radius: .35rem; background: transparent; color: inherit; cursor: pointer; }
.vz select option { color: #222; }
.vz .vz-seg { display: inline-flex; }
.vz .vz-seg button { border-radius: 0; margin-left: -1px; }
.vz .vz-seg button:first-child { border-radius: .35rem 0 0 .35rem; margin-left: 0; }
.vz .vz-seg button:last-child { border-radius: 0 .35rem .35rem 0; }
.vz .vz-seg button[aria-pressed=true] { background: rgba(127,127,127,.25); font-weight: 600; }
.vz .vz-note { font-size: .84rem; opacity: .8; margin: .5rem 0 0; }
.vz .vz-grid { display: grid; grid-template-columns: 1fr; gap: .6rem; }
@media (min-width: 760px) { .vz .vz-grid.two { grid-template-columns: 1.1fr 1fr; } }
.vz text { fill: currentColor; font-family: inherit; }
.vz .tick { stroke: currentColor; opacity: .18; }
.vz-readout { font-size: .85rem; font-variant-numeric: tabular-nums; line-height: 1.45; }
.vz-steps { display: flex; flex-wrap: wrap; gap: .25rem; margin: .2rem 0 .5rem; }
.vz-steps button { font: inherit; font-size: .8rem; padding: .1rem .55rem; border: 1px solid rgba(127,127,127,.45); border-radius: 1rem; background: transparent; color: inherit; cursor: pointer; }
.vz-steps button[aria-current=true] { background: #2a78d6; color: #fff; border-color: #2a78d6; }
.vz-hyp { display: grid; grid-template-columns: 2.6rem 1fr 3.2rem; gap: .2rem .5rem; align-items: center; font-size: .84rem; margin: .15rem 0; }
.vz-hyp .bar { height: .7rem; border-radius: .2rem; transition: width .5s ease; }
.vz-hyp .st { grid-column: 2 / 4; opacity: .75; font-size: .8rem; margin-top: -.15rem; }
.vz-pill { display: inline-block; font-size: .75rem; padding: 0 .45rem; border-radius: .7rem; border: 1px solid currentColor; margin-left: .3rem; }
.vz-good { color: #16a34a; } .vz-bad { color: #dc2626; } .vz-weak { color: #a16207; }
</style>
"""

# ---------------------------------------------------------------------------------------------
# 1. Decay world animation
# ---------------------------------------------------------------------------------------------

WORLD_HTML = r"""
<div class="vz" id="vz-world">
  <div class="vz-bar">
    <span class="vz-seg" role="group" aria-label="Скрытая причина">
      <button type="button" data-mech="carrier" aria-pressed="true">Невидимый носитель</button>
      <button type="button" data-mech="loss" aria-pressed="false">Потери в источнике (T0 верна)</button>
    </span>
    <span class="vz-seg" role="group" aria-label="Прибор">
      <button type="button" data-ins="spectrum" aria-pressed="true">Спектрометр</button>
      <button type="button" data-ins="calorimeter" aria-pressed="false">Калориметр</button>
    </span>
    <label id="vzw-tlab">толщина источника <input type="range" id="vzw-t" min="0" max="4" step="1" value="2"> <span id="vzw-tv">t = 1</span></label>
    <button type="button" id="vzw-play">Пауза</button>
    <label><input type="checkbox" id="vzw-other" checked> контур другого мира</label>
  </div>
  <div class="vz-grid two">
    <svg id="vzw-scene" viewBox="0 0 460 320" role="img" aria-label="Один распад: импульсы и потеря энергии в источнике"></svg>
    <div>
      <svg id="vzw-hist" viewBox="0 0 420 300" role="img" aria-label="Распределение измеряемой энергии"></svg>
      <div class="vz-readout" id="vzw-read"></div>
    </div>
  </div>
  <p class="vz-note">Данные — настоящий генератор (мир <b>__SEED__</b>, одинаковые публичные массы и Q у обоих механизмов). Слева — отдельный распад: синяя стрелка — лёгкая частица при вылете, её «хвост» внутри слоя — потеря энергии в источнике, серая — отдача ядра, <b>пунктир</b> — импульс, которого не хватает до нуля (его уносит невидимый носитель). Справа — точное распределение, которое увидит прибор (столбцы — выбранный мир, контур — другой мир). При t = 1 спектрометр почти не различает миры; калориметр и смена толщины различают сразу.</p>
</div>
<script>
(function () {
  const D = __DATA__;
  const root = document.getElementById('vz-world'), $ = (id) => document.getElementById(id), NS = 'http://www.w3.org/2000/svg';
  const BLUE = '#2a78d6', ORANGE = '#eb6834';
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  let mech = 'carrier', ins = 'spectrum', ti = 2, idx = 0, phase = 0, playing = true, visible = true, last = null, other = true;
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) playing = false;
  const scene = $('vzw-scene'), hist = $('vzw-hist');
  const col = () => mech === 'carrier' ? BLUE : ORANGE;

  function drawScene(f) {
    scene.innerHTML = '';
    const ev = D[mech].events[idx % D[mech].events.length];
    const [Te, Ta, p1, p3, ang, dep] = ev;
    const W = 460, cx = 150, cy = 165, S = 95;
    // source slab
    el('rect', { x: cx - 18, y: 40, width: 36, height: 250, fill: 'currentColor', opacity: 0.08 }, scene);
    const sl = el('text', { x: cx, y: 32, 'text-anchor': 'middle', 'font-size': 11 }, scene); sl.textContent = 'источник (t = 1)';
    el('circle', { cx, cy, r: 5, fill: 'currentColor' }, scene);
    const k = Math.min(1, f * 1.4);
    // light particle at emission (direction +x)
    const L1 = S * p1 * k;
    el('line', { x1: cx, y1: cy, x2: cx + L1, y2: cy, stroke: col(), 'stroke-width': 3, 'stroke-linecap': 'round' }, scene);
    // after the slab: remaining kinetic energy shown as a second arrow beyond the slab
    if (f > 0.5) {
      const pa = Ta < 0 ? 0 : Math.sqrt(Ta * (Ta + 2 * D.m_light));
      const x0 = cx + 26, L2 = S * pa * Math.min(1, (f - 0.5) * 2.5);
      if (Ta < 0) { const t = el('text', { x: x0 + 4, y: cy - 10, 'font-size': 11, fill: ORANGE }, scene); t.textContent = 'остановилась в источнике'; }
      else el('line', { x1: x0, y1: cy + 18, x2: x0 + L2, y2: cy + 18, stroke: col(), 'stroke-width': 2, 'stroke-dasharray': '1 0', opacity: 0.55 }, scene);
    }
    // recoil
    const rx = Math.cos(ang) * S * p3 * k, ry = -Math.sin(ang) * S * p3 * k;
    el('line', { x1: cx, y1: cy, x2: cx + rx, y2: cy + ry, stroke: 'currentColor', 'stroke-width': 3, opacity: 0.55, 'stroke-linecap': 'round' }, scene);
    // missing momentum = -(p1 + p3)
    const mx = -(L1 + rx), my = -ry;
    if (Math.hypot(mx, my) > 2) el('line', { x1: cx, y1: cy, x2: cx + mx, y2: cy + my, stroke: col(), 'stroke-width': 2, 'stroke-dasharray': '5 4' }, scene);
    const lab = (x, y, s, c) => { const t = el('text', { x, y, 'font-size': 11, fill: c || 'currentColor' }, scene); t.textContent = s; };
    lab(cx + L1 + 6, cy + 4, 'частица', col());
    lab(cx + rx + (rx < 0 ? -50 : 6), cy + ry + (ry < 0 ? -4 : 12), 'отдача');
    if (Math.hypot(mx, my) > 12) lab(cx + mx + (mx < 0 ? -64 : 6), cy + my + 12, 'не хватает', col());
    // energy bars
    const bx = 330, bw = 110, by = 60;
    const bars = [['при вылете', Te], ['спектрометр', Ta < 0 ? 0 : Ta], ['калориметр', dep]];
    bars.forEach((b, i) => {
      const y = by + i * 62;
      lab(bx, y, b[0]);
      el('rect', { x: bx, y: y + 6, width: bw, height: 12, fill: 'none', stroke: 'currentColor', 'stroke-opacity': 0.4 }, scene);
      el('rect', { x: bx, y: y + 6, width: Math.max(0, Math.min(1.2, b[1])) / 1.2 * bw, height: 12, fill: col(), opacity: 0.8 }, scene);
      el('line', { x1: bx + bw / 1.2, x2: bx + bw / 1.2, y1: y + 3, y2: y + 21, stroke: 'currentColor', 'stroke-width': 1.5 }, scene);
      lab(bx + bw + 4, y + 17, (b[1]).toFixed(2));
    });
    lab(bx, by + 190, 'вертикальная черта: Q');
    lab(10, 300, 'распад ' + (idx % D[mech].events.length + 1) + ' (энергии в единицах Q)');
  }

  function drawHist() {
    hist.innerHTML = '';
    const W = 420, H = 300, L = 40, R = 10, T = 16, B = 38;
    const isS = ins === 'spectrum', edges = isS ? D.spec_edges : D.cal_edges;
    const cur = isS ? D[mech].spec[ti] : D[mech].cal, oth = isS ? D[mech === 'carrier' ? 'loss' : 'carrier'].spec[ti] : D[mech === 'carrier' ? 'loss' : 'carrier'].cal;
    const nb = cur.length, x0 = edges[0], x1 = edges[nb];
    const mx = Math.max(Math.max.apply(null, cur), other ? Math.max.apply(null, oth) : 0) * 1.1;
    const X = (v) => L + (v - x0) / (x1 - x0) * (W - L - R), Y = (v) => T + (1 - v / mx) * (H - T - B);
    for (let b = 0; b < nb; b++) el('rect', { x: X(edges[b]) + 0.5, y: Y(cur[b]), width: X(edges[b + 1]) - X(edges[b]) - 1, height: (H - B) - Y(cur[b]), fill: col(), opacity: 0.75 }, hist);
    if (other) { const pts = []; for (let b = 0; b < nb; b++) { pts.push(X(edges[b]).toFixed(1) + ',' + Y(oth[b]).toFixed(1)); pts.push(X(edges[b + 1]).toFixed(1) + ',' + Y(oth[b]).toFixed(1)); } el('polyline', { points: pts.join(' '), fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5, opacity: 0.8 }, hist); }
    for (let v = Math.ceil(x0 * 5) / 5; v <= x1 + 1e-9; v += 0.2) { el('line', { x1: X(v), x2: X(v), y1: H - B, y2: H - B + 4, stroke: 'currentColor', opacity: 0.5 }, hist); const t = el('text', { x: X(v), y: H - B + 16, 'text-anchor': 'middle', 'font-size': 10 }, hist); t.textContent = v.toFixed(1); }
    el('line', { x1: X(1), x2: X(1), y1: T, y2: H - B, stroke: 'currentColor', 'stroke-dasharray': '3 3', opacity: 0.6 }, hist);
    const q = el('text', { x: X(1) + 3, y: T + 10, 'font-size': 10 }, hist); q.textContent = 'Q';
    const xl = el('text', { x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 11 }, hist);
    xl.textContent = isS ? 'энергия частицы на спектрометре / Q' : 'энергия в калориметре за распад / Q';
    const yl = el('text', { x: 12, y: (T + H - B) / 2, 'text-anchor': 'middle', 'font-size': 11, transform: 'rotate(-90 12 ' + (T + H - B) / 2 + ')' }, hist); yl.textContent = 'доля событий';
    const kl = isS ? D.kl_spec[ti] : D.kl_cal;
    $('vzw-read').innerHTML = (isS ? 'Спектр при t = ' + D.thick[ti] : 'Калориметр') + ': ожидаемый log Bayes factor на 400 событиях между мирами ≈ <b>' + (kl * 400 < 10 ? (kl * 400).toFixed(1) : Math.round(kl * 400)) + '</b> нат ' + (kl * 400 < 3 ? '(не различает)' : '(различает)') + '.';
  }

  function frame(ts) {
    if (last === null) last = ts;
    const dt = Math.min(0.1, (ts - last) / 1000); last = ts;
    if (playing && visible) { phase += dt * 0.8; if (phase >= 1) { phase = 0; idx++; } drawScene(phase); }
    requestAnimationFrame(frame);
  }
  root.querySelectorAll('[data-mech]').forEach((b) => b.addEventListener('click', () => { mech = b.dataset.mech; root.querySelectorAll('[data-mech]').forEach((x) => x.setAttribute('aria-pressed', x === b)); drawHist(); drawScene(1); }));
  root.querySelectorAll('[data-ins]').forEach((b) => b.addEventListener('click', () => { ins = b.dataset.ins; root.querySelectorAll('[data-ins]').forEach((x) => x.setAttribute('aria-pressed', x === b)); $('vzw-tlab').style.opacity = ins === 'spectrum' ? 1 : 0.35; drawHist(); }));
  $('vzw-t').addEventListener('input', (e) => { ti = +e.target.value; $('vzw-tv').textContent = 't = ' + D.thick[ti]; drawHist(); });
  $('vzw-other').addEventListener('change', (e) => { other = e.target.checked; drawHist(); });
  $('vzw-play').addEventListener('click', () => { playing = !playing; $('vzw-play').textContent = playing ? 'Пауза' : 'Играть'; });
  if (reduce) $('vzw-play').textContent = 'Играть';
  if ('IntersectionObserver' in window) new IntersectionObserver((es) => { visible = es[0].isIntersecting; }, { threshold: 0.05 }).observe(root);
  drawHist(); drawScene(1); requestAnimationFrame(frame);
})();
</script>
"""


def _rebin(probs: np.ndarray, edges: np.ndarray) -> list[float]:
    cdf = np.concatenate([[0.0], np.cumsum(probs)])
    c = np.interp(edges, ph.EDGES, cdf)
    return [float(x) for x in np.diff(c)]


def _kl(p, q) -> float:
    p, q = np.maximum(np.asarray(p), 1e-12), np.maximum(np.asarray(q), 1e-12)
    p, q = p / p.sum(), q / q.sum()
    return float(0.5 * (np.sum(p * np.log(p / q)) + np.sum(q * np.log(q / p))))


def world_data(seed: int) -> dict:
    out: dict = {"thick": list(THICK), "spec_edges": SPEC_EDGES.tolist(), "cal_edges": CAL_EDGES.tolist()}
    for mech in ("carrier", "loss"):
        w = World(EpisodeConfig(seed, mech))
        kin, h = w.kin, w.truth
        rng = np.random.default_rng([seed, 5])
        n = 160
        if h.decay == "carrier":
            T1, p3, T3 = ph.decay_carrier(kin, h.m_x, n, rng)
            p1 = kin.p_light(T1)
            E2 = 1.0 - T1 - T3
            p2sq = np.maximum(E2**2 - h.m_x**2, 0.0)
            cos13 = np.clip((p2sq - p1**2 - p3**2) / (2 * p1 * p3 + 1e-12), -1, 1)
            ang = np.arccos(cos13) * np.where(rng.random(n) < 0.5, 1, -1)
        else:
            T1, p3, T3 = ph.decay_two_body(kin, n)
            p1 = kin.p_light(T1)
            ang = np.full(n, math.pi)
        Ta = T1 - ph.transport_loss(h.material, 1.0, n, rng)
        Ta = np.where(Ta > 0, Ta, -1.0)
        dep = T1 + T3
        out[mech] = {
            "events": [[round(float(a), 4) for a in row] for row in zip(T1, Ta, p1, p3, ang, dep)],
            "spec": [_rebin(ph.spectrum_probs(h, kin, t), SPEC_EDGES) for t in THICK],
            "cal": _rebin(ph.calorimeter_probs(h, kin), CAL_EDGES),
        }
        out["m_light"] = kin.m_light
    out["kl_spec"] = [_kl(a, b) for a, b in zip(out["carrier"]["spec"], out["loss"]["spec"])]
    out["kl_cal"] = _kl(out["carrier"]["cal"], out["loss"]["cal"])
    return out


# ---------------------------------------------------------------------------------------------
# 2. Episode replay
# ---------------------------------------------------------------------------------------------

EPISODE_HTML = r"""
<div class="vz" id="vz-ep">
  <div class="vz-bar">
    <label>эпизод <select id="vze-sel"></select></label>
    <button type="button" id="vze-prev">← шаг</button>
    <button type="button" id="vze-next">шаг →</button>
    <button type="button" id="vze-play">Проиграть</button>
  </div>
  <div class="vz-steps" id="vze-steps"></div>
  <div class="vz-grid two">
    <div>
      <svg id="vze-plot" viewBox="0 0 440 300" role="img" aria-label="Данные и прогнозы шага"></svg>
      <div class="vz-readout" id="vze-cap"></div>
    </div>
    <div>
      <div id="vze-hyps"></div>
      <div class="vz-readout" id="vze-read" style="margin-top:.5rem"></div>
    </div>
  </div>
  <p class="vz-note">Реальные эпизоды агента (журнал оркестратора, прогнозы записаны до измерения). Цвет гипотезы — её поведенческий класс: <span style="color:#2a78d6">■</span> носитель, <span style="color:#eb6834">■</span> потери, <span style="color:#8a8f98">■</span> другое. На шаге D — скрытая проверка: точки (энергия частицы, импульс отдачи) на тонком источнике, которых агент не видел никогда: серые — истина, синие — итоговая модель агента, оранжевые — «учебный» ответ (безмассовый носитель, спектр Ферми).</p>
</div>
<script>
(function () {
  const EPS = __DATA__;
  const root = document.getElementById('vz-ep'), $ = (id) => document.getElementById(id), NS = 'http://www.w3.org/2000/svg';
  const C = { carrier: '#2a78d6', loss: '#eb6834', other: '#8a8f98' };
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const fmt = (x) => x === null || x === undefined ? '–' : (Math.abs(x) >= 100 ? Math.round(x).toString() : Math.abs(x) >= 0.01 ? x.toFixed(3) : x.toExponential(1));
  let ep = 0, st = 0, timer = null;
  const sel = $('vze-sel');
  EPS.forEach((e, i) => { const o = document.createElement('option'); o.value = i; o.textContent = e.label; sel.appendChild(o); });

  function steps(e) {
    const s = [{ kind: 'A' }];
    e.steps.forEach((x, i) => { s.push({ kind: 'B', i }); if (x.obs) s.push({ kind: 'C', i }); });
    if (e.final) s.push({ kind: 'D' });
    return s;
  }
  function axes(svg, x0, x1, y1, xlab, ylab) {
    const W = 440, H = 300, L = 40, R = 10, T = 14, B = 36;
    const X = (v) => L + (v - x0) / (x1 - x0) * (W - L - R), Y = (v) => T + (1 - v / y1) * (H - T - B);
    const step = (x1 - x0) > 0.9 ? 0.2 : 0.1;
    for (let v = Math.ceil(x0 / step) * step; v <= x1 + 1e-9; v += step) { el('line', { x1: X(v), x2: X(v), y1: T, y2: H - B, class: 'tick' }, svg); const t = el('text', { x: X(v), y: H - B + 14, 'text-anchor': 'middle', 'font-size': 10 }, svg); t.textContent = v.toFixed(1); }
    const xl = el('text', { x: (L + W - R) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 11 }, svg); xl.textContent = xlab;
    const yl = el('text', { x: 12, y: (T + H - B) / 2, 'text-anchor': 'middle', 'font-size': 11, transform: 'rotate(-90 12 ' + (T + H - B) / 2 + ')' }, svg); yl.textContent = ylab;
    return { X, Y, H, B, T, L, W, R };
  }
  function histo(svg, a, edges, h, color, filled) {
    if (filled) { for (let b = 0; b < h.length; b++) el('rect', { x: a.X(edges[b]) + 0.5, y: a.Y(h[b]), width: Math.max(0, a.X(edges[b + 1]) - a.X(edges[b]) - 1), height: (a.H - a.B) - a.Y(h[b]), fill: color, opacity: 0.35 }, svg); return; }
    const pts = []; for (let b = 0; b < h.length; b++) { pts.push(a.X(edges[b]).toFixed(1) + ',' + a.Y(h[b]).toFixed(1)); pts.push(a.X(edges[b + 1]).toFixed(1) + ',' + a.Y(h[b]).toFixed(1)); }
    el('polyline', { points: pts.join(' '), fill: 'none', stroke: color, 'stroke-width': 2.2 }, svg);
  }
  function hypRows(hyps) {
    const box = $('vze-hyps'); box.innerHTML = '';
    hyps.forEach((h) => {
      const d = document.createElement('div'); d.className = 'vz-hyp';
      d.innerHTML = '<b>' + h.id + '</b><div style="background:rgba(127,127,127,.15);border-radius:.2rem"><div class="bar" style="width:' + (100 * h.credence) + '%;background:' + C[h.cls] + '"></div></div><span>' + h.credence.toFixed(2) + '</span><div class="st">' + h.statement.replace(/</g, '&lt;') + '</div>';
      box.appendChild(d);
    });
  }
  function verdict(v) {
    if (!v) return '';
    const cls = v.startsWith('justified') ? 'vz-good' : v.startsWith('unjustified') ? 'vz-bad' : 'vz-weak';
    const ru = { justified_keep: 'обоснованно сохранена', justified_switch: 'обоснованно сменена', unjustified_keep: 'сохранена вопреки данным', unjustified_switch: 'сменена вопреки данным', weak_evidence: 'свидетельство слабое' };
    const base = Object.keys(ru).find((k) => v.startsWith(k));
    return '<span class="vz-pill ' + cls + '">' + (ru[base] || v) + (v.includes('same_class') ? ', альтернатива того же класса' : '') + '</span>';
  }
  function draw() {
    const e = EPS[ep], S = steps(e), s = S[st], svg = $('vze-plot');
    svg.innerHTML = '';
    const sb = $('vze-steps'); sb.innerHTML = '';
    S.forEach((x, i) => { const b = document.createElement('button'); b.textContent = x.kind + (x.i !== undefined ? (x.i + 1) : ''); b.setAttribute('aria-current', i === st); b.onclick = () => { st = i; draw(); }; sb.appendChild(b); });
    const head = '<b>Истина: ' + (e.truth === 'carrier' ? 'носитель' : 'потери') + '</b> · мир ' + e.seed + ' · ' + (e.menu ? 'меню дано' : 'без меню') + ' · повтор ' + e.rep + '<br>';
    if (s.kind === 'A') {
      const mx = Math.max.apply(null, e.initial) * 1.15, a = axes(svg, 0.1, 1.3, mx, 'энергия на спектрометре / Q', 'доля событий');
      histo(svg, a, e.spec_edges, e.initial, 'currentColor', true);
      $('vze-cap').innerHTML = 'A. Начальные данные: спектр при t = 1, 400 событий.';
      $('vze-read').innerHTML = head + 'Категория экземпляра: <b>' + e.category + '</b> (max log-LR носитель − потери = ' + fmt(e.dllA) + ' нат). Эталонные семейства объясняют эти данные почти одинаково.';
      $('vze-hyps').innerHTML = '';
      return;
    }
    if (s.kind === 'B' || s.kind === 'C') {
      const x = e.steps[s.i], edges = x.edges;
      let mx = 0; x.hyps.forEach((h) => { mx = Math.max(mx, Math.max.apply(null, h.fc)); }); if (s.kind === 'C') mx = Math.max(mx, Math.max.apply(null, x.obs));
      const a = axes(svg, edges[0], edges[edges.length - 1], mx * 1.15, x.mtype === 'calorimeter' ? 'энергия в калориметре / Q' : 'энергия на спектрометре / Q (t = ' + x.t + ')', 'доля событий');
      if (s.kind === 'C') histo(svg, a, edges, x.obs, 'currentColor', true);
      x.hyps.forEach((h) => histo(svg, a, edges, h.fc, C[h.cls], false));
      hypRows(x.hyps);
      const m = x.mtype === 'calorimeter' ? 'калориметр' : 'спектр при t = ' + x.t;
      $('vze-cap').innerHTML = s.kind === 'B' ? 'B' + (s.i + 1) + '. Записанные до измерения прогнозы гипотез (линии) для выбранного измерения: ' + m + '.' : 'C' + (s.i + 1) + '. Результат измерения (серые столбцы) против записанных прогнозов.';
      let r = head + 'Измерение: <b>' + m + '</b>, n = ' + x.n + '. Информативность: свои модели ' + fmt(x.own) + ' нат, эталон ' + fmt(x.ref) + ' нат (' + (x.frac === null ? '–' : Math.round(100 * x.frac) + '%') + ' от лучшего в меню).<br>Доверие к носителю: агент ' + fmt(x.pA) + ', эталон по тем же данным ' + fmt(x.pR) + (x.over ? ' <span class="vz-pill vz-bad">сверхуверенность</span>' : '');
      if (s.kind === 'C') r += '<br>Реализованный log BF (альтернатива : текущая) = <b>' + fmt(x.lbf) + '</b> ± ' + fmt(x.lbfsd) + ' → гипотеза ' + verdict(x.verdict);
      $('vze-read').innerHTML = r;
      return;
    }
    const f = e.final;
    hypRows(f.hyps);
    const a = axes(svg, 0.1, 1.3, 1.25, 'энергия частицы / Q (тонкий источник)', 'импульс отдачи / p_Q');
    const sc = (pts, color, r, op) => pts.forEach((p) => el('circle', { cx: a.X(p[0]), cy: a.Y(p[1]), r, fill: color, opacity: op }, svg));
    sc(f.truth, 'currentColor', 1.6, 0.35); sc(f.textbook, '#eb6834', 1.6, 0.45); sc(f.agent, '#2a78d6', 1.8, 0.6);
    const yt = [0, 0.25, 0.5, 0.75, 1.0, 1.25]; yt.forEach((v) => { const t = el('text', { x: a.L - 5, y: a.Y(v) + 3, 'text-anchor': 'end', 'font-size': 10 }, svg); t.textContent = v; });
    $('vze-cap').innerHTML = 'D. Скрытая проверка: совместное распределение энергии и отдачи на источнике t = 0.05 (вне меню измерений).';
    $('vze-read').innerHTML = head + 'Итоговый класс: <b>' + f.cls + '</b>, доверие к истинному механизму ' + fmt(f.pTrue) + '. ' + (f.mass_true !== null ? 'Масса носителя / Q: агент ' + fmt(f.mass_agent) + ', поведенческая ' + fmt(f.mass_beh) + ', истина ' + fmt(f.mass_true) + '.<br>' : '<br>') +
      'Расстояние до истины (меньше — лучше): <b>агент ' + fmt(f.check) + '</b> · эталон ' + fmt(f.ref) + ' · учебный ' + fmt(f.textbook_ed) + ' · шумовой пол ' + fmt(f.floor) + ' · противоположный механизм ' + fmt(f.opp) +
      '<br>Разложение: энергия ' + fmt(f.ed_energy) + ', отдача ' + fmt(f.ed_recoil) + '; корреляция энергия–отдача: агент ' + (f.corr_agent === null ? '–' : f.corr_agent.toFixed(2)) + ', истина ' + (f.corr_truth === null ? '–' : f.corr_truth.toFixed(2));
  }
  sel.addEventListener('change', () => { ep = +sel.value; st = 0; draw(); });
  $('vze-prev').onclick = () => { st = Math.max(0, st - 1); draw(); };
  $('vze-next').onclick = () => { st = Math.min(steps(EPS[ep]).length - 1, st + 1); draw(); };
  $('vze-play').onclick = () => {
    if (timer) { clearInterval(timer); timer = null; $('vze-play').textContent = 'Проиграть'; return; }
    st = 0; draw(); $('vze-play').textContent = 'Стоп';
    timer = setInterval(() => { const n = steps(EPS[ep]).length; if (st >= n - 1) { clearInterval(timer); timer = null; $('vze-play').textContent = 'Проиграть'; return; } st++; draw(); }, 2200);
  };
  draw();
})();
</script>
"""


def _hist(x, edges) -> list[float]:
    h, _ = np.histogram(np.asarray(x, float), edges)
    s = h.sum()
    return [round(float(v), 5) for v in (h / s if s else h)]


def _sub(a: np.ndarray, n: int, seed: int = 0) -> np.ndarray:
    if len(a) <= n:
        return a
    return a[np.random.default_rng(seed).choice(len(a), n, replace=False)]


def episode_data(run_dir: Path, row: dict) -> dict | None:
    evals = sorted(run_dir.glob("evaluation-*.json"))
    if not evals:
        return None
    res = json.loads(evals[-1].read_text())
    s = load_session(run_dir / "state")
    w, Q, kin = s.world, s.world.Q, s.world.kin
    log = [json.loads(x) for x in (run_dir / "state" / "log.jsonl").read_text().splitlines()]
    regs = [ev for ev in log if ev["event"] == "register"]
    used = [st for st in s.steps if st.kind == "register"]
    out = {
        "label": f"мир {row['world_seed']} · {('носитель' if row['truth'] == 'carrier' else 'потери')} · "
                 f"{'меню' if row['menu'] else 'без меню'} · повтор {row['rep']}" +
                 ("" if row["condition"] == "ambiguous" else f" · {row['condition']}"),
        "seed": row["world_seed"], "truth": row["truth"], "menu": row["menu"], "rep": row["rep"],
        "category": res["instance"]["category"], "dllA": res["instance"].get("ref_dll_initial"),
        "spec_edges": SPEC_EDGES.tolist(),
        "initial": _hist(s.initial[0][1]["kinetic_energy"] / Q, SPEC_EDGES) if s.initial else [0.0] * 48,
        "steps": [],
    }
    for st, rs in zip(used, res["steps"]):
        q = st.measurement
        key = "deposited_energy" if q["type"] == "calorimeter" else "kinetic_energy"
        edges = CAL_EDGES if q["type"] == "calorimeter" else SPEC_EDGES
        hyps = [{"id": h.id, "credence": h.credence, "statement": h.statement[:220],
                 "cls": rs["classes"].get(h.id, "other"), "fc": _hist(h.forecast[key] / Q, edges)} for h in st.hyps]
        f = rs.get("forecast", {})
        out["steps"].append({
            "mtype": q["type"], "t": q.get("thickness"), "n": q["n"], "edges": edges.tolist(), "hyps": hyps,
            "obs": _hist(st.observation[key] / Q, edges) if st.observation is not None else None,
            "own": rs["design_info_own"], "ref": rs["design_info_ref"], "frac": rs["design_info_ref_frac_of_menu_max"],
            "pA": rs["uncertainty_before"]["agent_P_carrier"], "pR": rs["uncertainty_before"]["ref_P_carrier"],
            "over": rs["uncertainty_before"]["overconfident"],
            "lbf": f.get("logbf_alt_vs_current"), "lbfsd": f.get("logbf_forecast_noise_sd"),
            "verdict": (rs.get("revision") or {}).get("verdict"),
        })
    fin = res.get("final")
    final_step = next((st for st in s.steps if st.kind == "final"), None)
    if fin and final_step is not None:
        cons = fin.get("consistency", {})
        hyps = [{"id": h.id, "credence": h.credence, "statement": h.statement[:220],
                 "cls": (cons.get(h.id, {}).get("behaviour") or {}).get("class", "other")} for h in final_step.hyps]
        n = 350
        tr = w.truth_sample(dict(HIDDEN_CHECK), n, seed=9)
        truth = np.column_stack([tr["kinetic_energy"], tr["recoil_momentum"] / kin.p_ref])
        try:
            pc = final_step.predictive.simulate_many([dict(HIDDEN_CHECK)], n, 31)[0]
            agent = np.column_stack([pc["kinetic_energy"] / Q, pc["recoil_momentum"] / Q / kin.p_ref])
        except Exception:
            agent = np.zeros((0, 2))
        tb = bl._textbook_fn(Session(EpisodeConfig.from_dict(res["config"])))(dict(HIDDEN_CHECK), n, 41)
        textbook = np.column_stack([tb["kinetic_energy"] / Q, tb["recoil_momentum"] / Q / kin.p_ref])
        rnd = lambda a: [[round(float(x), 3), round(float(y), 3)] for x, y in a]  # noqa: E731
        anchors = {"reference_adaptive": row.get("ref"), "textbook": row.get("textbook")}
        parts = fin.get("check_parts") or {}
        out["final"] = {
            "hyps": hyps, "cls": fin.get("current_class"), "pTrue": row.get("final_P_true"),
            "mass_true": row.get("true_mx_over_Q"), "mass_agent": row.get("agent_mass_over_Q"),
            "mass_beh": row.get("behavioural_mass_over_Q"),
            "check": fin.get("check_ed"), "floor": fin.get("check_ed_floor_truth"), "opp": fin.get("check_ed_opposite_mechanism"),
            "ref": anchors.get("reference_adaptive"), "textbook_ed": anchors.get("textbook"),
            "truth": rnd(truth), "agent": rnd(agent), "textbook": rnd(textbook),
            "ed_energy": parts.get("ed_energy"), "ed_recoil": parts.get("ed_recoil"),
            "corr_agent": parts.get("corr_agent"), "corr_truth": parts.get("corr_truth"),
        }
    return out


# ---------------------------------------------------------------------------------------------
# 3. Charts across episodes
# ---------------------------------------------------------------------------------------------

CHARTS_HTML = r"""
<div class="vz" id="vz-check">
  <div class="vz-bar">
    <span class="vz-seg" role="group" aria-label="Условие">
      <button type="button" data-f="all" aria-pressed="true">Все</button>
      <button type="button" data-f="menu" aria-pressed="false">Меню дано</button>
      <button type="button" data-f="free" aria-pressed="false">Без меню</button>
    </span>
  </div>
  <svg id="vzc-plot" viewBox="0 0 760 420" role="img" aria-label="Скрытая проверка по эпизодам"></svg>
  <p class="vz-note">Каждая строка — мир и истинный механизм; точки — эпизоды агента (● меню дано, ○ без меню), наведите курсор для подробностей. Вертикальные метки того же мира: <b>|</b> серая — шумовой пол (истина против истины), синяя — эталонный решатель, оранжевая — «учебный» ответ, красная — противоположный механизм. Шкала логарифмическая: меньше — лучше.</p>
</div>
<div class="vz" id="vz-mass">
  <svg id="vzm-plot" viewBox="0 0 520 380" role="img" aria-label="Масса носителя: агент против истины"></svg>
  <p class="vz-note">Эпизоды в мирах с носителем. ● заявленная масса (только при меню), ○ поведенческая — масса, которую подразумевает спектр модели агента на тонком источнике (есть и без меню). Диагональ — точное попадание. Для калибровки: «учебная» безмассовая модель со спектром Ферми даёт поведенческую массу ≈ 0.12.</p>
</div>
<script>
(function () {
  const R = __DATA__;
  const NS = 'http://www.w3.org/2000/svg', $ = (id) => document.getElementById(id);
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const BLUE = '#2a78d6', ORANGE = '#eb6834', RED = '#dc2626';
  const fmt = (x) => x === null || x === undefined ? '–' : (x >= 0.01 ? x.toFixed(3) : x.toExponential(1));
  let filt = 'all';
  function check() {
    const svg = $('vzc-plot'); svg.innerHTML = '';
    const rows = []; const key = (r) => r.world_seed + '|' + r.truth;
    R.forEach((r) => { if (r.check_ed === null || r.condition !== 'ambiguous') return; if (!rows.includes(key(r))) rows.push(key(r)); });
    rows.sort((a, b) => { const [sa, ta] = a.split('|'), [sb, tb] = b.split('|'); return ta === tb ? (+sa - +sb) : (ta < tb ? -1 : 1); });
    const W = 760, L = 150, Rr = 14, T = 16, rowH = Math.max(18, Math.min(34, 360 / Math.max(rows.length, 1))), H = T + rows.length * rowH + 40;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    const lo = -5, hi = 0, X = (v) => L + (Math.log10(Math.max(v, 1e-5)) - lo) / (hi - lo) * (W - L - Rr);
    for (let d = lo; d <= hi; d++) { el('line', { x1: X(Math.pow(10, d)), x2: X(Math.pow(10, d)), y1: T - 4, y2: H - 34, class: 'tick' }, svg); const t = el('text', { x: X(Math.pow(10, d)), y: H - 20, 'text-anchor': 'middle', 'font-size': 10 }, svg); t.textContent = '1e' + d; }
    const xl = el('text', { x: (L + W) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 11 }, svg); xl.textContent = 'энергетическое расстояние до истины на скрытой проверке (лог-шкала)';
    rows.forEach((k, i) => {
      const [seed, truth] = k.split('|'), y = T + i * rowH + rowH / 2, rs = R.filter((r) => key(r) === k && r.condition === 'ambiguous' && r.check_ed !== null);
      if (i % 2 === 0) el('rect', { x: 0, y: y - rowH / 2, width: W, height: rowH, fill: 'currentColor', opacity: 0.04 }, svg);
      const lab = el('text', { x: 8, y: y + 4, 'font-size': 11 }, svg); lab.textContent = 'мир ' + seed + ' · ' + (truth === 'carrier' ? 'носитель' : 'потери');
      const a = rs[0];
      const mark = (v, c, w) => { if (v === null || v === undefined) return; el('line', { x1: X(v), x2: X(v), y1: y - rowH * 0.38, y2: y + rowH * 0.38, stroke: c, 'stroke-width': w || 2.5, opacity: 0.85 }, svg); };
      mark(a.floor, 'currentColor', 2); mark(a.ref, BLUE); mark(a.textbook, ORANGE); mark(a.opposite, RED);
      rs.forEach((r, j) => {
        const show = filt === 'all' || (filt === 'menu') === r.menu; if (!show) return;
        const c = el('circle', { cx: X(r.check_ed), cy: y + (j % 3 - 1) * rowH * 0.18, r: 5, fill: r.menu ? 'currentColor' : 'none', stroke: 'currentColor', 'stroke-width': 1.6, opacity: 0.85 }, svg);
        const tt = el('title', {}, c); tt.textContent = r.run + '\n' + (r.menu ? 'меню' : 'без меню') + ', повтор ' + r.rep + '\nпроверка ' + fmt(r.check_ed) + ' (эталон ' + fmt(r.ref) + ', учебный ' + fmt(r.textbook) + ')\nитог: ' + r.final_class + ', доверие к истине ' + fmt(r.final_P_true) + '\nпересмотры: ' + r.revisions.join(', ');
      });
    });
  }
  function mass() {
    const svg = $('vzm-plot'); svg.innerHTML = '';
    const W = 520, H = 380, L = 52, Rr = 14, T = 14, B = 42, mx = 0.4;
    const X = (v) => L + v / mx * (W - L - Rr), Y = (v) => T + (1 - v / mx) * (H - T - B);
    for (let v = 0; v <= mx + 1e-9; v += 0.1) { el('line', { x1: X(v), x2: X(v), y1: T, y2: H - B, class: 'tick' }, svg); el('line', { x1: L, x2: W - Rr, y1: Y(v), y2: Y(v), class: 'tick' }, svg); const a = el('text', { x: X(v), y: H - B + 14, 'text-anchor': 'middle', 'font-size': 10 }, svg); a.textContent = v.toFixed(1); const b = el('text', { x: L - 6, y: Y(v) + 3, 'text-anchor': 'end', 'font-size': 10 }, svg); b.textContent = v.toFixed(1); }
    el('line', { x1: X(0), y1: Y(0), x2: X(mx), y2: Y(mx), stroke: 'currentColor', 'stroke-dasharray': '4 4', opacity: 0.5 }, svg);
    const xl = el('text', { x: (L + W) / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 11 }, svg); xl.textContent = 'истинная масса носителя / Q';
    const yl = el('text', { x: 14, y: (T + H - B) / 2, 'text-anchor': 'middle', 'font-size': 11, transform: 'rotate(-90 14 ' + (T + H - B) / 2 + ')' }, svg); yl.textContent = 'масса по агенту / Q';
    R.filter((r) => r.truth === 'carrier' && r.true_mx_over_Q !== null && r.condition === 'ambiguous').forEach((r, j) => {
      const jit = ((j * 37) % 7 - 3) * 0.0015;
      const add = (v, filled) => { if (v === null || v === undefined) return; const c = el('circle', { cx: X(r.true_mx_over_Q + jit), cy: Y(Math.min(v, mx)), r: 5, fill: filled ? BLUE : 'none', stroke: BLUE, 'stroke-width': 1.6, opacity: 0.85 }, svg); const t = el('title', {}, c); t.textContent = r.run + '\n' + (filled ? 'заявленная' : 'поведенческая') + ' ' + fmt(v) + ', истина ' + fmt(r.true_mx_over_Q) + '\n' + (r.menu ? 'меню' : 'без меню') + ', повтор ' + r.rep + ', итог ' + r.final_class; };
      add(r.agent_mass_over_Q, true); add(r.behavioural_mass_over_Q, false);
    });
  }
  document.querySelectorAll('#vz-check [data-f]').forEach((b) => b.addEventListener('click', () => { filt = b.dataset.f; document.querySelectorAll('#vz-check [data-f]').forEach((x) => x.setAttribute('aria-pressed', x === b)); check(); }));
  check(); mass();
})();
</script>
"""


# ---------------------------------------------------------------------------------------------
# 4. Tables and KPIs
# ---------------------------------------------------------------------------------------------


def _f(x, nd=3) -> str:
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "да" if x else "нет"
    if isinstance(x, float):
        if math.isnan(x):
            return "–"
        return f"{x:.{nd}g}"
    if isinstance(x, list):
        return ", ".join(str(v).replace("_", " ") for v in x if v)
    return str(x)


def tables(rows: list[dict], baseline_dir: Path | None) -> str:
    ok = [r for r in rows if r["status"] == "ok"]
    ok.sort(key=lambda r: (r["condition"], r["truth"], r["world_seed"], not r["menu"], r["rep"]))
    head = ("| мир | истина | условие | меню | повтор | итог | доверие к истине | m/Q истина | m/Q заявл. | m/Q поведен. "
            "| пересмотры | проверка | эталон | учебный | корр. агент / истина | $ |\n|---:|---|---|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---:|")
    lines = [head]
    for r in ok:
        lines.append("| " + " | ".join([
            str(r["world_seed"]), "носитель" if r["truth"] == "carrier" else "потери", r["condition"], _f(r["menu"]), str(r["rep"]),
            _f(r["final_class"]), _f(r["final_P_true"], 2), _f(r["true_mx_over_Q"]), _f(r["agent_mass_over_Q"]),
            _f(r["behavioural_mass_over_Q"]), _f(r["revisions"]), _f(r["check_ed"]), _f(r["ref"]), _f(r["textbook"]),
            f'{_f(r.get("corr_agent"), 2)} / {_f(r.get("corr_truth"), 2)}', _f(r["cost_usd"], 2)]) + " |")
    out = "\n".join(lines) + "\n"
    bad = [r["run"] for r in rows if r["status"] != "ok"]
    if bad:
        out += f"\nНе вошли (неполные, прерванные или неоценённые прогоны): {', '.join(bad)}.\n"
    if baseline_dir and (baseline_dir / "summary.json").exists():
        summ = json.loads((baseline_dir / "summary.json").read_text())
        out += "\n\n### Локальные baseline\n\n| политика | условие | истина | класс верен | доверие к истине | проверка | пол | противоп. | доля информативности 1-го измерения |\n|---|---|---|---:|---:|---:|---:|---:|---:|\n"
        for s in summ:
            out += "| " + " | ".join([s["policy"], s["condition"], s["mechanism"], _f(s["final_class_correct"], 2),
                                      _f(s["final_P_true"], 2), _f(s["check_ed"]), _f(s["check_floor"]),
                                      _f(s["check_opposite"]), _f(s["design_frac_menu_max_step1"], 2)]) + " |\n"
    return out


def kpi(rows: list[dict]) -> str:
    ok = [r for r in rows if r["status"] == "ok" and r["condition"] == "ambiguous"]
    n = len(ok)
    correct = sum(r["final_class"] == r["truth"] for r in ok)
    cal_first = sum(r["first_measurement"] == "calorimeter" for r in ok)
    ratios = [r["check_ed"] / r["ref"] for r in ok if r["check_ed"] and r["ref"]]
    cost = sum(r["cost_usd"] or 0 for r in rows if r["status"] == "ok")
    cells = [(str(n), "эпизодов с неоднозначными начальными данными"),
             (f"{correct}/{n}", "верный механизм в финале"),
             (f"{cal_first}/{n}", "первое измерение — калориметр"),
             (f"{np.median(ratios):.1f}×" if ratios else "–", "медиана: проверка агента / эталон"),
             (f"${cost:.2f}", "стоимость всех оценённых эпизодов")]
    md = "::: {.grid .kpi}\n"
    for v, lab in cells:
        md += f"::: {{.g-col-6 .g-col-md-2}}\n[{v}]{{.kpi-num}}\n[{lab}]{{.kpi-label}}\n:::\n"
    return md + ":::\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=str(REPO / "runs_episode"))
    ap.add_argument("--world-seed", type=int, default=0)
    ap.add_argument("--baselines", default=str(sorted(glob.glob(str(REPO / "results/episode/baselines-*")))[-1])
                    if glob.glob(str(REPO / "results/episode/baselines-*")) else "")
    a = ap.parse_args()
    rows = [r for r in collect_runs(Path(a.runs_root)) if r.get("family", "decay") != "orbit"]
    (HERE / "_anim_world.html").write_text(
        CSS + WORLD_HTML.replace("__SEED__", str(a.world_seed)).replace("__DATA__", json.dumps(world_data(a.world_seed), separators=(",", ":"))))
    eps = []
    for r in rows:
        if r["status"] != "ok":
            continue
        d = episode_data(Path(a.runs_root) / r["run"], r)
        if d:
            eps.append(d)
    eps.sort(key=lambda e: (e["truth"], e["seed"], not e["menu"], e["rep"]))
    (HERE / "_anim_episode.html").write_text(EPISODE_HTML.replace("__DATA__", json.dumps(eps, separators=(",", ":"))))
    slim = [{k: r.get(k) for k in ("run", "world_seed", "truth", "condition", "menu", "rep", "check_ed", "ref", "textbook",
                                  "floor", "opposite", "final_class", "final_P_true", "revisions", "true_mx_over_Q",
                                  "agent_mass_over_Q", "behavioural_mass_over_Q")} for r in rows if r["status"] == "ok"]
    (HERE / "_charts.html").write_text(CHARTS_HTML.replace("__DATA__", json.dumps(slim, separators=(",", ":"), default=float)))
    (HERE / "_tables.md").write_text(tables(rows, Path(a.baselines) if a.baselines else None))
    (HERE / "_kpi.md").write_text(kpi(rows))
    print(f"episodes in replay: {len(eps)}; table rows: {len(slim)}")


if __name__ == "__main__":
    main()
