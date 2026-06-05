"""
Bimodal-aware reweighting of exp 13's existing JSONL.

Three variants on the same 1000 raw target dicts:
  A. Gaussian, alive-only (reproduces exp 13's ESS as a sanity check).
  B. Gaussian, NaN-for-extinction on syph targets.
  C. Student-t df=3, NaN-for-extinction on syph targets.

No new simulations. Outputs per-variant weights, posterior ensembles,
and a comparative summary.json.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
JSONL_IN = HERE.parent / '13_trajectory_selection_post_anc_fix' / 'outputs' / 'results.jsonl'
OUTPUTS = HERE / 'outputs'
OUTPUTS.mkdir(parents=True, exist_ok=True)

OBSERVATIONS = {
    'hiv_prev_2000_2010':     (0.116, 0.015),
    'hiv_prev_2010_2020':     (0.092, 0.010),
    'ng_prev_2005_2015':      (0.020, 0.003),
    'ct_prev_f2530':          (0.120, 0.020),
    'tv_prev_2005_2015':      (0.111, 0.015),
    'syph_prev_f_2016':       (0.010, 0.002),
    'syph_prev_m_2016':       (0.006, 0.0013),
    'syph_seroprev_f_2016':   (0.030, 0.0033),
    'syph_seroprev_m_2016':   (0.024, 0.0033),
    'syph_anc_2000_2015':     (0.020, 0.0033),
    'syph_prev_hivpos_2016':  (0.029, 0.0053),
    'syph_prev_hivneg_2016':  (0.004, 0.0013),
}

SYPH_TARGETS = {k for k in OBSERVATIONS if 'syph' in k}
EXTINCT_CUTOFF = 0.001
SYPH_FILTER_CUTOFF = 0.005   # exp 13's alive-only filter, used for variant A.
STUDENT_T_DF = 3
SYPH_STD_MULT = 3.0
NONSYPH_STD_MULT = 2.0


def load_jsonl():
    rows = []
    with JSONL_IN.open() as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


def widened_std(target):
    mean, std = OBSERVATIONS[target]
    mult = SYPH_STD_MULT if 'syph' in target else NONSYPH_STD_MULT
    return mean, std * mult


def gaussian_loglik(val, mean, std):
    if pd.isna(val):
        return None
    return -0.5 * ((val - mean) / std) ** 2


def student_t_loglik(val, mean, std, df=STUDENT_T_DF):
    if pd.isna(val):
        return None
    return float(stats.t.logpdf(val, df=df, loc=mean, scale=std))


def row_loglik(row, loglik_fn, nan_for_extinction):
    """Per-row log-likelihood.

    nan_for_extinction: if True and the row is in the extinct set,
    syph targets are marginalised (contribute 0). If False and the row
    is in the extinct set, return -inf (alive-only filter).
    """
    extinct = row['syph_prev_f_2016'] <= EXTINCT_CUTOFF
    if extinct and not nan_for_extinction:
        return -np.inf
    ll = 0.0
    for target in OBSERVATIONS:
        if extinct and target in SYPH_TARGETS:
            continue
        mean, std = widened_std(target)
        val = row.get(target)
        if val is None or pd.isna(val):
            return -np.inf
        contrib = loglik_fn(val, mean, std)
        if contrib is None:
            continue
        ll += contrib
    return ll


def normalise_weights(log_lik):
    finite = np.isfinite(log_lik)
    if not finite.any():
        return np.zeros_like(log_lik), 0.0
    log_w = np.where(finite, log_lik, -np.inf)
    log_w = log_w - np.nanmax(log_w[finite])
    w = np.exp(log_w)
    w[~finite] = 0.0
    w = w / w.sum()
    ess = 1.0 / np.sum(w ** 2)
    return w, ess


def compute_variant(df, name, loglik_fn, nan_for_extinction, alive_filter):
    work = df.copy()
    if alive_filter:
        work = work[work['syph_prev_f_2016'] > SYPH_FILTER_CUTOFF].copy()
    work['log_lik'] = work.apply(
        lambda r: row_loglik(r, loglik_fn, nan_for_extinction), axis=1)
    log_lik = work['log_lik'].values
    w, ess = normalise_weights(log_lik)
    work['weight'] = w
    n_finite = int(np.isfinite(log_lik).sum())

    rng = np.random.default_rng(0)
    if ess > 0 and w.sum() > 0:
        idx = rng.choice(len(work), size=min(500, len(work)), replace=True, p=w)
        posterior = work.iloc[idx].copy()
    else:
        posterior = work.iloc[:0].copy()

    work.to_csv(OUTPUTS / f'weighted_{name}.csv', index=False)
    posterior.to_csv(OUTPUTS / f'posterior_{name}.csv', index=False)

    alive = work[work['syph_prev_f_2016'] > SYPH_FILTER_CUTOFF]
    alive_mean = float(alive['syph_prev_f_2020_2025'].mean()) if len(alive) else float('nan')
    post_mean = float((work['syph_prev_f_2020_2025'].values * w).sum())

    return {
        'variant': name,
        'n_input': len(df),
        'n_in_weighting': len(work),
        'n_finite_loglik': n_finite,
        'ess': float(ess),
        'ess_ratio': float(ess / n_finite) if n_finite else 0.0,
        'alive_pool_predictive_syph_late': alive_mean,
        'posterior_predictive_syph_late': post_mean,
        'gap_ratio': (alive_mean / post_mean) if (post_mean and not np.isnan(post_mean) and post_mean > 0) else float('inf'),
    }


def main():
    df = load_jsonl()
    df = df[df['status'] == 'ok'].copy()
    print(f'Loaded {len(df)} ok sims from {JSONL_IN}')

    variants = [
        ('A_gaussian_alive_only', gaussian_loglik,  False, True),
        ('B_gaussian_nan',        gaussian_loglik,  True,  False),
        ('C_studentt_nan',        student_t_loglik, True,  False),
    ]
    results = [compute_variant(df, name, fn, nan, alive)
               for name, fn, nan, alive in variants]

    header = ['variant', 'n_weighted', 'ESS', 'ESS/N',
              'alive syph_late', 'post syph_late', 'gap']
    rows = [[
        r['variant'],
        r['n_in_weighting'],
        f"{r['ess']:.1f}",
        f"{r['ess_ratio']:.3f}",
        f"{r['alive_pool_predictive_syph_late']:.4f}",
        f"{r['posterior_predictive_syph_late']:.4f}",
        f"{r['gap_ratio']:.1f}x" if r['gap_ratio'] != float('inf') else 'inf',
    ] for r in results]
    widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) for i, h in enumerate(header)]
    def fmt(row): return '  '.join(str(v).ljust(w) for v, w in zip(row, widths))

    print()
    print(fmt(header))
    print(fmt(['-' * w for w in widths]))
    for r in rows:
        print(fmt(r))

    summary = {
        'variants': results,
        'extinct_cutoff_on_syph_prev_f_2016': EXTINCT_CUTOFF,
        'alive_filter_cutoff_syph_prev_f_2016': SYPH_FILTER_CUTOFF,
        'student_t_df': STUDENT_T_DF,
        'syph_std_mult': SYPH_STD_MULT,
        'nonsyph_std_mult': NONSYPH_STD_MULT,
    }
    with (OUTPUTS / 'summary.json').open('w') as f:
        json.dump(summary, f, indent=2)
    print(f'\nWrote {OUTPUTS / "summary.json"}')


if __name__ == '__main__':
    main()
