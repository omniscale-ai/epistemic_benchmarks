# Минимальный реальный прогон эпизода (подготовлен, НЕ запускался)

Запуск требует отдельного разрешения: каждый вызов `run` без `--dry-run` — платный прогон `claude -p`.

## Предварительные бесплатные проверки

```bash
cd /home/mark/Desktop/Projects/ARIA/epistemic_benchmarks
PYTHONPATH=src .venv/bin/python -m abductbench.episode.cli sandbox-check      # репозиторий скрыт, numpy есть, claude --version
PYTHONPATH=src .venv/bin/python -m abductbench.episode.cli run --world-seed 0 --mechanism carrier --dry-run
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_episode_*.py
```

## Прогон: 4 эпизода

Один агент (`sonnet`), меню включено, условие `ambiguous`, один повтор. Миры 0 и 7: в обоих начальные
данные неоднозначны для обоих механизмов (|Δℓ| < 1 нат, см. `results/episode/.../posterior_initial.json`).

```bash
for ws in 0 7; do for mech in carrier loss; do
  PYTHONPATH=src .venv/bin/python -m abductbench.episode.cli run \
    --world-seed $ws --mechanism $mech --obs-seed 0 --rep 0 --condition ambiguous --menu \
    --runs-root runs_episode --model sonnet --timeout 3600 --max-budget-usd 3
done; done
for d in runs_episode/2026*; do PYTHONPATH=src .venv/bin/python -m abductbench.episode.cli evaluate "$d"; done
```

Ограничения прогона:
- Изоляция: `bwrap` (рабочая область `/work`, отдельный HOME с копией файла учётных данных, сеть для API,
  сервер эпизода за unix-сокетом). Проверено с фиктивным агентом и `claude --version`; поведение
  настоящего `claude -p` с пустым `CLAUDE_CONFIG_DIR` (вход, первичная настройка) **не проверено** —
  первый эпизод одновременно смоук-тест. Если claude не стартует, это видно в `transcript.jsonl`; не
  запускать без изоляции.
- Внутри песочницы виден путь к установке Python (`/home/mark/.local/share/uv/python/...`), т.е. имя пользователя.
- Лимит: 3600 с и `--max-budget-usd 3` на эпизод; модели агента: 120 с CPU, 4 ГБ, без сети.
- 4 эпизода — проверка протокола и первые наблюдения, не оценка способности.

Расширение после разбора (не раньше): те же 4 мира с `--no-menu` (уровень 2: самостоятельное выдвижение),
`--condition no_data` для обоих механизмов мира 0 (контроль памяти), `--condition t0_sufficient` для одного мира.

## Схема разбора каждого эпизода

`evaluate` пишет `evaluation-*.json` и `report-*.txt` (цепочка A→B→C→D) и считает на том же мире
локальные якоря. Читать по звеньям, не сворачивая:

| звено | что смотреть | что считать свидетельством |
|---|---|---|
| A | `instance.category` | эпизод интерпретируем как абдуктивный только при `ambiguous` |
| B | классы H1/H2, `alternative_differs_in_class`, доверия vs `ref_P_carrier`, `overconfident` | агент держит две содержательно разные гипотезы и не уверен сверх данных |
| B | `design_info_own`, `design_info_ref`, доля от лучшего в меню | измерение выбрано так, что его модели расходятся (own ≫ 0) и оно реально различает (ref, доля ≈ 1) |
| C | `ed_current/ed_alternative`, `logbf ± шум`, `revision.verdict` | прогноз, записанный до измерения, разошёлся/совпал с результатом и пересмотр следует знаку свидетельства |
| D | `check_ed` против `truth floor`, `opposite`, якорей `reference_adaptive`, `textbook`, `phenomenological`, `no_data` | итоговая модель предсказывает отдачу на тонком источнике близко к эталонному решателю и заметно лучше учебного ответа и подгонки |
| D | `current_consistent`, `consistency.*` | исполняемая модель ведёт себя как заявленный механизм (калориметр, толщина, кинематика отдачи при заявленной массе) |
| текст | `notes.md`, `statement`, `expected` | читается человеком; автоматически не оценивается |

Также читать `transcript.jsonl` на попытки выйти за `/work` и на использование `./episode`.
