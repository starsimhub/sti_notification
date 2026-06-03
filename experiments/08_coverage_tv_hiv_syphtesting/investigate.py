"""Investigate parameter insensitivity: syph primary saturation, network, HIV init_prev."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sciris as sc
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

RESULTS = Path(__file__).parent / 'results'

dfs = sc.load(RESULTS / 'coverage_dfs.obj')
draws = sc.load(RESULTS / 'coverage_draws.obj')

par_matrix = np.array([[d[p] for p in draws[0].keys()] for d in draws])

# ---- 1. Syphilis primary transmission saturation ----
print("=" * 70)
print("1. SYPHILIS PRIMARY TRANSMISSION SATURATION")
print("=" * 70)

betas = np.array([d['syph.beta_m2f'] for d in draws])
rtps = np.array([d['syph.rel_trans_primary'] for d in draws])
ecds = np.array([d['syph.eff_condom'] for d in draws])

raw = betas * rtps
eff = betas * rtps * (1 - ecds)

print(f"  beta_m2f:          [{betas.min():.3f}, {betas.max():.3f}]")
print(f"  rel_trans_primary: [{rtps.min():.1f}, {rtps.max():.1f}]")
print(f"  eff_condom:        [{ecds.min():.2f}, {ecds.max():.2f}]")
print()
print(f"  beta * rel_trans (no condom):     [{raw.min():.3f}, {raw.max():.3f}]")
print(f"  beta * rel_trans * (1-eff_cond):  [{eff.min():.3f}, {eff.max():.3f}]")
print(f"  Fraction with raw product > 1.0:  {np.sum(raw > 1.0)/len(raw):.0%}")
print(f"  Fraction with eff product > 0.5:  {np.sum(eff > 0.5)/len(eff):.0%}")
print(f"  Min raw product:                  {raw.min():.3f}")
print()
print("  --> If min product >> 0.5, primary transmission is saturated")
print("      and varying rel_trans_primary within 5-10 makes no difference.")

# ---- 2. Network parameter impact ----
print()
print("=" * 70)
print("2. NETWORK PARAMETERS — EFFECT ON SYPHILIS SUSTAINABILITY")
print("=" * 70)

# Check if network params correlate with syphilis sustainability
syph_prev_2016 = np.array([df[df['time'] == 2016]['syph.prevalence_f'].values[0] for df in dfs])
sustaining = syph_prev_2016 > 0.001

prop_f0 = np.array([d['structuredsexual.prop_f0'] for d in draws])
m1_conc = np.array([d['structuredsexual.m1_conc'] for d in draws])

rho_f0, _ = spearmanr(prop_f0, syph_prev_2016)
rho_m1, _ = spearmanr(m1_conc, syph_prev_2016)

print(f"  prop_f0 vs syph.prevalence_f@2016:  rho = {rho_f0:+.3f}")
print(f"  m1_conc vs syph.prevalence_f@2016:  rho = {rho_m1:+.3f}")

# Among sustaining draws only
if sustaining.sum() > 10:
    rho_f0s, _ = spearmanr(prop_f0[sustaining], syph_prev_2016[sustaining])
    rho_m1s, _ = spearmanr(m1_conc[sustaining], syph_prev_2016[sustaining])
    print(f"\n  Among sustaining draws only ({sustaining.sum()}):")
    print(f"  prop_f0 vs syph.prevalence_f@2016:  rho = {rho_f0s:+.3f}")
    print(f"  m1_conc vs syph.prevalence_f@2016:  rho = {rho_m1s:+.3f}")

# Point-biserial: do network params predict sustainability?
from scipy.stats import pointbiserialr
rpb_f0, p_f0 = pointbiserialr(sustaining, prop_f0)
rpb_m1, p_m1 = pointbiserialr(sustaining, m1_conc)
print(f"\n  Point-biserial (network param vs sustains?):")
print(f"  prop_f0:  r = {rpb_f0:+.3f}, p = {p_f0:.3f}")
print(f"  m1_conc:  r = {rpb_m1:+.3f}, p = {p_m1:.3f}")

# Average network params in sustaining vs extinct
print(f"\n  Mean prop_f0:  sustaining={prop_f0[sustaining].mean():.3f}  extinct={prop_f0[~sustaining].mean():.3f}")
print(f"  Mean m1_conc:  sustaining={m1_conc[sustaining].mean():.3f}  extinct={m1_conc[~sustaining].mean():.3f}")

# ---- 3. HIV rel_init_prev ----
print()
print("=" * 70)
print("3. HIV rel_init_prev — WHY NO IMPACT?")
print("=" * 70)

hiv_rip = np.array([d['hiv.rel_init_prev'] for d in draws])
hiv_beta = np.array([d['hiv.beta_m2f'] for d in draws])

# Check correlation with HIV prevalence at multiple time points
for year in [1990, 1995, 2000, 2005, 2010]:
    hiv_prev = np.array([df[df['time'] == year]['hiv.prevalence'].values[0] for df in dfs])
    rho_rip, _ = spearmanr(hiv_rip, hiv_prev)
    rho_beta, _ = spearmanr(hiv_beta, hiv_prev)
    print(f"  HIV prev @ {year}:  rho(rel_init_prev)={rho_rip:+.3f}  rho(beta)={rho_beta:+.3f}")

# Read the init prev data to understand the scale
print()
init_prev = pd.read_csv('data/init_prev_hiv.csv')
print("  init_prev_hiv.csv:")
print(init_prev.to_string(index=False))

print(f"\n  rel_init_prev range: [{hiv_rip.min():.2f}, {hiv_rip.max():.2f}]")
print(f"  Max init_prev in CSV: {init_prev['init_prev'].max():.3f}")
print(f"  Max init_prev * max rel_init_prev: {init_prev['init_prev'].max() * hiv_rip.max():.3f}")
print(f"  --> Does this exceed 1.0? Capping at 1.0 would flatten the effect.")

# Check early HIV dynamics: is the epidemic so fast that init_prev is irrelevant by 1990?
print()
print("  Early HIV prevalence by rel_init_prev quartile:")
q25, q75 = np.percentile(hiv_rip, [25, 75])
low_rip = hiv_rip < q25
high_rip = hiv_rip > q75
for year in [1988, 1990, 1995, 2000]:
    hiv_prev = np.array([df[df['time'] == year]['hiv.prevalence'].values[0] for df in dfs])
    print(f"  {year}: low quartile={hiv_prev[low_rip].mean():.4f}  high quartile={hiv_prev[high_rip].mean():.4f}  ratio={hiv_prev[high_rip].mean()/max(hiv_prev[low_rip].mean(), 1e-6):.2f}")
