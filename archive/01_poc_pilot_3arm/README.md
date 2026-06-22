# Exp 01 — Pilot: POC etiological testing × elevated PN willingness (3 arms × 10 draws)

**Question.** Does replacing Zimbabwe syndromic management of GUD +
VDS with point-of-care (POC) etiological testing measurably reduce
infections and unnecessary partner notifications, and how much of the
impact comes from dx accuracy alone vs from the assumed PN-willingness
increase that goes with definitive diagnosis? Cheap pilot (10 draws ×
3 seeds × 3 arms) to validate the pipeline and surface the rough
direction of the effect before committing to a full
ensemble-propagation run.

**Background.** The 169-draw calibrated posterior in
[`calibration/artifacts/draws_used.csv`](../../calibration/artifacts/draws_used.csv)
represents Zimbabwe in 2025 under current syndromic management
(presumptive ulcer treatment + weak rash channel) and baseline partner
notification (stable 0.20 / casual 0.10). This experiment runs the
same draws forward through three counterfactual policy worlds from
2027 onward.

## Five arms (3-arm decomposition + sensitivity sub-arms on PN willingness)

| Arm | Symptomatic care pathway (post-2027) | PN routing | PN willingness |
|---|---|---|---|
| **A: Status quo** | Syndromic NG/CT/TV (VDS + UDS algorithms) + two-channel syndromic syph (`syndromic_gud` 0.8 on ulcers + `syndromic_rash` 0.1 on rash) | Attendees routed through syndromic VDS / UDS | Baseline (stable 0.20 / casual 0.10) |
| **B: POC dx, baseline PN** | POC etiological NG/CT/TV panel (0.95 sens, 0.95 spec per pathogen) for both sexes + POC syph on ulcer channel (`gud2`: 0.95 primary / 0.95 secondary / 0.05 elsewhere). Syndromic VDS + UDS both stop at 2027. Rash channel keeps weak syndromic_rash 0.1 in all arms (secondary-rash presenters typically don't reach STI clinics) | Attendees routed through POC panel + POC syph test (unconditional on symptoms — latent attendees get the gud2 low-sens 0.05 screen) | Baseline (stable 0.20 / casual 0.10) |
| **C1: POC + 1.5× PN** | Same as B | Same as B | Stable 0.30 / casual 0.15 notify; attend = 1.5× baseline capped at 0.95 |
| **C2: POC + 2× PN** | Same as B | Same as B | Stable 0.40 / casual 0.20 notify; attend = 2× baseline capped at 0.95 |
| **C3: POC + 3× PN** | Same as B | Same as B | Stable 0.60 / casual 0.30 notify; attend = 3× baseline capped at 0.95 |

The POC syph product swap (`syndromic_gud` → `gud2`) shares the same
eligibility filter as the syndromic baseline (`chancre_visible |
gudp.symptomatic`). So `gud2`'s 0.95 secondary entry only fires when
a secondary-stage agent happens to present via the gudp pool (small
real-world impact on secondaries); the main effect is in the ulcer
channel, where presumptive 0.8 universal becomes definitive
0.95 primary / 0.05 elsewhere. For PN attendees in POC arms, the
`gud2` product is applied unconditionally — so latent / asymptomatic
notified partners still get a low-sens 0.05 screen, while primary /
secondary partners get 0.95.

Arm A is the calibrated baseline. Arm B isolates the **dx-accuracy
effect** (cleaner identification of true syph; non-syph GUD
presenters no longer get presumptive syph treatment; symptomatic
NG/CT/TV switches from syndromic to molecular). Arms C1/C2/C3 add the
**willingness effect** at three sensitivity multipliers (definitive
diagnosis assumed to raise willingness 1.5×/2×/3×). No
Zimbabwe-specific anchor on the willingness multiplier; the sweep is
the answer to "how much does this matter."

Pilot scale: 10 draws × 3 seeds × 5 arms = 150 sims. Production
ensemble propagation later: 169 draws × 3 seeds × 5 arms = 2,535 sims.

## Defaults documented for future override

| Setting | Default | Why this default |
|---|---|---|
| Intervention switch year | 2027 | Already hardcoded as `intv_year` in [interventions.py](../../interventions.py) |
| Time horizon | 1985–2040 | Matches calibration window |
| Outcome counting window | 2027–2040 (post-switch) | Captures full intervention effect |
| Elevated PN rates (arms C1/C2/C3) | 1.5× / 2× / 3× baseline notify; attend rates same multipliers capped at 0.95 | Sensitivity sweep over the willingness-elevation assumption |
| Draws | 10 (pilot); 169 (production) | 10 draws × 3 seeds × 5 arms = 150 sims is enough to see direction; 169 is the full calibrated posterior |
| Seeds per draw | 3 | Matches calibration convention |
| Sim workers | 60 | No other heavy jobs; matches recalibration setup |

## Endpoints (this experiment)

Tracking the cheapest endpoints that are already instrumented:
1. **HIV new infections 2027–2040** — `hiv.results.new_infections`
2. **Syph new infections 2027–2040** — `syph.results.new_infections`
3. **Syph treatments delivered** — `syph_tx.results.new_treated`
4. **Syph unnecessary treatments** (treatments on truly negative agents)
   — `syph_tx.results.new_treated_unnecessary` if exposed; otherwise
   compute post-hoc from `(ti_treated == ti) & ~currently_active`
5. **Notifications / attendances** — `pn.results.new_notifications`,
   `pn.results.new_attendances` if exposed; otherwise compute post-hoc

Defer to a later experiment: APO/ABO outcomes (need `FetalHealth`
connector verification post-Fix C), DALYs (need post-hoc weight
calculation), cost-effectiveness (no cost numbers in repo yet).

## Code changes required

This experiment requires these pieces of code on `scenarios/zimbabwe`:

1. **`interventions.py`**: extend `make_syph_testing` to accept a
   `poc=` flag. When `poc=True`, add a second syph_symp_test instance
   with `start=intv_year` using `gud2` product; the existing
   `syph_symp_test` gets `stop=intv_year` so the ulcer channel
   switches cleanly at 2027. The syph_tx is moved to the end of the
   intervention list so it picks up POC-test positives this step
   rather than next step.
2. **`interventions.py`**: add `POCPanel` — an inline NG/CT/TV
   etiological-test panel (single eligibility for both sexes, 0.95
   sens / 0.95 spec per pathogen, no presumptive metronidazole).
   Sidesteps a pre-existing upstream bug in stisim's
   `SymptomaticTesting` and removes the women-only restriction.
3. **`interventions.py`**: add `POCPN` — partner-notification class
   that routes attendees through `POCPanel` and the POC syph test
   (looked up by name at runtime). Used in `make_testing(poc=True)`
   instead of `SyndromicPN`.
4. **`interventions.py`**: extend `make_testing` to accept
   overrideable notify / attend rate dicts so we can pass elevated
   rates per arm; in POC mode, stop both syndromic_vds and
   syndromic_uds at intv_year and use POCPanel + POCPN instead.
5. **`experiments/01_poc_pilot_3arm/run.py`**: orchestration —
   loads 10 random draws, runs each at 3 seeds × 5 arms, writes
   per-(arm, draw, seed) summary stats to a single JSONL.

**Success criteria.** All 90 sims complete cleanly. Per-arm summary
statistics differ meaningfully between A, B, C in the expected
direction (B reduces unnecessary syph treatment vs A; C reduces
infections vs B). If those signs are right, scale up to the full
169-draw ensemble in exp 02.

**Expected wall time:** ~5 min on 30 workers.

---

## Status (2026-06-11)

Pilot has run and expanded beyond the original 5-arm design as policy
levers were added in response to muted impact. Current state: 9 arms,
270 sims per run, ~7 min wall on 60 workers. See [SUMMARY.md](SUMMARY.md)
for results.

**Arms now in the pilot** (see `ARMS` list in `run.py`):

- **A_soc** — syndromic NG/CT/TV + syndromic syph + baseline PN (original).
- **B_poc_baseline** — POC NG/CT/TV + POC syph (gud2) + baseline PN (original).
- **C1/C2/C3_poc_pn_{1_5,2,3}x** — POC + PN ×1.5/2/3 (original C1-C3).
- **D_poc_pn_3x_fsw_out** — C3 + direct FSW outreach (POCPanel screening
  of currently-active FSW at ~10%/step ≈ 70%/yr reach). Added because
  the symptomatic-care + PN pipeline cannot reach the asymptomatic-FSW
  reservoir.
- **E1/E2/E3_d_careseek_{1_5,2,3}x** — D + symptomatic care-seeking
  ×1.5/2/3 (applied equally to F and M, clipped to 1.0). ×3 is a
  near-ceiling: all rates saturate except TV M (0.27→0.81).

**Headline finding.** For NG/CT/TV undertreatment, symptomatic
care-seeking is by far the dominant lever (E2 vs A: NG -31%, CT -24%,
TV -33% relative). PN intensity and FSW outreach together give ~10%
relative gains. Syph and BV don't respond to E (syph care-seeking is on
`data/symp_test_prob.csv`, not the NG/CT/TV `p_symp_care`; BV is in
equilibrium at ~40%). See [SUMMARY.md](SUMMARY.md) per-disease tables.

**Endpoints added beyond the original spec:**

- Per-disease n_infected + prevalence at 2040 (every disease in DISEASES list).
- Per-disease treatments: total, successful, unnecessary, by sex.
- Proportion of new infections successfully treated, overall + by sex.
- BV prevalence + counts (new — dominant VDS-driver, surfaces SOC
  over-treatment dynamics).
- Wasted PN attendance — attendees with no current STI at attendance
  (NG/CT/TV/syph all negative; BV excluded). Captures the clinic-time
  + relationship-risk cost of false-alarm PN.
- Syph APO: native `new_congenital` (`new_nnds` / `new_stillborns`
  require FetalHealth wiring; off for this pilot).

**Code additions in `interventions.py`:**

- `GonorrheaTreatmentFixed` — workaround for stisim's `rel_treat = NaN`
  bug ([[feedback-stisim-rel-treat-bug]]). Required for any NG dynamics.
- `PartnerNotificationNoCycle` — base class with A→B→A cycle prevention
  via per-agent `last_notifier`. Both `SyndromicPN` and `POCPN` inherit.
- `POCPanel` — POC NG/CT/TV etiological panel (per-pathogen sens/spec).
- `POCPN` / `SyndromicPN` — PN classes that route attendees through the
  arm-appropriate panel.
- `FSWOutreach` — periodic POC screening of currently-active FSW (uses
  POCPanel internals; eligibility = `structuredsexual.fsw.uids` filtered
  by per-step bernoulli).
- `make_pn` — extracted as top-level function; PN is a single
  intervention shared across all diseases, sits between `make_testing`
  and `make_syph_testing` in the orchestration order so `syph_pn_test`
  positives get picked up by `syph_tx` same-step.
- `syph_anc_confirm` — POC arms add an RPR confirmation step after
  `syph_anc_rdt` to prevent re-treatment of previously-cured women
  whose treponemal antibodies still light up the dual RDT. Time-gated
  to ≥intv_year (pre-2027 the calibration baseline `anc_rdt → tx` path
  is preserved).
- `make_discharging_stis(care_seek_mult=...)` accepts a scalar or
  `(F_mult, M_mult)` tuple for sex-specific scaling.

**Known limitations / TODOs flagged in SUMMARY.md:**

- PN cascade indices not stratified by which STI drove the index.
- Treated-within-3-months metric not yet implemented (requires
  per-agent `ti_infected - ti_treated` tracking).
- FSW outreach screens NG/CT/TV only, NOT syph. Real-world FSW outreach
  panels include syph dx. If retained as an arm, extend `FSWOutreach`
  to also call `syph_pn_test` on screened FSW.
- FetalHealth wiring is off — syph APO is just `new_congenital`; NND
  and stillbirth require the `sti_fetal` connector. Decision: enable
  for the next iteration once decision-analysis stage begins.
- No cost overlay yet. Decision-analysis stage needs unit costs for
  POC test, syndromic visit, PN visit, FSW outreach visit, treatment.

**Next session pickup:** the experiment is a sandboxed iteration ground
for the PN/care-seeking scenario question, not yet production. Two
natural next moves: (1) sex-specific care-seeking sweep to isolate F vs
M effect (`(1.0, 2.0)` vs `(2.0, 1.0)`); (2) cost-side overlay so
wasted-PN dollar-cost can be balanced against case-finding gain. The
project memory [[project-scenario-levers]] captures the lever
hierarchy as of this pilot.

