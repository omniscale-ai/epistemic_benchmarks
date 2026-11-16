# Результаты локальных baseline эпизода (2026-11-13)

Команда: `PYTHONPATH=src .venv/bin/python -m abductbench.episode.cli baselines --seeds 0-9 --post-seeds 40 --out results/episode/baselines-20261113`
(116 с, 8 процессов; полные строки в `results/episode/baselines-20261113/`, каталог не в git).
10 миров × 2 механизма на строку. ED — энергетическое расстояние в (T/Q, p_R/p_Q); меньше — лучше.
`final_class_correct` у `no_data` — артефакт ничьей 0.5/0.5 (текущей выбирается первая гипотеза); смотреть `final_P_true`.

## Интерпретация

- **A неоднозначна по данным, а не по тексту.** По 40 мирам: |Δℓ|<3 нат у 88% миров носителя и 93% миров потерь; ни один мир
  не даёт Δℓ≥3 в пользу носителя; 12% миров носителя и 7% миров потерь «склоняются к потерям» — такие экземпляры
  помечаются `lean_loss`, а не считаются неоднозначными.
- **Простые признаки не работают:** лучший одиночный признак спектра — тест AUC 0.45–0.53; метаданные пары тождественны (50% по построению).
- **Различающее измерение есть и оно информационно отличается от бесполезного:** ожидаемый log-BF калориметра ≈ 6.8·10³ нат,
  повтора номинального спектра ≈ 1.2–1.8 нат. Неадаптивный план (повтор) оставляет класс неверным в 20–30% и даёт check ED 0.12–0.19;
  случайный план получает 43% максимальной информации и решает все 20 эпизодов.
- **D различает механизмы:** шумовой пол ≈ 1–3·10⁻⁴, противоположный механизм ≈ 0.80. Эталонный решатель: 5·10⁻⁴ / 1.5·10⁻⁴.
- **Знакомого ответа недостаточно, но в мирах носителя он близок:** «учебный» безмассовый носитель со спектром Ферми —
  check 0.0064 в мирах носителя (≈12× эталона) и 0.88 в мирах потерь. Разрыв с эталоном в мирах носителя — от массы носителя
  и Лоренц-инвариантного фазового объёма; он есть, но мал по сравнению с разрывом между механизмами.
- **Подгонки недостаточно:** феноменологический предсказатель — check 0.057 / 0.94, сверхуверенность в 80% / 50% эпизодов.
- **Пересмотр:** упрямый агент получает `unjustified_keep` 10/10 только в мире, противоречащем его гипотезе, и `justified_keep`
  10/10 в согласном; эталонный решатель в мирах потерь 5 раз обоснованно меняет начальную (носитель) гипотезу.
- **Хеджирование не штрафуется:** контроль без данных (0.5/0.5) — check 0.17/0.23, в среднем по паре лучше уверенного учебного ответа (0.0064/0.88).
- **`t0_sufficient`:** все 20 экземпляров классифицируются как `lean_*`; `no_measurement`: эталон остаётся при 0.80/0.46.

## Обнаруженные слабости измерителя (не исправлены подгонкой порогов)

1. Вердикт пересмотра относителен к **собственной** альтернативе агента: феноменологический предсказатель с «соломенной» альтернативой
   T0 получает `justified_keep` 10/10. Это компенсируется только тем, что `design_info_ref` (1.2 нат, 0.02% от лучшего) показывает
   бесполезность его измерения; читать звенья вместе.
2. Флаг сверхуверенности использует |Δℓ|<3, а апостериори — веса Акаике; сам эталон без измерений помечен сверхуверенным в 30%
   миров носителя, потому что штраф AIC за 2 лишних параметра даёт P≈0.88–0.95 при Δℓ≈0. Флаг зависит от выбора априорных.
3. После калориметра выбор механизма тривиален (log-BF в тысячи нат); свидетельство абдукции сосредоточено в выборе измерения (B)
   и количественном выводе отдачи (D), а не в трудном взвешивании свидетельств в C.

## Таблица

| policy | condition | mechanism | n | categories | final_class_correct | final_P_true | final_ref_P_true | overconfident_final | initial_fit_ed | check_ed | check_floor | check_opposite | design_info_ref_step1 | design_frac_menu_max_step1 | forecast_ed_current_step1 | revision_step1 | consistent_current |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no_data | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 0.5 | 0.799 | 0 | 0.00176 | 0.169 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| no_data | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0.5 | 0.458 | 0 | 0.00181 | 0.232 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| no_data | no_data | carrier | 10 | {'no_data': 10} | 1 | 0.5 | 0.5 | 0 | 0.00176 | 0.169 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| no_data | no_data | loss | 10 | {'no_data': 10} | 0 | 0.5 | 0.5 | 0 | 0.00181 | 0.232 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| no_data | no_measurement | carrier | 10 | {'ambiguous': 10} | 1 | 0.5 | 0.799 | 0 | 0.00176 | 0.169 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| no_data | no_measurement | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0.5 | 0.458 | 0 | 0.00181 | 0.232 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| phenomenological | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 0.9 | 0.741 | 0.8 | 0.0011 | 0.0571 | 0.000256 | 0.798 | 1.18 | 0.000184 | 0.00101 | {'justified_keep': 10} | – |
| phenomenological | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0 | 0.628 | 0.5 | 0.000866 | 0.94 | 0.000104 | 0.794 | 1.79 | 0.000291 | 0.00181 | {'justified_keep': 10} | – |
| reference_adaptive | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 1 | 1 | 0 | 0.000201 | 0.000536 | 0.000256 | 0.798 | 6.81e+03 | 1 | 0.00073 | {'justified_keep': 10} | 1 |
| reference_adaptive | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 1 | 1 | 1 | 0 | 0.000733 | 0.000153 | 0.000104 | 0.794 | 6.68e+03 | 1 | 0.429 | {'justified_keep': 5, 'justified_switch': 5} | 1 |
| reference_adaptive | no_data | carrier | 10 | {'no_data': 10} | 1 | 0.5 | 0.5 | 0 | 0.00176 | 0.169 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| reference_adaptive | no_data | loss | 10 | {'no_data': 10} | 0 | 0.5 | 0.5 | 0 | 0.00181 | 0.232 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| reference_adaptive | no_measurement | carrier | 10 | {'ambiguous': 10} | 1 | 0.799 | 0.799 | 0.3 | 0.000353 | 0.0421 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| reference_adaptive | no_measurement | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0.5 | 0.458 | 0.458 | 0.1 | 0.00102 | 0.303 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| reference_adaptive | t0_sufficient | carrier | 10 | {'lean_carrier': 10} | 1 | 1 | 1 | 0 | 0.000197 | 0.000603 | 0.000256 | 0.798 | 6.9e+03 | 1 | 0.000705 | {'justified_keep': 10} | 1 |
| reference_adaptive | t0_sufficient | loss | 10 | {'lean_loss': 10} | 1 | 1 | 1 | 0 | 0.000762 | 0.000144 | 0.000104 | 0.794 | 7.32e+03 | 1 | 0.000152 | {'justified_keep': 10} | 1 |
| reference_random | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 1 | 1 | 0 | 0.000218 | 0.000633 | 0.000256 | 0.798 | 2.94e+03 | 0.439 | 0.000646 | {'justified_keep': 10} | 1 |
| reference_random | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 1 | 1 | 1 | 0 | 0.000577 | 0.000127 | 0.000104 | 0.794 | 2.93e+03 | 0.43 | 0.264 | {'justified_keep': 4, 'justified_switch': 5, 'weak_evidence': 1} | 1 |
| reference_repeat | ambiguous | carrier | 10 | {'ambiguous': 10} | 0.8 | 0.741 | 0.741 | 0.3 | 0.000261 | 0.12 | 0.000256 | 0.798 | 1.18 | 0.000184 | 0.000735 | {'justified_keep': 1, 'justified_switch': 2, 'weak_evidence': 7} | 1 |
| reference_repeat | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0.7 | 0.628 | 0.628 | 0 | 0.000333 | 0.187 | 0.000104 | 0.794 | 1.79 | 0.000291 | 0.00147 | {'unjustified_keep': 2, 'weak_evidence': 8} | 1 |
| reference_repeat | t0_sufficient | carrier | 10 | {'lean_carrier': 10} | 1 | 1 | 1 | 0 | 0.000206 | 0.000648 | 0.000256 | 0.798 | 241 | 0.0327 | 0.000698 | {'justified_keep': 10} | 1 |
| reference_repeat | t0_sufficient | loss | 10 | {'lean_loss': 10} | 1 | 1 | 1 | 0 | 0.000472 | 0.000126 | 0.000104 | 0.794 | 5.37 | 0.00073 | 0.0016 | {'justified_keep': 3, 'unjustified_keep': 1, 'weak_evidence': 6} | 1 |
| stubborn_carrier | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 0.9 | 1 | 0 | 0.000201 | 0.000536 | 0.000256 | 0.798 | 6.81e+03 | 1 | 0.00073 | {'justified_keep': 10} | 1 |
| stubborn_carrier | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0.1 | 1 | 0 | 0.00259 | 0.756 | 0.000104 | 0.794 | 6.68e+03 | 1 | 0.864 | {'unjustified_keep': 10} | 1 |
| stubborn_loss | ambiguous | carrier | 10 | {'ambiguous': 10} | 0 | 0.1 | 1 | 0 | 0.000664 | 0.794 | 0.000256 | 0.798 | 6.81e+03 | 1 | 0.869 | {'unjustified_keep': 10} | 1 |
| stubborn_loss | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 1 | 0.9 | 1 | 0 | 0.000733 | 0.000153 | 0.000104 | 0.794 | 6.68e+03 | 1 | 0.000152 | {'justified_keep': 10} | 1 |
| textbook | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 0.95 | 1 | 0 | 0.00451 | 0.00637 | 0.000256 | 0.798 | 6.81e+03 | 1 | 0.00485 | {'justified_keep': 10} | 1 |
| textbook | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0 | 1 | 0 | 0.00498 | 0.884 | 0.000104 | 0.794 | 6.68e+03 | 1 | 0.943 | {'unjustified_keep': 10} | 1 |
| textbook | no_data | carrier | 10 | {'no_data': 10} | 1 | 0.95 | 0.5 | 1 | 0.00451 | 0.00637 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| textbook | no_data | loss | 10 | {'no_data': 10} | 0 | 0 | 0.5 | 1 | 0.00498 | 0.884 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| textbook | no_measurement | carrier | 10 | {'ambiguous': 10} | 1 | 0.95 | 0.799 | 1 | 0.00451 | 0.00637 | 0.000256 | 0.798 | – | – | – | {} | 1 |
| textbook | no_measurement | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 0 | 0 | 0.458 | 0.8 | 0.00498 | 0.884 | 0.000104 | 0.794 | – | – | – | {} | 1 |
| truth_fed | ambiguous | carrier | 10 | {'ambiguous': 10} | 1 | 1 | 1 | 0 | 0.00017 | 0.000531 | 0.000256 | 0.798 | 6.81e+03 | 1 | 0.000763 | {'justified_keep': 10} | 1 |
| truth_fed | ambiguous | loss | 10 | {'ambiguous': 8, 'lean_loss': 2} | 1 | 1 | 1 | 0 | 0.000279 | 9.09e-05 | 0.000104 | 0.794 | 6.68e+03 | 1 | 0.000152 | {'justified_keep': 10} | 1 |

Single-feature heuristic on the initial spectrum (threshold fitted on train seeds 100-299, test 0-99):

- mean: train acc 0.532, test acc 0.525, test AUC 0.519
- frac_above_0.8: train acc 0.535, test acc 0.495, test AUC 0.449
- std: train acc 0.545, test acc 0.500, test AUC 0.525
- q90: train acc 0.522, test acc 0.485, test AUC 0.506
- initial data, carrier worlds (n=40): max log-LR carrier-loss median -0.51, |dll|<3 (ambiguous): 0.88, dll>=3: 0.00, dll<=-3: 0.12; AIC P(carrier) median 0.82
- initial data, loss worlds (n=40): max log-LR carrier-loss median -1.17, |dll|<3 (ambiguous): 0.93, dll>=3: 0.00, dll<=-3: 0.07; AIC P(carrier) median 0.70
