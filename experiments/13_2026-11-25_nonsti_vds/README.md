# Exp 13 — calibration with non-STI VDS presentations matched to Chirenje 2018

**Question.** In exp 12's ensemble, women presenting with vaginal discharge were 85% NG/CT/TV-positive, against about 43% in the Zimbabwe STI Etiology Study (Chirenje 2018, 200 women at 6 STI clinics). The reason: SimpleBV, which stands for every non-STI cause of discharge (BV, candida, idiopathic), let half its episodes persist for 100 years, so those women presented only once. With SimpleBV `p_clear=1`, every episode clears and can recur. Does the ensemble still fit, and does the presenter mix match Chirenje?

**Changes from exp 12.**
- **`model.py`:** `SimpleBV(p_clear=1.0)`.
- **New target in exp 10:** the share of female VDS presenters with no NG/CT/TV, 2014–16. Band 50.6–64.4% (about 115/200 without NG/CT/TV, excluding *M. genitalium*). Weight 2; accepted within 0.5 band-widths.
- **New validation:** NG or CT among presenters, about 33% (NG 24%, CT 14%).

A 3×3 screen on two exp 12 draws found that `p_clear=1`, with the default `p_symp_care=0.3`, gives 60% non-STI and 28% NG or CT. NG prevalence barely changed (1.4% to 1.3%).

**Method.** Exp 12's 200 combinations (`../12_2026-11-25_mix_and_match/outputs/combos.csv`), K=5, 10k agents, 1985–2030, through exp 10's `main()`. Env `stinotif4`.

```bash
N_WORKERS=150 python experiments/13_2026-11-25_nonsti_vds/run.py
```
