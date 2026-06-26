# Exp 04 — SOC vs POC+PN wiring check

> **Closed — see `SUMMARY.md`.** Two changes from this pre-registration:
> the trace pivoted **NG → CT** (NG/TV are extinct in draw 773), and a
> second arm (A = SOC) was added so the contrast is real. The cascade
> verified correct; POC+PN beats SOC modestly; reinfection is driven by
> *undertreated concurrent regular partners*, not a sex-work reservoir.

**Question.** Before we trust any "partner notification barely improves
health outcomes" finding, is the PN cascade actually wired end-to-end?
The exp 01 pilot showed notifications scaling cleanly (links 1–3:
index selection → edge-walk → notify/attend filters), but the
*downstream* links were never directly verified: (4) `notify_attendees`
routing attendees into treatment, (5) those tests/treatments firing on
the attendee UIDs and curing them, (6) cures averting onward
transmission. A silent break in 4–5 would look identical, from the
outside, to a true null. This experiment isolates and verifies links
4–6 on the rc1.5.7 baseline.

**Plan.** One calibrated draw (`draw_idx=773`, the median-n_pass row of
`experiments/03_calibration_rc1.5.7/outputs/draws_used.csv`), one seed,
two arms sharing that (draw, seed):

- **Arm A — SOC:** `poc=False`, baseline edge-stratified PN
  (`BASELINE_NOTIFY` / `BASELINE_ATTEND`). Syndromic VDS/UDS for
  NG/CT/TV; syndromic GUD for syph.
- **Arm B — POC + increased PN:** `poc=True` (flips *both* VDS→`panel`
  and GUD→`gud2`/`syph_pn_test` at intv_year=2027) + PN rates scaled
  ×3 (`scale_pn(3.0)`, the exp 01 C3 level). The ×3 is deliberately
  strong — we want an unambiguous PN signal to test the cascade, not a
  calibrated policy level.

No FSW outreach, no care-seeking multiplier — those are separate levers
and would confound a clean PN-wiring read. Built on the validated
`_pipeline` path (load draw → `set_pars_local` → edge-stratified
`pn_rates`), following `experiments/01_poc_pilot_3arm/run.py`. A probe
analyzer tracks, each step, the attendee→treatment handoff directly:
of the agents notified-and-attending at step *t*, how many are treated
at *t*/*t+1*. Raw per-step cascade series saved to `outputs/`.

**Success criteria.** This is a **wiring check, not a science check** —
success is *not* "PN improves health." Success is:

1. Both arms load draw 773 and differ (Arm B has POC dx active post-2027
   and notification volume ≈3× Arm A).
2. The handoff converts: a non-trivial fraction of PN attendees show up
   as treated within one step — the probe is not flat zero.
3. Attendee-driven treatments are attributable (POC arm: `panel` /
   `syph_pn_test` fire on attendee UIDs; SOC arm: `syndromic_vds`/`uds`
   do).

A **failure** looks like: notifications scale but the handoff probe is
zero (link 4 broken), or treatments don't rise with attendance (link 5),
or the arms are identical (draw/poc/PN not applied). Any of these would
mean the exp 01 null is a wiring artifact and must be re-run. If all
three pass, the null is a genuine model property and the full ensemble
sweep can proceed.
