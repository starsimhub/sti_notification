"""
Epi diagnostic plots from the posterior ensemble.

Runs top-weighted posterior draws and produces a battery of figures:
prevalence time series, age-stratified prevalence, coinfection stats,
STI burden by sex/HIV status, transmission routes, etc.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as plt

from model import make_sim
from priors import calib_pars

OUTPUTS = Path(__file__).parent / 'outputs'
FIGURES = Path(__file__).parent / 'figures'
DATA = Path(__file__).resolve().parents[2] / 'data'

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 40))
N_RUNS    = int(os.environ.get('N_RUNS', 50))
START     = 1985
STOP      = 2025
PLOT_START = 2000  # Trim burn-in from timeseries plots


def set_pars_local(sim, pars):
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        for category in ('diseases', 'networks', 'interventions',
                         'connectors', 'analyzers', 'demographics', 'custom'):
            container = sim.pars.get(category)
            if container is None:
                continue
            if isinstance(container, list):
                for mod in container:
                    if hasattr(mod, 'name') and mod.name == mod_name:
                        existing = mod.pars.get(par_name)
                        if hasattr(existing, 'set'):
                            existing.set(mean=value)
                        else:
                            mod.pars[par_name] = value
                        break
    return sim


def run_one(par_row, seed):
    """Run one posterior sim and extract rich results."""
    par_cols = ['hiv.beta_m2f', 'syph.beta_m2f', 'ng.beta_m2f', 'ct.beta_m2f',
                'tv.beta_m2f', 'structuredsexual.prop_f0',
                'structuredsexual.m1_conc', 'structuredsexual.dur_sw']
    sim_pars = {k: par_row[k] for k in par_cols}

    sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                   pn_pars=None, fetal_health=False, verbose=-1)
    set_pars_local(sim, sim_pars)
    sim.init()
    sim.run()

    r = sim.results
    ppl = sim.people
    tvec = r['hiv']['prevalence'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])

    out = dict(years=years)

    # --- Prevalence time series ---
    for d in ['hiv', 'ng', 'ct', 'tv']:
        out[f'{d}_prev'] = r[d]['prevalence'].values.copy()
        out[f'{d}_prev_f'] = r[d]['prevalence_f'].values.copy()
        out[f'{d}_prev_m'] = r[d]['prevalence_m'].values.copy()

    out['syph_prev'] = r['syph']['prevalence'].values.copy()
    out['syph_prev_f'] = r['syph']['prevalence_f'].values.copy()
    out['syph_prev_m'] = r['syph']['prevalence_m'].values.copy()
    out['syph_seroprev'] = r['syph']['serological_prevalence'].values.copy()
    out['syph_seroprev_f'] = r['syph']['serological_prevalence_f'].values.copy()
    out['syph_seroprev_m'] = r['syph']['serological_prevalence_m'].values.copy()
    out['syph_active_prev'] = r['syph']['active_prevalence'].values.copy()
    out['syph_preg_prev'] = r['syph']['pregnant_prevalence'].values.copy()

    # --- Coinfection ---
    coinf = r['syph_hiv_coinfection']
    out['syph_prev_hivpos'] = coinf['syph_prev_has_hiv'].values.copy()
    out['syph_prev_hivneg'] = coinf['syph_prev_no_hiv'].values.copy()

    # --- New infections ---
    for d in ['hiv', 'ng', 'ct', 'tv', 'syph']:
        out[f'{d}_new_inf'] = r[d]['new_infections'].values.copy()

    # --- Age-stratified prevalence at 2020 ---
    age_bins = [(15, 20), (20, 25), (25, 30), (30, 35), (35, 50), (50, 65)]
    idx_2020 = np.argmin(np.abs(years - 2020))
    for d in ['ng', 'ct', 'tv']:
        for sex in ['f', 'm']:
            for a1, a2 in age_bins:
                key = f'prevalence_{sex}_{a1}_{a2}'
                if key in r[d]:
                    out[f'{d}_prev_{sex}_{a1}_{a2}'] = float(r[d][key].values[idx_2020])

    for sex in ['f', 'm']:
        for a1, a2 in age_bins:
            key = f'active_prevalence_{sex}_{a1}_{a2}'
            if key in r['syph']:
                out[f'syph_active_{sex}_{a1}_{a2}'] = float(r['syph'][key].values[idx_2020])

    # --- STI coinfection snapshot at 2020 ---
    # Count how many STIs each person has at final timestep
    hiv_inf = sim.diseases.hiv.infected
    ng_inf = sim.diseases.ng.infected
    ct_inf = sim.diseases.ct.infected
    tv_inf = sim.diseases.tv.infected
    syph_inf = sim.diseases.syph.infected

    adults = np.array((ppl.age >= 15) & (ppl.age < 50) & ppl.alive)
    n_stis = (np.array(ng_inf, dtype=int) + np.array(ct_inf, dtype=int) +
              np.array(tv_inf, dtype=int) + np.array(syph_inf, dtype=int))

    hiv_arr = np.array(hiv_inf)
    female_arr = np.array(ppl.female)
    male_arr = np.array(ppl.male)
    for hiv_label, hiv_mask in [('all', adults), ('hivpos', adults & hiv_arr), ('hivneg', adults & ~hiv_arr)]:
        for sex_label, sex_mask in [('all', adults), ('f', adults & female_arr), ('m', adults & male_arr)]:
            mask = hiv_mask & sex_mask
            n = int(mask.sum())
            if n == 0:
                for k in range(4):
                    out[f'sti_count_{k}_{hiv_label}_{sex_label}'] = 0.0
                continue
            for k in range(4):
                if k < 3:
                    out[f'sti_count_{k}_{hiv_label}_{sex_label}'] = float((n_stis[mask] == k).sum()) / n
                else:
                    out[f'sti_count_{k}_{hiv_label}_{sex_label}'] = float((n_stis[mask] >= k).sum()) / n

    # --- HIV prevalence by age at 2016 ---
    idx_2016 = np.argmin(np.abs(years - 2016))
    for sex in ['f', 'm']:
        for a1, a2 in age_bins:
            key = f'prevalence_{sex}_{a1}_{a2}'
            if key in r['hiv']:
                out[f'hiv_prev_{sex}_{a1}_{a2}'] = float(r['hiv'][key].values[idx_2016])

    # --- Syphilis congenital ---
    out['syph_congenital'] = r['syph']['new_congenital'].values.copy()
    out['syph_congenital_deaths'] = r['syph']['new_congenital_deaths'].values.copy()

    return out


def plot_prevalence_timeseries(results):
    """Prevalence time series for all diseases with data overlay."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.ravel()
    years = results[0]['years']

    diseases = [
        ('hiv_prev', 'HIV prevalence', 'zimbabwe_hiv_calib.csv', 'hiv_prevalence'),
        ('ng_prev', 'NG prevalence', 'zimbabwe_sti_data.csv', 'ng_prevalence'),
        ('ct_prev', 'CT prevalence', None, None),
        ('tv_prev', 'TV prevalence', 'zimbabwe_sti_data.csv', 'tv_prevalence'),
        ('syph_prev', 'Syphilis prevalence (current infection)', None, None),
        ('syph_seroprev', 'Syphilis seroprevalence', None, None),
    ]

    for ax, (key, title, datafile, datacol) in zip(axes, diseases):
        for res in results:
            ax.plot(res['years'], res[key], color='steelblue', alpha=0.15, lw=0.8)

        # Median
        all_vals = np.array([res[key] for res in results])
        ax.plot(years, np.median(all_vals, axis=0), color='steelblue', lw=2, label='Posterior median')

        # Data overlay
        if datafile:
            try:
                data = pd.read_csv(DATA / datafile)
                data = data.dropna(subset=[datacol])
                ax.scatter(data['time'], data[datacol], color='C3', s=20, zorder=5, label='Data')
            except (FileNotFoundError, KeyError):
                pass

        # ZIMPHIA syphilis points
        if key == 'syph_prev':
            syph_data = pd.read_csv(DATA / 'zimbabwe_syph_data.csv')
            for col, marker, label in [('syph.prevalence_f', 'v', 'ZIMPHIA F'),
                                        ('syph.prevalence_m', '^', 'ZIMPHIA M')]:
                d = syph_data.dropna(subset=[col])
                if len(d):
                    ax.scatter(d['time'], d[col], marker=marker, s=30, zorder=5, label=label)

        if key == 'syph_seroprev':
            syph_data = pd.read_csv(DATA / 'zimbabwe_syph_data.csv')
            for col, marker, label in [('syph.serological_prevalence_f', 'v', 'ZIMPHIA F'),
                                        ('syph.serological_prevalence_m', '^', 'ZIMPHIA M')]:
                d = syph_data.dropna(subset=[col])
                if len(d):
                    ax.scatter(d['time'], d[col], marker=marker, s=30, zorder=5, label=label)

        ax.set_title(title, fontsize=11)
        ax.set_xlabel('Year')
        ax.set_xlim(PLOT_START, STOP)
        ax.legend(fontsize=8, loc='best')
        ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'prevalence_timeseries.png', dpi=120, bbox_inches='tight')
    print(f'Saved prevalence_timeseries.png')


def plot_prevalence_by_sex(results):
    """Prevalence by sex for each disease."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.ravel()
    years = results[0]['years']

    diseases = [
        ('hiv', 'HIV'),
        ('ng', 'NG'),
        ('ct', 'CT'),
        ('tv', 'TV'),
        ('syph', 'Syphilis'),
        ('syph_seroprev', 'Syphilis seroprevalence'),
    ]

    for ax, (d, title) in zip(axes, diseases):
        fkey = f'{d}_prev_f' if d != 'syph_seroprev' else 'syph_seroprev_f'
        mkey = f'{d}_prev_m' if d != 'syph_seroprev' else 'syph_seroprev_m'

        f_vals = np.array([res[fkey] for res in results])
        m_vals = np.array([res[mkey] for res in results])

        ax.plot(years, np.median(f_vals, axis=0), color='C1', lw=2, label='Female')
        ax.fill_between(years, np.percentile(f_vals, 10, axis=0),
                        np.percentile(f_vals, 90, axis=0), color='C1', alpha=0.15)
        ax.plot(years, np.median(m_vals, axis=0), color='C0', lw=2, label='Male')
        ax.fill_between(years, np.percentile(m_vals, 10, axis=0),
                        np.percentile(m_vals, 90, axis=0), color='C0', alpha=0.15)

        ax.set_title(title, fontsize=11)
        ax.set_xlim(PLOT_START, STOP)
        ax.legend(fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'prevalence_by_sex.png', dpi=120, bbox_inches='tight')
    print(f'Saved prevalence_by_sex.png')


def plot_new_infections(results):
    """New infections time series."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.ravel()
    years = results[0]['years']

    for ax, d, title in zip(axes, ['hiv', 'ng', 'ct', 'tv', 'syph'],
                             ['HIV', 'NG', 'CT', 'TV', 'Syphilis']):
        key = f'{d}_new_inf'
        all_vals = np.array([res[key] for res in results])
        ax.plot(years, np.median(all_vals, axis=0), color='steelblue', lw=2)
        ax.fill_between(years, np.percentile(all_vals, 10, axis=0),
                        np.percentile(all_vals, 90, axis=0), color='steelblue', alpha=0.2)
        ax.set_title(f'{title} new infections', fontsize=11)
        ax.set_xlim(PLOT_START, STOP)
        ax.spines[['top', 'right']].set_visible(False)

    axes[5].axis('off')
    sc.figlayout()
    fig.savefig(FIGURES / 'new_infections.png', dpi=120, bbox_inches='tight')
    print(f'Saved new_infections.png')


def plot_age_prevalence(results):
    """Age-stratified prevalence at 2020 for discharging STIs + syphilis."""
    age_bins = [(15, 20), (20, 25), (25, 30), (30, 35), (35, 50), (50, 65)]
    age_labels = ['15-20', '20-25', '25-30', '30-35', '35-50', '50-65']
    x = np.arange(len(age_bins))
    width = 0.35

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.ravel()

    for ax, (d, title, key_prefix) in zip(axes, [
        ('ng', 'NG', 'ng_prev'),
        ('ct', 'CT', 'ct_prev'),
        ('tv', 'TV', 'tv_prev'),
        ('syph', 'Syphilis (active)', 'syph_active'),
    ]):
        f_medians = []
        m_medians = []
        for a1, a2 in age_bins:
            fkey = f'{key_prefix}_f_{a1}_{a2}'
            mkey = f'{key_prefix}_m_{a1}_{a2}'
            f_vals = [res.get(fkey, np.nan) for res in results]
            m_vals = [res.get(mkey, np.nan) for res in results]
            f_medians.append(np.nanmedian(f_vals))
            m_medians.append(np.nanmedian(m_vals))

        ax.bar(x - width/2, f_medians, width, color='C1', alpha=0.7, label='Female')
        ax.bar(x + width/2, m_medians, width, color='C0', alpha=0.7, label='Male')
        ax.set_xticks(x)
        ax.set_xticklabels(age_labels)
        ax.set_title(f'{title} prevalence by age & sex (2020)', fontsize=11)
        ax.legend(fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'age_prevalence.png', dpi=120, bbox_inches='tight')
    print(f'Saved age_prevalence.png')


def plot_coinfection_counts(results):
    """STI coinfection distribution by HIV status and sex."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 8))

    combos = [
        ('all', 'all', 'All adults'),
        ('all', 'f', 'Women'),
        ('all', 'm', 'Men'),
        ('hivpos', 'all', 'HIV+'),
        ('hivneg', 'all', 'HIV−'),
        ('hivpos', 'f', 'HIV+ women'),
    ]

    for ax, (hiv, sex, title) in zip(axes.ravel(), combos):
        counts = {k: [] for k in range(4)}
        for res in results:
            for k in range(4):
                counts[k].append(res.get(f'sti_count_{k}_{hiv}_{sex}', np.nan))

        medians = [np.nanmedian(counts[k]) for k in range(4)]
        labels = ['0 STIs', '1 STI', '2 STIs', '3+ STIs']
        colors = ['#4daf4a', '#ff7f00', '#e41a1c', '#984ea3']

        ax.bar(range(4), medians, color=colors, alpha=0.7)
        ax.set_xticks(range(4))
        ax.set_xticklabels(labels)
        ax.set_ylabel('Proportion')
        ax.set_title(title, fontsize=11)
        ax.set_ylim(0, 1)
        ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'coinfection_counts.png', dpi=120, bbox_inches='tight')
    print(f'Saved coinfection_counts.png')


def plot_hiv_coinfection_timeseries(results):
    """Syphilis prevalence by HIV status over time."""
    fig, ax = plt.subplots(figsize=(8, 5))
    years = results[0]['years']

    hp = np.array([res['syph_prev_hivpos'] for res in results])
    hn = np.array([res['syph_prev_hivneg'] for res in results])

    ax.plot(years, np.median(hp, axis=0), color='C3', lw=2, label='Syph prev | HIV+')
    ax.fill_between(years, np.percentile(hp, 10, axis=0),
                    np.percentile(hp, 90, axis=0), color='C3', alpha=0.15)
    ax.plot(years, np.median(hn, axis=0), color='C0', lw=2, label='Syph prev | HIV−')
    ax.fill_between(years, np.percentile(hn, 10, axis=0),
                    np.percentile(hn, 90, axis=0), color='C0', alpha=0.15)

    # ZIMPHIA data
    ax.scatter([2016], [0.029], color='C3', s=50, zorder=5, marker='D', label='ZIMPHIA HIV+')
    ax.scatter([2016], [0.004], color='C0', s=50, zorder=5, marker='D', label='ZIMPHIA HIV−')

    ax.set_title('Syphilis prevalence by HIV status')
    ax.set_xlabel('Year')
    ax.set_xlim(PLOT_START, STOP)
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'syph_by_hiv_status.png', dpi=120, bbox_inches='tight')
    print(f'Saved syph_by_hiv_status.png')


def plot_congenital_syphilis(results):
    """Congenital syphilis over time."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    years = results[0]['years']

    cong = np.array([res['syph_congenital'] for res in results])
    deaths = np.array([res['syph_congenital_deaths'] for res in results])

    for ax, vals, title in zip(axes, [cong, deaths],
                                ['Congenital syphilis cases', 'Congenital syphilis deaths']):
        ax.plot(years, np.median(vals, axis=0), color='steelblue', lw=2)
        ax.fill_between(years, np.percentile(vals, 10, axis=0),
                        np.percentile(vals, 90, axis=0), color='steelblue', alpha=0.2)
        ax.set_title(title)
        ax.set_xlabel('Year')
        ax.set_xlim(PLOT_START, STOP)
        ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'congenital_syphilis.png', dpi=120, bbox_inches='tight')
    print(f'Saved congenital_syphilis.png')


def plot_hiv_by_age(results):
    """HIV prevalence by age and sex at 2016."""
    age_bins = [(15, 20), (20, 25), (25, 30), (30, 35), (35, 50), (50, 65)]
    age_labels = ['15-20', '20-25', '25-30', '30-35', '35-50', '50-65']
    x = np.arange(len(age_bins))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    f_medians = []
    m_medians = []
    for a1, a2 in age_bins:
        f_vals = [res.get(f'hiv_prev_f_{a1}_{a2}', np.nan) for res in results]
        m_vals = [res.get(f'hiv_prev_m_{a1}_{a2}', np.nan) for res in results]
        f_medians.append(np.nanmedian(f_vals))
        m_medians.append(np.nanmedian(m_vals))

    ax.bar(x - width/2, f_medians, width, color='C1', alpha=0.7, label='Female')
    ax.bar(x + width/2, m_medians, width, color='C0', alpha=0.7, label='Male')
    ax.set_xticks(x)
    ax.set_xticklabels(age_labels)
    ax.set_title('HIV prevalence by age & sex (2016)', fontsize=12)
    ax.set_ylabel('Prevalence')
    ax.legend()
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'hiv_by_age.png', dpi=120, bbox_inches='tight')
    print(f'Saved hiv_by_age.png')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)

    # Load posterior params and select top-weighted draws
    params = pd.read_csv(OUTPUTS / 'posterior_params.csv')
    top = params.nlargest(N_RUNS, 'weight')
    print(f'Running {len(top)} posterior draws at {N_AGENTS} agents...')

    T = sc.timer()
    tasks = [dict(par_row=row.to_dict(), seed=int(row['seed']))
             for _, row in top.iterrows()]

    if N_WORKERS > 1:
        results = sc.parallelize(run_one, iterkwargs=tasks, ncpus=N_WORKERS)
    else:
        results = [run_one(**t) for t in sc.progressbar(tasks)]
    T.toc(f'Ran {len(results)} sims')

    # Filter failed
    results = [r for r in results if 'years' in r]
    print(f'{len(results)} successful runs')

    # Save extracted results
    sc.save(OUTPUTS / 'epi_results.obj', results)

    # Generate all plots
    plot_prevalence_timeseries(results)
    plot_prevalence_by_sex(results)
    plot_new_infections(results)
    plot_age_prevalence(results)
    plot_coinfection_counts(results)
    plot_hiv_coinfection_timeseries(results)
    plot_congenital_syphilis(results)
    plot_hiv_by_age(results)

    print(f'\nAll plots saved to {FIGURES}')
