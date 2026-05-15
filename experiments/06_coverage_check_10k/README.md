# Exp 06 — Coverage check: 10k agents

**Question.** Is the syphilis extinction in exps 02–05 a stochastic
artifact of 5k agents, or a structural model issue? At 2% prevalence
in 5k agents, the high-risk transmission core is ~5–10 people.

**Plan.** Identical to exp 05 (same priors, same network), but with
n_agents=10000. 100 draws.

**Success criteria.** If stochastic extinction is the cause, substantially
more draws (>30/100) should sustain syphilis at 10k. If the results are
similar to exp 05, the problem is structural.
