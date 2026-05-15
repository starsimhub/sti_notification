# Exp 03 — Coverage check: network risk structure and syphilis transmissibility

**Question.** Exp 02 showed syphilis seeds but crashes to zero by ~2010
in 99/100 draws. Comparison with `syph_dx_zim` (which sustains syphilis)
identified four structural gaps: (1) the high-risk group is too small
(`prop_f2=0.025` vs 0.10), (2) high-risk concurrency is absent,
(3) `rel_trans_primary` is fixed at 5 instead of calibrated (posterior
median 8 in `syph_dx_zim`), and (4) `syph.eff_condom` is fixed. This
experiment aligns the network with `syph_dx_zim` defaults and opens
`rel_trans_primary` and `syph.eff_condom` as calibration parameters.

**Plan.** Changes to `model.py`:
- Set `prop_f2=0.05`, `prop_m2=0.15` (from 0.025, 0.05).
- Add `m2_conc=0.50`, `f2_conc=0.25` to StructuredSexual.
- Keep `f1_conc=0.05` as-is (syph_dx_zim used 0.15 — conservative start).

Changes to `priors.py`:
- Add `syph.rel_trans_primary` (range 3–10, linear).
- Add `syph.eff_condom` (range 0.30–0.70, linear).

Run: 100-draw prior predictive check, same setup as exp 01/02 (n_agents=5000,
1985–2025, no PN, no FetalHealth).

**Success criteria.** Syphilis trajectories sustain through 2020–2025 in
a meaningful fraction of draws (not necessarily all — the prior is wide)
and bracket the ~1.7–2.2% data points. NG/CT/TV/HIV should remain
unchanged. If syphilis still crashes, the next lever is `f1_conc` and
the HIV-syphilis coinfection connectors.
