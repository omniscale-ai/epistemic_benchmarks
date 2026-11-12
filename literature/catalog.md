# Каталог работ, связанных цитированием с разобранными бенчмарками

Дата: 2026-11-12. Как собрано: ссылки и цитирования 11 бенчмарков из `benchmark_comparison.md` (Semantic Scholar + библиографии из arXiv HTML). Исключены работы, которые только цитируют AI Feynman как метод (1434 шт., в основном прикладная символьная регрессия), и технические отчёты моделей. Всего 626 работ.

Уровни и аннотации поставлены LLM-агентами **по названию и аннотации**, полные тексты не читались. Уровни A и B стоит перепроверять при использовании. Работы, по которым есть полный разбор, отмечены ссылкой на `info.md`.

- **A** — прямое пересечение с нашим проектом, кандидаты на полный разбор: 19
- **B** — релевантные ссылки: 151
- **C** — по касательной: 272
- **D** — не по теме (в конце файла одним списком): 184

Связь: `→ X` — работа цитирует бенчмарк X; `← X` — X цитирует эту работу. Сокращения: AIF AI Feynman, LSRB LLM-SRBench, NB NewtonBench, PG PhysGym, DP DiscoverPhysics, DW DiscoveryWorld, DB DiscoveryBench, GB Gravity-Bench, SU Synthetic Universes, US Unsatz, UD ULTRADISCOVERY.


## Уровень A — прямое пересечение


### Бенчмарки открытия законов (6)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Beyond Equation Search: Conjecture-Guided Discovery with SCOPE and ClosureBench | [2610.18938](https://arxiv.org/abs/2610.18938) · [**info**](closurebench/info.md) | → AIF,LSRB,NB | 4 | SCOPE + ClosureBench (60 интерактивных задач): оценивает не уравнение, а решение сохранить/пересмотреть/отвергнуть гипотезу и отчёт с доказательствами — близко к нашей рубрике объяснения. |
| 2026 | Can LLMs Discover Scientific Laws in Real and Parallel Worlds? | [2609.01552](https://arxiv.org/abs/2609.01552) · [**info**](scilaws-bench/info.md) | → AIF,DB,DW,GB,LSRB,NB,PG | 2 | SciLaws-Bench: 118 задач по 6 дисциплинам; Real (фиксированные данные + рубрики валидности) и Parallel (синтезированный структурный вариант закона через запросы к симулятору) — почти наши этапы 1/3. |
| 2026 | MechBench: Can AI Scientific Agents Discover Mechanisms Beyond Phenomenal Laws? | [2609.35515](https://arxiv.org/abs/2609.35515) · [**info**](mechbench/info.md) | → AIF,LSRB | 1 | MechBench: отделяет восстановление феноменологического закона от механизма (probe-вопросы, мутированные механизмы против памяти); разрыв 35% vs ниже — ровно наша ось «механизм vs фит». |
| 2026 | Can LLMs Uncover Hidden Physical Laws through Free Exploration? | [2610.37649](https://arxiv.org/abs/2610.37649) · [**info**](longchang/info.md) | → DP,DW,NB,PG | 0 | LongChang: симулированные миры с изменённой физикой, LLM свободно исследуют без подсказок; лишь 1 из 12 моделей открыла (16.7%) — альтернативная физика + заметить аномалию. |
| 2026 | Testing Frontier Large Language Models' Physics Literacy in Parallel Physical Worlds | [2607.00276](https://arxiv.org/abs/2607.00276) · [**info**](parallel-physical-worlds/info.md) | → DP,NB | 0 | Четырёхэтапная диагностика (индукция→формулировка→предсказание→ревью) в параллельных мирах (F=mv, Аристотель, Decay World) с LLM-судьями; модели скатываются к стандартной физике. |
| 2026 | SciGame: Let Agents Play the Scientific Discovery Games in the Real and Counterfactual World | [2610.37919](https://arxiv.org/abs/2610.37919) · [**info**](scigame/info.md) | → GB | 0 | SciGame: пары оригинальных/контрфактических сред законов, исторический и пост-cutoff наборы, протоколы Prior-only/Fixed/Adaptive; знакомые априоры вредят, объяснения маскируют количественные провалы — прямой конкурент. |

### Абдукция и пересмотр теории (6)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Sheaf-Theoretic Transport and Obstruction for Detecting Scientific Theory Shift in AI Agents | [2605.14033](https://arxiv.org/abs/2605.14033) · [**info**](sheaf-theory-shift/info.md) | → AIF,DB,DW | 2 | Пучковый (sheaf) формализм для детекции смены теории: различает деформацию внутри языка теории и его расширение на контролируемом бенчмарке — аналог «модифицировать закон vs ввести сущность». |
| 2026 | EvoSCM: Scientific Belief Revision Through Causal Model Evolution and Experimentation | [2609.01526](https://arxiv.org/abs/2609.01526) | → DP | 2 | EvoSCM: популяция SCM-гипотез, дискриминирующие эксперименты и ревизия причинных связей, латентных факторов и механизмов при расхождении с данными — метод ревизии теории с латентными сущностями. |
| 2026 | Learning to Outgrow a Theory: Experimental Discovery Beyond the Initial Hypothesis Space | [2610.07627](https://arxiv.org/abs/2610.07627) · [**info**](outgrow-a-theory/info.md) | → AIF,DP,LSRB | 0 | Ревизия класса моделей: агент предлагает структурную правку и диагностический эксперимент, когда все кандидаты упускают механизм; 89.5% при бюджете 32 эксперимента — прямой аналог «нужна ли новая сущность». |
| 2026 | Don't Let Me Ask for It: LLMs Show Deficiencies in Active Multi-Turn Information Acquisition for Abductive Inference | [2608.03388](https://arxiv.org/abs/2608.03388) · [**info**](active-abduction-probe/info.md) | → PG | 0 | Alien Abduction game: интерактивный зонд абдукции — сбор свидетельств, ревизия гипотез, остановка; модели фиксируются рано или исчерпывают бюджет — прямой аналог нашего режима. |
| 2026 | Treating the Symptom, Missing the Cause: Anatomy of a Scientific Reasoning Failure | [2611.04473](https://arxiv.org/abs/2611.04473) · [**info**](luca/info.md) | → DB | 0 | Агенты в синтетических регуляторных системах ищут скрытую неисправность: «лечат» фенотип чаще, чем диагностируют причину (Opus 4.6: 100% vs 55%); прямой аналог mechanism-vs-fit и абдукции скрытой причины. |
| 2024 | IDEA: Enhancing the Rule Learning Ability of Large Language Model Agent through Induction, Deduction, and Abduction | [2408.10455](https://arxiv.org/abs/2408.10455) | → DW | 31 | RULEARN/IDEA: бенчмарк интерактивного обучения правилам и агент с циклом абдукция–дедукция–индукция, сравнение с людьми — прямой прецедент абдукции в интерактивной среде. |

### Методология оценки (2)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | AI scientists produce results without reasoning scientifically | [2604.18805](https://arxiv.org/abs/2604.18805) · [**info**](ai-scientists-without-reasoning/info.md) | ← DP | 24 | 25 000 прогонов ИИ-учёных в 8 доменах: свидетельства игнорируются в 68% трасс, ревизия через опровержение лишь в 26% — обоснование оценивать процесс ревизии, а не ответ. |
| 2026 | Position: Correct Answer, Wrong Mechanism - When AI Scientists Defend General Claims Their Own Data Contradicts | [2606.23175](https://arxiv.org/abs/2606.23175) · [**info**](correct-answer-wrong-mechanism/info.md) | → DW; ← SU | 6 | Correct Answer, Wrong Mechanism: агенты переоткрывают наблюдаемое в Geant4, в 4/20 верный результат с неверным механизмом, при ложном приоре — прямой довод за оценку механизма, а не фита. |

### Активный эксперимент (2)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | LUCA: A Synthetic World for Experimental Reasoning | [2611.03100](https://arxiv.org/abs/2611.03100) · [**info**](luca/info.md) | → DB,DW | 1 | LUCA: синтетический мир с бюджетным экспериментированием, диагностикой скрытых неисправностей и полной истиной; разделяет выбор эксперимента, предсказание и диагноз (разброс 7x vs 1.4x). |
| 2025 | BoxingGym: Benchmarking Progress in Automated Experimental Design and Model Discovery | [2501.01540](https://arxiv.org/abs/2501.01540) · [**info**](boxinggym/info.md) | ← US | 28 | BoxingGym: 10 интерактивных сред с EIG-оценкой дизайна экспериментов и оценкой объяснения через предсказания другого агента; эталон для нашего режима с бюджетом и оценки объяснений. |

### Скрытые сущности / латентные переменные (1)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | CausaLab: A Scalable Environment for Interactive Causal Discovery Toward AI Scientists | [2605.26029](https://arxiv.org/abs/2605.26029) · [**info**](causalab/info.md) | → DW; ← UD | 10 | CausaLab: интерактивное открытие случайной скрытой SCM, нельзя вспомнить ответ; GPT-5.2 даёт 92% точности предсказания, но F1 рёбер 0.47 — разрыв предсказания и механизма. |

### Контаминация и запоминание (1)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Are We Measuring Scientific Intelligence? Rethinking the Evaluation of AI Scientists | [2610.04915](https://arxiv.org/abs/2610.04915) · [**info**](evidence-grounded-accuracy/info.md) | → DB | 2 | Evidence-grounded accuracy: данные с удалённым/обращённым свидетельством; Claude 95% точности, но 83% без данных и лишь 41% заземлённо — ключевой метод отделить открытие от априорного знания. |

### Бенчмарки агентов-учёных (1)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Stargazer: A Scalable Model-Fitting Benchmark Environment for AI Agents under Astrophysical Constraints | [2604.15664](https://arxiv.org/abs/2604.15664) · [**info**](stargazer/info.md) | → GB | 4 | Stargazer: 120 задач фитинга RV-данных экзопланет; агенты дают хороший фит, но не восстанавливают физические параметры — прямо про mechanism-vs-fit в физической интерактивной среде. |

## Уровень B — релевантные


### LLM-методы символьной регрессии (26)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Think like a Scientist: Physics-guided LLM Agent for Equation Discovery | [2602.12259](https://arxiv.org/abs/2602.12259) | → AIF,LSRB; ← DP | 23 | Физически-направляемый LLM-агент для открытия уравнений (сначала симметрии/структура, потом SR); цитируется DiscoverPhysics. |
| 2026 | A Probabilistic Framework for LLM-Based Model Discovery | [2602.18266](https://arxiv.org/abs/2602.18266) | → AIF; ← DP | 10 | ModelSMC: открытие механистических моделей как вероятностный вывод (SMC с LLM-предложениями) с posterior predictive checks. |
| 2026 | Learning to Design SR Solvers: Harness Optimization for Symbolic Regression | [2610.16966](https://arxiv.org/abs/2610.16966) | → AIF,LSRB | 4 | Оптимизация harness агентного SR (промпты, workflow) как отдельной цели; важно для честного сравнения агентов. |
| 2026 | From Score to Diagnosis: Search-Independent Post-Diagnosis for Symbolic Regression | [2610.24535](https://arxiv.org/abs/2610.24535) | → AIF,LSRB | 3 | Пост-диагностика SR-кандидатов: объясняет, почему скелет уравнения не подходит, независимо от поисковика. |
| 2026 | Prior-Guided Symbolic Regression: Towards Scientific Consistency in Equation Discovery | [2602.13021](https://arxiv.org/abs/2602.13021) | → AIF,LSRB | 2 | Prior-guided SR против «псевдо-уравнений», которые фитят данные, но нарушают научные принципы. |
| 2026 | FunctionEvolve: Structure-Guided Symbolic Regression with LLMs | [2606.07704](https://arxiv.org/abs/2606.07704) | → AIF,LSRB | 1 | FunctionEvolve: LLM-SR со структурно-направленными мутациями. |
| 2026 | Programmatic Context Augmentation for LLM-based Symbolic Regression | [2605.03101](https://arxiv.org/abs/2605.03101) | → AIF,LSRB | 1 | Программная аугментация контекста для LLM-SR. |
| 2026 | LegoSR: A Unified Framework for Self-improving Agent-Guided Scientific Discovery | [2610.33465](https://arxiv.org/abs/2610.33465) | → AIF,LSRB | 0 | LegoSR: самоулучшающийся агентный SR, переиспользующий частичные структуры из неудачных поисков. |
| 2026 | DIGEST: Discovery-Guided LLM Tuning for Symbolic Regression | [2610.33880](https://arxiv.org/abs/2610.33880) | → AIF,LSRB | 0 | DIGEST: дообучение LLM для символьной регрессии на траекториях открытия; LLM-SR метод. |
| 2026 | L2G-SR: Learning to Guide LLM-based Symbolic Regression | [2610.20685](https://arxiv.org/abs/2610.20685) | → AIF,LSRB | 0 | L2G-SR: LLM-SR с обученным структурным верификатором, чтобы не предпочитать точный суррогат правильной структуре — проблема «fit vs mechanism». |
| 2026 | RISR: Residual-Informed Scientific Equation Discovery with Large Language Models | [2610.11387](https://arxiv.org/abs/2610.11387) | → AIF,LSRB | 0 | RISR: LLM-SR, направляемый структурой остатков по входам — ср. наш сценарий анализа невязок T0. |
| 2026 | SRHarness: A Harness for Agentic Symbolic Regression | [2609.35501](https://arxiv.org/abs/2609.35501) | → LSRB,NB | 0 | SRHarness: инфраструктура для агентного SR (оценивается на NewtonBench). |
| 2026 | SymbolicLM: Training Language Models as Symbolic Regressors | [2609.33594](https://arxiv.org/abs/2609.33594) | → LSRB | 0 | SymbolicLM: обучение LLM как символьных регрессоров. |
| 2025 | AlphaEvolve: A coding agent for scientific and algorithmic discovery | [2506.13131](https://arxiv.org/abs/2506.13131) | ← DP,SU,UD | 1192 | AlphaEvolve: эволюционный кодовый агент на LLM для научных и алгоритмических задач; сильный бейзлайн поиска программ/формул. |
| 2025 | SR-Scientist: Scientific Equation Discovery With Agentic AI | [2510.11661](https://arxiv.org/abs/2510.11661) | → LSRB | 46 | SR-Scientist: агентный LLM-фреймворк открытия уравнений с инструментами анализа данных; сильный бейзлайн. |
| 2025 | DrSR: LLM based Scientific Equation Discovery with Dual Reasoning from Data and Experience | [2506.04282](https://arxiv.org/abs/2506.04282) | → AIF,LSRB | 35 | DrSR: LLM-SR с двойным рассуждением по данным и накопленному опыту. |
| 2025 | LLM-Feynman: Leveraging Large Language Models for Universal Scientific Formula and Theory Discovery | [2503.06512](https://arxiv.org/abs/2503.06512) | → AIF; ← PG | 16 | LLM-Feynman: LLM-фреймворк открытия формул и теорий с интерпретацией; цитируется PhysGym. |
| 2025 | AI-Newton: A Concept-Driven Physical Law Discovery System without Prior Physical Knowledge | [2504.01538](https://arxiv.org/abs/2504.01538) | ← NB | 9 | AI-Newton: концептуальная система открытия физических законов без априорных знаний; родственная задача переоткрытия. |
| 2025 | Mimicking the Physicist's Eye:A VLM-centric Approach for Physics Formula Discovery | [2508.17380](https://arxiv.org/abs/2508.17380) | → AIF,DB,LSRB | 7 | VIPER-R1: VLM открывает физические формулы по видео движения, а не только по таблицам. |
| 2024 | LLM-SR: Scientific Equation Discovery via Programming with Large Language Models | [2404.18400](https://arxiv.org/abs/2404.18400) | → AIF; ← DP,PG,SU,US | 173 | LLM-SR: открытие уравнений как программ с LLM-приорами и эволюционным поиском; базовый метод и бейзлайн. |
| 2024 | Symbolic Regression with a Learned Concept Library | [2409.09359](https://arxiv.org/abs/2409.09359) | → AIF; ← LSRB | 125 | LaSR: SR с библиотекой абстрактных текстовых концептов, индуцируемых LLM. |
| 2024 | LLM and Simulation as Bilevel Optimizers: A New Paradigm to Advance Physical Scientific Discovery | [2405.09783](https://arxiv.org/abs/2405.09783) | ← GB,LSRB,PG | 120 | SGA: LLM + симуляция как двухуровневая оптимизация для физического открытия (дискретные гипотезы LLM, непрерывные параметры симулятором). |
| 2024 | Large language models for automatic equation discovery of nonlinear dynamics | [doi](https://doi.org/10.1063/5.0224297) | ← LSRB,PG | 62 | LLM для открытия уравнений нелинейной динамики (генерация и оптимизация кандидатов). |
| 2024 | In-Context Symbolic Regression: Leveraging Large Language Models for Function Discovery | [2404.19094](https://arxiv.org/abs/2404.19094) | → AIF; ← LSRB,PG | 56 | ICSR: in-context символьная регрессия — LLM итеративно улучшает функцию по данным. |
| 2024 | LLM4ED: Large Language Models for Automatic Equation Discovery | [2405.07761](https://arxiv.org/abs/2405.07761) | ← PG | 20 | LLM4ED: LLM генерирует и итеративно оптимизирует уравнения (в т.ч. PDE) из данных; базовый LLM-метод открытия уравнений для сравнения. |
| 2023 | Mathematical discoveries from program search with large language models | [doi](https://doi.org/10.1038/s41586-023-06924-6) | ← DW,SU | 1619 | FunSearch: LLM + эволюционный поиск программ даёт новые математические результаты; базовый метод LLM-поиска, применяемый к SR. |

### Методология оценки (20)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | The need for verification in artificial intelligence-driven scientific discovery. | [doi](https://doi.org/10.1098/rsta.2024.0591) | → AIF; ← SU | 6 | Nature-перспектива о необходимости верификации гипотез, генерируемых ИИ в науке; цитируется synthetic-universes. |
| 2026 | Scores Alone Do Not Prove Discovery: The Discovery Certification Protocol for Auditing AI Research Agents | [2609.09219](https://arxiv.org/abs/2609.09219) | → DW | 3 | Discovery Certification Protocol: аудит заявленного открытия агентом через проверку восстановимости контрольными агентами; методология отличения открытия от утечки. |
| 2026 | TruthInsightBench: An Evidence-Grounded Benchmark for Automated Evaluation of Open-Ended Scientific Discovery Agents | [2609.05079](https://arxiv.org/abs/2609.05079) · [**info**](truthinsightbench/info.md) | → DB,DW | 3 | TruthInsightBench: доказательная автоматическая оценка открытых научных агентов вместо воспроизведения скрытого исследования; релевантно для LLM-судьи. |
| 2026 | StatefulDiscovery: Evidence-Calibrated Claim Formation in Open-Ended Scientific Discovery | [2606.11851](https://arxiv.org/abs/2606.11851) | → DB | 2 | StatefulDiscovery: связывает исследование с калибровкой утверждений по доказательствам, избегая переинтерпретации; релевантно оценке границ применимости. |
| 2026 | Open-Endedness Bench: Measuring Epistemic Process from Agent Records | [2610.02588](https://arxiv.org/abs/2610.02588) · [**info**](open-endedness-bench/info.md) | → DW | 1 | OEB: оценка эпистемического процесса агента по логам (граф событий: доказательства, эксперимент, ревизия, отсутствие reward hacking) без эталона; полезно для рубрики. |
| 2026 | OpenDiscoveryTrace: Process Traces for Evaluating AI Scientist Workflows | [2609.09203](https://arxiv.org/abs/2609.09203) | → DB | 1 | OpenDiscoveryTrace: 558 траекторий научных агентов с пошаговыми следами для аудита процесса, а не только ответа; полезно для оценки процесса рассуждений. |
| 2026 | Observable-Specific Validity Tests for Scientific AI: Controlled Approximations and Intervention Response | [2610.41939](https://arxiv.org/abs/2610.41939) | → AIF,LSRB,PG | 0 | Формализует «записи валидности» аппроксимации (домен, допуск, интервенции); полезно для оценки границ применимости закона, а не только точности. |
| 2026 | On the post-hoc Evaluation of PDE Discovery: A Multifaceted Challenge of Scientific Advancement | [2607.23753](https://arxiv.org/abs/2607.23753) | → AIF,LSRB | 0 | Пост-hoc оценка открытия PDE: многогранные метрики помимо точности; полезно для метрик восстановления закона. |
| 2026 | ERBench: A Benchmark and Testsuite for Equation Discovery Algorithms | [2606.09276](https://arxiv.org/abs/2606.09276) · [**info**](erbench/info.md) | → AIF,LSRB,PG | 0 | ERBench: бенчмарк и тестсьют для алгоритмов открытия уравнений, оценка по точности и восстановлению известных уравнений. |
| 2026 | Know When the Equation Is Wrong: Structural Uncertainty for LLM-Guided Symbolic Regression under Extrapolation | [2610.42024](https://arxiv.org/abs/2610.42024) | → LSRB | 0 | LLM-SR-UQ: структурная неопределённость по конкурирующим формам уравнения при экстраполяции — релевантно оценке границ применимости. |
| 2026 | The Verifier Is Part of the Simulator: Evidence-View Gaming in Agentic Equation Discovery | [2611.01334](https://arxiv.org/abs/2611.01334) | → NB | 0 | Верификатор агентного открытия уравнений сам вносит ошибку дискретизации и может быть «обыгран» — предупреждение для нашего численного скоринга. |
| 2026 | When Does AI for PDEs Yield Scientific Evidence? | [2608.22504](https://arxiv.org/abs/2608.22504) | → DB | 0 | Различие точности и доказательной силы выводов AI для PDE: метрики точности и поддержки научного утверждения ранжируют модели по-разному; аргумент за оценку механизма, не фита. |
| 2025 | The Need for Verification in AI-Driven Scientific Discovery | [2509.01398](https://arxiv.org/abs/2509.01398) | → AIF,LSRB | 7 | Arxiv-версия статьи о необходимости верификации в ИИ-открытиях; дубликат id 64. |
| 2024 | AI Agents That Matter | [2407.01502](https://arxiv.org/abs/2407.01502) | → DB | 311 | AI Agents That Matter: критика оценки агентов — учёт стоимости, переобучение на бенчмарк; важно для дизайна бюджета и честных сравнений. |
| 2024 | Agent-as-a-Judge: Evaluate Agents with Agents | [2410.10934](https://arxiv.org/abs/2410.10934) | → DW | 297 | Agent-as-a-Judge: агенты оценивают агентов по промежуточным шагам; методологический ориентир для нашего LLM-судьи. |
| 2023 | Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting | [2305.04388](https://arxiv.org/abs/2305.04388) | ← SU | 2127 | Неверные объяснения в CoT: модели не говорят, что думают; риск для оценки объяснений по рубрике. |
| 2023 | Measuring Faithfulness in Chain-of-Thought Reasoning | [2307.13702](https://arxiv.org/abs/2307.13702) | ← SU | 700 | Измерение верности CoT-рассуждений; важно для оценки объяснений агента. |
| 2022 | Rethinking Symbolic Regression Datasets and Benchmarks for Scientific Discovery | [2206.10540](https://arxiv.org/abs/2206.10540) · [**info**](srsd/info.md) | → AIF; ← LSRB,PG | 65 | SRSD: пересоздание 120 Feynman-датасетов с реалистичными диапазонами и метрикой структурной близости (NED) для «SR для научного открытия». |
| 2021 | Contemporary Symbolic Regression Methods and their Relative Performance | [2107.14351](https://arxiv.org/abs/2107.14351) | → AIF; ← LSRB,US | 487 | SRBench: открытый воспроизводимый бенчмарк 14 SR-методов; стандарт оценки SR. |
| 2007 | Strictly Proper Scoring Rules, Prediction, and Estimation | [doi](https://doi.org/10.1198/016214506000001437) | ← US | 7791 | Строго собственные скоринговые правила (Gneiting–Raftery); основа оценки вероятностных предсказаний и интервалов. |

### Контаминация и запоминание (17)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | LLMs Struggle to Balance Reasoning and World Knowledge in Causal Narrative Understanding | — | ← SU | 2 | LLM плохо балансируют рассуждение и мировое знание в каузальных нарративах «(без аннотации)»; про конфликт априора и контекста. |
| 2026 | InquiTree: Evaluating AI Agents in the Scientific Inquiry Loop with Paper-Derived Research Trees | [2606.09550](https://arxiv.org/abs/2606.09550) | → DW | 1 | InquiTree: научный поиск как дерево исследования; падение на статьях после отсечки знаний показывает роль памяти — релевантно разделению открытия и запоминания. |
| 2026 | Do Tabular Foundation Models Know Physics? Contamination, Units, and the Deterministic Limit | [2609.02766](https://arxiv.org/abs/2609.02766) | → AIF,LSRB | 0 | Табличные foundation-модели на 316 физических уравнениях: интерполируют физику, но не используют единицы и не моделируют детерминированные механизмы; контаминация в табличном режиме. |
| 2026 | In-Context Examples Suppress Scientific Knowledge Recall in LLMs | [2604.27540](https://arxiv.org/abs/2604.27540) | → LSRB | 0 | In-context примеры подавляют использование научных знаний LLM (60 задач восстановления латентной структуры) — важно для режима статической таблицы. |
| 2026 | InfiniteWorld: Separating Visual Evidence from Familiar Physics | [2610.33777](https://arxiv.org/abs/2610.33777) | → NB | 0 | InfiniteWorld: видео с изменёнными физическими параметрами; VLM упорно предпочитают земную физику вопреки данным — конфликт приора и свидетельств. |
| 2026 | BioStudyBench: Evaluating Agents on Post-Cutoff Biomedical Studies | [2610.07614](https://arxiv.org/abs/2610.07614) · [**info**](biostudybench/info.md) | → DB | 0 | BioStudyBench: 25 задач по биомедицинским исследованиям, опубликованным после cutoff, с прогоном с данными и без; полезный приём разделения анализа и памяти. |
| 2025 | LLMs, Reasoning and Plagiarism | [2601.02380](https://arxiv.org/abs/2601.02380) | ← SU | 1 | LLM, рассуждения и плагиат: синтез нового знания против воспроизведения выученного; концептуальная мотивация разделения открытия и памяти. |
| 2024 | GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in Large Language Models | [2410.05229](https://arxiv.org/abs/2410.05229) | ← LSRB | 741 | GSM-Symbolic: шаблонные варианты задач показывают хрупкость рассуждения LLM — прецедент для нашей обфускации. |
| 2024 | LiveBench: A Challenging, Contamination-Free LLM Benchmark | [doi](https://doi.org/10.48550/arXiv.2406.19314) | ← SU | 366 | LiveBench: бенчмарк без контаминации с регулярно обновляемыми задачами «(без аннотации)». |
| 2024 | LiveBench: A Challenging, Contamination-Limited LLM Benchmark | [2406.19314](https://arxiv.org/abs/2406.19314) | ← US | 313 | LiveBench: регулярно обновляемый бенчмарк с объективной оценкой против контаминации. |
| 2024 | Benchmark Data Contamination of Large Language Models: A Survey | [2406.04244](https://arxiv.org/abs/2406.04244) | ← SU | 172 | Обзор контаминации бенчмарков LLM: виды, детекция, смягчение; справочник для нашей защиты от запоминания. |
| 2024 | On Memorization of Large Language Models in Logical Reasoning | [2410.23123](https://arxiv.org/abs/2410.23123) | ← LSRB | 161 | Изучает запоминание в логических задачах (Knights&Knaves) через возмущения; методика отделения рассуждения от памяти. |
| 2023 | NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark | [2310.18018](https://arxiv.org/abs/2310.18018) | ← SU | 519 | Позиция о необходимости измерять контаминацию для каждого бенчмарка; методологическое обоснование. |
| 2023 | Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Tasks | [2307.02477](https://arxiv.org/abs/2307.02477) | ← LSRB | 392 | Reasoning or Reciting: контрфактические варианты задач выявляют опору на запомненное — методологическая основа нашего контрфактического этапа. |
| 2023 | Investigating Data Contamination in Modern Benchmarks for Large Language Models | [2311.09783](https://arxiv.org/abs/2311.09783) | ← US | 219 | Исследование контаминации современных бенчмарков LLM (поиск, угадывание пропусков); методы детекции памяти. |
| 2023 | LatestEval: Addressing Data Contamination in Language Model Evaluation through Dynamic and Time-Sensitive Test Construction | [2312.12343](https://arxiv.org/abs/2312.12343) | ← SU | 81 | LatestEval: динамические тесты из свежих текстов против контаминации; приём, аналогичный пост-cutoff наборам. |
| 2023 | Counterfactual reasoning: Testing language models’ understanding of hypothetical scenarios | [2305.16572](https://arxiv.org/abs/2305.16572) | ← SU | 42 | Контрфактические условные: могут ли LM переопределить мировое знание; основа контрфактической стадии против априоров. |

### Активный эксперимент (15)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | LLM-AutoSciLab: Closed-Loop Scientific Discovery via Active Experimentation with LLMs | [2605.24043](https://arxiv.org/abs/2605.24043) | → AIF,LSRB,NB | 11 | LLM-AutoSciLab: замкнутый цикл активного эксперимента с LLM для открытия механизмов, а не подгонки по фиксированным данным. |
| 2026 | Model Discovery Agent: LLM-assisted Bayesian experiment design for data-efficient discovery of mechanistic world models | [2608.09696](https://arxiv.org/abs/2608.09696) | ← UD | 11 | Model Discovery Agent: LLM-предложения моделей + VOI-дизайн экспериментов + байесовский вывод по латентным траекториям; сильный метод для интерактивного режима. |
| 2026 | Science-Gym: a simple testbed for AI-driven scientific discovery · [**info**](science-gym/info.md) | [doi](https://doi.org/10.1007/s10994-025-06914-x) | → AIF,DW; ← PG | 7 | Science-Gym: Gym-среда с 7 симуляциями (рычаг, бросок и др.), где агент сам собирает данные и открывает уравнение. |
| 2026 | LLM-ACES: Closed-Loop Discovery of Dynamical Systems with LLM-Guided Adaptive Search | [2606.25039](https://arxiv.org/abs/2606.25039) | → AIF,LSRB | 5 | LLM-ACES: замкнутый цикл открытия ОДУ с адаптивным выбором новых траекторий вместо фиксированного датасета. |
| 2026 | Autonomous Science Bench: Evaluating AI Agents for Autonomous Scientific Discovery | [2610.18449](https://arxiv.org/abs/2610.18449) · [**info**](autonomous-science-bench/info.md) | → DW | 2 | Autonomous Science Bench: 6 бюджетных DBTL-кампаний с гейтами «открытие» и «обучение модели»; близкий дизайн бюджетного экспериментирования. |
| 2026 | WhatWorkedBench: Benchmarking Experimental Understanding in AI Agents | [2609.27490](https://arxiv.org/abs/2609.27490) · [**info**](whatworkedbench/info.md) | → DP,DB,DW,GB | 1 | WhatWorkedBench: агенты покупают измерения поверхности отклика и восстанавливают эффекты компонентов; бюджетированные измерения близки к нашему симулятору. |
| 2026 | Explore, Then Commit: Measurement-Efficient Scientific Law Discovery with Language Models | [2610.07620](https://arxiv.org/abs/2610.07620) | → AIF,DW,LSRB,NB | 0 | Explore-then-commit протокол на NewtonBench: LLM-гипотезы + планировщик измерений сокращают число измерений в 2.5–5 раз; ориентир для нашего бюджета симуляций. |
| 2026 | LLM-IDEA: Identifiability-Driven Experimental Agent for Autonomous Discovery of Mechanistic World Models | [2610.11253](https://arxiv.org/abs/2610.11253) | → DP,GB,LSRB,NB,PG | 0 | LLM-IDEA: агент с проверкой идентифицируемости (предел способностей / решаемо / исчерпано); находит дефекты рубрики DiscoverPhysics — важно для нашей рубрики и бюджета. |
| 2026 | ACED-Bench: Evaluating How LLM Agents Acquire and Act on Causal Evidence | [2610.14381](https://arxiv.org/abs/2610.14381) · [**info**](aced-bench/info.md) | → DB,DW,NB,PG | 0 | ACED-Bench: скрытая каузальная модель, агент выбирает ≤15 экспериментов и решает; 43%→0% — пример бенчмарка с бюджетом и скрытой истиной. |
| 2026 | AdaExploreBench: Benchmarking LLM Agents for Proactive Exploration and Test-time Adaptation in Evolving Environments | [2610.25950](https://arxiv.org/abs/2610.25950) · [**info**](adaexplorebench/info.md) | → PG | 0 | AdaExploreBench: бенчмарк проактивного исследования и адаптации LLM-агентов в эволюционирующих средах; близко к интерактивному открытию правил среды. |
| 2026 | PerturbTrace: Evaluating Feedback Use by AI Co-Scientist Agents in Perturbation Discovery | [doi](https://doi.org/10.64898/2026.08.18.745260) | → DB | 0 | PerturbTrace: используют ли агенты-соучёные обратную связь между раундами при дизайне перторбационных экспериментов; релевантно интерактивному режиму с бюджетом. |
| 2025 | Auto-Discovery-Bench: Diagnosing Structured State Tracking in Oracle-Guided Discovery | [2502.15224](https://arxiv.org/abs/2502.15224) · [**info**](auto-discovery-bench/info.md) | → DW,PG | 18 | Auto-Discovery-Bench: диагностика отслеживания структурированных убеждений в оракульном открытии; изолирует предпосылку интерактивного открытия. |
| 2024 | Can foundation models actively gather information in interactive environments to test hypotheses? | [2412.06438](https://arxiv.org/abs/2412.06438) · [**info**](active-hypothesis-testing/info.md) | → DW | 9 | Feature World/Alchemy: умеют ли фундаментальные модели активно собирать информацию для проверки гипотез; бенчмарк активного тестирования гипотез. |
| 2011 | Simulation-based optimal Bayesian experimental design for nonlinear systems | [1108.4146](https://arxiv.org/abs/1108.4146) | ← US | 507 | Симуляционный байесовский оптимальный дизайн экспериментов для нелинейных систем; теория выбора измерений при бюджете. |
| 2009 | Automating Science | [doi](https://doi.org/10.1126/science.1172781) | ← SU | 83 | «Automating Science» (Robot Scientist): замкнутый цикл гипотез и экспериментов; классика активного экспериментирования. |

### Индукция моделей мира (12)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence | [2603.24621](https://arxiv.org/abs/2603.24621) | ← UD | 39 | ARC-AGI-3: интерактивные среды, где агент должен вывести динамику и цели без инструкций; индукция модели мира. |
| 2026 | DiG-bench: Discovery in Games | [2608.12593](https://arxiv.org/abs/2608.12593) · [**info**](dig-bench/info.md) | → DW,NB,PG | 4 | DiG-bench: 70 игр с неизвестными правилами преобразований, открываемыми экспериментами; часть закрыта от контаминации. |
| 2026 | Can Current Agents Close the Discovery-to-Application Gap? A Case Study in Minecraft | [2604.24697](https://arxiv.org/abs/2604.24697) | → DW | 2 | SciCrafter: Minecraft-бенчмарк цикла «открытие причинных закономерностей → применение»; интерактивное открытие правил. |
| 2026 | LatentGym: A Testbed For Cross-Task Experiential Learning With Controllable Latent Structure | [2606.15306](https://arxiv.org/abs/2606.15306) · [**info**](latentgym/info.md) | ← UD | 2 | LatentGym: среды с контролируемой латентной переменной, разделяющие исследование и эксплуатацию; полезный дизайн метрик скрытой структуры. |
| 2026 | ExplorationBench: Measuring AI Systems' Exploration in Verifiable Alien Worlds | [2609.30199](https://arxiv.org/abs/2609.30199) · [**info**](explorationbench/info.md) | → DW,NB | 1 | ExplorationBench: «чужие миры» с исполняемыми правилами, противоречащими известному знанию (AlienCode/AlienLogic), чтобы отделить исследование от припоминания. |
| 2026 | Witness: Discovery, Deciphering, and Epiphany in Interactive Puzzle Environments | [2609.32208](https://arxiv.org/abs/2609.32208) · [**info**](witness/info.md) | → PG | 0 | Witness: пазлы с выводом скрытых правил через эксперимент, лучший из 18 моделей решает 24%; родственная постановка вывода скрытых правил. |
| 2025 | CodeARC: Benchmarking Reasoning Capabilities of LLM Agents for Inductive Program Synthesis | [2503.23145](https://arxiv.org/abs/2503.23145) · [**info**](codearc/info.md) | ← PG | 21 | CodeARC: индуктивный синтез программ агентами с интерактивными запросами к оракулу — аналог интерактивного восстановления функции. |
| 2025 | One Life to Learn: Inferring Symbolic World Models for Stochastic Environments from Unguided Exploration | [2510.12088](https://arxiv.org/abs/2510.12088) · [**info**](onelife/info.md) | → DW,PG | 15 | OneLife: вывод символьной вероятностной модели мира из программных законов в стохастической среде без подсказок; индукция законов из исследования. |
| 2025 | Benchmarking World-Model Learning with Environment-Level Queries | [2510.19788](https://arxiv.org/abs/2510.19788) · [**info**](autumnbench/info.md) | → DW; ← UD | 11 | WorldTest/AutumnBench: 43 интерактивные среды, проверка модели мира запросами об интервенциях и контрфактах, люди лучше моделей; близкая методология. |
| 2022 | Towards Understanding How Machines Can Learn Causal Overhypotheses | [2206.08353](https://arxiv.org/abs/2206.08353) | ← UD | 24 | Каузальные сверхгипотезы в среде blicket detector: машины против детей; про выбор формы каузальной структуры. |
| 2018 | Toward an AI Physicist for Unsupervised Learning | [1810.10525](https://arxiv.org/abs/1810.10525) | ← AIF | 74 | «AI Physicist» (Wu, Tegmark): агент учит набор теорий, каждая со своей областью применимости, и объединяет их в theory hub — прообраз оценки границ применимости закона. |
| 2015 | Causal inference by using invariant prediction: identification and confidence intervals | [1501.01332](https://arxiv.org/abs/1501.01332) | ← SU | 1353 | Invariant causal prediction: причинность как инвариантность при вмешательствах; концептуальная основа проверки закона вне распределения. |

### Классическая символьная регрессия (12)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2023 | Interpretable Machine Learning for Science with PySR and SymbolicRegression.jl | [2305.01582](https://arxiv.org/abs/2305.01582) | ← NB | 123 | PySR / SymbolicRegression.jl: практическая SR-библиотека; стандартный бейзлайн. |
| 2020 | AI Feynman 2.0: Pareto-optimal symbolic regression exploiting graph modularity | [2006.10782](https://arxiv.org/abs/2006.10782) | → AIF; ← SU | 281 | AI Feynman 2.0: Парето-оптимальная SR с модулярностью графа; один из главных классических бейзлайнов. |
| 2020 | A Bayesian machine scientist to aid in the solution of challenging scientific problems | [2004.12157](https://arxiv.org/abs/2004.12157) | ← GB | 167 | Байесовский машинный учёный: MCMC по замкнутым формулам с априором из корпуса уравнений; важный SR-бейзлайн с явным априором. |
| 2019 | Data-driven discovery of coordinates and governing equations | [1904.02107](https://arxiv.org/abs/1904.02107) | ← US | 1137 | SINDy-автоэнкодер: совместное открытие координат и уравнений; классический бейзлайн. |
| 2019 | Deep symbolic regression: Recovering mathematical expressions from data via risk-seeking policy gradients | [1912.04871](https://arxiv.org/abs/1912.04871) | → AIF; ← LSRB,PG | 558 | DSR: глубокая SR с risk-seeking policy gradient; стандартный бейзлайн. |
| 2016 | Data-driven discovery of partial differential equations | [1609.06401](https://arxiv.org/abs/1609.06401) | ← US | 1866 | PDE-FIND: разреженная регрессия для открытия PDE по данным; классический бейзлайн. |
| 2015 | Discovering governing equations from data by sparse identification of nonlinear dynamical systems | [1509.03580](https://arxiv.org/abs/1509.03580) | ← AIF,SU,US | 5813 | SINDy (Brunton et al.): разреженная регрессия по библиотеке функций для открытия уравнений динамики; ключевой классический бейзлайн SR (5800+ цитирований). |
| 2009 | Distilling Free-Form Natural Laws from Experimental Data | [doi](https://doi.org/10.1126/science.1165893) | ← AIF,LSRB,PG,SU,US | 3355 | Schmidt & Lipson: GP-символьная регрессия, извлекающая законы сохранения и движения из экспериментальных данных маятников — классическая точка отсчёта «машинного открытия законов». |
| 2007 | Automated reverse engineering of nonlinear dynamical systems | [doi](https://doi.org/10.1073/pnas.0609476104) | ← US | 865 | Автоматическая реверс-инженерия нелинейных динамических систем (Bongard–Lipson); классика SR с активным выбором. |
| 1994 | Genetic programming as a means for programming computers by natural selection | [doi](https://doi.org/10.1007/BF00175355) | ← PG | 1643 | Коза: генетическое программирование — основа классической символьной регрессии; базовая ссылка для SR-бейзлайнов. |
| 1993 | Discovering Dynamics | [doi](https://doi.org/10.1016/b978-1-55860-307-3.50019-8) | ← PG | 55 | LAGRANGE (1993): построение систем ОДУ/алгебраических уравнений по траекториям динамических систем; классический метод открытия динамики. |
| 1977 | BACON: A Production System That Discovers Empirical Laws | — | ← PG | 60 | BACON (1977): продукционная система, переоткрывающая эмпирические законы ранней физики; исторический прародитель задачи восстановления закона. |

### Бенчмарки агентов-учёных (12)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | FIRE-Bench: Evaluating AI Agents on the Rediscovery of Scientific Insights | [2602.02905](https://arxiv.org/abs/2602.02905) · [**info**](fire-bench/info.md) | → DB | 18 | FIRE-Bench: агенты переоткрывают выводы недавних ML-статей с верифицируемой оценкой; родственный дизайн «переоткрытия». |
| 2026 | FIRE-Bench: Evaluating Agents on the Rediscovery of Scientific Insights | [doi](https://doi.org/10.48550/arXiv.2602.02905) | → DB | 17 | FIRE-Bench (дубликат): переоткрытие выводов недавних ML-статей агентами. |
| 2026 | ScienceIDE: Turning World's Scientific Codebase into Agent Learnable Environments | [2609.19134](https://arxiv.org/abs/2609.19134) · [**info**](scienceide/info.md) | → AIF,DB,DW | 7 | ScienceIDE: превращает научные кодовые базы в обучающие среды для агентов. |
| 2026 | EurekaBench: Measuring Agentic Ability to Discover New Scientific Insights | [2610.00492](https://arxiv.org/abs/2610.00492) · [**info**](eurekabench/info.md) | → DP,DB,DW,GB,LSRB,NB,PG | 2 | EurekaBench: 26 долгих задач, оценка механизмов по 306 научным инсайтам, предсказанию и соблюдению ограничений; агенты переобучаются на данных. |
| 2026 | Are LLMs Ready for Scientific Discovery? A Capability-Oriented Benchmark for AI Scientists | [2607.11079](https://arxiv.org/abs/2607.11079) · [**info**](capability-benchmark-ai-scientists/info.md) | → DB | 1 | SDABench: 6 типов научного анализа (вкл. механистический) на 527 реальных и 6000 синтетических задачах; модели проваливаются на латентных процессах и механизмах. |
| 2026 | SciExam for ENSO: Can AI Agents Build Climate Models? | [2610.10513](https://arxiv.org/abs/2610.10513) · [**info**](sciexam-enso/info.md) | → LSRB | 0 | SciExam for ENSO: могут ли агенты построить климатические модели; критика оценки по рубрике/LLM-рецензенту. |
| 2026 | CME-SpectrumBench: Can LLMs Analyze Condensed Matter Spectral Data? | [2610.24304](https://arxiv.org/abs/2610.24304) · [**info**](cme-spectrumbench/info.md) | → DB,GB | 0 | CME-SpectrumBench: LLM анализируют экспериментальные спектральные данные конденсированных сред; пример бенчмарка физического анализа реальных данных. |
| 2025 | ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery | — | ← LSRB | 54 | ScienceAgentBench: строгая оценка агентов в data-driven научных задачах (без аннотации). |
| 2025 | Evaluating Large Language Models in Scientific Discovery | [2512.15567](https://arxiv.org/abs/2512.15567) · [**info**](sde-benchmark/info.md) | ← SU | 46 | SDE: сценарный бенчмарк научного открытия (гипотезы, дизайн экспериментов, интерпретация) в 4 науках с проектным уровнем. |
| 2024 | The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery | [2408.06292](https://arxiv.org/abs/2408.06292) | ← DP,GB,LSRB,PG,US | 1399 | The AI Scientist: сквозной автоматический исследовательский агент (1400 цитирований); ориентир по агентному научному циклу. |
| 2024 | ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery | [2410.05080](https://arxiv.org/abs/2410.05080) · [**info**](scienceagentbench/info.md) | ← DP,SU,UD,US | 312 | ScienceAgentBench: 102 задачи data-driven научного открытия из статей с проверкой кода; эталонный бенчмарк научных агентов. |
| — | FIRE-B ENCH : E VALUATING R ESEARCH A GENTS ON THE R EDISCOVERY OF S CIENTIFIC I NSIGHTS | — | → DB | 0 | FIRE-Bench (дубликат, без года) «(без аннотации)». |

### Философия и история науки (10)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2024 | Is machine learning good or bad for the natural sciences? | [2405.18095](https://arxiv.org/abs/2405.18095) | → AIF; ← DP | 16 | Hogg et al.: эпистемология ML конфликтует с научной практикой (только данные, только held-out) — аргумент за оценку механизма, а не фита. |
| 2021 | Abduction | [doi](https://doi.org/10.4135/9781483346663.n2) | ← UD | 336 | Пирс об абдукции (ретродукции) как третьем типе вывода; исходное определение нашей задачи. |
| 2009 | Abductive Cognition - The Epistemological and Eco-Cognitive Dimensions of Hypothetical Reasoning | [doi](https://doi.org/10.1007/978-3-642-03631-6) | ← UD | 392 | Магнани, «Абдуктивное познание»: эпистемология гипотетического рассуждения; теоретическая база понятия абдукции. |
| 1995 | A 4-Space Model of Scientific Discovery | — | ← UD | 61 | 4-пространственная модель научного открытия (эксперименты, гипотезы, представления, эвристики); полезная рамка для дизайна задач. |
| 1988 | The Logic of Scientific Discovery | [doi](https://doi.org/10.4135/9781412961288.n223) | ← DW,SU | 9754 | Поппер «Логика научного открытия»: фальсификационизм; философская опора для критериев ревизии теории и границ применимости. (без аннотации) |
| 1988 | Dual Space Search During Scientific Reasoning | [doi](https://doi.org/10.1207/s15516709cog1201_1) | ← UD | 1196 | Klahr–Dunbar: открытие как двойной поиск в пространствах гипотез и экспериментов; классика для интерактивного режима. |
| 1988 | Scientific Discovery: Computational Explorations of the Creative Processes | [doi](https://doi.org/10.3233/AIC-1988-1306) | ← DW,SU,UD | 1164 | Лэнгли, Саймон и др. «Scientific Discovery» (BACON, GLAUBER, STAHL, DALTON) — классика вычислительного открытия законов и скрытых сущностей. (без аннотации) |
| 1981 | Data-Driven Discovery of Physical Laws | [doi](https://doi.org/10.1111/j.1551-6708.1981.tb00869.x) | ← DB,LSRB | 194 | BACON.3 (Langley): переоткрытие закона идеального газа, Кеплера, Кулона, Ома — исторический предтеча «переоткрытия» законов. |
| 1964 | The Structure of Scientific Revolutions | [doi](https://doi.org/10.1007/978-94-010-9731-4_3) | ← UD | 8462 | Кун, «Структура научных революций»: аномалии и смена парадигм; концептуальная основа сценария провала T0. |
| 1960 | Patterns of Discovery : An Inquiry into the Conceptual Foundations of Science. | [doi](https://doi.org/10.1001/ARCHINTE.1960.03820060160039) | ← UD | 599 | Хэнсон, «Паттерны открытия»: ретродукция и теоретическая нагруженность наблюдения; классика по абдукции. |

### Генерация гипотез (10)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents | [2607.09195](https://arxiv.org/abs/2607.09195) | → DP | 6 | HEP: протокол явной генерации, проверки и эволюции гипотез для аудируемых LLM-агентов; полезен для дизайна логирования и рубрики процесса. |
| 2026 | Towards Diverse Scientific Hypothesis Search with Large Language Models | [2606.10587](https://arxiv.org/abs/2606.10587) | → LSRB | 3 | Поиск разнообразных наборов научных гипотез с LLM вместо одной лучшей. |
| 2026 | Before the Action: Benchmarking LLMs on Prospective Hypothesis Discovery | [2607.15766](https://arxiv.org/abs/2607.15766) · [**info**](hypoarena/info.md) | → DB; ← UD | 2 | HypoArena: 988 кейсов построения пространства гипотез из неполных/аномальных данных с арена-оценкой и рубриками; близко к нашей оценке объяснений. |
| 2026 | Evidence-Informed LLM Beliefs for Continual Scientific Discovery | [2606.29182](https://arxiv.org/abs/2606.29182) | → DB | 1 | Нестационарный байесовский сюрприз с обновляемыми убеждениями LLM для непрерывного открытия; релевантно конфликту априора и данных. |
| 2026 | From Scientific Observations to Mechanisms: Benchmarking Hypothesis Generation by AI Scientists | [2610.05197](https://arxiv.org/abs/2610.05197) · [**info**](obs-to-mechanisms/info.md) | → DB,LSRB | 0 | MechHypoBench: агенты предлагают механистические гипотезы по реальным данным 14 областей; оценка через следствия при скрытых условиях. |
| 2025 | Automated Hypothesis Validation with Agentic Sequential Falsifications | [2502.09858](https://arxiv.org/abs/2502.09858) | ← UD | 66 | POPPER: агентная последовательная фальсификация гипотез с контролем ошибки I рода; релевантно проверке гипотез о сущности. |
| 2025 | HypoBench: Towards Systematic and Principled Benchmarking for Hypothesis Generation | [2504.11524](https://arxiv.org/abs/2504.11524) · [**info**](hypobench/info.md) | → DW | 47 | HypoBench: систематический бенчмарк генерации гипотез, вкл. синтетические задачи с известной истиной; релевантная методология оценки гипотез. |
| 2025 | AutoDiscovery: Open-ended Scientific Discovery via Bayesian Surprise | [2507.00310](https://arxiv.org/abs/2507.00310) | → DB | 46 | AutoDiscovery: открытое открытие с байесовским сюрпризом как наградой; метрика сдвига убеждений LLM полезна для оценки неожиданности данных. |
| 2025 | HypoSpace: Evaluating LLM Creativity as Set-Valued Hypothesis Generators under Underdetermination | [doi](https://doi.org/10.48550/arXiv.2510.15614) | → GB,LSRB | 11 | HypoSpace (другая версия): LLM как сэмплеры множеств гипотез при недоопределённости; дубликат id 157. |
| 2025 | HypoSpace: A Diagnostic Benchmark for Set-Valued Hypothesis Generation under Underdetermination and Sublinear Coverage Bounds | [2510.15614](https://arxiv.org/abs/2510.15614) · [**info**](hypospace/info.md) | → GB,LSRB | 8 | HypoSpace: генерация множеств гипотез при недоопределённости (валидность, уникальность, покрытие) — релевантно неоднозначности «сущность vs модификация». |

### Открытие на основе данных (6)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | D3-Gym: Constructing Real-World Verifiable Environments for Data-Driven Discovery | [2604.27977](https://arxiv.org/abs/2604.27977) · [**info**](d3-gym/info.md) | → DB,LSRB | 4 | D3-Gym: автоматически построенные верифицируемые среды data-driven открытия. |
| 2026 | InfiniteScienceGym: An Unbounded, Procedurally-Generated Benchmark for Scientific Analysis | [2604.13201](https://arxiv.org/abs/2604.13201) · [**info**](infinitesciencegym/info.md) | → DB,LSRB | 1 | InfiniteScienceGym: процедурно генерируемый бенчмарк научного анализа без known-knowledge bias. |
| 2026 | Searching for What Matters: Open-Ended Discovery of Multiple Hypotheses with Agentic Data Exploration | [2610.17874](https://arxiv.org/abs/2610.17874) | → DW | 0 | Открытое обнаружение множества гипотез через агентное исследование данных без заданного вопроса; data-driven открытие, релевантно режиму статических таблиц. |
| 2024 | BLADE: Benchmarking Language Model Agents for Data-Driven Science | [2408.09667](https://arxiv.org/abs/2408.09667) · [**info**](blade/info.md) | ← DB | 105 | BLADE: бенчмарк агентов в data-driven науке с оценкой аналитических решений против экспертов; релевантен режиму статических таблиц. |
| 2024 | Automated Statistical Model Discovery with Language Models | [2402.17879](https://arxiv.org/abs/2402.17879) | ← DB,US | 51 | BoxLM: LLM предлагает и критикует вероятностные программы для автоматического открытия статистических моделей; близко к поиску модели по данным. |
| 2024 | Data-driven Discovery with Large Generative Models | [2402.13610](https://arxiv.org/abs/2402.13610) | ← DB,LSRB | 37 | Позиционная статья DiscoveryBench-группы о data-driven открытии с большими генеративными моделями. |

### Абдукция и пересмотр теории (5)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Tiny Moves: Game-based Hypothesis Refinement | [2602.09801](https://arxiv.org/abs/2602.09801) | → DB | 1 | Hypothesis Game: агенты пошагово правят гипотезу грамматикой ходов, восстанавливая внесённые ошибки; модель локальной ревизии теории. |
| 2026 | Evidence-Gated Symbolic Correction for Data-Limited Geomechanical Models | [doi](https://doi.org/10.3390/app162110955) | → AIF,LSRB | 0 | SR-коррекция существующей геомеханической модели (базовая модель сохраняется), доп. наблюдения запрашиваются только при расхождении кандидатов; близкий аналог «ревизии T0 под бюджетом». |
| 2026 | SciR: A Controllable Benchmark for Scientific Reasoning in LLMs | [2606.13020](https://arxiv.org/abs/2606.13020) · [**info**](scir/info.md) | → DB,LSRB | 0 | SciR: контролируемый бенчмарк дедукции, индукции и каузальной абдукции в научных текстах с верифицируемыми ответами. |
| 2011 | Automated refinement and inference of analytical models for metabolic networks | [doi](https://doi.org/10.1088/1478-3975/8/5/055011) | ← AIF | 140 | Автоматическое исправление существующей модели метаболической сети (добавление нелинейных членов) с выбором экспериментов, разводящих кандидатов; ранний прецедент ревизии T0 по данным. |
| 1986 | STAHLp: Belief Revision in Scientific Discovery | — | ← PG | 10 | STAHLp (1986): система открытия, гипотезирующая ошибочные посылки и ревизующая их; классический прецедент ревизии теории при конфликте с данными. |

### Бенчмарки открытия законов (3)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2025 | Can Language Models Discover Scaling Laws? | [2507.21184](https://arxiv.org/abs/2507.21184) · [**info**](scaling-law-discovery/info.md) | → AIF,LSRB | 13 | Бенчмарк открытия законов масштабирования LLM (5000+ экспериментов, 8 задач) — out-of-textbook законы, низкий риск запоминания. |
| 2025 | SURFACEBENCH: A Geometry-Aware Benchmark for Symbolic Surface Discovery | [2511.10833](https://arxiv.org/abs/2511.10833) · [**info**](surfacebench/info.md) | → AIF,LSRB | 2 | SurfaceBench: бенчмарк открытия символьных поверхностей с геометрической оценкой. |
| 2022 | Rediscovering orbital mechanics with machine learning | [2202.02306](https://arxiv.org/abs/2202.02306) | → AIF; ← GB | 152 | Открытие законов орбитальной механики Солнечной системы GNN+SR с выводом неизвестных масс — близко к Gravity-Bench и нашему Нептуну. |

### Скрытые сущности / латентные переменные (2)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2024 | Discovery of the Hidden World with Large Language Models | [doi](https://doi.org/10.48550/arXiv.2402.03941) | ← US | 29 | COAT: LLM предлагают скрытые каузальные факторы из неструктурированных данных для каузального открытия; близко к обнаружению скрытых сущностей. |
| 2022 | Discovering governing equations from partial measurements with deep delay autoencoders | [2201.05136](https://arxiv.org/abs/2201.05136) | ← US | 156 | Открытие уравнений по частичным измерениям через delay-автоэнкодеры: восстановление скрытых переменных; SR с латентными сущностями. |

### Обзоры (1)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2025 | From Reasoning to Learning: A Survey on Hypothesis Discovery and Rule Learning with Large Language Models | [2505.21935](https://arxiv.org/abs/2505.21935) | → DW | 6 | Обзор открытия гипотез и обучения правилам с LLM (абдукция, индукция, дедукция); прямой обзор нашей способности. |

## Уровень C — по касательной


### Агенты (общее) (45)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Towards end-to-end automation of AI research | [2606.15497](https://arxiv.org/abs/2606.15497) | ← SU | 389 | AI Scientist: сквозная автоматизация AI-исследований. |
| 2026 | A multi-agent system for automating scientific discovery | [doi](https://doi.org/10.1038/s41586-026-10652-y) | ← SU | 238 | Robin: мультиагентная система автоматизации открытия в биологии. |
| 2026 | Towards Execution-Grounded Automated AI Research | [2601.14525](https://arxiv.org/abs/2601.14525) | → DB | 26 | Исполнение идей автоматизированного AI-исследования и обучение на обратной связи. |
| 2026 | Making large language models reliable data science programming copilots for biomedical research | [doi](https://doi.org/10.1038/s41551-025-01587-2) | → DB | 17 | Агент-копилот для биомедицинского data science с планом анализа (74% точности). |
| 2026 | DataSTORM: Deep Research on Large-Scale Databases using Exploratory Data Analysis and Data Storytelling | [2604.06474](https://arxiv.org/abs/2604.06474) | → DB | 8 | DataSTORM: deep research над большими БД с EDA и сторителлингом. |
| 2026 | MineExplorer: Evaluating Open-World Exploration of MLLM Agents in Minecraft | [2605.30931](https://arxiv.org/abs/2605.30931) | ← UD | 6 | MineExplorer: открытое исследование MLLM-агентами в Minecraft. |
| 2026 | Beyond Blind Following: Evaluating Robustness of LLM Agents under Imperfect Guidance | [doi](https://doi.org/10.18653/v1/2026.eacl-long.310) | → DW | 5 | Устойчивость LLM-агентов к несовершенным подсказкам (ошибочные мануалы); близко к ложному приору, но общий домен. |
| 2026 | CODA-BENCH: Can Code Agents Handle Data-Intensive Tasks? | [2606.15300](https://arxiv.org/abs/2606.15300) | → DB | 5 | CODA-BENCH: кодовые агенты на задачах с большими данными. |
| 2026 | Agents Explore but Agents Ignore: LLMs Lack Environmental Curiosity | [2604.17609](https://arxiv.org/abs/2604.17609) | → DW | 3 | Агенты исследуют, но игнорируют неожиданную релевантную информацию; полезное наблюдение о неиспользовании аномалий. |
| 2026 | SciNav: A General Agent Framework for Scientific Coding Tasks | [2603.20256](https://arxiv.org/abs/2603.20256) | → DB | 2 | SciNav: общий агентный фреймворк для научных кодовых задач. |
| 2026 | Grounding LLMs in Scientific Discovery via Embodied Actions | [2602.20639](https://arxiv.org/abs/2602.20639) | → GB | 2 | EmbodiedAct: LLM в MATLAB с тесным циклом восприятия-исполнения симуляций. |
| 2026 | EmbodiedLab: Benchmarking Embodied Agents That Act to Know | [2610.35385](https://arxiv.org/abs/2610.35385) | → DW,NB,PG | 1 | EmbodiedLab: воплощённые агенты, действующие для получения знания о системе. |
| 2026 | SciResearcher: Scaling Deep Research Agents for Frontier Scientific Reasoning | [2605.01489](https://arxiv.org/abs/2605.01489) | → NB | 1 | SciResearcher: масштабирование deep research агентов для научного рассуждения. |
| 2026 | Recovering Wasted Compute in Autoresearch Agents | [2608.10424](https://arxiv.org/abs/2608.10424) | → DB | 1 | Возврат «потраченного» вычисления в autoresearch-агентах. |
| 2026 | One Reflection Is Not Enough: Self-Correcting Autonomous Research via Multi-Hypothesis Failure Attribution | [2606.31478](https://arxiv.org/abs/2606.31478) | → DB | 1 | Самокоррекция исследовательских агентов через атрибуцию отказов по множеству гипотез. |
| 2026 | SciDER: Scientific Data-centric End-to-end Researcher | [2603.01421](https://arxiv.org/abs/2603.01421) | → DB | 1 | SciDER: сквозной data-центричный научный агент для сырых экспериментальных данных. |
| 2026 | Toward Knowledge-Centric AI: Discovering, Internalizing, and Using Explicit Knowledge Across Agents and Generations | [2611.03157](https://arxiv.org/abs/2611.03157) | → AIF,DB,LSRB | 0 | Позиционная работа о явном, проверяемом знании, накапливаемом и передаваемом между ИИ-агентами и поколениями. |
| 2026 | Learning What to Investigate Next: Meta-Reasoning for Long-Horizon Research Agents | [2610.02525](https://arxiv.org/abs/2610.02525) | → DP,LSRB | 0 | MIRA: мета-рассуждение «что исследовать дальше» для долгогоризонтных исследовательских агентов. |
| 2026 | ReplayRCA: Measuring Post-hoc Diagnosis and Live Oversight of Agent Failures by Counterfactual Replay | [2610.41025](https://arxiv.org/abs/2610.41025) | → DW,NB | 0 | ReplayRCA: оценка диагностики сбоев агентов через контрфактический реплей. |
| 2026 | The Marathon of Scientific Reasoning: Robustness of Scientific Agents to Perturbations in Multi-Turn Interactions | [2609.34537](https://arxiv.org/abs/2609.34537) | → GB,NB | 0 | SciARP: устойчивость научных агентов к возмущениям в многоходовом взаимодействии. |
| 2026 | ArtifactArena: Evaluating Models by What They Build in the Physical World | [2610.06511](https://arxiv.org/abs/2610.06511) | → PG | 0 | ArtifactArena: оценка моделей по роботам, спроектированным для симулированной арены; инженерия, не открытие законов. |
| 2026 | LEGION: Benchmarking Language Agents on Sparse-Signal Investigation Under Adversarial Noise | [2611.11896](https://arxiv.org/abs/2611.11896) | → DW | 0 | LEGION: бенчмарк расследования при разреженном сигнале и враждебном шуме; общие агентные навыки поиска. |
| 2026 | VerifiedLab: Harnessing Knowns for Unknowns | [2610.37923](https://arxiv.org/abs/2610.37923) | → DB | 0 | VerifiedLab: мультиагентный харнесс над верифицированными научными записями для прогнозов; инфраструктура, слабо связана. |
| 2026 | EvalRx: Agentic Diagnosis and Verified Repair of Foundation Models | [2610.25767](https://arxiv.org/abs/2610.25767) | → DB | 0 | EvalRx: агентная диагностика и проверенный ремонт отказов моделей через фальсифицируемые гипотезы; ML-инженерия. |
| 2026 | PRAXIS-MD: a long-term brain-enhanced agent framework for end-to-end molecular dynamics research. | [doi](https://doi.org/10.1016/j.jmgm.2026.109623) | → DB | 0 | PRAXIS-MD: агентный фреймворк для сквозных исследований молекулярной динамики; доменное применение. |
| 2026 | Can AI Scientists Coordinate at Runtime? | [2610.00980](https://arxiv.org/abs/2610.00980) | → DB | 0 | Исследование runtime-координации мультиагентных AI-учёных против фиксированных воркфлоу. |
| 2026 | OpenAI4S: Code as Action, Science as Sessions | [2609.15096](https://arxiv.org/abs/2609.15096) | → DB | 0 | OpenAI4S: открытый научный агент «код как действие» с сохранением состояния и провенанса. |
| 2025 | AIDE: AI-Driven Exploration in the Space of Code | [2502.13138](https://arxiv.org/abs/2502.13138) | ← PG | 262 | AIDE: агентный поиск по пространству кода для ML-инжиниринга. |
| 2025 | CodeScientist: End-to-End Semi-Automated Scientific Discovery with Code-based Experimentation | [2503.22708](https://arxiv.org/abs/2503.22708) | ← NB | 71 | CodeScientist: полуавтоматическое открытие через кодовые эксперименты. |
| 2025 | R&D-Agent: An LLM-Agent Framework Towards Autonomous Data Science | [2505.14738](https://arxiv.org/abs/2505.14738) | → DB | 51 | R&D-Agent: LLM-агентный фреймворк для автономного data science. |
| 2025 | Scaling Generalist Data-Analytic Agents | [2509.25084](https://arxiv.org/abs/2509.25084) | → DB | 16 | Масштабирование генералистских агентов анализа данных (DataMind). |
| 2025 | K-Dense Analyst: Towards Fully Automated Scientific Analysis | [2508.07043](https://arxiv.org/abs/2508.07043) | → DB | 14 | K-Dense Analyst: автоматизированный биоинформатический анализ. |
| 2025 | Why Do Open-Source LLMs Struggle with Data Analysis? A Systematic Empirical Study | [2506.19794](https://arxiv.org/abs/2506.19794) | → DB | 9 | Почему open-source LLM слабы в анализе данных: эмпирическое исследование. |
| 2025 | DatasetResearch: Benchmarking Agent Systems for Demand-Driven Dataset Discovery | [2508.06960](https://arxiv.org/abs/2508.06960) | → DB | 7 | DatasetResearch: агенты для поиска датасетов по запросу. |
| 2025 | ReX-MLE: The Autonomous Agent Benchmark for Medical Imaging Challenges | [2512.17838](https://arxiv.org/abs/2512.17838) | → DW,LSRB | 5 | ReX-MLE: агентный бенчмарк на задачах медицинской визуализации. |
| 2025 | AIRUS: a simple workflow for AI-assisted exploration of scientific data | [doi](https://doi.org/10.1101/2025.02.23.639768) | → DB | 0 | AIRUS: простой воркфлоу ИИ-исследования научных данных под надзором. |
| 2024 | MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering | [2410.07095](https://arxiv.org/abs/2410.07095) | ← PG | 578 | MLE-bench: 75 Kaggle-соревнований для ML-агентов. |
| 2024 | Automated Design of Agentic Systems | [2408.08435](https://arxiv.org/abs/2408.08435) | ← PG | 525 | ADAS: автоматический дизайн агентных систем. |
| 2024 | RE-Bench: Evaluating frontier AI R&D capabilities of language model agents against human experts | [2411.15114](https://arxiv.org/abs/2411.15114) | ← PG | 221 | RE-Bench: R&D-задачи ИИ для агентов против экспертов-людей. |
| 2024 | OMNI-EPIC: Open-endedness via Models of human Notions of Interestingness with Environments Programmed in Code | [2405.15568](https://arxiv.org/abs/2405.15568) | ← PG | 89 | OMNI-EPIC: открытая генерация сред-задач в коде по модели «интересности» человека; про open-endedness, не про открытие законов. |
| 2023 | SWE-bench: Can Language Models Resolve Real-World GitHub Issues? | [2310.06770](https://arxiv.org/abs/2310.06770) | ← GB | 4885 | SWE-bench: агенты решают реальные GitHub-задачи. |
| 2023 | CLIN: A Continually Learning Language Agent for Rapid Task Adaptation and Generalization | [2310.10134](https://arxiv.org/abs/2310.10134) | ← DB,DW | 114 | CLIN: непрерывно обучающийся языковой агент в ScienceWorld; общая агентная адаптация. |
| 2022 | ReAct: Synergizing Reasoning and Acting in Language Models | [2210.03629](https://arxiv.org/abs/2210.03629) | ← DB,DW | 13872 | ReAct: чередование рассуждения и действий LLM-агентов; базовая агентная схема, возможно скаффолд нашего агента. |
| — | DSG YM : A H OLISTIC F RAMEWORK FOR A DVANCING D ATA S CIENCE A GENTS | — | → DB | 0 | DSGym: целостный фреймворк для агентов data science. |
| — | DSG YM : A H OLISTIC F RAMEWORK FOR A DVANCING D ATA S CIENCE A GENTS | — | → DB | 0 | DSGym (дубликат) «(без аннотации)». |

### Бенчмарки агентов-учёных (45)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Collider-Bench: Benchmarking AI Agents with Particle Physics Analysis Reproduction | [2605.13950](https://arxiv.org/abs/2605.13950) | → GB,NB | 20 | Collider-Bench: воспроизведение анализов LHC агентами. |
| 2026 | SciAgentGym: Benchmarking Multi-Step Scientific Tool-use in LLM Agents | [2602.12984](https://arxiv.org/abs/2602.12984) | → DW | 17 | SciAgentGym: 1780 научных инструментов для многошаговых задач; tool-use, не открытие. |
| 2026 | LABBench2: An Improved Benchmark for AI Systems Performing Biology Research | [2604.09554](https://arxiv.org/abs/2604.09554) | → DB,DW | 15 | LABBench2: бенчмарк ИИ для биологических исследований; доменный. |
| 2026 | HeurekaBench: A Benchmarking Framework for AI Co-scientist | [2601.01678](https://arxiv.org/abs/2601.01678) | → DB | 14 | HeurekaBench: фреймворк оценки AI-соучёных на сквозных сценариях анализа данных. |
| 2026 | ASI-Bench: At the Dawn of Artificial Superintelligence | [2608.17271](https://arxiv.org/abs/2608.17271) | → DB,DW | 9 | ASI-Bench: бенчмарк создания нового знания и проверяемых результатов; широкий, не про законы. |
| 2026 | Training AI Scientists to Replicate Research | [2608.13331](https://arxiv.org/abs/2608.13331) | → DB | 9 | Обучение AI-учёных репликации исследований; репликация статей, не открытие законов. |
| 2026 | gwBenchmarks: Stress-Testing LLM Agents on High-Precision Gravitational Wave Astronomy | [2605.11269](https://arxiv.org/abs/2605.11269) | → DP,DB,NB | 8 | gwBenchmarks: высокоточные задачи гравитационно-волновой астрономии для агентов. |
| 2026 | BixBench3: Benchmarking AI agents on research-study-scale computational biology tasks | [2608.25286](https://arxiv.org/abs/2608.25286) | → DW | 7 | BixBench3: агенты на задачах вычислительной биологии масштаба исследования; доменный бенчмарк. |
| 2026 | EviGraph: Evidence-Guided Autonomous Research Agents | [2608.04738](https://arxiv.org/abs/2608.04738) | → DW | 5 | EviGraph: исследовательские агенты с графом доказательств против неподкреплённых утверждений; архитектура агента-учёного. |
| 2026 | K-Bench: measuring model performance on real scientific agent requests | [2608.21601](https://arxiv.org/abs/2608.21601) | → DB | 3 | K-Bench: оценка на реальных недоопределённых научных запросах к агентам. |
| 2026 | Data Analysis in the Wild: Benchmarking Large Language Models Against Real-World Data Complexities | [2607.06482](https://arxiv.org/abs/2607.06482) | → DB | 2 | DSWild: бенчмарк анализа данных LLM на сложных реальных мультитабличных данных. |
| 2026 | CompMat-Bench: Benchmarking AI Agents for Computational Materials Science | [2610.00636](https://arxiv.org/abs/2610.00636) | → DB | 1 | CompMat-Bench: агенты в вычислительном материаловедении с кешированными симуляциями; доменный бенчмарк. |
| 2026 | Mind the alignment gap: a spatial transcriptomics benchmark for scientific coding agents | [doi](https://doi.org/10.64898/2026.07.05.736638) | → DB | 1 | Бенчмарк выравнивания пространственной транскриптомики для кодовых агентов. |
| 2026 | PAPERBENCHX: Can AI Reproduce Science Across Disciplines? | [2610.39744](https://arxiv.org/abs/2610.39744) | → DB,DW | 0 | PaperBenchX: воспроизведение научных результатов из разных дисциплин агентами; воспроизведение, не открытие. |
| 2026 | SCI-AGENT-EXAM: Benchmarking Agents on Scientific Research Tasks | [2610.32441](https://arxiv.org/abs/2610.32441) | → DW | 0 | SCI-AGENT-EXAM: широкий бенчмарк агентов на научных исследовательских задачах; общий научный агентный бенчмарк. |
| 2026 | Publications as benchmarks: auditing AI agents on spatial transcriptomics alignment | [2611.11796](https://arxiv.org/abs/2611.11796) | → DB | 0 | Превращение публикаций в аудируемые бенчмарки для агентов на примере выравнивания пространственной транскриптомики; доменный агентный бенчмарк. |
| 2026 | PersonaScienceBench: Evaluating Scientific Agents with Diverse Simulated Researchers | [2610.32106](https://arxiv.org/abs/2610.32106) | → DB | 0 | PersonaScienceBench: 200 научных задач с симулированными исследователями разных предпочтений; про коллаборацию, не про открытие законов. |
| 2026 | POSEIDON: Scaling Training Environments for Scientific Agents from Code Repositories | [2610.32448](https://arxiv.org/abs/2610.32448) | → DB | 0 | POSEIDON: автоматическая генерация обучающих сред для data-driven научных агентов из репозиториев кода; масштабирование сред. |
| 2026 | ST-Bench: A Spatial-Temporal Benchmark for Multi-Agent System Generation on Scientific Research Tasks | [2610.07763](https://arxiv.org/abs/2610.07763) | → DB | 0 | ST-Bench: мультиагентные системы на научных пространственно-временных задачах анализа данных. |
| 2026 | EarthVerse: Benchmarking Scientific Agents Across Dynamic Earth Systems and Natural Hazards | [2608.23525](https://arxiv.org/abs/2608.23525) | → DB | 0 | EarthVerse: бенчмарк научных агентов по системам Земли и природным опасностям. |
| 2026 | ClinLens: Towards Long-Horizon LLM Agents for Longitudinal Multimodal Clinical Data Science | [2607.26155](https://arxiv.org/abs/2607.26155) | → DB | 0 | ClinLens: агенты для лонгитюдной мультимодальной клинической науки о данных. |
| 2025 | The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search | [2504.08066](https://arxiv.org/abs/2504.08066) | ← PG | 515 | AI Scientist-v2: агентный поиск по дереву, первая принятая на воркшоп статья ИИ. |
| 2025 | PaperBench: Evaluating AI's Ability to Replicate AI Research | [2504.01848](https://arxiv.org/abs/2504.01848) | → DW | 393 | PaperBench: воспроизведение 20 статей ICML с иерархическими рубриками и LLM-судьёй; идея рубрик, домен ML. |
| 2025 | BixBench: a Comprehensive Benchmark for LLM-based Agents in Computational Biology | [2503.00096](https://arxiv.org/abs/2503.00096) | → DB; ← DP,PG | 137 | BixBench: бенчмарк агентов в вычислительной биологии. |
| 2025 | MLGym: A New Framework and Benchmark for Advancing AI Research Agents | [2502.14499](https://arxiv.org/abs/2502.14499) | → DW | 129 | MLGym: фреймворк и бенчмарк агентов на ML-исследовательских задачах; другой домен. |
| 2025 | PHYBench: Holistic Evaluation of Physical Perception and Reasoning in Large Language Models | [2504.16074](https://arxiv.org/abs/2504.16074) | ← PG | 60 | PHYBench: 500 оригинальных задач по физике против контаминации; физрассуждение, не открытие. |
| 2025 | EXP-Bench: Can AI Conduct AI Research Experiments? | [2505.24785](https://arxiv.org/abs/2505.24785) | → DB | 48 | EXP-Bench: агенты проводят полные эксперименты AI-исследований. |
| 2025 | MLRC-Bench: Can Language Agents Solve Machine Learning Research Challenges? | [2504.09702](https://arxiv.org/abs/2504.09702) | → DB | 34 | MLRC-Bench: агенты на ML-соревнованиях исследовательского уровня. |
| 2025 | PaperArena: An Evaluation Benchmark for Tool-Augmented Agentic Reasoning on Scientific Literature | [2510.10909](https://arxiv.org/abs/2510.10909) | → DB | 19 | PaperArena: инструментальные рассуждения агентов над научной литературой. |
| 2025 | AstroVisBench: A Code Benchmark for Scientific Computing and Visualization in Astronomy | [2505.20538](https://arxiv.org/abs/2505.20538) | → GB | 14 | AstroVisBench: код для вычислений и визуализации в астрономии. |
| 2025 | FEM-Bench: a structured scientific reasoning benchmark for evaluating code-generating LLMs | [2512.20732](https://arxiv.org/abs/2512.20732) | → LSRB | 12 | FEM-Bench: генерация кода МКЭ LLM-ами. |
| 2025 | SUPERChem: A Multimodal Reasoning Benchmark in Chemistry | [2512.01274](https://arxiv.org/abs/2512.01274) | → LSRB | 12 | SUPERChem: 500 экспертных задач по химическому рассуждению. |
| 2025 | BioDSA-1K: Benchmarking Data Science Agents for Biomedical Research | [2505.16100](https://arxiv.org/abs/2505.16100) | → DB | 12 | BioDSA-1K: агенты проверяют биомедицинские гипотезы на реальных данных. |
| 2025 | ReplicationBench: Can AI Agents Replicate Astrophysics Research Papers? | [2510.24591](https://arxiv.org/abs/2510.24591) | → GB | 9 | ReplicationBench: агенты реплицируют астрофизические статьи. |
| 2025 | CFD-LLMBench: A Benchmark Suite for Evaluating Large Language Models in Computational Fluid Dynamics | [2509.20374](https://arxiv.org/abs/2509.20374) | → DB | 5 | CFD-LLMBench: LLM в вычислительной гидродинамике. |
| 2025 | From Canonical to Complex: Benchmarking LLM Capabilities in Undergraduate Thermodynamics | [2508.21452](https://arxiv.org/abs/2508.21452) | → LSRB | 2 | Бенчмарк LLM по бакалаврской термодинамике. |
| 2024 | SciCode: A Research Coding Benchmark Curated by Scientists | [2407.13168](https://arxiv.org/abs/2407.13168) | ← PG | 220 | SciCode: научный исследовательский кодинг-бенчмарк. |
| 2024 | CORE-Bench: Fostering the Credibility of Published Research Through a Computational Reproducibility Agent Benchmark | [2409.11363](https://arxiv.org/abs/2409.11363) | → DB | 158 | CORE-Bench: агенты воспроизводят вычисления опубликованных работ. |
| 2024 | DSBench: How Far Are Data Science Agents from Becoming Data Science Experts? | [2409.07703](https://arxiv.org/abs/2409.07703) | ← DB | 147 | DSBench: агенты data science на реальных задачах анализа и моделирования; общий бенчмарк. |
| 2023 | GPQA: A Graduate-Level Google-Proof Q&A Benchmark | [2311.12022](https://arxiv.org/abs/2311.12022) | ← DP,GB | 3949 | GPQA: 448 экспертных вопросов (физика, химия, биология) «защищённых от гугла»; QA-бенчмарк знаний, не открытия. |
| 2023 | Autonomous chemical research with large language models | [doi](https://doi.org/10.1038/s41586-023-06792-0) | ← DW,SU,US | 1591 | Coscientist: GPT-4 автономно планирует и выполняет химические эксперименты; знаковый пример агентного учёного. |
| 2023 | Augmenting large language models with chemistry tools | [2304.05376](https://arxiv.org/abs/2304.05376) | ← DW | 1490 | ChemCrow: LLM-агент с химическими инструментами; прикладной научный агент. |
| 2023 | MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation | [2310.03302](https://arxiv.org/abs/2310.03302) | ← DW,SU | 461 | MLAgentBench: агенты проводят ML-эксперименты; экспериментирование в ML, не открытие законов. |
| 2023 | Emergent autonomous scientific research capabilities of large language models | [2304.05332](https://arxiv.org/abs/2304.05332) | ← PG | 198 | Coscientist-подобная система: LLM автономно планирует химические эксперименты; ранний пример агентного учёного. |
| 2022 | ScienceWorld: Is your Agent Smarter than a 5th Grader? | [2203.07540](https://arxiv.org/abs/2203.07540) | ← DW,UD | 439 | ScienceWorld: текстовая среда с научными задачами уровня начальной школы; ранний интерактивный научный бенчмарк. |

### Классическая символьная регрессия (24)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | DASS: A Solver-Adaptable Dynamic Auxiliary Search Strategy for Symbolic Regression | [2610.16812](https://arxiv.org/abs/2610.16812) | → AIF,LSRB | 4 | DASS: динамическая вспомогательная стратегия поиска для ускорения разных SR-решателей. |
| 2026 | Synthesizing Physics Formulae with Transformers | [2610.03947](https://arxiv.org/abs/2610.03947) | → AIF,LSRB | 1 | Трансформерный синтез физических формул по парам вход-выход, сравнение с поисковыми SR. |
| 2026 | SMILE: Bridging Continuous Optimization and Discrete Symbolic Recovery | [2609.04639](https://arxiv.org/abs/2609.04639) | → AIF,LSRB | 0 | SMILE: непрерывная оптимизация с последующим дискретным символьным восстановлением. |
| 2026 | EditSR: Enhancing Neural Symbolic Regression via Edit-based Rectification | [2606.07915](https://arxiv.org/abs/2606.07915) | → AIF,LSRB | 0 | EditSR: редактирующая коррекция выходов нейросетевой SR. |
| 2026 | FoundPDE: A generative foundation model for data-driven symbolic discovery of partial differential equations | [2610.26963](https://arxiv.org/abs/2610.26963) | → LSRB | 0 | FoundPDE: генеративная foundation-модель для символьного открытия PDE. |
| 2026 | The Dynamics of Discoverability: How Trajectories and Priors Shape Equation Recovery | [2607.18490](https://arxiv.org/abs/2607.18490) | → LSRB | 0 | Как режим динамики (Lorenz-84) и приоры влияют на восстановимость уравнений SINDy/PySR; про идентифицируемость по данным. |
| 2025 | Discovering Symbolic Differential Equations with Symmetry Invariants | [2505.12083](https://arxiv.org/abs/2505.12083) | → AIF,LSRB | 6 | Открытие символьных дифференциальных уравнений через инварианты симметрии. |
| 2025 | Analyzing Generalization in Pre-Trained Symbolic Regression | [2509.19849](https://arxiv.org/abs/2509.19849) | → AIF,LSRB | 4 | Анализ обобщения предобученных трансформерных SR вне распределения предобучения. |
| 2025 | Beyond Accuracy and Complexity: The Effective Information Criterion for Structurally Stable Symbolic Regression | [2509.21780](https://arxiv.org/abs/2509.21780) | → AIF,LSRB | 1 | Effective Information Criterion для структурно устойчивой SR вместо accuracy–complexity. |
| 2023 | Transformer-based Planning for Symbolic Regression | [2303.06833](https://arxiv.org/abs/2303.06833) | → AIF; ← LSRB | 132 | TPSR: трансформерная SR с планированием MCTS при декодировании. |
| 2023 | SNIP: Bridging Mathematical Symbolic and Numeric Realms with Unified Pre-training | [2310.02227](https://arxiv.org/abs/2310.02227) | → AIF; ← LSRB | 56 | SNIP: совместное предобучение символьного и численного представлений. |
| 2022 | End-to-end symbolic regression with transformers | [2204.10532](https://arxiv.org/abs/2204.10532) | → AIF; ← LSRB | 346 | E2E: сквозная трансформерная SR с константами. |
| 2022 | A Unified Framework for Deep Symbolic Regression | — | ← LSRB | 173 | Единый фреймворк глубокой SR (uDSR) (без аннотации). |
| 2022 | Symbolic Regression is NP-hard | [2207.01018](https://arxiv.org/abs/2207.01018) | → AIF; ← LSRB | 118 | Доказательство NP-трудности символьной регрессии. |
| 2022 | Symbolic Physics Learner: Discovering governing equations via Monte Carlo tree search | [2205.13134](https://arxiv.org/abs/2205.13134) | → AIF; ← LSRB | 105 | Symbolic Physics Learner: открытие уравнений нелинейной динамики через MCTS. |
| 2021 | Neural Symbolic Regression that Scales | [2106.06427](https://arxiv.org/abs/2106.06427) | → AIF; ← LSRB | 320 | NeSymReS: предобученная нейросимвольная SR, масштабируемая с данными. |
| 2021 | Symbolic Regression via Deep Reinforcement Learning Enhanced Genetic Programming Seeding | — | ← LSRB,PG | 101 | SR через deep RL с затравкой генетического программирования (DSO) (без аннотации). |
| 2018 | Sparse identification of nonlinear dynamics for rapid model recovery. | [1803.00894](https://arxiv.org/abs/1803.00894) | ← AIF | 183 | SINDy-вариант для быстрого восстановления модели динамики после резких изменений системы по малым шумным данным. |
| 2016 | Inference of compact nonlinear dynamic models by epigenetic local search | [doi](https://doi.org/10.1016/J.ENGAPPAI.2016.07.004) | ← LSRB | 53 | Эпигенетический локальный поиск для компактных моделей динамики в GP. |
| 2011 | Semantically-based crossover in genetic programming: application to real-valued symbolic regression | [doi](https://doi.org/10.1007/s10710-010-9121-2) | ← LSRB | 355 | Семантический кроссовер в генетическом программировании для SR. |
| 2011 | FFX: Fast, Scalable, Deterministic Symbolic Regression Technology | [doi](https://doi.org/10.1007/978-1-4614-1770-5_13) | ← AIF | 222 | FFX: быстрая детерминированная неэволюционная символьная регрессия через обобщённые линейные модели. |
| 2009 | A Statistical Learning Perspective of Genetic Programming | [doi](https://doi.org/10.1007/978-3-642-01181-8_28) | ← AIF | 21 | Статистико-обучающий анализ генетического программирования: состоятельность при парсимонной фитнес-функции. |
| 2003 | Genetic Programming: Theory and Practice | [doi](https://doi.org/10.1007/0-387-23254-0_1) | ← AIF | 195 | Сборник воркшопа GPTP по теории и практике генетического программирования. |
| 1992 | Genetic Programming: On the Programming of Computers by Means of Natural Selection | — | ← AIF | 15439 | Koza: классическая книга по генетическому программированию — основа GP-подхода к SR. |

### Прочее (24)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Synthesizing scientific literature with retrieval-augmented language models | [doi](https://doi.org/10.1038/s41586-025-10072-4) | ← GB | 134 | OpenScholar: RAG-модель для синтеза научной литературы. |
| 2026 | CREATE: Testing LLMs for Associative Creativity | [2603.09970](https://arxiv.org/abs/2603.09970) | → DB | 10 | CREATE: бенчмарк ассоциативной креативности LLM. |
| 2026 | DataSense-Bench: The First Step Toward an AI Scientist | [2610.12190](https://arxiv.org/abs/2610.12190) | → DB | 1 | DataSense-Bench: умеют ли модели выбирать правильные данные для обучения; не про научные законы. |
| 2026 | MUSES: A Benchmark for Prospective Intellectual-Roots Retrieval | [2609.00313](https://arxiv.org/abs/2609.00313) | → DB | 1 | MUSES: бенчмарк поиска «интеллектуальных корней» будущих работ в литературе. |
| 2026 | SciCodePile: A 128GB Corpus and Executable Benchmark for Challenging Scientific Code Generation | [2607.19104](https://arxiv.org/abs/2607.19104) | → DB | 1 | SciCodePile: корпус 128 ГБ и исполнимый бенчмарк научного кода. |
| 2026 | The unintended consequences of large language models as a labor-augmenting technology in science | [2607.17397](https://arxiv.org/abs/2607.17397) | → DB | 1 | Непреднамеренные последствия LLM как трудосберегающей технологии в науке; социология науки. |
| 2026 | Large language models for partial differential equation workflows | [2608.03600](https://arxiv.org/abs/2608.03600) | → DP,LSRB | 0 | Обзор LLM в рабочих процессах с PDE (формулировка, решатели, проектирование). |
| 2025 | Roll the dice & look before you leap: Going beyond the creative limits of next-token prediction | [2504.15266](https://arxiv.org/abs/2504.15266) | → DW | 39 | Минимальные алгоритмические задачи для оценки креативных пределов next-token prediction; косвенно к «скачку» гипотезы. |
| 2025 | LLEMA: Evolutionary Search with LLMs for Multi-Objective Materials Discovery | [2510.22503](https://arxiv.org/abs/2510.22503) | → LSRB | 15 | LLEMA: LLM-эволюция для многокритериального открытия материалов. |
| 2025 | Benchmarking Abstract and Reasoning Abilities Through A Theoretical Perspective | [2505.23833](https://arxiv.org/abs/2505.23833) | → DB | 6 | Теоретический бенчмарк абстрактных рассуждений LLM. |
| 2025 | SimulRAG: Simulator-based RAG for Grounding LLMs in Long-form Scientific QA | [2509.25459](https://arxiv.org/abs/2509.25459) | → DB | 3 | SimulRAG: RAG с симулятором для длинных научных ответов. |
| 2025 | SciTableQA: A Question-Answering Benchmark for Complex Scientific Tables | [doi](https://doi.org/10.1007/978-3-032-05409-8_7) | → DB | 2 | SciTableQA: QA по 320 сложным научным таблицам. |
| 2025 | From Factoid Questions to Data Product Requests: Benchmarking Data Product Discovery over Tables and Text | [doi](https://doi.org/10.48550/arXiv.2510.21737) | → DB | 1 | Бенчмарк поиска дата-продуктов по таблицам и тексту. |
| 2025 | Universe of Thoughts: A Computational Framework for Creative Reasoning in Large Language Models | [2511.20471](https://arxiv.org/abs/2511.20471) | → NB | 0 | Universe of Thoughts: вычислительный фреймворк творческого рассуждения LLM. |
| 2024 | Large Language Monkeys: Scaling Inference Compute with Repeated Sampling | [2407.21787](https://arxiv.org/abs/2407.21787) | ← GB | 1159 | Large Language Monkeys: масштабирование инференса повторной выборкой; общий приём. |
| 2023 | LILO: Learning Interpretable Libraries by Compressing and Documenting Code | [2310.19791](https://arxiv.org/abs/2310.19791) | ← UD | 65 | LILO: обучение интерпретируемых библиотек кода. |
| 2022 | Discovering faster matrix multiplication algorithms with reinforcement learning | [doi](https://doi.org/10.1038/s41586-022-05172-4) | ← SU | 786 | AlphaTensor: RL находит быстрые алгоритмы умножения матриц. |
| 2022 | SciFact-Open: Towards open-domain scientific claim verification | [2210.13777](https://arxiv.org/abs/2210.13777) | ← DB | 143 | SciFact-Open: открытая проверка научных утверждений по большому корпусу статей; фактчекинг, не открытие законов. |
| 2021 | DreamCoder: bootstrapping inductive program synthesis with wake-sleep library learning | [doi](https://doi.org/10.1145/3453483.3454080) | ← UD | 331 | DreamCoder: индуктивный синтез программ с библиотечным обучением. |
| 2021 | Approximation Methods for Partially Observed Markov Decision Processes (POMDPs) | [2108.13965](https://arxiv.org/abs/2108.13965) | ← GB | 2 | Методы аппроксимации POMDP; теоретический фон для частичной наблюдаемости. |
| 2016 | Why Does Deep and Cheap Learning Work So Well? | [1608.08225](https://arxiv.org/abs/1608.08225) | ← AIF | 658 | Lin, Tegmark, Rolnick: почему глубокое обучение работает — связь класса физически значимых функций с дешёвой аппроксимацией; фон для AI Feynman. |
| 2015 | WHFAST: a fast and unbiased implementation of a symplectic Wisdom-Holman integrator for long-term gravitational simulations | [1506.01084](https://arxiv.org/abs/1506.01084) | ← GB | 341 | WHFast: симплектический интегратор для гравитационных симуляций; инструмент для N-body симуляторов. |
| 2011 | REBOUND: An open-source multi-purpose N-body code for collisional dynamics | [1110.4876](https://arxiv.org/abs/1110.4876) | ← GB | 918 | REBOUND: открытый N-body код; возможная основа симулятора небесной механики (Нептун/Вулкан). |
| 1998 | Planning and Acting in Partially Observable Stochastic Domains | [doi](https://doi.org/10.1016/S0004-3702(98)00023-X) | ← GB | 5778 | Планирование и действие в частично наблюдаемых стохастических средах (POMDP); теоретический фон. |

### Обзоры (22)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | The Hitchhiker’s Guide to Autonomous Research: A Survey of Scientific Agents | [doi](https://doi.org/10.1109/TPAMI.2026.3721500) | → DB,DW,LSRB | 13 | Обзор научных агентов для автономного исследования. |
| 2026 | AutoResearch AI: Towards AI-Powered Research Automation for Scientific Discovery | [2605.23204](https://arxiv.org/abs/2605.23204) | → AIF,DB | 10 | AutoResearch AI: обзор автоматизации исследовательского цикла ИИ. |
| 2026 | Discovery Foundation Models: Toward Open-Ended Discovery Intelligence | [2609.15973](https://arxiv.org/abs/2609.15973) | → AIF,DB | 5 | Позиционная статья о «discovery foundation models» для открытого научного открытия. |
| 2026 | From Rules to Reasoning: A Survey of Large Language Model-Based Approaches to Scientific Hypothesis and Idea Generation | [doi](https://doi.org/10.1145/3815423) | → DW | 3 | Обзор LLM-подходов к генерации научных гипотез и идей; общий обзор. |
| 2026 | Agentic AI systems for scientific discovery | [doi](https://doi.org/10.1038/s43586-026-00534-y) | → DW | 0 | Обзор Nature Reviews об агентных ИИ-системах для научного открытия; общий контекст. |
| 2026 | Puzzles to Paradigms: A Survey of Human–Agent Collaboration in Scientific Innovation | [2611.09917](https://arxiv.org/abs/2611.09917) | → GB | 0 | Обзор коллаборации человек–агент в научных инновациях. |
| 2025 | Survey on Evaluation of LLM-based Agents | [2503.16416](https://arxiv.org/abs/2503.16416) | → DW | 269 | Обзор методов оценки LLM-агентов; общий контекст по оценке. |
| 2025 | From Automation to Autonomy: A Survey on Large Language Models in Scientific Discovery | [2505.13259](https://arxiv.org/abs/2505.13259) | → AIF,DW,GB; ← UD | 132 | Обзор LLM в научном открытии: от автоматизации к автономии (132 цитирования). |
| 2025 | Towards Scientific Intelligence: A Survey of LLM-based Scientific Agents | [2503.24047](https://arxiv.org/abs/2503.24047) | → DW | 130 | Обзор LLM-научных агентов; общий контекст. |
| 2025 | LLM4SR: A Survey on Large Language Models for Scientific Research | [2501.04306](https://arxiv.org/abs/2501.04306) | ← GB | 112 | LLM4SR: обзор LLM на всех этапах научного исследования. |
| 2025 | From AI for Science to Agentic Science: A Survey on Autonomous Scientific Discovery | [2508.14111](https://arxiv.org/abs/2508.14111) | ← NB | 102 | Обзор агентной науки: от AI for Science к автономному открытию. |
| 2025 | How Far Are AI Scientists from Changing the World? | [2507.23276](https://arxiv.org/abs/2507.23276) | → DW | 17 | Обзор: насколько ИИ-учёные далеки от изменения мира; общий контекст. |
| 2025 | Evolving Roles of LLMs in Scientific Innovation: Assistant, Collaborator, Scientist, and Evaluator | [2507.11810](https://arxiv.org/abs/2507.11810) | → DB,DW | 15 | Обзор ролей LLM в научных инновациях (ассистент, соавтор, учёный, оценщик); общий контекст. |
| 2025 | From Hypothesis to Publication: A Comprehensive Survey of AI-Driven Research Support Systems | [2503.01424](https://arxiv.org/abs/2503.01424) | → DW | 13 | Обзор систем поддержки исследований от гипотезы до публикации; общий контекст. |
| 2025 | A Survey of AI Scientists | [2510.23045](https://arxiv.org/abs/2510.23045) | → AIF,DB | 10 | Обзор «ИИ-учёных» и полного научного цикла. |
| 2025 | Measuring Data Science Automation: A Survey of Evaluation Tools for AI Assistants and Agents | [2506.08800](https://arxiv.org/abs/2506.08800) | → DB,DW | 7 | Обзор инструментов оценки автоматизации data science; общий контекст. |
| 2024 | Understanding the planning of LLM agents: A survey | [2402.02716](https://arxiv.org/abs/2402.02716) | ← NB | 562 | Обзор планирования LLM-агентов. |
| 2024 | A Comprehensive Survey of Scientific Large Language Models and Their Applications in Scientific Discovery | [2406.10833](https://arxiv.org/abs/2406.10833) | ← PG | 158 | Обзор научных LLM и их применений в открытии. |
| 2024 | Towards Scientific Discovery with Generative AI: Progress, Opportunities, and Challenges | [2412.11427](https://arxiv.org/abs/2412.11427) | → AIF; ← LSRB,PG | 87 | Обзор перспектив генеративного ИИ для научного открытия. |
| 2023 | Scientific discovery in the age of artificial intelligence | [doi](https://doi.org/10.1038/s41586-023-06221-2) | ← PG | 2061 | Обзор Nature об ИИ в научном открытии (гипотезы, эксперименты, данные); общий контекст для введения. |
| 2023 | Automated Scientific Discovery: From Equation Discovery to Autonomous Discovery Systems | [2305.02251](https://arxiv.org/abs/2305.02251) | → AIF,DB,DW | 30 | Обзор автоматического научного открытия: от символьной регрессии к автономным системам. |
| — | for “AI4Research: a survey of artificial intelligence for scientific research” | — | → LSRB | 3 | Обзор AI4Research (приложение) (без аннотации). |

### Генерация гипотез (21)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Autonomous Scientific Discovery via Iterative Meta-Reflection | [2607.01131](https://arxiv.org/abs/2607.01131) | → DB | 2 | Автономное открытие через итеративную мета-рефлексию без заданного вопроса. |
| 2026 | HypoForge: A Self-Improving Multi-Agent Framework for Automated Hypothesis Generation and Testing via Scientific Skill Learning | [2608.25770](https://arxiv.org/abs/2608.25770) | → DB | 1 | HypoForge: самосовершенствующийся мультиагентный фреймворк генерации и проверки гипотез с обучением навыкам. |
| 2026 | Learning the ARTS of Search for Automated Discovery | [2606.21891](https://arxiv.org/abs/2606.21891) | → DB | 1 | ARTS: обучаемый поиск по пространству гипотез и экспериментов вместо MCTS. |
| 2026 | Matter to Mechanism: A Benchmark for AI Co-Scientists in Materials and Battery Research | [2606.02258](https://arxiv.org/abs/2606.02258) | → DB | 1 | Matter to Mechanism: бенчмарк механистических гипотез в материалах и батареях. |
| 2026 | Re-Search: Dissecting LLM Ideation Through a Two-Player Questioning Game | [2611.14487](https://arxiv.org/abs/2611.14487) | → DW | 0 | Re-Search: исследовательская идеация как игра «20 вопросов»; анализ поиска идей LLM. |
| 2026 | Selecting LLM-Generated Hypotheses Raises Truth Beyond What an LLM Panel Expects: A Pre-registered Study on NAS-Bench-201 and HPOBench | [2611.00643](https://arxiv.org/abs/2611.00643) | → DW | 0 | Тестбед с проверяемой истинностью и неочевидностью LLM-гипотез на табличных бенчмарках NAS/HPO; методика проверки гипотез, но другой домен. |
| 2026 | DiscoveryRSI: Recursively Learning to Discover Valuable Hypotheses | [2610.23839](https://arxiv.org/abs/2610.23839) | → DB | 0 | DiscoveryRSI: эволюционный поиск деревьев гипотез и рекурсивное обучение исследовательского харнесса; генерация гипотез общего вида. |
| 2026 | CrossTrace: A Cross-Domain Dataset of Grounded Scientific Reasoning Traces for Hypothesis Generation | [2603.28924](https://arxiv.org/abs/2603.28924) | → DB | 0 | CrossTrace: кросс-доменный датасет следов рассуждений для генерации гипотез. |
| 2025 | Accelerating scientific discovery with Co-Scientist | [2502.18864](https://arxiv.org/abs/2502.18864) | ← SU | 636 | Co-Scientist (Google): мультиагентная система генерации гипотез на Gemini. |
| 2025 | ResearchBench: Benchmarking LLMs in Scientific Discovery via Inspiration-Based Task Decomposition | [2503.21248](https://arxiv.org/abs/2503.21248) | ← SU | 72 | ResearchBench: генерация гипотез через декомпозицию по «вдохновениям». |
| 2025 | Sparks of Science: Hypothesis Generation Using Structured Paper Data | [2504.12976](https://arxiv.org/abs/2504.12976) | → DB,DW | 34 | Sparks of Science: генерация гипотез по структурированным данным статей; литературная идеация. |
| 2025 | BioDisco: Multi-agent hypothesis generation with dual-mode evidence, iterative feedback and temporal evaluation | [2508.01285](https://arxiv.org/abs/2508.01285) | → DB | 4 | BioDisco: мультиагентная генерация биомедицинских гипотез с временной оценкой. |
| 2025 | Augmenting Research Ideation with Data: An Empirical Investigation in Social Science | [2505.21396](https://arxiv.org/abs/2505.21396) | → DB | 1 | Дополнение генерации идей данными в социальных науках. |
| 2025 | What Are Research Hypotheses? | [2509.00185](https://arxiv.org/abs/2509.00185) | → DB | 0 | Что такое исследовательские гипотезы: систематизация понятия для NLP. |
| 2024 | SciAgents: Automating Scientific Discovery Through Bioinspired Multi‐Agent Intelligent Graph Reasoning | [doi](https://doi.org/10.1002/adma.202413523) | ← PG | 308 | SciAgents: мультиагентная генерация гипотез на графах знаний. |
| 2024 | ResearchAgent: Iterative Research Idea Generation over Scientific Literature with Large Language Models | [2404.07738](https://arxiv.org/abs/2404.07738) | ← GB,PG | 299 | ResearchAgent: итеративная генерация исследовательских идей по литературе с LLM-рецензентами; генерация идей, не проверка гипотез на данных. |
| 2024 | MOOSE-Chem: Large Language Models for Rediscovering Unseen Chemistry Scientific Hypotheses | [2410.07076](https://arxiv.org/abs/2410.07076) | ← NB | 94 | MOOSE-Chem: переоткрытие невиденных химических гипотез LLM. |
| 2024 | Generating interesting scientific ideas using knowledge graphs and LLMs: Evaluations with 100 research group leaders. | [2405.17044](https://arxiv.org/abs/2405.17044) | ← PG | 31 | SciMuse: идеи на графах знаний + LLM, оценены 100 руководителями групп. |
| 2024 | Literature Meets Data: A Synergistic Approach to Hypothesis Generation | [2410.17309](https://arxiv.org/abs/2410.17309) | → DW | 29 | Совмещение литературы и данных для генерации гипотез (HypoGeniC); data+theory идея, но не законы. |
| 2024 | Theorizing with Large Language Models | [doi](https://doi.org/10.3386/w33033) | → DB | 20 | Построение теорий с LLM в менеджменте и организационных исследованиях. |
| 2023 | SciMON: Scientific Inspiration Machines Optimized for Novelty | [2305.14259](https://arxiv.org/abs/2305.14259) | ← LSRB,PG | 267 | SciMON: генерация новых научных идей по литературе с оптимизацией новизны. |

### Философия и история науки (19)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2025 | Position: Biology is the Challenge Physics-Informed ML Needs to Evolve | [2510.25368](https://arxiv.org/abs/2510.25368) | → LSRB | 6 | Позиция: биология как вызов для physics-informed ML. |
| 2025 | Active Inference AI Systems for Scientific Discovery | [2506.21329](https://arxiv.org/abs/2506.21329) | → DW | 4 | Перспектива активного вывода (active inference) для научного открытия; концептуальная. |
| 2023 | On the scope of scientific hypotheses | [doi](https://doi.org/10.1098/rsos.230607) | ← DB | 13 | О масштабе научных гипотез (Royal Society Open Science); концептуально к формулировке гипотез и границ применимости. |
| 2016 | Artificial Intelligence to Win the Nobel Prize and Beyond: Creating the Engine for Scientific Discovery | [doi](https://doi.org/10.1609/aimag.v37i1.2642) | ← DB,DW | 123 | Китано: вызов «ИИ на Нобелевскую премию»; мотивационный текст об автоматизации открытий. |
| 2013 | Thomas Kuhn | [doi](https://doi.org/10.52712/issn.1850-0013-665) | ← UD | 36 | Томас Кун: от истории науки к эпистемологии (исп.); философский фон. |
| 2013 | The Astronomical Revolution : Copernicus - Kepler - Borelli | [doi](https://doi.org/10.4324/9780203706312) | ← AIF | 25 | История астрономической революции (Коперник, Кеплер, Борелли); может пригодиться как исторический фон для этапа 1 (без аннотации). |
| 2010 | Formal Theory of Creativity, Fun, and Intrinsic Motivation (1990–2010) | [doi](https://doi.org/10.1109/TAMD.2010.2056368) | ← PG | 937 | Шмидхубер: формальная теория креативности и любопытства через прогресс сжатия; концептуальный фон для «интересности» открытий. (без аннотации) |
| 2010 | Artificial Scientists & Artists Based on the Formal Theory of Creativity | [doi](https://doi.org/10.2991/AGI.2010.32) | ← PG | 16 | Шмидхубер: искусственные учёные как максимизаторы прогресса сжатия/предсказания; философский фон для автоматизации науки. |
| 2009 | Three Types of Conceptual Change: Belief Revision, Mental Model Transformation, and Categorical Shift | [doi](https://doi.org/10.4324/9780203874813-9) | ← UD | 673 | Три типа концептуальных изменений (Chi) «(без аннотации)»; фон по ревизии убеждений. |
| 2008 | Driven by Compression Progress: A Simple Principle Explains Essential Aspects of Subjective Beauty, Novelty, Surprise, Interestingness, Attention, Curiosity, Creativity, Art, Science, Music, Jokes | [0812.4360](https://arxiv.org/abs/0812.4360) | ← PG | 221 | Шмидхубер: прогресс сжатия объясняет новизну, любопытство и науку; философский фон, к бенчмарку отношения не имеет. |
| 2008 | A brief history of the hypothesis. | [doi](https://doi.org/10.1016/j.cell.2008.07.033) | ← DB | 73 | Краткая история понятий «гипотеза» и «модель» в науке; философский фон, слабо связан с абдукцией. |
| 2001 | A PRELIMINARY REPORT ON A GENERAL THEORY OF INDUCTIVE INFERENCE | — | ← PG | 220 | Соломонов: предварительный отчёт об общей теории индуктивного вывода; теоретический фон индукции. |
| 2000 | The Origin of Concepts | [doi](https://doi.org/10.1207/S15327647JCD0101N_3) | ← UD | 2286 | Carey, «Происхождение понятий» «(без аннотации)»; когнитивная наука. |
| 1995 | The Creative Mind: Myths and Mechanisms. | [doi](https://doi.org/10.1037/004007) | ← UD | 1601 | Боден, «Творческий разум» «(без аннотации)»; фон по креативности. |
| 1987 | Scientific discovery: compulalional explorations of the creative process | [doi](https://doi.org/10.2307/1578567) | ← PG | 68 | Лэнгли и др.: книга о вычислительном моделировании научного открытия (BACON и др.); классика истории машинного открытия. (без аннотации) |
| 1983 | EURISKO: A Program That Learns New Heuristics and Domain Concepts | [doi](https://doi.org/10.1016/S0004-3702(83)80005-8) | ← PG | 297 | EURISKO (Ленат): программа, изобретающая эвристики и понятия в 8 доменах; исторический пример машинного открытия. |
| 1977 | Scientific Discovery and the Psychology of Problem Solving | [doi](https://doi.org/10.1007/978-94-010-9521-1_16) | ← PG | 189 | Саймон: научное открытие как психология решения задач; философско-исторический фон. (без аннотации) |
| 1970 | On generality and problem solving: a case study using the DENDRAL program | — | ← PG | 245 | DENDRAL: ранняя экспертная система вывода структуры молекул; исторический контекст машинного открытия. |
| 1964 | A Formal Theory of Inductive Inference. Part I | [doi](https://doi.org/10.1016/s0019-9958(64)90223-2) | ← PG | 513 | Соломонов 1964: формальная теория индуктивного вывода (алгоритмическая вероятность); теоретический фундамент индукции. |

### Методология оценки (18)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | The Story is Not the Science: Execution-Grounded Evaluation of Mechanistic Interpretability Research | [2602.18458](https://arxiv.org/abs/2602.18458) | ← SU | 8 | Исполнимая оценка исследований по механистической интерпретируемости: история ≠ наука. |
| 2026 | BenchEvolver: Frontier Task Synthesis via Solution-Centric Evolution | [2606.01286](https://arxiv.org/abs/2606.01286) | → LSRB | 7 | BenchEvolver: синтез сложных задач эволюцией решений против насыщения бенчмарков. |
| 2026 | The Illusion of What If: Evaluating the Breakdown of Counterfactual Reasoning in LLMs | [2608.27953](https://arxiv.org/abs/2608.27953) | → NB | 0 | Бенчмарк контрфактического рассуждения LLM в открытых сценариях. |
| 2026 | SciLens: Multi-modal Scientific Claim Verification with Agentic Entailment and Grounding | [2606.20873](https://arxiv.org/abs/2606.20873) | → NB | 0 | SciLens: мультимодальная верификация научных утверждений с агентным entailment. |
| 2026 | From Outcomes to Components: A Counterfactual Evaluation Framework for LLM-Proposed Repairs | [2610.26650](https://arxiv.org/abs/2610.26650) | → PG | 0 | Контрфактическая оценка компонент LLM-предложенных исправлений данных (цели vs значения); идея разложения оценки, но домен другой. |
| 2026 | Beyond fabrication: Misattributed numbers in papers written by AI research agents | [2610.38691](https://arxiv.org/abs/2610.38691) | → DW | 0 | Ошибочно атрибутированные числа в статьях ИИ-агентов; проверка численных утверждений, косвенно к LLM-судьям. |
| 2026 | ChemArgus: Automated Scientific Diagnostics for Lab-Grade Multimodal Chemistry Reasoning: A Frontier Benchmark | [2610.20012](https://arxiv.org/abs/2610.20012) | → DW | 0 | ChemArgus: химический бенчмарк с пошаговой диагностикой, отделяющей запомненное от выведенного; идея оценки процесса, другой домен. |
| 2026 | CausalVerify: End-to-End Verification of Causal Analyses by Language Models | [2609.07944](https://arxiv.org/abs/2609.07944) | → DB | 0 | CausalVerify: исполнимый бенчмарк проверки, восстанавливает ли LLM-воркфлоу нужный каузальный эстиманд; эконометрика. |
| 2025 | PCS Workflow for Veridical Data Science in the Age of AI | [2508.00835](https://arxiv.org/abs/2508.00835) | → DB | 15 | PCS-воркфлоу (предсказуемость, вычислимость, устойчивость) для веридичной науки о данных. |
| 2025 | Progress over Points: Reframing LM Benchmarks Around Scientific Objectives | [2512.11183](https://arxiv.org/abs/2512.11183) | → LSRB | 0 | Позиция: бенчмарки LM вокруг прогресса по научным целям, а не статичных задач. |
| 2025 | Model-Aware Automatic Benchmark Generation with Self-Error Instructions for Data-Driven Models | [doi](https://doi.org/10.3390/make7040148) | → LSRB | 0 | Автоматическая генерация бенчмарков, нацеленных на ошибки data-driven моделей. |
| 2023 | FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation | [2305.14251](https://arxiv.org/abs/2305.14251) | ← DB | 1992 | FActScore: атомарная оценка фактической точности длинных текстов; идея разложения на атомарные утверждения для оценки объяснений. |
| 2023 | GPTScore: Evaluate as You Desire | [2302.04166](https://arxiv.org/abs/2302.04166) | ← DB | 531 | GPTScore: оценка генерации через вероятность у LLM по заданному критерию; общий метод LLM-оценки, к научным судьям отношения мало. |
| 2023 | Evaluating Large Language Models at Evaluating Instruction Following | [2310.07641](https://arxiv.org/abs/2310.07641) | ← DB | 385 | LLMBar: насколько LLM-оценщики надёжно оценивают следование инструкциям; общая надёжность LLM-судей. |
| 2019 | On the Measure of Intelligence | [1911.01547](https://arxiv.org/abs/1911.01547) | ← DP | 0 | Шолле «О мере интеллекта»: обобщение и эффективность навыков, ARC; общий фон. |
| 1950 | VERIFICATION OF FORECASTS EXPRESSED IN TERMS OF PROBABILITY | [doi](https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2) | ← US | 6712 | Brier score: верификация вероятностных прогнозов «(без аннотации)». |
| — | CausalVerify: An Execution-Grounded Benchmark for LLM Causal Inference Workflows | — | → DB | 1 | CausalVerify (дубликат): исполнимая проверка каузальных воркфлоу LLM. |
| — | Paperena: Reliable Science from Unreliable AI | — | → DW | 0 | Paperena: платформа записи и оценки исследований ИИ на валидность и новизну; косвенно. |

### LLM-методы символьной регрессии (17)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | DeltaEvolve: Accelerating Scientific Discovery through Momentum-Driven Evolution | [2602.02919](https://arxiv.org/abs/2602.02919) | → LSRB | 31 | DeltaEvolve: эволюция с «моментумом» вместо полной истории кода. |
| 2026 | Simple Baselines are Competitive with Code Evolution | [2602.16805](https://arxiv.org/abs/2602.16805) | ← UD | 13 | Простые бейзлайны конкурентны с эволюцией кода; предупреждение для сравнения методов. |
| 2026 | Evolution Fine-Tuning: Learning to Discover Across 371 Optimization Tasks | [2606.29082](https://arxiv.org/abs/2606.29082) | → LSRB | 6 | Evolution fine-tuning на 371 оптимизационной задаче, включая открытие законов. |
| 2026 | SMCEvolve: Principled Scientific Discovery via Sequential Monte Carlo Evolution | [2605.15308](https://arxiv.org/abs/2605.15308) | → LSRB | 4 | SMCEvolve: эволюция программ как SMC-сэмплирование с гарантиями сходимости. |
| 2026 | AutoSR: Automatic Symbolic Regression by Searching Research States | [2608.16876](https://arxiv.org/abs/2608.16876) | → AIF,LSRB | 0 | AutoSR: поиск по состояниям исследования, а не изолированным уравнениям; учитывает расхождение экстраполяций. |
| 2026 | AgenticEvolve: Evolutionary Program Search with Persistent Language Model Agents that Design and Run Experiments | [2610.31326](https://arxiv.org/abs/2610.31326) | → LSRB | 0 | AgenticEvolve: эволюционный поиск программ с персистентными LLM-агентами, ставящими эксперименты. |
| 2026 | ExpEvolve: Structuring and Reusing Experience for Open-Ended Discovery | [2610.29303](https://arxiv.org/abs/2610.29303) | → DB,LSRB | 0 | ExpEvolve: структурирование и переиспользование опыта в эволюционных coding-агентах. |
| 2026 | SpecEvo: Speculative Evolution with Large Language Models for Cost-Efficient Scientific Discovery | [2610.28706](https://arxiv.org/abs/2610.28706) | → LSRB | 0 | SpecEvo: спекулятивная эволюция с дешёвыми и дорогими LLM для экономии. |
| 2026 | The Weight of Teamwork: Does Communication Structure Help LLM Scientists Search for Scientific Laws? | [2610.24131](https://arxiv.org/abs/2610.24131) | → LSRB | 0 | Влияние структуры коммуникации в командах LLM-учёных на поиск законов (SR). |
| 2026 | Coupled Harness--Model Evolution for Scientific Equation Discovery | [2610.17740](https://arxiv.org/abs/2610.17740) | → LSRB | 0 | Совместная эволюция harness и модели для открытия уравнений. |
| 2026 | EvoMO-SR: Multiobjective LLM-based Evolution of Symbolic Expressions with substructure guidance | [2609.36187](https://arxiv.org/abs/2609.36187) | → LSRB | 0 | EvoMO-SR: многокритериальная LLM-эволюция выражений. |
| 2026 | Evolutionary Identification of Scientific Equations Using Language-Model-Guided Symbolic Regression | [doi](https://doi.org/10.1145/3795101.3805332) | → LSRB | 0 | LLM-управляемая эволюционная SR для семейств уравнений, заданных неявно. |
| 2026 | GAE: Graph-Augmented Evolution for Scientific Discovery via Reinforcement Optimization | [2607.10127](https://arxiv.org/abs/2607.10127) | → LSRB | 0 | GAE: графово-дополненная эволюция программ с RL для научного открытия. |
| 2025 | ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution | [2509.19349](https://arxiv.org/abs/2509.19349) | ← UD | 225 | ShinkaEvolve: эффективная LLM-эволюция программ для открытия. |
| 2025 | Finetuning Large Language Model as an Effective Symbolic Regressor | [2508.09897](https://arxiv.org/abs/2508.09897) | → LSRB | 2 | Дообучение LLM как символьного регрессора. |
| 2025 | EvoSLD: Automated Neural Scaling Law Discovery With Large Language Models | [doi](https://doi.org/10.48550/arXiv.2507.21184) | → AIF,LSRB | 1 | EvoSLD: эволюционное LLM-открытие законов масштабирования нейросетей (без аннотации). |
| — | C ONTEXT A UGMENTATION FOR LLM-BASED | — | → AIF,LSRB | 0 | Битая запись про контекстную аугментацию LLM-SR (вероятно дубликат id 63) (без аннотации). |

### Индукция моделей мира (11)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | PatchWorld: Gradient-Free Optimization of Executable World Models | [2605.30880](https://arxiv.org/abs/2605.30880) | → NB | 7 | PatchWorld: безградиентная оптимизация исполняемых кодовых моделей мира текстовых сред. |
| 2026 | PACE-Bench: Benchmarking Physics Adaptation via Code Evolution in Dynamic Environments | [2608.14441](https://arxiv.org/abs/2608.14441) | → NB | 2 | PACE-Bench: адаптация агентов к изменённой физике симулятора через эволюцию кода (144 задачи). |
| 2026 | VisualPatchWorld: Code World Models as Latent Structured Representations for Planning | [2607.25236](https://arxiv.org/abs/2607.25236) | → NB | 2 | VisualPatchWorld: кодовые модели мира как латентные структурные представления для планирования. |
| 2026 | Do Enterprise Systems Need Learned World Models? The Importance of Context to Infer Dynamics | [2605.12178](https://arxiv.org/abs/2605.12178) | → DW | 2 | Нужны ли выученные модели мира в корпоративных системах — вывод динамики из контекста; нетехнический домен. |
| 2026 | ChemWorld: Programmable Chemical Worlds for Controlled and Replayable Agent Experimentation | [2608.10792](https://arxiv.org/abs/2608.10792) | → DW,NB | 1 | ChemWorld: программируемые химические миры для воспроизводимых экспериментов агентов. |
| 2026 | EvoSim: Learning to Model, Modeling to Learn | [2610.11344](https://arxiv.org/abs/2610.11344) | → NB | 0 | EvoSim: агент строит физические модели (процессы, уравнения, параметры) из экспериментов. |
| 2026 | EvoBelief: Falsifiable World Models for Self-Improving LLM Agents | [2610.12789](https://arxiv.org/abs/2610.12789) | → DW | 0 | EvoBelief: фальсифицируемые модели мира, обновляемые агентом при развёртывании; ревизия убеждений о динамике среды в агентном (не научном) контексте. |
| 2026 | Continual Enterprise World Model Discovery in Dynamic Systems | [2609.19551](https://arxiv.org/abs/2609.19551) | → DW | 0 | Непрерывное открытие правил корпоративной системы как модели мира; индукция скрытых правил в нетехническом домене. |
| 2026 | CASSANDRA: Programmatic and Probabilistic Learning and Inference for Stochastic World Modeling | [2601.18620](https://arxiv.org/abs/2601.18620) | → DW | 0 | CASSANDRA: нейросимвольная вероятностная модель мира с LLM для бизнес-доменов; индукция динамики из малых данных. |
| 2021 | Alchemy: A structured task distribution for meta-reinforcement learning | [doi](https://doi.org/10.48550/arXiv.2102.02926) | ← DW | 28 | Alchemy: структурированное распределение задач для мета-RL со скрытой причинной структурой. (без аннотации) |
| 2008 | The discovery of structural form | [doi](https://doi.org/10.1073/pnas.0802631105) | ← UD | 660 | Kemp–Tenenbaum: открытие структурной формы данных байесовским выбором. |

### Активный эксперимент (11)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Sampling Is Not Curiosity: Why LLM Agents Should Investigate | [2611.10501](https://arxiv.org/abs/2611.10501) | → DW | 0 | Позиционная работа: семплирование не есть любопытство, LLM-агенты должны целенаправленно исследовать; концептуально близко к активному эксперименту. |
| 2026 | CrashGym: Measuring the Decision Value of Experimentation for LLM Agents in Counterfactual Market Crashes | [2610.29245](https://arxiv.org/abs/2610.29245) | → DW | 0 | CrashGym: ценность экспериментов агента для решений в контрфактических рыночных крахах; бюджет экспериментов, но финансовый домен. |
| 2026 | Before Agents Decide: Epistemic Action in LLM-Based Systems | [2610.00511](https://arxiv.org/abs/2610.00511) | → DW | 0 | Эпистемические действия LLM-агентов для улучшения свидетельств перед решением; концептуально близко к активному сбору данных. |
| 2025 | Shoot First, Ask Questions Later? Building Rational Agents that Explore and Act Like People | [2510.20886](https://arxiv.org/abs/2510.20886) | → DW | 12 | Рациональные ли LM-агенты в стратегическом поиске информации (вопросы под неопределённостью); близко к выбору информативных запросов. |
| 2025 | Exploring exploration with foundation agents in interactive environments | — | → DW | 2 | Исследование стратегий исследования фундаментальных агентов (Feature World, скрытая функция награды); журнальная версия 385. |
| 2025 | Information Seeking for Robust Decision Making under Partial Observability | [2510.01531](https://arxiv.org/abs/2510.01531) | → DW | 0 | Информационный поиск LLM при частичной наблюдаемости для робастных решений; общий активный сбор информации. |
| 2024 | BioDiscoveryAgent: An AI Agent for Designing Genetic Perturbation Experiments | [2405.17631](https://arxiv.org/abs/2405.17631) | ← DP | 107 | BioDiscoveryAgent: LLM-агент проектирует генетические эксперименты с генетическими возмущениями; активный эксперимент, но в биологии. |
| 2015 | Cheaper faster drug development validated by the repositioning of drugs against neglected tropical diseases | [doi](https://doi.org/10.1098/rsif.2014.1289) | ← DW | 153 | Робот-учёный Eve для репозиционирования лекарств; пример замкнутого цикла автоматического экспериментирования. |
| 2004 | Functional genomic hypothesis generation and experimentation by a robot scientist | [doi](https://doi.org/10.1038/nature02236) | ← DW | 764 | Робот-учёный Adam (Кинг, 2004): генерация гипотез и эксперименты в функциональной геномике; классический замкнутый цикл открытия. |
| 1991 | Curious model-building control systems | [doi](https://doi.org/10.1109/IJCNN.1991.170605) | ← PG | 745 | Шмидхубер 1991: любопытные контроллеры, строящие модель мира; ранний предок активного исследования среды. (без аннотации) |
| 1991 | A possibility for implementing curiosity and boredom in model-building neural controllers | [doi](https://doi.org/10.7551/mitpress/3115.003.0030) | ← PG | 677 | Шмидхубер 1991: подкрепление за прирост знаний модели (любопытство и скука); ранняя идея внутренней мотивации исследования. |

### Прикладная символьная регрессия (9)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Scattering Amplitudes as Programs: Self-Evolving Search for Theory and Event Generation | [2607.21629](https://arxiv.org/abs/2607.21629) | → DP | 6 | Амплитуды рассеяния как программы с самоэволюционирующим поиском; прикладной поиск структуры в теорфизике. |
| 2026 | Interpretable neural equation learning for high-dimensional materials data | [2610.37880](https://arxiv.org/abs/2610.37880) | → AIF,LSRB | 0 | nn-EQL: нейросетевое обучение уравнений для разреженных высокоразмерных данных материаловедения. |
| 2026 | Automatic Ordinary Differential Equations Discovery For Biological Systems Using Large Language Model Powered Agentic System | [2607.13608](https://arxiv.org/abs/2607.13608) | → AIF,LSRB | 0 | LLM-агентная система для открытия ОДУ биологических систем. |
| 2026 | AI-Assisted Tumor-Growth Law Discovery from Sparse Data: Refitting and LLM-Based Ranking | [2610.16891](https://arxiv.org/abs/2610.16891) | → LSRB | 0 | SR + LLM-ранжирование для законов роста опухоли по разреженным данным. |
| 2026 | Introduction to using symbolic regression for interpretable machine learning in healthcare | [doi](https://doi.org/10.1038/s43856-026-01914-x) | → LSRB | 0 | Введение в SR для интерпретируемого ML в медицине. |
| 2025 | Discovering network dynamics with neural symbolic regression | [doi](https://doi.org/10.1038/s43588-025-00893-8) | → AIF,LSRB | 24 | Нейросимвольная регрессия динамики сетей (генные регуляторные, эпидемии). |
| 2025 | Data-driven discovery of digital twins in biomedical research | [2508.21484](https://arxiv.org/abs/2508.21484) | → AIF,LSRB | 12 | Обзор data-driven открытия цифровых двойников в биомедицине. |
| 2025 | Deep Learning based discovery of Integrable Systems | [2503.10469](https://arxiv.org/abs/2503.10469) | → DW | 5 | Глубокое обучение для открытия интегрируемых систем (уравнение Янга–Бакстера); прикладное открытие в матфизике. |
| 2024 | AutoTurb: Using Large Language Models for Automatic Algebraic Model Discovery of Turbulence Closure | [2410.10657](https://arxiv.org/abs/2410.10657) | ← LSRB | 3 | AutoTurb: LLM для открытия алгебраических моделей турбулентного замыкания. |

### Открытие на основе данных (4)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Scaling Scientific Discovery Environments for Turn-Level Agentic RL | [2607.28990](https://arxiv.org/abs/2607.28990) | → DW | 4 | Масштабирование сред data-driven научного открытия для пошагового агентного RL; обучение, а не оценка. |
| 2025 | AutoSDT: Scaling Data-Driven Discovery Tasks Toward Open Co-Scientists | [2506.08140](https://arxiv.org/abs/2506.08140) | → DB,LSRB | 12 | AutoSDT: автоматический сбор задач data-driven открытия для обучения ко-сайентистов. |
| 2025 | Automated Model Discovery via Multi-modal & Multi-step Pipeline | [2509.25946](https://arxiv.org/abs/2509.25946) | → AIF,DB | 3 | Мультимодальный многошаговый пайплайн автоматического выбора модели (гауссовские процессы и т.п.). |
| 2024 | Are LLMs Capable of Data-based Statistical and Causal Reasoning? Benchmarking Advanced Quantitative Reasoning with Data | [2402.17644](https://arxiv.org/abs/2402.17644) | ← DB | 105 | QRData: статистическое и причинное рассуждение LLM на реальных данных; смежная оценка количественного вывода. |

### Контаминация и запоминание (2)

| Год | Работа | Ссылка | Связь | Цит. | Суть |
|---|---|---|---|---|---|
| 2026 | Adversarial Fast-Moving Real-World Domains as Test Beds for Benchmarking AI Scientist Capabilities | [2608.03569](https://arxiv.org/abs/2608.03569) | → DB | 0 | Быстро меняющиеся реальные домены (F1, MTG) как бенчмарк новизны идей без утечки; идея анти-контаминации, но далеко от физики. |
| 2025 | ScienceMeter: Tracking Scientific Knowledge Updates in Language Models | [2505.24302](https://arxiv.org/abs/2505.24302) | → DW | 5 | ScienceMeter: обновление научных знаний LLM (сохранение 85.9%, приобретение 71.7%, проекция 37.7%); про знания, не открытие. |

## Уровень D — не по теме

- 2026 — Feynman Explanation Prompting: A Pedagogically Grounded Framework for Large Language Models (→ AIF,LSRB)
- 2026 — Assessing Large Language Models for Stabilizing Numerical Expressions in Scientific Software (→ LSRB)
- 2026 — The rise of agentic AI in drug discovery from static tools to autonomous virtual scientists (→ NB)
- 2026 — Learning Meta-Skills for Agent Harness Design in Test-Time AI4AI (→ NB)
- 2026 — Absorbing State Phase Transitions in Multi-Agent Search (→ NB)
- 2026 — ActiveMem: Dynamic Latent Memory Trees for Long-Horizon Agents (→ NB)
- 2026 — StudyBench: Can Self-Evolution Squeeze Textbooks for Olympiad Capability? (→ NB)
- 2026 — AutoTrainess: Teaching Language Models to Improve Language Models Autonomously (→ NB)
- 2026 — PhysAI-Bench: A Benchmark for LLM-Based Agentic Decision-Making in Autonomous UAV-Centric Physical AI (→ PG)
- 2026 — NuPaD: A Generative AI Framework for Fostering Deep Learning in Subatomic Physics (→ DP)
- 2026 — ScienceVision: Can AI Observe and Reason Like a Scientist? (→ DW)
- 2026 — Can agents reliably design therapeutic antibodies? (→ DW)
- 2026 — CaliMem: Search-Efficient Data Agent via Calibrated Memory (→ DW)
- 2026 — EvolvingBrain: An Adaptive Skill System for Multi-modal Agents Self-Evolution in Open Worlds (→ DW)
- 2026 — Davinci-Tool: Scaling Agentic Tool-Use Supervision with Verifiable Executable Environments (→ DW)
- 2026 — Safe, Persistent, and Evolving Agent Harness for Understanding Partially Observable Worlds (→ DW)
- 2026 — ServeLearnBench: How Well Can Agents Self-Improve from Serving Experience? (→ DW)
- 2026 — Are Frontier VLM Agents Ready to Be Robot Generalists? An Empirical Study with the Embodied Agent Arena (→ DW)
- 2026 — AI Agents Accelerate the Discovery and Engineering of Food Molecules (→ DW)
- 2026 — KV-streams for Efficient Compaction in Agentic Reinforcement Learning (→ DW)
- 2026 — Beyond Scaling: A Survey of Data-Efficient Learning for LLM Agents (→ DW)
- 2026 — TraceML: What Auto-Research Agents Miss in Long-Horizon ML Development (→ DW)
- 2026 — Trustworthy LLM-Based Agents for Data-Centric AI (→ DW)
- 2026 — AutoWorldModel-Bench: A State-Centric Benchmark for Automated World-Model Research (→ DW)
- 2026 — SciForge: An AI-Native, Multimodal Workbench for Scientific Discovery (→ DW)
- 2026 — PaperClaw: Harnessing Agents for Autonomous Research and Human-in-the-Loop Refinement (→ DB,DW)
- 2026 — LabOSBench: Benchmarking Computer Use Agents for Scientific Instrument Control (→ DW)
- 2026 — AdaMEM: Test-Time Adaptive Memory for Language Agents (→ DW)
- 2026 — AutoMedBench: Towards Medical AutoResearch with Agentic AI Models (→ DW)
- 2026 — ElasticMem: Latent Memory as a Learnable Resource for LLM Agents (→ DW)
- 2026 — AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration (→ DW)
- 2026 — ArtifactLinker: Linking Scientific Artifacts for Automatic State-of-the-Art Discovery (→ DW)
- 2026 — Behavior Cue Reasoning: Monitorable Reasoning Improves Efficiency and Safety through Oversight (→ DW)
- 2026 — Evolving Idea Graphs with Learnable Edits-and-Commits for Multi-Agent Scientific Ideation (→ DB,DW)
- 2026 — Revisiting the Travel Planning Capabilities of Large Language Models (→ DW)
- 2026 — Models Recall What They Violate: Constraint Adherence in Multi-Turn LLM Ideation (→ DW)
- 2026 — Relational Archetypes: A Comparative Analysis of AV-Human and Agent-Human Interactions (→ DW)
- 2026 — TREX: Automating LLM Fine-tuning via Agent-Driven Tree-based Exploration (→ DW)
- 2026 — AgentCE-Bench: Agent Configurable Evaluation with Scalable Horizons and Controllable Difficulty under Lightweight Environments (→ DW)
- 2026 — How Well Does Agent Development Reflect Real-World Work? (→ DB,DW)
- 2026 — From physics to machine learning and back: Part II - Learning and observational bias in prognostics and health management (PHM) (→ DW)
- 2026 — A Survey on Evaluation of LLM-based Agents (→ DW)
- 2026 — TraceML: An Empirical Analysis of Human-Agent Planning in Machine Learning Development (→ DW)
- 2026 — "Nothing to See Here": Unintended Disclosure through Revision Traces of LLM Deliverables (→ DB)
- 2026 — Searching for Synergy in Shared Workspace Human-AI Collaboration (→ DB)
- 2026 — ABC-Bench: An Agentic Bio-Capabilities Benchmark for Biosecurity (→ DB)
- 2026 — Agentics 2.0: Logical Transduction Algebra for Agentic Data Workflows (→ DB)
- 2025 — FELA: A Multi-Agent Evolutionary System for Feature Engineering of Industrial Event Log Data (→ LSRB)
- 2025 — Paper2Video: Automatic Video Generation from Scientific Papers (→ LSRB)
- 2025 — VFSI: Validity First Spatial Intelligence for Constraint-Guided Traffic Diffusion (→ LSRB)
- 2025 — Large Language Model-Based Automatic Formulation for Stochastic Optimization Models (→ LSRB)
- 2025 — Ascending the Infinite Ladder: Benchmarking Spatial Deformation Reasoning in Vision-Language Models (→ LSRB)
- 2025 — GGBench: A Geometric Generative Reasoning Benchmark for Unified Multimodal Models (→ NB)
- 2025 — CritiCal: Can Critique Help LLM Uncertainty or Confidence Calibration? (→ NB)
- 2025 — Empowering Real-World: A Survey on the Technology, Practice, and Evaluation of LLM-driven Industry Agents (→ DW,PG)
- 2025 — Mode-Conditioning Unlocks Superior Test-Time Scaling (→ DW)
- 2025 — Mini Amusement Parks (MAPs): A Testbed for Modelling Business Decisions (→ DW)
- 2025 — The End of Trial-and-Error: A Vision for Generative Intelligence in Metamaterial Design (→ DW)
- 2025 — OpenLens AI: Fully Autonomous Research Agent for Health Infomatics (→ DW)
- 2025 — Beyond Benchmarks: LLM Evaluation with an Anthropomorphic and Lifecycle-oriented Roadmap (→ DW)
- 2025 — Levels of Autonomy for AI Agents (→ DW)
- 2025 — Perspective on utilizing foundation models for laboratory automation in materials research (→ DW)
- 2025 — Evolutionary Perspectives on the Evaluation of LLM-Based AI Agents: A Comprehensive Survey (→ DW)
- 2025 — Smotrom tvoja pa ander drogoj verden! Resurrecting Dead Pidgin with Generative Models: Russenorsk Case Study (→ DW)
- 2025 — OpenFOAMGPT 2.0: End-to-end, trustworthy automation for computational fluid dynamics (→ DW)
- 2025 — debug-gym: A Text-Based Environment for Interactive Debugging (→ DW)
- 2025 — AgentRxiv: Towards Collaborative Autonomous Research (→ DB,DW)
- 2025 — HCAST: Human-Calibrated Autonomy Software Tasks (→ DW)
- 2025 — LLM Agents for Education: Advances and Applications (→ DW)
- 2025 — Probing Semantic Routing in Large Mixture-of-Expert Models (→ DW)
- 2025 — The AI Agent Index (→ DW)
- 2025 — Meta-regression to explain shrinkage and heterogeneity in large-scale replication projects (← DB)
- 2025 — JoyAgent-JDGenie: Technical Report on the GAIA (→ DB)
- 2025 — Transduction is All You Need for Structured Data Workflows (→ DB)
- 2025 — BIASINSPECTOR: Detecting Bias in Structured Data through LLM Agents (→ DB)
- 2025 — Exploring LLM Agents for Cleaning Tabular Machine Learning Datasets (→ DB)
- 2025 — From System 1 to System 2: A Survey of Reasoning Large Language Models (← NB)
- 2025 — Emergent Hierarchical Reasoning in LLMs through Reinforcement Learning (← NB)
- 2025 — Beyond the 80/20 Rule: High-Entropy Minority Tokens Drive Effective Reinforcement Learning for LLM Reasoning (← NB)
- 2024 — Scientific Large Language Models: A Survey on Biological & Chemical Domains (← PG)
- 2024 — MetaScientist: A Human-AI Synergistic Framework for Automated Mechanical Metamaterial Design (→ DW)
- 2024 — Cocoa: Co-Planning and Co-Execution with AI Agents (→ DW)
- 2024 — SUPER: Evaluating Agents on Setting Up and Executing Tasks from Research Repositories (→ DW)
- 2024 — Industrial Practices of Requirements Engineering for ML-Enabled Systems in Brazil (← DB)
- 2024 — Effect of introduction pathways on the invasion success of non-native plants along environmental gradients (← DB)
- 2024 — Are Machines Better at Complex Reasoning? Unveiling Human-Machine Inference Gaps in Entailment Verification (← DB)
- 2024 — SciDFM: A Large Language Model with Mixture-of-Experts for Science (← GB)
- 2024 — FrontierMath: A Benchmark for Evaluating Advanced Mathematical Reasoning in AI (← US)
- 2024 — Large Language Models for Mathematical Reasoning: Progresses and Challenges (← NB)
- 2023 — A Comprehensive Overview of Large Language Models (← PG)
- 2023 — ADaPT: As-Needed Decomposition and Planning with Language Models (← DW)
- 2023 — Generalized Biomolecular Modeling and Design with RoseTTAFold All-Atom (← DW)
- 2023 — InterCode: Standardizing and Benchmarking Interactive Coding with Execution Feedback (← DW)
- 2023 — Minigrid & Miniworld: Modular & Customizable Reinforcement Learning Environments for Goal-Oriented Tasks (← DW)
- 2023 — Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models (← DW)
- 2023 — Democratizing LLMs: An Exploration of Cost-Performance Trade-offs in Self-Refined Open-Source Models (← DB)
- 2023 — Status Quo and Problems of Requirements Engineering for Machine Learning: Results from an International Survey (← DB)
- 2023 — Exploring Progress in Multivariate Time Series Forecasting: Comprehensive Benchmarking and Heterogeneity Analysis (← DB)
- 2023 — Accelerated body size evolution in upland environments is correlated with recent speciation in South American freshwater fishes (← DB)
- 2023 — Evaluating Instruction-Tuned Large Language Models on Code Comprehension and Generation (← DB)
- 2023 — Impact of Education on Economic Development (← DB)
- 2023 — AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web (← DB)
- 2023 — AutoML-GPT: Automatic Machine Learning with GPT (← DB)
- 2023 — Self-Refine: Iterative Refinement with Self-Feedback (← DB,UD)
- 2023 — Reflexion: language agents with verbal reinforcement learning (← DB)
- 2023 — Toolformer: Language Models Can Teach Themselves to Use Tools (← DB,SU)
- 2023 — Unter Hügeln. Bronzezeitliche Transformationsprozesse in Schleswig-Holstein am Beispiel des Fundplatzes von Mang de Bargen (Bornhöved, Kr. Segeberg). BAND 2 (← DB)
- 2023 — AutoKeras: An AutoML Library for Deep Learning (← DB)
- 2023 — Scaling deep learning for materials discovery (← SU)
- 2022 — Decomposed Prompting: A Modular Approach for Solving Complex Tasks (← DW)
- 2022 — MineDojo: Building Open-Ended Embodied Agents with Internet-Scale Knowledge (← DW)
- 2022 — AMLB: an AutoML Benchmark (← DB)
- 2022 — A systematic literature review of methods and datasets for anomaly-based network intrusion detection (← DB)
- 2022 — The Impact of Education on GDP per Capita (← DB)
- 2022 — WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents (← NB)
- 2021 — ‘Supporting Evidence’ (← DW)
- 2021 — MiniHack the Planet: A Sandbox for Open-Ended Reinforcement Learning Research (← DW)
- 2021 — Highly accurate protein structure prediction with AlphaFold (← DB,DW,SU)
- 2021 — The Dynamic Impact of Government Expenditure in Education on Economic Growth (← DB)
- 2021 — Radiocarbon Dated Trends and Central Mediterranean Prehistory (← DB)
- 2021 — Long-Term Demographic Trends in Prehistoric Italy: Climate Impacts and Regionalised Socio-Ecological Trajectories (← DB)
- 2021 — National Longitudinal Survey of Youth 1997 (← DB)
- 2021 — Evaluating Large Language Models Trained on Code (← DB)
- 2021 — Measuring Mathematical Problem Solving With the MATH Dataset (← GB)
- 2020 — Classical Electrodynamics (← AIF)
- 2020 — ALFWorld: Aligning Text and Embodied Environments for Interactive Learning (← DW)
- 2020 — The NetHack Learning Environment (← DW)
- 2020 — H2O AutoML: Scalable Automatic Machine Learning (← DB)
- 2020 — Array programming with NumPy (← GB)
- 2019 — ALFRED: A Benchmark for Interpreting Grounded Instructions for Everyday Tasks (← DW)
- 2019 — Interactive Fiction Games: A Colossal Adventure (← DW)
- 2019 — How's Life?. Living Conditions in the 2nd and 1st Millennia BCE (← DB)
- 2019 — Human impact and population dynamics in the Neolithic and Bronze Age: Multi-proxy evidence from north-western Central Europe (← DB)
- 2019 — Monuments and economies: What drove their variability in the middle-Holocene Neolithic? (← DB)
- 2019 — SciPy 1.0: fundamental algorithms for scientific computing in Python (← GB,US)
- 2019 — HellaSwag: Can a Machine Really Finish Your Sentence? (← GB)
- 2018 — A disciplined approach to neural network hyper-parameters: Part 1 - learning rate, batch size, momentum, and weight decay (← AIF)
- 2018 — Machine Learning-Assisted Discovery of Solid Li-Ion Conducting Materials (← DW)
- 2018 — TextWorld: A Learning Environment for Text-based Games (← DW)
- 2018 — Kommunikationsstrukturen mittelneolithischer Gesellschaften im nordmitteleuropäischen Tiefland (← DB)
- 2018 — Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge (← GB)
- 2017 — Genetic Algorithms for Pattern Recognition (← AIF)
- 2017 — Super-Convergence: Very Fast Training of Residual Networks Using Large Learning Rates (← AIF)
- 2017 — AI2-THOR: An Interactive 3D Environment for Visual AI (← DW)
- 2017 — The Effect of Education Expenditure on Per Capita GDP in Developing Countries (← DB)
- 2017 — Quantitative historical analysis uncovers a single dimension of complexity that structures global variation in human social organization (← SU)
- 2016 — Race, Wealth and Incarceration: Results from the National Longitudinal Survey of Youth (← DB)
- 2015 — Efficient and Robust Automated Machine Learning (← DB)
- 2015 — Seshat: The Global History Databank (← SU)
- 2013 — Quantum Field Theory and the Standard Model (← AIF)
- 2013 — Outer Wilds A Game of Curiosity-Driven Space Exploration (← UD)
- 2012 — I and J (← AIF)
- 2012 — The Pennsylvania State University (← AIF)
- 2012 — A measure of intelligence (← DP)
- 2011 — Eureqa: software review (← AIF)
- 2010 — Genetic Algorithm-based Dynamic Vehicle Route Search using Car-to-Car Communication (← AIF)
- 2010 — Genetic Algorithm-based Dynamic Vehicle Route Search using Car-toCar Communication (← AIF)
- 2010 — A Study of Clustered Data and Approaches to Its Analysis (← DB)
- 2010 — The Impact of Incarceration on Employment during the Transition to Adulthood (← DB)
- 2010 — Immigration, Offshoring and American Jobs (← DB)
- 2010 — Data Structures for Statistical Computing in Python (← DB)
- 2010 — Positive (← UD)
- 2007 — Measurement (← DW)
- 2007 — Historical Dynamics: Why States Rise and Fall (← SU)
- 2006 — Influence of cultivation temperature on the ligninolytic activity of selected fungal strains (← AIF)
- 2006 — Invited review of the book Statistical and Inductive Inference by Minimum Message Length (← PG)
- 2005 — Are time preference and body mass index associated? Evidence from the National Longitudinal Survey of Youth. (← DB)
- 2004 — Genetic algorithms in cryptography (← AIF)
- 2003 — 3G mobile wireless routing optimization by genetic algorithm (← AIF)
- 2003 — Numeracy, literacy and earnings: evidence from the National Longitudinal Survey of Youth (← DB)
- 2002 — A genetic algorithms approach to growth phase forecasting of wireless subscribers (← AIF)
- 1999 — Classical Electrodynamics, 3rd ed. (← AIF)
- 1994 — Genetic Algorithms and Investment Strategies (← AIF)
- 1994 — Using Genetic Algorithms to Learn Reactive Control Parameters for Autonomous Robotic Navigation (← AIF)
- 1994 — Gerätegeld Sichel: Studien zur monetären Struktur bronzezeitlicher Horte im nördlichen Mitteleuropa (← DB)
- 1990 — Construction of higher order symplectic integrators (← DP)
- 1990 — Are different events involved in the development of sporadic versus hereditary tumours? The possible importance of the microenvironment in hereditary cancer. (← DW)
- 1983 — Approximations to the radii of Roche lobes (← GB)
- 1982 — Social Background, Academic Resources, and College Graduation: Recent Evidence from the National Longitudinal Survey (← DB)
- 1973 — Gravitation and Cosmology: Principles and Applications of the General Theory of Relativity (← AIF)
- 1971 — Feynman Lectures on Physics (← AIF)
- — — AND D (← AIF)
- — — O RCHESTRATING T OOL E COSYSTEM OF D RUG D IS - COVERY WITH I NTENTION -A WARE LLM A GENTS (→ DW)
- — — : ACTION (← US)
