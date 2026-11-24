#!/usr/bin/env python3
"""Generate the merged 'slide 2 + 2a' timeline and patch it into slides_en.md and slides.md.

Five benchmark stages: a card per stage (examples, what the agent does not know, lesson) on top, a stack of
period bars on the time axis below, a leader line from each bar to its card.
The time scale is piecewise: 1950-2020 on the left, a break, then 2021-2026 stretched (2026 in halves).
Idempotent: replaces everything from '## 2. ' up to the '## 3. ' slide.
"""
import re
import sys
from pathlib import Path

W = 1168
STAGE_COL = ["#4F6D99", "#008CE3", "#00A987", "#FFC622", "#DB4F3D"]
STAGE_TXT = ["#fff", "#fff", "#fff", "#00204D", "#fff"]
NAVY = "#00204D"


def xl(y):  # 1950..2020
    return 20 + (y - 1950) * 10.4


X2021 = 800


def xr(y):  # 2021..2027, 2026 split in two 60 px halves
    if y <= 2026:
        return X2021 + (y - 2021) * 46
    return X2021 + 5 * 46 + (y - 2026) * 120


CARD_H = 306
GANT_Y = CARD_H + 56  # top of the stack of period bars
ROW = 16
AXIS_Y = GANT_Y + 5 * ROW + 12
H = AXIS_Y + 30

TXT = {
    "en": {
        "h": "2. How the field developed: five stages",
        "stages": [
            ("Law from a table", "1977–2021", "AI Feynman, SRBench",
             "a table of numbers from a formula", "a formula", "exact symbolic match", "code (sympy)"),
            ("Realizing contamination", "2022–2025", "SRSD, LLM-SR, LLM-SRBench",
             "a table; the formula may be memorized (renamed and synthetic tasks)", "a formula",
             "error in and out of range, symbolic accuracy", "code; in LLM-SRBench a GPT-4o judge"),
            ("Active experimentation", "2024–2025", "DiscoveryWorld, PhysGym, NewtonBench, Gravity-Bench",
             "an environment: the agent chooses the measurements", "a formula or a number",
             "formula equivalent to the reference; number within a threshold",
             "code + an LLM for formula equivalence"),
            ("Understanding, not fitting", "2026 H1", "DiscoverPhysics, MechBench, EurekaBench, SciLaws-Bench",
             "a simulator of a world with changed physics", "a mechanism: code + explanation",
             "error on held-out data; explanation against the reference",
             "code + an LLM judge, validated only in SciLaws-Bench"),
            ("Theory revision, abduction", "2026 H2", "ULTRADISCOVERY, Unsatz, SciGame, Stargazer",
             "a world where theory T0 breaks; experiments cost a budget",
             "T0 refuted, a hidden entity, an exact prediction",
             "error on held-out experiments; evidence in the agent's log",
             "code + an LLM judge (ULTRADISCOVERY, SciGame)"),
        ],
        "k_in": "Input: ", "k_out": "Output: ", "k_sc": "Scored: ", "k_ju": "Judge: ",
        "foot": "**Stage 4: “Kepler or Newton: same orbits, the question is why”. Stage 5: “Uranus deviates: add Neptune or change the law of gravity”.**",
        "notes": """<!--
Main lesson of each stage: 1 exact symbolic match; 2 numerical fit ≠ formula found; 3 memory protection becomes a
controllable axis; 4 good prediction ≠ correct mechanism; 5 models drop the axiom but do not introduce an
unobservable entity. What the agent does not know: 1 the formula (a human chose the variables); 2 a formula the
model may have seen; 3 the formula + which measurements to make; 4 the mechanism within a given language;
5 the language itself (T0 breaks, a new quantity or entity is needed).
Judges by benchmark: LLM-SRBench GPT-4o (130 tasks, 94.6% agreement); NewtonBench Nemotron-ultra-253b (120 pairs, 98.3%);
PhysGym gemini-2.5-flash as a fallback (one of the tested models); DiscoveryWorld GPT-4o for knowledge questions;
DiscoverPhysics claude-opus-4-6 (explanation 0-10, no validation); EurekaBench Claude Opus 4.8 + GPT 5.6 Sol with
access to the simulator (no quantitative validation); SciLaws-Bench GPT-5.4-mini with code (5 experts, kappa 0.77-0.84);
MechBench, Unsatz, Stargazer, Gravity-Bench: no judge; ULTRADISCOVERY Qwen3.8-27B (kappa 0.88 / 0.75 on 51 pairs);
SciGame GPT-6 Astra (one of the tested models). Source: literature/evaluation_methods.md.
The stages differ by question, not date: the finding on entities first came from DiscoverPhysics (May 2026).
Trends: from tables to environments with a budget, from public reference answers to generation from a private
seed, from a single score to separate scoring of prediction, mechanism and process.
Before LLMs (general knowledge, not from our corpus of 64 papers; check the years before the talk):
Lindley 1956 (Bayesian experimental design, expected information gain: the EIG metric); DENDRAL (1965, structures
from spectra) and MECHEM (reaction mechanisms with unobserved intermediates); BACON, STAHL, DALTON (Langley, Simon,
1977-87: laws from tables; BACON.4 "intrinsic properties", DALTON an unobservable composition); Swanson 1986
(literature-based discovery, ancestor of the post-cutoff defense); KEKADA 1988 (the urea cycle discovery:
experiment planning, reaction to surprise); PC/FCI and TETRAD (1990s, causal graphs, FCI allows hidden common
causes); Robot Scientist Adam (2004-09, closed loop in a real lab, experiments with a cost).
The memory problem had an analogue: the critique of BACON, the programmer chose the variables and the
representation; hidden things could be postulated only within a given vocabulary. Stage 5 asks whether LLMs go
beyond it. No benchmarks in the current sense then: the test was rediscovering historical cases.
Citations: AI Feynman 1489 (growing as an SR method, not as an LLM benchmark), DiscoveryWorld 136,
DiscoveryBench 124; NewtonBench grew 10x+ in 2026. Of 37 papers with zero citations, 30 appeared in the last 3 months.
Stage 4 example: Synthetic Universes, Drag — prediction correct 5/5, mechanism 1/5; MechBench — law 35%, mechanism 13.75%.
The time axis is piecewise: 1950-2020 compressed, 2021-2026 stretched.
-->""",
    },
    "ru": {
        "h": "2. Как развивалась область: пять этапов",
        "stages": [
            ("Закон из таблицы", "1977–2021", "AI Feynman, SRBench",
             "таблица чисел из формулы", "формула", "точное символьное совпадение", "код (sympy)"),
            ("Осознание контаминации", "2022–2025", "SRSD, LLM-SR, LLM-SRBench",
             "таблица; формула могла быть в памяти (переименованные и синтетические задачи)", "формула",
             "ошибка в диапазоне и вне него, символьная точность", "код; в LLM-SRBench судья GPT-4o"),
            ("Активный эксперимент", "2024–2025", "DiscoveryWorld, PhysGym, NewtonBench, Gravity-Bench",
             "среда: агент сам выбирает измерения", "формула или число",
             "формула эквивалентна эталону; число в пределах порога",
             "код + LLM для эквивалентности формул"),
            ("Понимание, а не подгонка", "2026, 1-я пол.", "DiscoverPhysics, MechBench, EurekaBench, SciLaws-Bench",
             "симулятор мира с изменённой физикой", "механизм: код + объяснение",
             "ошибка на отложенных данных; объяснение против эталона",
             "код + LLM-судья, проверен на людях только в SciLaws-Bench"),
            ("Пересмотр теории, абдукция", "2026, 2-я пол.", "ULTRADISCOVERY, Unsatz, SciGame, Stargazer",
             "мир, где теория T0 ломается; эксперименты стоят бюджета",
             "T0 опровергнута, скрытая сущность, точный прогноз",
             "ошибка на отложенных экспериментах; свидетельства в логе агента",
             "код + LLM-судья (ULTRADISCOVERY, SciGame)"),
        ],
        "k_in": "Вход: ", "k_out": "Выход: ", "k_sc": "Оценивается: ", "k_ju": "Судья: ",
        "foot": "**Этап 4: «Кеплер или Ньютон: орбиты те же, вопрос почему». Этап 5: «Уран отклоняется: добавить Нептун или менять закон тяготения».**",
        "notes": """<!--
Главный урок этапов: 1 точное символьное совпадение; 2 численный fit ≠ найденная формула; 3 защита от памяти
становится управляемой осью; 4 хороший прогноз ≠ верный механизм; 5 от аксиомы отказываются, ненаблюдаемую
сущность не вводят. Что неизвестно агенту: 1 формула (переменные выбрал человек); 2 формула, которую модель
могла видеть; 3 формула + какие измерения делать; 4 механизм внутри заданного языка; 5 сам язык (T0 ломается,
нужна новая величина или сущность).
Судьи по бенчмаркам: LLM-SRBench GPT-4o (130 задач, согласие 94.6%); NewtonBench Nemotron-ultra-253b (120 пар,
98.3%); PhysGym gemini-2.5-flash как запасной (одна из испытуемых); DiscoveryWorld GPT-4o для вопросов о знании;
DiscoverPhysics claude-opus-4-6 (объяснение 0-10, без валидации); EurekaBench Claude Opus 4.8 + GPT 5.6 Sol с
доступом к симулятору (количественной валидации нет); SciLaws-Bench GPT-5.4-mini с кодом (5 экспертов, κ 0.77-0.84);
MechBench, Unsatz, Stargazer, Gravity-Bench: судьи нет; ULTRADISCOVERY Qwen3.8-27B (κ 0.88 / 0.75 на 51 паре);
SciGame GPT-6 Astra (одна из испытуемых). Источник: literature/evaluation_methods.md.
Этапы различаются вопросом, а не датой: вывод про сущности впервые получен в DiscoverPhysics (май 2026).
Тренды: от таблиц к средам с бюджетом, от публичных эталонов к генерации по приватному seed, от одного балла
к раздельной оценке предсказания, механизма и процесса.
До языковых моделей (общие знания, не из корпуса из 64 работ; годы проверить перед докладом):
Lindley 1956 (байесовский дизайн экспериментов, ожидаемый прирост информации: метрика EIG); DENDRAL (1965,
структуры по спектрам) и MECHEM (механизмы реакций с ненаблюдаемыми интермедиатами); BACON, STAHL, DALTON
(Langley, Simon, 1977-87: законы из таблиц; BACON.4 «внутренние свойства», DALTON — ненаблюдаемый состав);
Swanson 1986 (литературное открытие, предок пост-срезовой защиты); KEKADA 1988 (открытие цикла мочевины:
план экспериментов, реакция на сюрприз); PC/FCI и TETRAD (1990-е, причинные графы, FCI допускает скрытые общие
причины); Robot Scientist Adam (2004-09, замкнутый цикл в реальной лаборатории, эксперименты с ценой).
Аналог проблемы памяти был и тогда: критика BACON — переменные и представление выбрал программист; скрытое
можно было постулировать только внутри заданного словаря. Этап 5 спрашивает, выходят ли за него LLM.
Бенчмарков в нынешнем смысле не было: проверкой служило повторное открытие исторических случаев.
Цитирования: AI Feynman 1489 (растёт как метод СР, а не бенчмарк для LLM), DiscoveryWorld 136,
DiscoveryBench 124; NewtonBench вырос в 10+ раз за 2026. Из 37 работ с нулём цитирований 30 вышли за последние 3 месяца.
Этап 4, пример: Synthetic Universes, Drag — прогноз верен 5/5, механизм 1/5; MechBench — закон 35%, механизм 13.75%.
Ось времени кусочная: 1950-2020 сжаты, 2021-2026 растянуты.
-->""",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_bold(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


SPANS = [(xl(1977), X2021), (xr(2022), xr(2026)), (xr(2024), xr(2026)), (xr(2026), xr(2026.5)), (xr(2026.5), xr(2027))]


def build(lang):
    t = TXT[lang]
    svg = []
    cgap = 12
    ccw = (W - 4 * cgap) / 5
    for i, (a, b) in enumerate(SPANS):  # stage 1 nearest the axis, later stages stacked upwards
        y = GANT_Y + (4 - i) * ROW
        lx = a + 8
        cx = i * (ccw + cgap) + ccw / 2
        svg.append(f'<polyline points="{lx:.1f},{y} {lx:.1f},{GANT_Y-10} {cx:.1f},{CARD_H+8}" fill="none" stroke="{STAGE_COL[i]}" stroke-opacity=".75" stroke-width="1.3"/>')
        svg.append(f'<rect x="{a:.1f}" y="{y}" width="{b-a:.1f}" height="{ROW-4}" rx="3" fill="{STAGE_COL[i]}"/>')
        svg.append(f'<circle cx="{lx:.1f}" cy="{y+(ROW-4)/2:.1f}" r="4" fill="#fff"/>')
        svg.append(f'<text x="{b-12:.1f}" y="{y+ROW-6:.1f}" font-size="10.5" font-weight="700" fill="{STAGE_TXT[i]}">{i+1}</text>')
    svg.append(f'<line x1="20" y1="{AXIS_Y}" x2="758" y2="{AXIS_Y}" stroke="{NAVY}" stroke-width="2"/>')
    svg.append(f'<line x1="{X2021-14}" y1="{AXIS_Y}" x2="{W-4}" y2="{AXIS_Y}" stroke="{NAVY}" stroke-width="2"/>')
    svg.append(f'<polygon points="{W-2},{AXIS_Y} {W-10},{AXIS_Y-4} {W-10},{AXIS_Y+4}" fill="{NAVY}"/>')
    for dx in (764, 776):
        svg.append(f'<line x1="{dx}" y1="{AXIS_Y-6}" x2="{dx+8}" y2="{AXIS_Y+6}" stroke="{NAVY}" stroke-width="2"/>')

    def tick(x, label, anchor="middle", bold=False):
        svg.append(f'<line x1="{x:.1f}" y1="{AXIS_Y-4}" x2="{x:.1f}" y2="{AXIS_Y+4}" stroke="{NAVY}" stroke-width="1.5"/>')
        svg.append(f'<text x="{x:.1f}" y="{AXIS_Y+18}" font-size="12" text-anchor="{anchor}" fill="#004381" font-weight="{700 if bold else 400}">{label}</text>')

    for yr in (1950, 1975, 2000):
        tick(xl(yr), yr, "start" if yr == 1950 else "middle")
    for yr in range(2021, 2027):
        tick(xr(yr), yr, bold=True)

    out = [f'<div class="tl" style="height:{H}px">']
    out.append(f'<svg class="tl-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="inherit">{"".join(svg)}</svg>')
    for i, (name, yrs, ex, inp, outp, sc, ju) in enumerate(t["stages"]):
        x = i * (ccw + cgap)
        rows = "".join(f'<div class="tl-p"><b>{t[k]}</b>{esc(v)}</div>' for k, v in
                       (("k_in", inp), ("k_out", outp), ("k_sc", sc), ("k_ju", ju)))
        out.append(
            f'<div class="tl-card" style="left:{x:.1f}px;width:{ccw:.1f}px;height:{CARD_H}px;border-top-color:{STAGE_COL[i]}">'
            f'<div class="tl-ct"><span class="tl-n" style="background:{STAGE_COL[i]};color:{STAGE_TXT[i]}">{i+1}</span>{esc(name)}</div>'
            f'<div class="tl-y">{esc(yrs)}</div><div class="tl-ex">{esc(ex)}</div>{rows}</div>'
        )
    out.append("</div>")
    html = "\n".join(out)
    return f"## {t['h']}\n\n{html}\n\n<p class=\"tl-foot\">{md_bold(t['foot'])}</p>\n\n{t['notes']}\n"


def patch(path, lang):
    p = Path(path)
    s = p.read_text()
    if "slide2_timeline_" in s and "--force" not in sys.argv:  # slide 2 is an edited drawio export
        print("skip", p.name, "(slide 2 is an image; pass --force to regenerate)")
        return
    new = build(lang)
    pat = re.compile(r"## 2\. .*?(?=\n---\n\n## 3\. )", re.S)
    assert len(pat.findall(s)) == 1, path
    s = pat.sub(lambda m: new.rstrip("\n") + "\n", s)
    p.write_text(s)


if __name__ == "__main__":
    here = Path(__file__).parent
    patch(here / "slides_en.md", "en")
    patch(here / "slides.md", "ru")
    print("patched slides_en.md and slides.md")
