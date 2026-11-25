# Scientific Discovery Benchmarks for LLM Agents: Speaker Notes

Notes follow the current deck (`slides_en.md`, 10 pages): the title, two unnumbered picture slides, then slides 1–7 as numbered on the slides.

## Title

This is a five-minute talk at the workshop "Do Androids Dream of Electric Papers?" in Manchester on 25 November. Today I will talk about benchmarks that test whether language models, and agents built on them, can make scientific discoveries. I am not asking how well a model solves physics, biology or chemistry problems. My question is narrower: can existing benchmarks tell us whether an agent actually chooses an explanatory hypothesis, or whether it just fits a curve to the data or recalls the answer from a textbook?

The numbers in this talk come from a survey of the literature: 439 papers in our list of benchmarks, 296 of them classified with one schema, and 103 of those are discovery benchmarks in our sense; 81 papers we read in full. The workshop programme still says 64 benchmarks, which was the number of full reads when the survey started. I will go through the field as a whole: how it developed, what the tasks require of an agent, how they are scored, where agents fail, where benchmarks themselves are flawed, and what follows for a good benchmark.

## The classical scientific loop

Before talking about agents, let me recall how science itself works. It is a loop of four stages.

Context: what do we already know — the literature, the data, earlier results. Hypothesis: what could explain it — candidate laws, mechanisms, entities that nobody has observed. Experiment: how do we test it — a simulation, a measurement, a lab run. Evidence: what did we learn — fits, residuals, a ranking of the explanations. And then the evidence becomes the new context, and the loop repeats.

The examples on the cards are only illustrations. The picture is the same for any field; what changes is what stands behind each stage.

## An agent inside the loop

Now we put an LLM agent into the same loop. It is the same four stages, and under each one there is now a concrete job for the agent.

At the Context stage it reads the task, the data and its own memory. At the Hypothesis stage the LLM proposes explanations. At the Experiment stage it calls tools and acts in the environment. At the Evidence stage it analyses the results and updates its memory. In the centre is the agent itself: an LLM plus memory plus tools.

The point of the picture: a benchmark can sit on any part of this loop. Some give the agent a table and look only at the hypothesis. Others give it an environment and watch the whole loop. What exactly a benchmark sees determines what it can measure, and that is the thread of the rest of the talk.

## Slide 1. What we mean by epistemic abilities

First, let us agree on what exactly we want to measure. Scientific discovery is not a single correct answer but a chain of steps.

First, you have to notice an anomaly: a known theory, let us call it T0, stops explaining the data. Then you propose alternatives, and these include not only "the law is slightly different" but also "there is something we cannot see". The classic example is Neptune, found from perturbations in the orbit of Uranus. Next, you plan an experiment on which the hypotheses make different predictions, make a prediction before measuring, and honestly record it. After the measurement, you update your confidence in the hypotheses exactly as much as the evidence warrants. From the chosen mechanism you derive a new prediction that cannot be obtained by extending a fitted curve. You need to understand where the law you found stops working. And all of this has to be done from data, not from memory.

An important point: a correct final answer says almost nothing about which of these steps the agent actually took. From here on I will look at benchmarks through exactly this lens: which steps they can see and which they cannot.

Two things about the survey itself. We studied 103 discovery benchmarks, and they cover many domains: physics 31, biology 28, medicine and materials 12 each, chemistry 11, and so on; one benchmark can belong to several domains. And it does not cover everything: 42 of the 103 use purely synthetic data, only 19 real data, and the cost of an experiment enters the budget in only 7. So the survey says little about slow, expensive or noisy experiments, and about tasks with sparse ground truth. That is exactly where Track B starts.

## Slide 2. How the field developed: five stages

The picture has two parts. The five cards show the stages; the timeline below places them in time; and the bars at the bottom show how many discovery-benchmark papers appeared each year. There are 103 in total, out of the 296 papers we classified, and the last bar, 2026, is a year to date, counted to 23 November and not a forecast, and is the largest by far: 68 papers, against 20 in 2025 and 8 in 2024. The time axis is piecewise: the long past is compressed and 2021–2026 is stretched.

The first stage is the law from a table. This is classical symbolic regression, represented here by AI Feynman and SRBench. You get a table of clean data, you have to find a known formula, and scoring is exact symbolic match. Memorization in today's sense did not exist then, because the solvers were not language models. But there was an analogue: a human chose the variables and the representation of the problem, so the hardest part of the work was done by the person, not the program.

The second stage is the realization of contamination. When LLMs took on these tasks, it turned out that models simply recall well-known formulas. SRSD, LLM-SR and LLM-SRBench introduced renamed and synthetic tasks and a no-data probe. The main lesson of this stage: a good numerical fit does not mean the formula has been found.

The third stage is active experimentation. DiscoveryWorld, PhysGym, NewtonBench and Gravity-Bench move the task into an interactive environment where the agent chooses the measurements. Protection against memorization turns from a filter into a controllable axis: you can hide the text, or you can change the physics itself.

The fourth and fifth stages both fall in 2026, and they differ not by date but by what is treated as unknown.

At the fourth stage, the language of the task is correct: the variables and the model class are given correctly. The question is whether the agent found the right internal structure or only a formula that predicts well. Several groups independently showed that these are different things and must be scored separately: DiscoverPhysics, MechBench, EurekaBench, SciLaws-Bench. An analogy: Kepler and Newton describe the same orbits, but only Newton says why they are the way they are. In Synthetic Universes, in the world with drag, the prediction is correct in five runs out of five, but the mechanism in only one.

At the fifth stage, the language itself is wrong. The agent is given a theory T0 that works at first and then breaks. It has to realize that adjusting parameters will not help and that a new quantity or entity, or a different model class, is needed. This is ULTRADISCOVERY, Unsatz, SciGame, Stargazer. One result keeps repeating here: models are willing to abandon an old axiom, but they do not introduce an unobservable entity. This result was first obtained in DiscoverPhysics, in May, so by the calendar it still belongs to the fourth stage.

The overall trend: from static tables to environments, from public reference answers to task generation from a private seed, and from a single score to separate scoring of the prediction, the mechanism and the process.

If asked: what was before language models. Hypothesis generation did not appear together with LLMs. The programs of Simon and Langley, BACON, STAHL and DALTON, derived laws from tables; BACON already had "intrinsic properties", that is, quantities that are not in the data, and DALTON formed hypotheses about unobservable composition. KEKADA modeled how Krebs found the urea cycle, planning experiments and reacting to surprises. DENDRAL and MECHEM inferred structures and reaction mechanisms with unobserved intermediates. FCI in causal discovery explicitly allows hidden common causes, and Robot Scientist Adam ran a closed loop in a real laboratory. There are two differences from today: those systems postulated hidden things only within a vocabulary a human gave them, and there were no benchmarks in the current sense, the test was rediscovering historical cases.

## Slide 3. What is required, how it is scored, and how memorization is excluded

The slide has two tables, and they answer two different questions. The first: what exactly must the answer explain, how is it scored, and where does the scoring go wrong. The second: how do we make sure the agent infers rather than remembers.

First table, with orbits as the example. The important point: depth is defined by what the check verifies, not by the form of the answer. Fit: the check looks at the parameter values for a given form, for example k in T² = k·a³. Law: the check looks at the prediction of observables outside the training range, that is, the form of the relation itself, Kepler's third law. Mechanism: the check looks at hidden quantities and at the response to an intervention, here a force falling off as the inverse square of distance, acting on a hidden quantity, the mass of the Sun, together with F = ma. Kepler's law is then a consequence: the centripetal acceleration of the orbit is not an extra ingredient, it follows from the force. A mechanism answers questions that a law cannot: from Newton you can obtain the mass of the Sun and predict what happens if it changes, but from Kepler you cannot. Structural: the check looks at the choice between rival structures, whether we need a new planet or a new law.

The same formula can have different explanations. In MechBench, logistic growth of a population arises equally if density lowers the birth rate or if it raises the death rate. One formula, different mechanisms, and only an intervention can tell them apart.

The right half of the same table says what is scored at each depth and where this goes wrong.

Fit: the score is a point estimate of the parameters. The pitfall: it cannot tell the right form from a wrong form that fits well. This is essentially the fit task, and it gives very little about discovery.

Law: the score is on the trajectory, plus the form of the law where it is checked. This is better, but the form of a law can be good for interpolation and bad for extrapolation. It can also be hard to interpret, for example with too many parameters. And wherever code cannot check that two expressions are equivalent, the form of the law needs a judge, and the judge needs to be validated: one more hyperparameter.

Mechanism: the trajectory, the symbolic form and, on top of that, the explanation of the mechanism. The same pitfalls apply, and the mechanism often needs a judge too, which must be calibrated against humans. There are good counterexamples: MechHypoBench and BLADE use the judge only as a parser, and the score is computed by code.

Structural: the full explanation, that is, the choice and its grounding in the evidence. This is the best level, but the pitfall is that the explanation does not always agree with the fit and with the mechanism. A good answer on one axis can come with a poor one on another. Almost no benchmark scores this level at all: among the 103 discovery papers only 4 require a structural answer, against 19 for fit, 40 for law and 40 for mechanism, and ULTRADISCOVERY comes closest, with a judge it validated against humans.

Why numbers alone are not enough, several papers show. SciLaws-Bench compared thousands of pairs of answers: the one that fits the data better turns out to be more scientifically valid in only about half the pairs. In Unsatz, the agent sees only the error on its own data and optimizes exactly that; the error on the hidden check can grow by orders of magnitude outside the explored range. In EurekaBench, agents have almost caught up with humans on prediction accuracy but lag far behind on the scientific insights that follow from the mechanism. The same is visible without language models: in LLM-SRBench, the classical tool PySR often fits the data well but rarely finds the correct formula.

About judges. The LLM judge contributes to the final score in a good share of papers, but only a minority validate it against humans with concrete numbers. The judge often belongs to the same model family as the models being tested. And reliability does not transfer between tasks: in Parallel Physical Worlds, two judges disagreed in a large share of cases, and each round needed a human audit.

The practical rule: compute numbers with code, call a judge only where you cannot do without one, and always validate it against humans.

Second table, the memory ladder. It is four versions of the same task. Rung a is historical: real names and laws, Earth and Moon, F proportional to 1/r². Memory helps. Rung b is obfuscated: the same law, but names and units are hidden. Memory helps only if the model recognizes the law. Rung c is counterfactual: a recognizable textbook law is deliberately changed, here gravity with F proportional to r to the power minus 2.6. Here memory hurts: it pulls toward the textbook answer, and the rung tests whether the agent trusts the data over the textbook. Rung d is synthetic: an invented force from an invented "charge", no real prototype. Memory is neutral, so what is tested is pure induction. But legitimate domain knowledge disappears too.

So the ladder is not monotonic in the amount of memory, and each difference measures something different. The difference between a and b is recognition from text. Between b and c, how much of the answer comes from memory rather than from data. Comparing c and d shows the cost of the textbook's pull.

For examples of how large the effect is, if asked: in PhysGym, removing the text description of the task roughly halves success for one of the strongest models, and in NewtonBench the no-data probe on counterfactual laws scores zero. Across the 180 papers in our catalog that have their own task set, the main rung is historical in 122, synthetic in 46, counterfactual in 7 and obfuscated in 5. No paper runs the same task through all four rungs, and only one goes beyond two rungs on one task, so the contribution of memory cannot be measured directly anywhere. Hiding the text alone is not enough either: in PhysGym, models recognize the speed of light or the gravitational acceleration directly from the numbers.

## Slide 4. Saturation: a high score on the familiar version hides a drop

The slide shows what happens to a score when the memory support is removed. Each row is one benchmark and one model, with a single change: the dot on the right is the version where memory helps, the dot on the left is the version without that help.

In Synthetic Universes an agent gets 100 percent on a famous law and 40 on its synthetic twin. In EGA, a model scores 97 with gene names and 37 with anonymised genes. In BioStudyBench the best model gets 95 percent with data and still 51 without it, so about half of the studies are solved from knowledge alone. In SciGame the original laws are identified at 92 percent and the counterfactual ones at 48. In PhysGym, with the priors open a model scores 74, and with them hidden 32. In SciR, on induction, natural language gives 90 and the obfuscated version 67.

The bottom row keeps this honest: in the causal track of SciR, obfuscation changes almost nothing, so the drop is not universal. The point of the slide is saturation: a benchmark whose familiar version is near the ceiling can still be far from solved once the version that memory cannot help is taken. Only 4 of the 62 benchmarks with a common scale are saturated in every slice, and in 28 more at least one slice, usually the easy one, is above 85 percent for the best model.

Caveats for questions. The rows are examples chosen to cover obfuscation, hidden priors, counterfactual laws and no data, not every pair in the corpus. The scores are not comparable across rows, since the metrics differ. The models in the rows are: one Claude Code agent (Synthetic Universes), Sonnet 5 (EGA), GPT-6 Astra (BioStudyBench), DeepSeek-V4 Flash (SciGame), Gemini 2.5 Pro (PhysGym), o3-mini (SciR); the PhysGym models are from 2025, and a 2026 model gets 48 on the hidden level. CodeARC also drops, from 60 to 53 with anonymized code. The saturation categories are our own, computed from the best model in each slice of our table of 503 slices.

## Slide 5. Typical agent failure modes

Now what agents actually do. The table is ordered from simple to hard, and all these failures are compatible with a high score on the final answer. I will go through the rows.

They guess from general regularities. In BioStudyBench, for studies published after the model's training cutoff, one model, seeing only the question, guesses the direction and significance of the effect for most of the non-null findings; for null findings it is far worse. This is not recall but inference from general regularities, so a cutoff-date defense protects against lookup but not against this kind of guessing.

They fit rather than find the law. The answer matches the data the agent saw but has the wrong form, and so it breaks on data the agent did not see. In Synthetic Universes, the agent described a pendulum as a linear oscillator with a tiny error on its data, and this answer was rejected over a wider range of angles. In the world with drag, the agent itself estimated the exponent as about 1.54 but submitted a linear law. Something similar shows up in program synthesis: in CodeARC, o3-mini's first function passes the visible examples in about two thirds of tasks and the hidden tests in under 40 percent.

They collect the evidence but do not use it. In LUCA, the discriminating observation appears in more than 90 percent of sessions, but the correct diagnosis comes in about 30. In Solution Injection, models notice the hint in 79 to 97 percent of cases but use it in 0.5 to 50.

They miss the anomaly. In LongChang, the discovery rate is zero for 11 of 12 models. In Gravity-Bench, in our recount of the logs, o4-mini never acknowledged in 18 runs that Kepler's law was violated, even though it did find the modification parameter itself. That second number is our own count for one model, not a figure from the paper.

They notice the deviation but do not postulate an entity. In DiscoverPhysics, no run of the best models proposed hidden sources. In ULTRADISCOVERY, the old axiom is rejected in almost half of the open episodes, but no episode postulates a hidden entity. The difference from the previous row: there the agent does not see that something is wrong; here it sees it, drops the old law, and still does not add a new entity.

They take the right actions but do not draw the conclusion. In DiscoveryWorld, for GPT-4o the process score is 0.49 to 0.64, while task completion is 0.08 to 0.38 and the knowledge score is 0.01 to 0.34. The agent performs many of the right steps but does not turn them into a solved task or a correct statement about the world.

## Slide 6. Typical defects of the benchmarks themselves

Now about defects in the benchmarks themselves. We found many of them by reading the code, not only the papers.

Correctness feedback before submission. If the agent learns at every step whether it is right, the task turns into search against an oracle. Stargazer, Witness, CodeARC and PhysGym work this way: the correctness signal is available right inside the episode.

Reference leaks. In NewtonBench, the law can apparently be imported from inside the sandbox. In Gravity-Bench, the answer sometimes appears right in the data file name.

Hints about the form. Gravity-Bench states in the prompt that the force is proportional to r to the power of minus two plus alpha. After that, the counterfactual task reduces to fitting a single parameter.

A correct answer that cannot be scored as correct. In Stargazer, the answer "there are no extra planets" cannot get credit, by the way the metric is built.

Metrics that mislead. LLM-SRBench drops NaNs when computing NMSE, so failed fits disappear from the average. ULTRADISCOVERY uses a binary outcome on which every model scores zero, so it separates nobody.

And reproducibility: in 11 of the 81 benchmark papers we reviewed in full, the code and data are not published, some only promise to release them, and several, SciGame, SLDBench, BoxingGym, ERBench and HypoArena, have numbers that contradict each other within the text.

## Slide 7. What a good discovery benchmark needs

All of this gives a list of requirements for a benchmark that genuinely measures epistemic abilities. Each of them answers something we have seen in the failure modes or the defects.

First: a no-data probe on every task, with the same tools, and "undetermined" must be an allowed answer. Second: paired tasks, where the same anomaly requires a new entity in one case and not in the other. Without such pairs you cannot distinguish abduction from a habit of complicating the model: an agent that always adds a hidden body scores highly on a benchmark where a hidden body is always there. Third: the same task on all four rungs a to d, so that the drop between them shows the contribution of memory.

Fourth: precommitment. The hypothesis and the forecast are recorded in machine-readable form before each measurement. Then you can assess whether the agent chooses discriminating measurements and whether its updates are consistent with the evidence. Fifth: no correctness feedback before submission, and the reference is kept outside the agent's sandbox.

Sixth: the law is tested on conditions the agent has not seen, that is, outside the data range and under interventions, and the form of the law is checked separately. Seventh: the explanation is scored on two axes: whether it rests on the agent's log with quotes, and whether it matches the reference. Eighth: baselines, namely constant answers, the no-data answer, a non-LLM solver and an oracle. Ninth: judges from a different model family, with kappa compared against human–human agreement.

The main thesis: an agent's epistemics should be measured by process, by paired cases and with memory decomposed, not by the final answer.


## Thank you

Thank you for your attention. The link to the Atlas is on the slide and in the corner of every slide; I am happy to take questions, and the backup slide with the references is next.

## Appendix. References

A backup slide for questions: the full reference for every benchmark named on the slides, with its arXiv number. Two caveats to keep in mind when citing: the 0/18 for Gravity-Bench is our recount of the o4-mini runs, it is not in the paper and must not be cited as a published result, and the benchmark defects on slide 6 are the result of our reading of the papers and code, not quotations from the papers.
