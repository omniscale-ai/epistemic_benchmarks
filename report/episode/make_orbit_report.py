"""Orbit part of the episode report: writes _anim_orbit_world.html, _orbit_charts.html, _orbit_tables.md, _orbit_kpi.md.

    PYTHONPATH=src .venv/bin/python report/episode/make_orbit_report.py [--runs-root runs_episode] [--world-seed 0]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from abductbench.episode import orbitworld as ow
from abductbench.episode.cli import collect_runs

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

WORLD_HTML = r"""
<div class="vz" id="vz-orb">
  <div class="vz-bar">
    <span class="vz-seg" role="group" aria-label="Скрытая причина">
      <button type="button" data-m="body" aria-pressed="true">Скрытое внутреннее тело</button>
      <button type="button" data-m="force" aria-pressed="false">Изменённый закон силы</button>
    </span>
    <button type="button" id="vzr-play">Пауза</button>
    <label>скорость <input type="range" id="vzr-speed" min="0.1" max="3" step="0.1" value="0.6"> <span id="vzr-sv">0,6 цикла/с</span></label>
  </div>
  <div class="vz-grid two">
    <svg id="vzr-sys" viewBox="-210 -210 420 420" role="img" aria-label="Система: звезда, планеты, скрытое тело"></svg>
    <div>
      <svg id="vzr-c1" viewBox="0 0 440 210" role="img" aria-label="Невязка цели"></svg>
      <svg id="vzr-c2" viewBox="0 0 440 210" role="img" aria-label="Невязка соседней планеты"></svg>
    </div>
  </div>
  <p class="vz-note">Настоящий генератор (мир __SEED__). Слева: планеты вокруг центра масс C (крестик); в мире тела звезда и тело обращаются вокруг C (покачивание звезды сильно увеличено, движение тела замедлено в 10 раз, чтобы его было видно). Справа: невязки наблюдений относительно T0 без шума: <b>сплошная</b> — выбранный мир, <b>пунктир</b> — другой мир той же системы. Окрашенная полоса — окно начальных данных (0–10 циклов). На цели миры почти неразличимы, у соседней планеты расходятся.</p>
</div>
<script>
(function () {
  const D = __DATA__;
  const root = document.getElementById('vz-orb'), $ = (id) => document.getElementById(id), NS = 'http://www.w3.org/2000/svg';
  const C = { body: '#2a78d6', force: '#eb6834' };
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  let mode = 'body', t = 0, playing = true, speed = 0.6, visible = true, last = null;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) playing = false;
  const K = 110, f = (r) => K * Math.pow(r, 0.6);
  function kepler(M, e) { let E = M; for (let i = 0; i < 10; i++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E)); return E; }
  function pos(p, tt) { const n = Math.sqrt(D.gm / (p.a * p.a * p.a)), E = kepler(p.L0 + n * tt - p.w, p.e), x = p.a * (Math.cos(E) - p.e), y = p.a * Math.sqrt(1 - p.e * p.e) * Math.sin(E); const X = x * Math.cos(p.w) - y * Math.sin(p.w), Y = x * Math.sin(p.w) + y * Math.cos(p.w); const r = Math.hypot(X, Y), th = Math.atan2(Y, X); return [f(r) * Math.cos(th), -f(r) * Math.sin(th)]; }
  const sys = $('vzr-sys');
  function drawSys() {
    sys.innerHTML = '';
    D.planets.forEach((p) => { const pts = []; for (let k = 0; k <= 120; k++) { const nu = k / 120 * 2 * Math.PI, r = p.a * (1 - p.e * p.e) / (1 + p.e * Math.cos(nu)), th = nu + p.w; pts.push((f(r) * Math.cos(th)).toFixed(1) + ',' + (-f(r) * Math.sin(th)).toFixed(1)); } el('polyline', { points: pts.join(' '), fill: 'none', stroke: 'currentColor', 'stroke-opacity': 0.2 }, sys); });
    el('line', { x1: -5, x2: 5, y1: 0, y2: 0, stroke: 'currentColor' }, sys); el('line', { x1: 0, x2: 0, y1: -5, y2: 5, stroke: 'currentColor' }, sys);
    let sx = 0, sy = 0;
    if (mode === 'body') {
      const ang = D.body.ph + D.body.n * t / 10, rb = f(D.body.a);
      el('circle', { cx: 0, cy: 0, r: rb, fill: 'none', stroke: C.body, 'stroke-dasharray': '3 3', opacity: 0.5 }, sys);
      const bx = rb * Math.cos(ang), by = -rb * Math.sin(ang);
      el('circle', { cx: bx, cy: by, r: 4, fill: 'none', stroke: C.body, 'stroke-width': 2 }, sys);
      const lb = el('text', { x: bx + 7, y: by - 5, 'font-size': 10, fill: C.body }, sys); lb.textContent = 'скрытое тело';
      const wob = Math.min(9, 3000 * D.body.frac * f(D.body.a)); sx = -wob * Math.cos(ang); sy = wob * Math.sin(ang);
    }
    el('circle', { cx: sx, cy: sy, r: 7, fill: '#e0a800' }, sys);
    D.planets.forEach((p, i) => { const q = pos(p, t); el('circle', { cx: q[0], cy: q[1], r: i === 0 ? 5 : 3.5, fill: i === 0 ? C[mode] : 'currentColor', 'fill-opacity': i === 0 ? 1 : 0.6 }, sys); const lb = el('text', { x: q[0] + 7, y: q[1] - 6, 'font-size': 10 }, sys); lb.textContent = p.name + (i === 0 ? ' (цель)' : ''); });
    const tl = el('text', { x: -200, y: 200, 'font-size': 11 }, sys); tl.textContent = 't = ' + t.toFixed(1) + ' цикла';
  }
  function chart(svg, key, title) {
    svg.innerHTML = '';
    const W = 440, H = 210, L = 46, R = 10, T = 18, B = 30, tm = D.t;
    const a = D[mode][key], b = D[mode === 'body' ? 'force' : 'body'][key];
    let lo = Math.min(Math.min.apply(null, a), Math.min.apply(null, b)), hi = Math.max(Math.max.apply(null, a), Math.max.apply(null, b)); const pad = 0.1 * (hi - lo || 1); lo -= pad; hi += pad;
    const X = (v) => L + v / tm[tm.length - 1] * (W - L - R), Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    el('rect', { x: X(0), y: T, width: X(10) - X(0), height: H - T - B, fill: C[mode], opacity: 0.1 }, svg);
    for (let v = 0; v <= tm[tm.length - 1] + 1e-9; v += 5) { el('line', { x1: X(v), x2: X(v), y1: T, y2: H - B, class: 'tick' }, svg); const l = el('text', { x: X(v), y: H - B + 13, 'text-anchor': 'middle', 'font-size': 10 }, svg); l.textContent = v; }
    const st = Math.pow(10, Math.floor(Math.log10((hi - lo) / 3))); for (let v = Math.ceil(lo / st) * st; v <= hi; v += st) { const l = el('text', { x: L - 4, y: Y(v) + 3, 'text-anchor': 'end', 'font-size': 9 }, svg); l.textContent = +v.toFixed(2); el('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: 'tick' }, svg); }
    const line = (arr, col, dash) => el('polyline', { points: arr.map((v, i) => X(tm[i]).toFixed(1) + ',' + Y(v).toFixed(1)).join(' '), fill: 'none', stroke: col, 'stroke-width': 2, 'stroke-dasharray': dash }, svg);
    line(b, C[mode === 'body' ? 'force' : 'body'], '5 4'); line(a, C[mode], '');
    el('line', { x1: X(t), x2: X(t), y1: T, y2: H - B, stroke: 'currentColor', opacity: 0.6 }, svg);
    const tt = el('text', { x: L, y: 12, 'font-size': 11 }, svg); tt.textContent = title;
  }
  function frame(ts) {
    if (last === null) last = ts; const dt = Math.min(0.1, (ts - last) / 1000); last = ts;
    if (playing && visible) { t += dt * speed; if (t > D.t[D.t.length - 1]) t = 0; drawSys(); chart($('vzr-c1'), 'target', 'невязка цели ' + D.planets[0].name + ', угл. сек'); chart($('vzr-c2'), 'next', 'невязка соседней планеты ' + D.planets[1].name + ', угл. сек'); }
    requestAnimationFrame(frame);
  }
  root.querySelectorAll('[data-m]').forEach((b) => b.addEventListener('click', () => { mode = b.dataset.m; root.querySelectorAll('[data-m]').forEach((x) => x.setAttribute('aria-pressed', x === b)); drawSys(); chart($('vzr-c1'), 'target', 'невязка цели ' + D.planets[0].name + ', угл. сек'); chart($('vzr-c2'), 'next', 'невязка соседней планеты ' + D.planets[1].name + ', угл. сек'); }));
  $('vzr-play').onclick = () => { playing = !playing; $('vzr-play').textContent = playing ? 'Пауза' : 'Играть'; };
  $('vzr-speed').addEventListener('input', (e) => { speed = +e.target.value; $('vzr-sv').textContent = String(speed).replace('.', ',') + ' цикла/с'; });
  if ('IntersectionObserver' in window) new IntersectionObserver((es) => { visible = es[0].isIntersecting; }, { threshold: 0.05 }).observe(root);
  drawSys(); chart($('vzr-c1'), 'target', 'невязка цели'); chart($('vzr-c2'), 'next', 'невязка соседней планеты'); requestAnimationFrame(frame);
})();
</script>
"""

CHARTS_HTML = r"""
<div class="vz" id="vz-ocheck">
  <svg id="vzo2-plot" viewBox="0 0 760 420" role="img" aria-label="Скрытая проверка по орбитальным эпизодам"></svg>
  <p class="vz-note">Строка — мир и истинный механизм; точки — эпизоды агента (● меню, ○ без меню, <span style="color:#16a34a">■</span> меню + готовые симуляторы обеих гипотез; наведите курсор). Метки того же мира: серая — шумовой пол, синяя — эталонный решатель, оранжевая — учебный ответ («поправка как в ОТО, тела нет»), красная — противоположный механизм. Лог-шкала, меньше — лучше.</p>
</div>
<script>
(function () {
  const R = __DATA__, NS = 'http://www.w3.org/2000/svg';
  const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const fmt = (x) => x === null || x === undefined ? '–' : (x >= 0.01 ? x.toFixed(3) : x.toExponential(1));
  const svg = document.getElementById('vzo2-plot');
  const key = (r) => r.world_seed + '|' + r.truth, rows = [];
  R.forEach((r) => { if (r.check_ed !== null && !rows.includes(key(r))) rows.push(key(r)); });
  rows.sort((a, b) => { const [sa, ta] = a.split('|'), [sb, tb] = b.split('|'); return ta === tb ? (+sa - +sb) : (ta < tb ? -1 : 1); });
  const W = 760, L = 150, Rr = 14, T = 16, rowH = Math.max(18, Math.min(34, 360 / Math.max(rows.length, 1))), H = T + rows.length * rowH + 40;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const lo = -2.5, hi = 1.5, X = (v) => L + (Math.log10(Math.max(v, 3e-3)) - lo) / (hi - lo) * (W - L - Rr);
  for (let d = Math.ceil(lo); d <= hi; d++) { el('line', { x1: X(Math.pow(10, d)), x2: X(Math.pow(10, d)), y1: T - 4, y2: H - 34, class: 'tick' }, svg); const t = el('text', { x: X(Math.pow(10, d)), y: H - 20, 'text-anchor': 'middle', 'font-size': 10 }, svg); t.textContent = '1e' + d; }
  const xl = el('text', { x: (L + W) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 11 }, svg); xl.textContent = 'средняя энергетическая дистанция до истины на скрытой проверке, в единицах σ (лог-шкала)';
  rows.forEach((k, i) => {
    const [seed, truth] = k.split('|'), y = T + i * rowH + rowH / 2, rs = R.filter((r) => key(r) === k && r.check_ed !== null);
    if (i % 2 === 0) el('rect', { x: 0, y: y - rowH / 2, width: W, height: rowH, fill: 'currentColor', opacity: 0.04 }, svg);
    const lab = el('text', { x: 8, y: y + 4, 'font-size': 11 }, svg); lab.textContent = 'мир ' + seed + ' · ' + (truth === 'body' ? 'тело' : 'сила');
    const a = rs[0], mark = (v, c) => { if (v === null || v === undefined) return; el('line', { x1: X(v), x2: X(v), y1: y - rowH * 0.38, y2: y + rowH * 0.38, stroke: c, 'stroke-width': 2.5, opacity: 0.85 }, svg); };
    mark(a.floor, 'currentColor'); mark(a.ref, '#2a78d6'); mark(a.textbook, '#eb6834'); mark(a.opposite, '#dc2626');
    rs.forEach((r, j) => { const cx = X(r.check_ed), cy = y + (j % 5 - 2) * rowH * 0.12; const c = r.tools ? el('rect', { x: cx - 4.5, y: cy - 4.5, width: 9, height: 9, fill: '#16a34a', stroke: 'currentColor', 'stroke-width': 1, opacity: 0.85 }, svg) : el('circle', { cx, cy, r: 5, fill: r.menu ? 'currentColor' : 'none', stroke: 'currentColor', 'stroke-width': 1.6, opacity: 0.85 }, svg); const tt = el('title', {}, c); tt.textContent = r.run + '\n' + (r.tools ? 'меню + инструменты' : r.menu ? 'меню' : 'без меню') + ', повтор ' + r.rep + '\nпроверка ' + fmt(r.check_ed) + ' (эталон ' + fmt(r.ref) + ', учебный ' + fmt(r.textbook) + ')\nитог ' + r.final_class + ', доверие к истине ' + fmt(r.final_P_true) + '\nизмерения: ' + r.meas + '\nпересмотры: ' + r.revisions.join(', '); });
  });
})();
</script>
"""


def world_data(seed: int) -> dict:
    s = ow.system(seed)
    rb, _ = ow.body_truth(seed)
    rf = ow.force_truth(seed)
    t = np.linspace(0.0, 15.0, 301)
    a_b, ph, m, _ = ow.body_params(seed)
    series = lambda r: {"target": ow.at(r[:, 0], t).round(3).tolist(), "next": ow.at(r[:, 1], t).round(3).tolist()}  # noqa: E731
    return {
        "gm": ow.GM_C, "t": t.round(3).tolist(),
        "planets": [{"name": ow.PLANETS[i], "a": float(s.elements[i, 0]), "e": float(s.elements[i, 1]),
                     "w": float(s.elements[i, 2]), "L0": float(s.elements[i, 3])} for i in range(4)],
        "body": {"a": a_b, "ph": ph, "n": math.sqrt(ow.GM_C / a_b**3), "frac": m / ow.GM_C, **series(rb)},
        "force": series(rf),
    }


def _f(x, nd=3):
    if x is None:
        return "–"
    if isinstance(x, bool):
        return "да" if x else "нет"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def _meas(m: dict) -> str:
    t = m["type"]
    if t == "planet":
        return f"планета {m['planet']}"
    if t == "dense":
        return f"плотная с {m['start']:g}"
    if t == "search":
        return f"поиск t={m['time']:g} [{m['lon_min']:.0f}°, {m['lon_max']:.0f}°]"
    return "продление"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=str(REPO / "runs_episode"))
    ap.add_argument("--world-seed", type=int, default=0)
    ap.add_argument("--baselines", default=str(REPO / "results/episode/orbit-baselines-20261116"))
    a = ap.parse_args()
    from make_report import CSS  # same styles as the decay part

    wd = world_data(a.world_seed)
    (HERE / "_anim_orbit_world.html").write_text(
        CSS + WORLD_HTML.replace("__SEED__", str(a.world_seed)).replace("__DATA__", json.dumps(wd, separators=(",", ":"))))
    rows = [r for r in collect_runs(Path(a.runs_root)) if r.get("family") == "orbit" and r["status"] == "ok"]
    rows.sort(key=lambda r: (r["truth"], r["world_seed"], bool(r.get("tools")), not r["menu"], r["rep"]))
    slim = [{**{k: r.get(k) for k in ("run", "world_seed", "truth", "menu", "tools", "rep", "check_ed", "ref", "textbook", "floor",
                                      "opposite", "final_class", "final_P_true", "revisions")},
             "meas": "; ".join(_meas(m) for m in r["measurements"])} for r in rows]
    (HERE / "_orbit_charts.html").write_text(CHARTS_HTML.replace("__DATA__", json.dumps(slim, separators=(",", ":"), default=float)))
    lines = ["| мир | истина | условие | повтор | измерения (B1; B2) | доля от лучшего | доверие к телу на B1 | пересмотры | итог | доверие к истине | сверхуверен. | проверка | эталон | учебный | $ |",
             "|---:|---|---|---:|---|---|---:|---|---|---:|---|---:|---:|---:|---:|"]
    for r in rows:
        cond = "меню + инструменты" if r.get("tools") else ("меню" if r["menu"] else "без меню")
        lines.append("| " + " | ".join([str(r["world_seed"]), "тело" if r["truth"] == "body" else "сила", cond, str(r["rep"]),
                                         "; ".join(_meas(m) for m in r["measurements"]),
                                         ", ".join(_f(x, 2) for x in r["frac_best"]), _f(r["B1_P_body"], 2),
                                         ", ".join((v or "–").replace("_", " ") for v in r["revisions"]),
                                         _f(r["final_class"]), _f(r["final_P_true"], 2), _f(r["overconfident_any"]),
                                         _f(r["check_ed"]), _f(r["ref"]), _f(r["textbook"]), _f(r["cost_usd"], 2)]) + " |")
    md = "\n".join(lines) + "\n"
    bdir = Path(a.baselines)
    if (bdir / "summary.json").exists():
        md += "\n### Локальные baseline (орбиты)\n\n| политика | условие | истина | класс верен | доверие к истине | сверхуверен. | проверка | пол | противоп. | доля информативности 1-го измерения |\n|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n"
        for s in json.loads((bdir / "summary.json").read_text()):
            md += "| " + " | ".join([s["policy"], s["condition"], s["mechanism"], _f(s["final_class_correct"], 2), _f(s["final_P_true"], 2),
                                     _f(s["overconfident_final"], 2), _f(s["check_ed"]), _f(s["check_floor"]), _f(s["check_opposite"]),
                                     _f(s["design_frac_menu_max_step1"], 2)]) + " |\n"
    (HERE / "_orbit_tables.md").write_text(md)
    n = len(rows)
    ok = sum(r["final_class"] == r["truth"] for r in rows)
    ratios = [r["check_ed"] / r["ref"] for r in rows if r["check_ed"] and r["ref"]]
    cost = sum(r["cost_usd"] or 0 for r in rows)
    first = {}
    for r in rows:
        if r["measurements"]:
            k = r["measurements"][0]["type"]
            first[k] = first.get(k, 0) + 1
    cells = [(str(n), "орбитальных эпизодов агента"), (f"{ok}/{n}", "верный механизм в финале"),
             (", ".join(f"{k} {v}" for k, v in sorted(first.items(), key=lambda x: -x[1])) or "–", "первое измерение"),
             (f"{np.median(ratios):.1f}×" if ratios else "–", "медиана: проверка агента / эталон"), (f"${cost:.2f}", "стоимость")]
    kpi = "::: {.grid .kpi}\n" + "".join(f"::: {{.g-col-6 .g-col-md-2}}\n[{v}]{{.kpi-num}}\n[{l}]{{.kpi-label}}\n:::\n" for v, l in cells) + ":::\n"
    (HERE / "_orbit_kpi.md").write_text(kpi)
    print(f"orbit episodes: {n}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE))
    main()
