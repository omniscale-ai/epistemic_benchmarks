# Популярность бенчмарков: цитирования и звёзды GitHub

Снимок на 2026-11-12. **Цитирования** — `citationCount` из Semantic Scholar (по arXiv id или DOI). OpenAlex обычно даёт меньше: например, у LLM-SRBench 77 против 98 в S2. **Звёзды** сняты со страницы репозитория на github.com, потому что API без авторизации исчерпан. Репозиторий — первый, указанный в разборе или карточке. «нет репо» — код не опубликован или не найден; «н/д» — страница не отдала счётчик (CausaLab-Benchmark) или вернула 404 (LEGION, Gen2Bench). **Возраст** — в месяцах от месяца в arXiv id до ноября 2026.

Всего 152 записей: 64 полных разборов (`*/info.md`) и 88 карточек (`benchmarks_general.md`). Те же числа вписаны строкой «Популярность» в начало каждого разбора и каждой карточки. Машиночитаемая версия: `benchmark_stats.csv`.

**Осторожно с фильтром «0 цитирований».** Таких записей 37, из них 17 с полным разбором. 30 из этих 37 вышли за последние 3 месяца и просто не успели набрать цитирования. Среди них самые близкие к нам работы: ULTRADISCOVERY, Unsatz, Synthetic Universes, LUCA. Разумнее фильтровать по сочетанию «0 цитирований и возраст ≥ 6 месяцев» или смотреть на звёзды.

| Бенчмарк | Разбор | Год | Возраст, мес. | Цитирований | ★ | arXiv | Репозиторий |
|---|---|---|---|---|---|---|---|
| SWE-bench (карточка) | карточка | 2023 | 37 | 4885 | 6180 | [2310.06770](https://arxiv.org/abs/2310.06770) | [SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench) |
| GPQA (карточка) | карточка | 2023 | 36 | 3949 | 549 | [2311.12022](https://arxiv.org/abs/2311.12022) | [idavidrein/gpqa](https://github.com/idavidrein/gpqa) |
| Coscientist (Nature) (карточка) | карточка | 2023 | — | 1591 | 214 | doi 10.1038/s41586-023-06792-0 | [gomesgroup/coscientist](https://github.com/gomesgroup/coscientist) |
| ChemCrow (карточка) | карточка | 2023 | 43 | 1490 | 971 | [2304.05376](https://arxiv.org/abs/2304.05376) | [ur-whitelab/chemcrow-public](https://github.com/ur-whitelab/chemcrow-public) |
| [AI Feynman / Feynman Symbolic Regression Database (FSReD)](ai-feynman/info.md) | полный | 2019 | 90 | 1489 | 785 | [1905.11481](https://arxiv.org/abs/1905.11481) | [SJ001/AI-Feynman](https://github.com/SJ001/AI-Feynman) |
| MLE-bench (карточка) | карточка | 2024 | 25 | 578 | 1798 | [2410.07095](https://arxiv.org/abs/2410.07095) | [openai/mle-bench](https://github.com/openai/mle-bench) |
| The AI Scientist-v2 (карточка) | карточка | 2025 | 19 | 515 | 7501 | [2504.08066](https://arxiv.org/abs/2504.08066) | [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) |
| MLAgentBench (карточка) | карточка | 2023 | 37 | 461 | 360 | [2310.03302](https://arxiv.org/abs/2310.03302) | [snap-stanford/MLAgentBench](https://github.com/snap-stanford/MLAgentBench) |
| ScienceWorld (карточка) | карточка | 2022 | 56 | 439 | 409 | [2203.07540](https://arxiv.org/abs/2203.07540) | [allenai/ScienceWorld](https://github.com/allenai/ScienceWorld) |
| PaperBench (карточка) | карточка | 2025 | 19 | 393 | 1340 | [2504.01848](https://arxiv.org/abs/2504.01848) | [openai/frontier-evals](https://github.com/openai/frontier-evals) |
| LiveBench (карточка) | карточка | 2024 | 29 | 313 | 1355 | [2406.19314](https://arxiv.org/abs/2406.19314) | [LiveBench/LiveBench](https://github.com/LiveBench/LiveBench) |
| [ScienceAgentBench](scienceagentbench/info.md) | полный | 2024 | 25 | 312 | 184 | [2410.05080](https://arxiv.org/abs/2410.05080) | [OSU-NLP-Group/ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench) |
| RE-Bench (карточка) | карточка | 2024 | 24 | 221 | 171 | [2411.15114](https://arxiv.org/abs/2411.15114) | [METR/RE-Bench](https://github.com/METR/RE-Bench) |
| SciCode (карточка) | карточка | 2024 | 28 | 220 | 246 | [2407.13168](https://arxiv.org/abs/2407.13168) | [scicode-bench/SciCode](https://github.com/scicode-bench/SciCode) |
| Coscientist (препринт) (карточка) | карточка | 2023 | 43 | 198 | нет репо | [2304.05332](https://arxiv.org/abs/2304.05332) | — |
| CORE-Bench (карточка) | карточка | 2024 | 26 | 158 | 80 | [2409.11363](https://arxiv.org/abs/2409.11363) | [siegelz/core-bench](https://github.com/siegelz/core-bench) |
| Rediscovering orbital mechanics (карточка) | карточка | 2022 | 57 | 152 | нет репо | [2202.02306](https://arxiv.org/abs/2202.02306) | — |
| DSBench (карточка) | карточка | 2024 | 26 | 147 | 131 | [2409.07703](https://arxiv.org/abs/2409.07703) | [LiqiangJing/DSBench](https://github.com/LiqiangJing/DSBench) |
| BixBench (карточка) | карточка | 2025 | 20 | 137 | 153 | [2503.00096](https://arxiv.org/abs/2503.00096) | [Future-House/BixBench](https://github.com/Future-House/BixBench) |
| [DiscoveryWorld](discoveryworld/info.md) | полный | 2024 | 29 | 136 | 229 | [2406.06769](https://arxiv.org/abs/2406.06769) | [allenai/discoveryworld](https://github.com/allenai/discoveryworld) |
| MLGym / MLGym-Bench (карточка) | карточка | 2025 | 21 | 129 | 625 | [2502.14499](https://arxiv.org/abs/2502.14499) | [facebookresearch/MLGym](https://github.com/facebookresearch/MLGym) |
| [DiscoveryBench](discoverybench/info.md) | полный | 2024 | 28 | 124 | 167 | [2407.01725](https://arxiv.org/abs/2407.01725) | [allenai/discoverybench](https://github.com/allenai/discoverybench) |
| QRData (карточка) | карточка | 2024 | 33 | 105 | 49 | [2402.17644](https://arxiv.org/abs/2402.17644) | [xxxiaol/QRData](https://github.com/xxxiaol/QRData) |
| [BLADE](blade/info.md) | полный | 2024 | 27 | 105 | 40 | [2408.09667](https://arxiv.org/abs/2408.09667) | [behavioral-data/BLADE](https://github.com/behavioral-data/BLADE) |
| [LLM-SRBench](llm-srbench/info.md) | полный | 2025 | 19 | 98 | 132 | [2504.10415](https://arxiv.org/abs/2504.10415) | [deep-symbolic-mathematics/llm-srbench](https://github.com/deep-symbolic-mathematics/llm-srbench) |
| OMNI-EPIC (карточка) | карточка | 2024 | 30 | 89 | 83 | [2405.15568](https://arxiv.org/abs/2405.15568) | [maxencefaldor/omni-epic](https://github.com/maxencefaldor/omni-epic) |
| ResearchBench (карточка) | карточка | 2025 | 20 | 72 | нет репо | [2503.21248](https://arxiv.org/abs/2503.21248) | — |
| [SRSD (SRSD-Feynman)](srsd/info.md) | полный | 2022 | 53 | 65 | 44 | [2206.10540](https://arxiv.org/abs/2206.10540) | [omron-sinicx/srsd-benchmark](https://github.com/omron-sinicx/srsd-benchmark) |
| PHYBench (карточка) | карточка | 2025 | 19 | 60 | нет репо | [2504.16074](https://arxiv.org/abs/2504.16074) | — |
| EXP-Bench (карточка) | карточка | 2025 | 18 | 48 | 373 | [2505.24785](https://arxiv.org/abs/2505.24785) | [Just-Curieous/Curie](https://github.com/Just-Curieous/Curie) |
| [HypoBench](hypobench/info.md) | полный | 2025 | 19 | 47 | 9 | [2504.11524](https://arxiv.org/abs/2504.11524) | [ChicagoHAI/HypoBench-code](https://github.com/ChicagoHAI/HypoBench-code) |
| [SDE (Scientific Discovery Evaluation)](sde-benchmark/info.md) | полный | 2025 | 11 | 46 | 65 | [2512.15567](https://arxiv.org/abs/2512.15567) | [HowieHwong/sde-harness](https://github.com/HowieHwong/sde-harness) |
| [NewtonBench](newtonbench/info.md) | полный | 2025 | 13 | 40 | 164 | [2510.07172](https://arxiv.org/abs/2510.07172) | [HKUST-KnowComp/NewtonBench](https://github.com/HKUST-KnowComp/NewtonBench) |
| MLRC-Bench (карточка) | карточка | 2025 | 19 | 34 | 12 | [2504.09702](https://arxiv.org/abs/2504.09702) | [yunx-z/MLRC-Bench](https://github.com/yunx-z/MLRC-Bench) |
| [BoxingGym](boxinggym/info.md) | полный | 2025 | 22 | 28 | 13 | [2501.01540](https://arxiv.org/abs/2501.01540) | [kanishkg/boxing-gym](https://github.com/kanishkg/boxing-gym) |
| [AI scientists produce results without reasoning scientifically (Corral)](ai-scientists-without-reasoning/info.md) | полный | 2026 | 7 | 24 | 21 | [2604.18805](https://arxiv.org/abs/2604.18805) | [lamalab-org/corral](https://github.com/lamalab-org/corral) |
| [PhysGym](physgym/info.md) | полный | 2025 | 16 | 21 | 103 | [2507.15550](https://arxiv.org/abs/2507.15550) | [principia-ai/PhysGym](https://github.com/principia-ai/PhysGym) |
| [CodeARC](codearc/info.md) | полный | 2025 | 20 | 21 | 28 | [2503.23145](https://arxiv.org/abs/2503.23145) | [Anjiang-Wei/CodeARC](https://github.com/Anjiang-Wei/CodeARC) |
| Collider-Bench (карточка) | карточка | 2026 | 6 | 20 | 10 | [2605.13950](https://arxiv.org/abs/2605.13950) | [dfaroughy/Collider-Bench](https://github.com/dfaroughy/Collider-Bench) |
| PaperArena (карточка) | карточка | 2025 | 13 | 19 | 18 | [2510.10909](https://arxiv.org/abs/2510.10909) | [ustc-ai4science/PaperArena](https://github.com/ustc-ai4science/PaperArena) |
| [FIRE-Bench](fire-bench/info.md) | полный | 2026 | 9 | 18 | 16 | [2602.02905](https://arxiv.org/abs/2602.02905) | [maitrix-org/FIRE-Bench](https://github.com/maitrix-org/FIRE-Bench) |
| [Gravity-Bench-v1](gravity-bench/info.md) | полный | 2025 | 22 | 18 | 6 | [2501.18411](https://arxiv.org/abs/2501.18411) | [NolanKoblischke/GravityBench](https://github.com/NolanKoblischke/GravityBench) |
| [Auto-Discovery-Bench (ранее Auto-Bench)](auto-discovery-bench/info.md) | полный | 2025 | 21 | 18 | нет репо | [2502.15224](https://arxiv.org/abs/2502.15224) | — |
| Causal narratives (карточка) | карточка | 2024 | 25 | 18 | нет репо | [2410.23884](https://arxiv.org/abs/2410.23884) | — |
| How Far Are AI Scientists from Changing the World? (обзор, не бенчмарк) (карточка) | карточка | 2025 | 16 | 17 | 317 | [2507.23276](https://arxiv.org/abs/2507.23276) | [ResearAI/Awesome-AI-Scientist](https://github.com/ResearAI/Awesome-AI-Scientist) |
| SciAgentGym / SciAgentBench (карточка) | карточка | 2026 | 9 | 17 | нет репо | [2602.12984](https://arxiv.org/abs/2602.12984) | — |
| LABBench2 (карточка) | карточка | 2026 | 7 | 15 | 67 | [2604.09554](https://arxiv.org/abs/2604.09554) | [EdisonScientific/labbench2](https://github.com/EdisonScientific/labbench2) |
| [DiscoverPhysics](discoverphysics/info.md) | полный | 2026 | 6 | 15 | 32 | [2605.26087](https://arxiv.org/abs/2605.26087) | [SampsonML/DiscoverPhysics](https://github.com/SampsonML/DiscoverPhysics) |
| [OneLife (One Life to Learn)](onelife/info.md) | полный | 2025 | 13 | 15 | 8 | [2510.12088](https://arxiv.org/abs/2510.12088) | [codezakh/onelife](https://github.com/codezakh/onelife) |
| HeurekaBench (карточка) | карточка | 2026 | 10 | 14 | 23 | [2601.01678](https://arxiv.org/abs/2601.01678) | [mlbio-epfl/HeurekaBench](https://github.com/mlbio-epfl/HeurekaBench) |
| AstroVisBench (карточка) | карточка | 2025 | 18 | 14 | 14 | [2505.20538](https://arxiv.org/abs/2505.20538) | [NSF-Simons-CosmicAI-Institute/AstroVisBench](https://github.com/NSF-Simons-CosmicAI-Institute/AstroVisBench) |
| [SLDBench / SLDAgent (Can Language Models Discover Scaling Laws?)](scaling-law-discovery/info.md) | полный | 2025 | 16 | 13 | 37 | [2507.21184](https://arxiv.org/abs/2507.21184) | [linhaowei1/SLD](https://github.com/linhaowei1/SLD) |
| BioDSA-1K (карточка) | карточка | 2025 | 18 | 12 | 106 | [2505.16100](https://arxiv.org/abs/2505.16100) | [RyanWangZf/BioDSA](https://github.com/RyanWangZf/BioDSA) |
| FEM-Bench (карточка) | карточка | 2025 | 11 | 12 | 10 | [2512.20732](https://arxiv.org/abs/2512.20732) | [elejeune11/FEM-bench](https://github.com/elejeune11/FEM-bench) |
| SUPERChem (карточка) | карточка | 2025 | 11 | 12 | нет репо | [2512.01274](https://arxiv.org/abs/2512.01274) | — |
| [AutumnBench (WorldTest)](autumnbench/info.md) | полный | 2025 | 13 | 11 | 2 | [2510.19788](https://arxiv.org/abs/2510.19788) | [BasisResearch/MARAProtocol](https://github.com/BasisResearch/MARAProtocol) |
| [CausaLab](causalab/info.md) | полный | 2026 | 6 | 10 | н/д | [2605.26029](https://arxiv.org/abs/2605.26029) | [DylanZSZ/CausaLab-Benchmark](https://github.com/DylanZSZ/CausaLab-Benchmark) |
| ASI-Bench (карточка) | карточка | 2026 | 3 | 9 | 303 | [2608.17271](https://arxiv.org/abs/2608.17271) | [apexin-ai/ASI-Bench](https://github.com/apexin-ai/ASI-Bench) |
| ReplicationBench (карточка) | карточка | 2025 | 13 | 9 | 11 | [2510.24591](https://arxiv.org/abs/2510.24591) | [Christine8888/replicationbench-release](https://github.com/Christine8888/replicationbench-release) |
| [Feature World + текстовый Alchemy (Can foundation models actively gather information… / Exploring exploration with foundation agents)](active-hypothesis-testing/info.md) | полный | 2024 | 23 | 9 | нет репо | [2412.06438](https://arxiv.org/abs/2412.06438) | — |
| Replica / Faraday (карточка) | карточка | 2026 | 3 | 9 | нет репо | [2608.13331](https://arxiv.org/abs/2608.13331) | — |
| Feature World + Alchemy (карточка) | карточка | 2024 | 23 | 9 | нет репо | [2412.06438](https://arxiv.org/abs/2412.06438) | — |
| [HypoSpace](hypospace/info.md) | полный | 2025 | 13 | 8 | 17 | [2510.15614](https://arxiv.org/abs/2510.15614) | [CTT-Pavilion/_HypoSpace](https://github.com/CTT-Pavilion/_HypoSpace) |
| gwBenchmarks (карточка) | карточка | 2026 | 6 | 8 | 3 | [2605.11269](https://arxiv.org/abs/2605.11269) | [tousifislam/gwBenchmarks](https://github.com/tousifislam/gwBenchmarks) |
| [ScienceIDE](scienceide/info.md) | полный | 2026 | 2 | 7 | 104 | [2609.19134](https://arxiv.org/abs/2609.19134) | [aitofound/ScienceIDE](https://github.com/aitofound/ScienceIDE) |
| DatasetResearch (карточка) | карточка | 2025 | 15 | 7 | 23 | [2508.06960](https://arxiv.org/abs/2508.06960) | [GAIR-NLP/DatasetResearch](https://github.com/GAIR-NLP/DatasetResearch) |
| BixBench3 (карточка) | карточка | 2026 | 3 | 7 | 15 | [2608.25286](https://arxiv.org/abs/2608.25286) | [EdisonScientific/BixBench3](https://github.com/EdisonScientific/BixBench3) |
| BenchEvolver / LiveCodeBench-Plus (карточка) | карточка | 2026 | 5 | 7 | 14 | [2606.01286](https://arxiv.org/abs/2606.01286) | [thu-wyz/BenchEvolver](https://github.com/thu-wyz/BenchEvolver) |
| PatchWorld (карточка) | карточка | 2026 | 6 | 7 | 10 | [2605.30880](https://arxiv.org/abs/2605.30880) | [HKBU-KnowComp/PatchWorld](https://github.com/HKBU-KnowComp/PatchWorld) |
| [Science-Gym](science-gym/info.md) | полный | 2026 | — | 7 | 3 | doi 10.1007/s10994-025-06914-x | [Pibborn/Science-gym](https://github.com/Pibborn/Science-gym) |
| MineExplorer (карточка) | карточка | 2026 | 6 | 6 | 30 | [2605.30931](https://arxiv.org/abs/2605.30931) | [meituan-longcat/MineExplorer](https://github.com/meituan-longcat/MineExplorer) |
| Абстрактное рассуждение через переназначение символов (Γ / Δ) (карточка) | карточка | 2025 | 18 | 6 | 8 | [2505.23833](https://arxiv.org/abs/2505.23833) | [MAC-AutoML/abstract-reason-benchmark](https://github.com/MAC-AutoML/abstract-reason-benchmark) |
| [Correct Answer, Wrong Mechanism (CAWM)](correct-answer-wrong-mechanism/info.md) | полный | 2026 | 5 | 6 | 2 | [2606.23175](https://arxiv.org/abs/2606.23175) | [seulig/g4_agent_icml_2026](https://github.com/seulig/g4_agent_icml_2026) |
| CFDLLMBench (CFD-LLMBench) (карточка) | карточка | 2025 | 14 | 5 | 50 | [2509.20374](https://arxiv.org/abs/2509.20374) | [NLR-Theseus/cfdllmbench](https://github.com/NLR-Theseus/cfdllmbench) |
| CoDA-Bench (карточка) | карточка | 2026 | 5 | 5 | 45 | [2606.15300](https://arxiv.org/abs/2606.15300) | [ruc-datalab/CoDA-Bench](https://github.com/ruc-datalab/CoDA-Bench) |
| ReX-MLE (карточка) | карточка | 2025 | 11 | 5 | 10 | [2512.17838](https://arxiv.org/abs/2512.17838) | [rajpurkarlab/ReX-MLE](https://github.com/rajpurkarlab/ReX-MLE) |
| EviGraph (карточка) | карточка | 2026 | 3 | 5 | нет репо | [2608.04738](https://arxiv.org/abs/2608.04738) | — |
| [DiG-bench](dig-bench/info.md) | полный | 2026 | 3 | 4 | 30 | [2608.12593](https://arxiv.org/abs/2608.12593) | [discos-research/dig-bench](https://github.com/discos-research/dig-bench) |
| [D3-Gym](d3-gym/info.md) | полный | 2026 | 7 | 4 | 13 | [2604.27977](https://arxiv.org/abs/2604.27977) | [OSU-NLP-Group/D3-Gym](https://github.com/OSU-NLP-Group/D3-Gym) |
| [Stargazer](stargazer/info.md) | полный | 2026 | 7 | 4 | 12 | [2604.15664](https://arxiv.org/abs/2604.15664) | [AIPS-UofT/Stargazer](https://github.com/AIPS-UofT/Stargazer) |
| [ClosureBench (и метод SCOPE)](closurebench/info.md) | полный | 2026 | 1 | 4 | нет репо | [2610.18938](https://arxiv.org/abs/2610.18938) | — |
| SciDisco / SciThèque (карточка) | карточка | 2026 | 4 | 4 | нет репо | [2607.28990](https://arxiv.org/abs/2607.28990) | — |
| [TruthInsightBench](truthinsightbench/info.md) | полный | 2026 | 2 | 3 | 3 | [2609.05079](https://arxiv.org/abs/2609.05079) | [TruthInsight-stack/TruthInsightBench](https://github.com/TruthInsight-stack/TruthInsightBench) |
| Solution Injection (карточка) | карточка | 2026 | 7 | 3 | нет репо | [2604.17609](https://arxiv.org/abs/2604.17609) | — |
| K-Bench 01 (карточка) | карточка | 2026 | 3 | 3 | нет репо | [2608.21601](https://arxiv.org/abs/2608.21601) | — |
| [EurekaBench](eurekabench/info.md) | полный | 2026 | 1 | 2 | 37 | [2610.00492](https://arxiv.org/abs/2610.00492) | [EurekaBench/EurekaBench](https://github.com/EurekaBench/EurekaBench) |
| [Autonomous Science Bench (AS-Bench)](autonomous-science-bench/info.md) | полный | 2026 | 1 | 2 | 11 | [2610.18449](https://arxiv.org/abs/2610.18449) | [Yibo-Wen/as-bench](https://github.com/Yibo-Wen/as-bench) |
| [SciLaws-Bench](scilaws-bench/info.md) | полный | 2026 | 2 | 2 | 10 | [2609.01552](https://arxiv.org/abs/2609.01552) | [yiyihum/SciLaws-Bench](https://github.com/yiyihum/SciLaws-Bench) |
| PACE-Bench (карточка) | карточка | 2026 | 3 | 2 | 8 | [2608.14441](https://arxiv.org/abs/2608.14441) | [thunlp/PACE-Bench](https://github.com/thunlp/PACE-Bench) |
| [SurfaceBench](surfacebench/info.md) | полный | 2025 | 12 | 2 | 6 | [2511.10833](https://arxiv.org/abs/2511.10833) | [deep-symbolic-mathematics/surfacebench](https://github.com/deep-symbolic-mathematics/surfacebench) |
| VisualPatchWorld (карточка) | карточка | 2026 | 4 | 2 | 4 | [2607.25236](https://arxiv.org/abs/2607.25236) | [HKBU-KnowComp/VisualPatchWorld](https://github.com/HKBU-KnowComp/VisualPatchWorld) |
| [LatentGym](latentgym/info.md) | полный | 2026 | 5 | 2 | 2 | [2606.15306](https://arxiv.org/abs/2606.15306) | [namkoong-lab/LatentGym](https://github.com/namkoong-lab/LatentGym) |
| [HypoArena (HypoData + HypoEval)](hypoarena/info.md) | полный | 2026 | 4 | 2 | 1 | [2607.15766](https://arxiv.org/abs/2607.15766) | [SKYLENAGE-AI/HypoArena](https://github.com/SKYLENAGE-AI/HypoArena) |
| DataGovBench (карточка) | карточка | 2026 | 4 | 2 | 0 | [2607.06482](https://arxiv.org/abs/2607.06482) | [SoHasegawa/datagovbench](https://github.com/SoHasegawa/datagovbench) |
| [Evidence-grounded accuracy (EGA)](evidence-grounded-accuracy/info.md) | полный | 2026 | 1 | 2 | нет репо | [2610.04915](https://arxiv.org/abs/2610.04915) | — |
| [Sheaf-Theoretic Transport and Obstruction (transition cards)](sheaf-theory-shift/info.md) | полный | 2026 | 6 | 2 | нет репо | [2605.14033](https://arxiv.org/abs/2605.14033) | — |
| CascadeBench (карточка) | карточка | 2026 | 6 | 2 | нет репо | [2605.12178](https://arxiv.org/abs/2605.12178) | — |
| UTQA (карточка) | карточка | 2025 | 15 | 2 | нет репо | [2508.21452](https://arxiv.org/abs/2508.21452) | — |
| SciTableQA (карточка) | карточка | 2025 | — | 2 | нет репо | doi 10.1007/978-3-032-05409-8_7 | — |
| ChemWorld (карточка) | карточка | 2026 | 3 | 1 | 50 | [2608.10792](https://arxiv.org/abs/2608.10792) | [sunyrain/ChemWorld-Public](https://github.com/sunyrain/ChemWorld-Public) |
| [ExplorationBench](explorationbench/info.md) | полный | 2026 | 2 | 1 | 28 | [2609.30199](https://arxiv.org/abs/2609.30199) | [Tencent-Hunyuan/ExplorationBench](https://github.com/Tencent-Hunyuan/ExplorationBench) |
| EmbodiedLab (карточка) | карточка | 2026 | 1 | 1 | 20 | [2610.35385](https://arxiv.org/abs/2610.35385) | [HexaFuture/EmbodiedLab](https://github.com/HexaFuture/EmbodiedLab) |
| CompMat-Bench (карточка) | карточка | 2026 | 1 | 1 | 10 | [2610.00636](https://arxiv.org/abs/2610.00636) | [cz2014/CompMat-Bench](https://github.com/cz2014/CompMat-Bench) |
| [LUCA (+ «Treating the Symptom, Missing the Cause»)](luca/info.md) | полный | 2026 | 0 | 1 | 5 | [2611.03100](https://arxiv.org/abs/2611.03100) | [RelationRx/luca](https://github.com/RelationRx/luca) |
| [Open-Endedness Bench (OEB)](open-endedness-bench/info.md) | полный | 2026 | 1 | 1 | 3 | [2610.02588](https://arxiv.org/abs/2610.02588) | [ARA-Labs/oeb](https://github.com/ARA-Labs/oeb) |
| [WhatWorkedBench](whatworkedbench/info.md) | полный | 2026 | 2 | 1 | 3 | [2609.27490](https://arxiv.org/abs/2609.27490) | [EthanNing/WhatWorkedBench](https://github.com/EthanNing/WhatWorkedBench) |
| [InfiniteScienceGym](infinitesciencegym/info.md) | полный | 2026 | 7 | 1 | 2 | [2604.13201](https://arxiv.org/abs/2604.13201) | [utahnlp/infinite-science-gym](https://github.com/utahnlp/infinite-science-gym) |
| [MechBench](mechbench/info.md) | полный | 2026 | 2 | 1 | 2 | [2609.35515](https://arxiv.org/abs/2609.35515) | [tsinghua-fib-lab/MechBench](https://github.com/tsinghua-fib-lab/MechBench) |
| DataSense-Bench (карточка) | карточка | 2026 | 1 | 1 | 0 | [2610.12190](https://arxiv.org/abs/2610.12190) | [DataSense-Bench/DataSense-Bench](https://github.com/DataSense-Bench/DataSense-Bench) |
| DPDisc / DPForge (карточка) | карточка | 2025 | 13 | 1 | 0 | [2510.21737](https://arxiv.org/abs/2510.21737) | [ibm/data-product-benchmark](https://github.com/ibm/data-product-benchmark) |
| [SDABench («Are LLMs Ready for Scientific Discovery?»)](capability-benchmark-ai-scientists/info.md) | полный | 2026 | 4 | 1 | нет репо | [2607.11079](https://arxiv.org/abs/2607.11079) | — |
| MUSES (карточка) | карточка | 2026 | 2 | 1 | нет репо | [2609.00313](https://arxiv.org/abs/2609.00313) | — |
| SciCodePile (карточка) | карточка | 2026 | 4 | 1 | нет репо | [2607.19104](https://arxiv.org/abs/2607.19104) | — |
| SABench-agent (Gen2Bench) (карточка) | карточка | 2026 | — | 1 | н/д | doi 10.64898/2026.07.05.736638 | [yiqunchen/Gen2Bench](https://github.com/yiqunchen/Gen2Bench) |
| Matter to Mechanism (карточка) | карточка | 2026 | 5 | 1 | нет репо | [2606.02258](https://arxiv.org/abs/2606.02258) | — |
| PaperBenchX (карточка) | карточка | 2026 | 1 | 0 | 46 | [2610.39744](https://arxiv.org/abs/2610.39744) | [UniPat-AI/PaperBenchX](https://github.com/UniPat-AI/PaperBenchX) |
| [LongChang](longchang/info.md) | полный | 2026 | 1 | 0 | 13 | [2610.37649](https://arxiv.org/abs/2610.37649) | [EnVision-Research/LongChang](https://github.com/EnVision-Research/LongChang) |
| EarthVerse (карточка) | карточка | 2026 | 3 | 0 | 13 | [2608.23525](https://arxiv.org/abs/2608.23525) | [CuiZHIQ/Earth-Verse](https://github.com/CuiZHIQ/Earth-Verse) |
| [SciR](scir/info.md) | полный | 2026 | 5 | 0 | 10 | [2606.13020](https://arxiv.org/abs/2606.13020) | [idiap/scir](https://github.com/idiap/scir) |
| [AdaExploreBench](adaexplorebench/info.md) | полный | 2026 | 1 | 0 | 6 | [2610.25950](https://arxiv.org/abs/2610.25950) | [HKUST-KnowComp/AdaExploreBench](https://github.com/HKUST-KnowComp/AdaExploreBench) |
| [SciExam for ENSO](sciexam-enso/info.md) | полный | 2026 | 1 | 0 | 4 | [2610.10513](https://arxiv.org/abs/2610.10513) | [ylzhang2447/SciExam-ENSO-code](https://github.com/ylzhang2447/SciExam-ENSO-code) |
| [Parallel Physical Worlds (PhysLit)](parallel-physical-worlds/info.md) | полный | 2026 | 4 | 0 | 2 | [2607.00276](https://arxiv.org/abs/2607.00276) | [dongzhang84/physlit](https://github.com/dongzhang84/physlit) |
| [SciGame](scigame/info.md) | полный | 2026 | 1 | 0 | 2 | [2610.37919](https://arxiv.org/abs/2610.37919) | [yushengzh/scigame](https://github.com/yushengzh/scigame) |
| [Witness (WitnessBench / WitnessGym)](witness/info.md) | полный | 2026 | 2 | 0 | 2 | [2609.32208](https://arxiv.org/abs/2609.32208) | [fleet-ai/witnessbench](https://github.com/fleet-ai/witnessbench) |
| SCI-AGENT-EXAM (карточка) | карточка | 2026 | 1 | 0 | 2 | [2610.32441](https://arxiv.org/abs/2610.32441) | [SKYLENAGE-AI/Sci-Agent-Exam](https://github.com/SKYLENAGE-AI/Sci-Agent-Exam) |
| [ACED-Bench](aced-bench/info.md) | полный | 2026 | 1 | 0 | 0 | [2610.14381](https://arxiv.org/abs/2610.14381) | [Rose-STL-Lab/ACED-Bench](https://github.com/Rose-STL-Lab/ACED-Bench) |
| [Alien Abduction (active-abduction-probe)](active-abduction-probe/info.md) | полный | 2026 | 3 | 0 | 0 | [2608.03388](https://arxiv.org/abs/2608.03388) | [mohiuddinshahrukh/Alien-Abduction](https://github.com/mohiuddinshahrukh/Alien-Abduction) |
| ChemArgus (карточка) | карточка | 2026 | 1 | 0 | 0 | [2610.20012](https://arxiv.org/abs/2610.20012) | [YunQi572/ChemArgus](https://github.com/YunQi572/ChemArgus) |
| Paper2Bench (spatial alignment) (карточка) | карточка | 2026 | 0 | 0 | 0 | [2611.11796](https://arxiv.org/abs/2611.11796) | [Y-Chen-LAB/spatial-alignment-agent](https://github.com/Y-Chen-LAB/spatial-alignment-agent) |
| F1 / MTG (карточка) | карточка | 2026 | 3 | 0 | 0 | [2608.03569](https://arxiv.org/abs/2608.03569) | [WilliamBolton/f1-ai-scientist-paper](https://github.com/WilliamBolton/f1-ai-scientist-paper) |
| [BioStudyBench](biostudybench/info.md) | полный | 2026 | 1 | 0 | нет репо | [2610.07614](https://arxiv.org/abs/2610.07614) | — |
| [CME-SpectrumBench](cme-spectrumbench/info.md) | полный | 2026 | 1 | 0 | нет репо | [2610.24304](https://arxiv.org/abs/2610.24304) | — |
| [ERBench](erbench/info.md) | полный | 2026 | 5 | 0 | нет репо | [2606.09276](https://arxiv.org/abs/2606.09276) | — |
| [MechHypoBench (From Scientific Observations to Mechanisms)](obs-to-mechanisms/info.md) | полный | 2026 | 1 | 0 | нет репо | [2610.05197](https://arxiv.org/abs/2610.05197) | — |
| [Learning to Outgrow a Theory (Joint Edit–Experiment)](outgrow-a-theory/info.md) | полный | 2026 | 1 | 0 | нет репо | [2610.07627](https://arxiv.org/abs/2610.07627) | — |
| [Synthetic Universes](synthetic-universes/info.md) | полный | 2026 | 2 | 0 | нет репо | [2609.36726](https://arxiv.org/abs/2609.36726) | — |
| [UltraDiscovery](ultradiscovery/info.md) | полный | 2026 | 1 | 0 | нет репо | [2610.03092](https://arxiv.org/abs/2610.03092) | — |
| [Unsatz](unsatz/info.md) | полный | 2026 | 0 | 0 | нет репо | [2611.03713](https://arxiv.org/abs/2611.03713) | — |
| ArtifactArena (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.06511](https://arxiv.org/abs/2610.06511) | — |
| LEGION (карточка) | карточка | 2026 | 0 | 0 | н/д | [2611.11896](https://arxiv.org/abs/2611.11896) | [legion-security/legion-bench](https://github.com/legion-security/legion-bench) |
| Selecting LLM-Generated Hypotheses… (карточка) | карточка | 2026 | 0 | 0 | нет репо | [2611.00643](https://arxiv.org/abs/2611.00643) | — |
| CrashGym (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.29245](https://arxiv.org/abs/2610.29245) | — |
| EvoBelief (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.12789](https://arxiv.org/abs/2610.12789) | — |
| EnterpriseWorldShift (карточка) | карточка | 2026 | 2 | 0 | нет репо | [2609.19551](https://arxiv.org/abs/2609.19551) | — |
| CASSANDRA (карточка) | карточка | 2026 | 10 | 0 | нет репо | [2601.18620](https://arxiv.org/abs/2601.18620) | — |
| PersonaScienceBench (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.32106](https://arxiv.org/abs/2610.32106) | — |
| POSEIDON / PEARL (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.32448](https://arxiv.org/abs/2610.32448) | — |
| ST-Bench (карточка) | карточка | 2026 | 1 | 0 | нет репо | [2610.07763](https://arxiv.org/abs/2610.07763) | — |
| ClinLens (карточка) | карточка | 2026 | 4 | 0 | нет репо | [2607.26155](https://arxiv.org/abs/2607.26155) | — |
| NanoGPT-speedrun env (карточка) | карточка | 2025 | 11 | 0 | нет репо | [2512.11183](https://arxiv.org/abs/2512.11183) | — |
| Model-aware benchmark generation (MDPI MAKE) (карточка) | карточка | 2025 | — | 0 | нет репо | doi 10.3390/make7040148 | — |
| CausalVerify (карточка) | карточка | 2026 | 2 | 0 | нет репо | [2609.07944](https://arxiv.org/abs/2609.07944) | — |
