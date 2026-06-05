# Exp 15 — Background syphilis case imports: coverage sweep

**Question.** Does adding a small background syphilis case importation
rate (a steady trickle of new infections independent of the sexual
network, standing in for cross-border movement, missed contacts, and
other unmodelled sources) collapse the two-attractor bifurcation we
saw in exp 13 into a single mode that brackets the observed data near
1% — *at a rate small enough to be epidemiologically defensible*?
The hard constraint is that imports must account for << 5% (ideally
~1%) of newly acquired syphilis cases. If the only rate that
eliminates the bifurcation makes imports the dominant transmission
mechanism, we have not fixed the model — we have replaced its
transmission dynamics with a thinly disguised incidence model, and
the experiment has failed.

**Motivation.** Exp 13 showed the model has two stable transmission
regimes around the calibration target — extinct (~half the NROY draws)
and over-sustained at 5–25% (the other half) — with the data in a
structural gap between them. Exp 14 demonstrated no likelihood retune
can rescue a posterior from this. The lightest-touch structural fix
flagged in [`../10_trajectory_selection/SUMMARY.md`](../10_trajectory_selection/SUMMARY.md) is
a small background importation rate: a steady trickle of new
infections each timestep, independent of network state, representing
the real-world reality that no closed population is fully
self-contained (cross-border movement, contacts outside the modelled
sexual network, partners not captured by the network structure).
Mechanistically this should:

- **Eliminate the extinct branch.** Once the rate is non-zero, the
  disease cannot go to absorbing zero — any draw whose endogenous
  transmission would otherwise die out is reseeded.
- **Attenuate the hot branch.** During the early-epidemic burn-through
  in 1985–1990, the network's susceptible pool is rapidly consumed.
  With a small steady import rate, the dynamics shift from "infect
  everyone available then collapse" toward an equilibrium where
  endogenous transmission balances natural recovery — which is what
  an endemic disease actually does.

Whether *both* effects are achievable simultaneously at a single rate is
the empirical question. It's possible the rate that prevents extinction
keeps the hot branch hot.

**Mechanism (implementation choice).** Add a custom `ss.Intervention`
class — `SyphilisImports` — that on each timestep draws a small Poisson
number of new infections and applies them to randomly-selected
susceptible adults (age ≥ 15). Single tunable parameter: `mean_imports_per_month`
(mean of the Poisson). The intervention sits alongside `make_syph_testing`
in the interventions list; no edits to `Syphilis` itself. This keeps the
fix reversible and easy to ablate.

This is *not* a re-seeding analyzer (which would re-introduce syphilis
only when extinct) — it operates continuously, so the import rate also
shapes the hot-branch equilibrium, not just the extinction threshold.

**Plan.** A coverage-check sweep, not a calibration run.

1. Implement `SyphilisImports(mean_imports_per_month)` as a top-level
   intervention class in this experiment folder (not in `interventions.py`
   yet — keep it local until we know what rate to bake in). The
   intervention tracks the number of infections it generates each
   timestep separately from the natural-FOI infections, so we can
   report imports as a fraction of total new acquisitions per draw.
2. Sweep six rates: `[0, 0.1, 0.5, 1, 2, 5]` mean imports per month
   per 10k agents. Rationale: rough endemic-equilibrium new-case flow
   is ~8/month per 10k (1% prevalence × ~1-yr infectious duration ×
   10k agents / 12 mo), so `0.1` is ~1% of natural flow,  `0.5` is
   ~6%, and `5` is ~62%. The lower end probes the policy-defensible
   region; the upper end characterises whether the bifurcation is
   even fixable by this mechanism alone. `0` reproduces exp 13.
3. For each rate, run 50 draws from the wave-8 NROY at 10k agents,
   1985–2025. Total 300 sims. With 24 workers at exp 13's ~28 s/sim,
   that's ~6 min compute.
4. Extract `syph_prev_f` time-series + the same 12 calibration target
   summaries as exp 13, *plus* per-sim:
   - `n_imported_total` — total imports applied across the sim window.
   - `n_new_acquisitions_total` — total new infections (imports + natural).
   - `import_fraction` — `n_imported_total / n_new_acquisitions_total`.
5. Plot per-rate bifurcation histograms (the same diagnostic figure
   that surfaced the problem in exp 13) plus a per-rate import-fraction
   summary, so we can see at a glance which rates are policy-defensible
   AND fix the bifurcation.

**Why NROY draws, not prior draws.** Using the NROY tests whether the
existing parameter region — already tuned for HIV/NG/CT/TV/TV — is
compatible with an FOI floor. If yes, exp 16 redoes trajectory
selection against the FOI-floor model on the same NROY. If no, exp 16
restarts HM from wave 1 against the FOI-floor model.

**Success criteria.** Two criteria — both must be met for the
experiment to count as a usable fix; either alone is failure.

- **Bifurcation closes (epi):** at the chosen rate, the
  syph_prev_f_2020-2025 histogram across 50 NROY draws is unimodal
  with median in the 0.5–3% range (i.e. brackets the data).
- **Import fraction stays small (policy):** at the same rate, median
  `import_fraction` across the 50 draws is well under 5%, ideally
  ~1%. This is the hard ceiling — if the rate that closes the
  bifurcation pushes imports above 5% of new acquisitions, the
  apparent fix is degenerate, because most syphilis transmission in
  the model is no longer endogenous.

The interesting outcomes:

- **Both met at the same rate** → FOI imports are a defensible fix;
  proceed to exp 16 (re-do HM, then trajectory selection).
- **Bifurcation closes only at rates that violate the import-fraction
  ceiling** → imports cannot do the work alone. The network or
  natural-history mechanism is fundamentally missing something.
  Escalate to waning syph immunity (exp 16) or wider network
  turnover (exp 17), not more imports.
- **Bifurcation does not close at any tested rate** → imports
  prevent the extinct branch but do not attenuate the hot branch.
  Same escalation as above.

- **Subsidiary:** the non-syph targets (HIV, NG, CT, TV) are roughly
  unchanged across rates. If imports inadvertently break the other
  diseases (e.g. via the syph-HIV coinfection connector amplifying
  HIV trajectories), we need to think harder about co-dependence.

**Framing.** Background case importation is *not* the real-world
driver of sustained syphilis transmission in Zimbabwe. Endemic
syphilis is maintained by within-population sexual transmission, and
imports are a minor addition layered on top — a few percent at most.
If this experiment finds that importation has to do the heavy lifting
to sustain modelled syphilis at the observed level, the model has
*not* been fixed; it has been quietly degraded into something closer
to an incidence model that randomly infects people. The right answer
in that case is to escalate to a different structural mechanism
(waning immunity, wider network turnover) — not to silently accept
a high import rate. The two-criterion success bar above is what
forces that distinction.
