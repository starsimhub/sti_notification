"""Analyze exp 01 pilot results: per-arm mean + median, A vs B vs C
deltas, including per-disease prevalence + by-sex treatment coverage +
syph APO. Writes SUMMARY.md."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs'
RESULTS = OUT / 'results.jsonl'

ARM_ORDER = ['A_soc', 'B_poc_baseline', 'C1_poc_pn_1_5x',
             'C2_poc_pn_2x', 'C3_poc_pn_3x', 'D_poc_pn_3x_fsw_out',
             'E1_d_careseek_1_5x', 'E2_d_careseek_2x', 'E3_d_careseek_3x']
ARM_SHORT = {
    'A_soc':               'A',
    'B_poc_baseline':      'B',
    'C1_poc_pn_1_5x':      'C1',
    'C2_poc_pn_2x':        'C2',
    'C3_poc_pn_3x':        'C3',
    'D_poc_pn_3x_fsw_out': 'D',
    'E1_d_careseek_1_5x':  'E1',
    'E2_d_careseek_2x':    'E2',
    'E3_d_careseek_3x':    'E3',
}
ARM_LABEL = {
    'A_soc':               'A: SOC (syndromic)',
    'B_poc_baseline':      'B: POC, baseline PN',
    'C1_poc_pn_1_5x':      'C1: POC, PN 1.5×',
    'C2_poc_pn_2x':        'C2: POC, PN 2×',
    'C3_poc_pn_3x':        'C3: POC, PN 3×',
    'D_poc_pn_3x_fsw_out': 'D: C3 + FSW outreach (~70%/yr)',
    'E1_d_careseek_1_5x':  'E1: D + care-seeking ×1.5',
    'E2_d_careseek_2x':    'E2: D + care-seeking ×2',
    'E3_d_careseek_3x':    'E3: D + care-seeking ×3 (ceiling)',
}

DISEASES = ['syph', 'ng', 'ct', 'tv', 'bv']


def load():
    rows = []
    with RESULTS.open() as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    df = pd.DataFrame(rows)
    print(f'Loaded {len(df)} rows from {RESULTS}')
    if 'status' in df.columns:
        ok = df['status'] == 'ok'
        n_err = (~ok).sum()
        if n_err:
            print(f'  WARN: {n_err} error rows excluded')
        df = df[ok].copy()
    return df


def fmt_count(v, scale='M'):
    if pd.isna(v):
        return 'NA'
    if scale == 'M':
        return f'{v/1e6:.2f}M'
    if scale == 'K':
        return f'{v/1e3:.1f}K'
    return f'{v:.0f}'


def fmt_pct_change(x):
    if pd.isna(x):
        return 'NA'
    sign = '+' if x >= 0 else ''
    return f'{sign}{100*x:.0f}%'


def fmt_pct(x):
    if pd.isna(x):
        return 'NA'
    return f'{100*x:.1f}%'


def arm_mean(df, arm, col):
    sub = df[df['arm'] == arm]
    if col not in sub.columns:
        return float('nan')
    return float(sub[col].astype(float).mean())


def write_summary(df, arms):
    n_draws = df['draw_idx'].nunique()
    n_seeds = df.groupby(['arm', 'draw_idx']).size().min()
    md = []
    md.append('# Exp 01 pilot — SUMMARY (v2: NG-fix + expanded endpoints)')
    md.append('')
    md.append(f'**Scale.** {n_draws} draws × {n_seeds} seeds × {len(arms)} arms = {len(df)} sims.')
    md.append('Counts over 2027-2040, scaled to Zimbabwe population (~8.7M). All "M" '
              'values are millions of events/infections; "K" is thousands.')
    md.append('')

    # =========== Section: Headline ============
    md.append('## Headline')
    md.append('')
    md.append('**Demand generation is the dominant lever for NG/CT/TV.** '
              'PN intensity (B→C3) and FSW outreach (D) together produce '
              'modest impact (~10% relative reduction in NG/CT/TV prev vs '
              'POC baseline). Symptomatic-care-seeking ×2 (E2) more than '
              'triples that gain. The E arms (`E1_d_careseek_1_5x`, '
              '`E2_d_careseek_2x`, `E3_d_careseek_3x`) stack a care-seeking '
              'multiplier on the full D intervention package; ×3 is a '
              'clipped ceiling (all rates except TV M saturate at 1.0). '
              'Syph and BV are unaffected: syph care-seeking is governed '
              'by `symp_test_prob.csv`, not the NG/CT/TV `p_symp_care` '
              'lever; BV is in a stable equilibrium at ~40% prev.')
    md.append('')
    md.append('Arms (all start from the calibrated baseline; intv_year=2027):')
    md.append('')
    md.append('  - **A** SOC: syndromic NG/CT/TV + syndromic syph + baseline PN.')
    md.append('  - **B** POC: POC etiological NG/CT/TV + POC syph (gud2) + baseline PN.')
    md.append('  - **C1/C2/C3** POC + PN 1.5/2/3× baseline rates.')
    md.append('  - **D** C3 + direct FSW NG/CT/TV outreach (~70%/yr reach).')
    md.append('  - **E1/E2/E3** D + symptomatic care-seeking ×1.5/2/3 '
              '(applied equally to F and M, clipped to 1.0).')
    md.append('')
    md.append('Wiring check on the symptomatic→PN pipeline (run before E '
              'arms were added): symptomatic NG men → `syndromic_uds` (90% '
              'presumptive NG tx under SOC) or `POCPanel` (95% sens under '
              'POC) → PN index pool → notify partners → female partners '
              'routed through `syndromic_vds` (SOC) or `POCPanel` (POC). '
              'Bounded by symptomatic care-seeking (~54% of NG men ever '
              'caught at care = 65% symp × 83% care), PN attendance (stable '
              'F 80%, casual M 25% at baseline), and asymptomatic '
              'transmission chains via the FSW reservoir.')
    md.append('')
    md.append('Endpoints added this iteration:')
    md.append('  - **BV prevalence + counts** (`sim.results.bv`). Surfaced '
              'because BV is the dominant cause of VDS-like presentations '
              '(~40% prev in women, equilibrium) and drives unnecessary '
              'syndromic NG/CT/TV treatment under SOC.')
    md.append('  - **Wasted PN attendance**: PN attendees who had no '
              'current STI (NG/CT/TV/syph all negative at attendance). '
              'BV is excluded — not sexually transmitted, so PN triggered '
              'by BV-driven over-treatment is wasted by definition. '
              'Counts the clinic-time and partner-relationship cost of '
              'false-alarm PN.')
    md.append('')
    md.append('Effects (A baseline → C3 dx+PN → D adds FSW outreach → E2 adds 2× care-seeking):')

    # NG/CT/TV prev impact across the four-step ladder
    for d in ('ng', 'ct', 'tv'):
        vals = {a: arm_mean(df, k, f'{d}_prevalence_end')
                for a, k in (('A','A_soc'), ('C3','C3_poc_pn_3x'),
                             ('D','D_poc_pn_3x_fsw_out'),
                             ('E2','E2_d_careseek_2x'))}
        if all(np.isfinite(list(vals.values()))):
            parts = ' → '.join(f'{fmt_pct(v)} ({k})' for k, v in vals.items())
            rel_e2_vs_a = vals['E2']/vals['A'] - 1 if vals['A'] else float('nan')
            md.append(f'  - **{d.upper()} point-prevalence at 2040:** '
                      f'{parts}. E2 vs A: '
                      f'{fmt_pct_change(rel_e2_vs_a)} relative.')

    a_pev = arm_mean(df, 'A_soc', 'syph_sti_prev_end')
    b_pev = arm_mean(df, 'B_poc_baseline', 'syph_sti_prev_end')
    c3_pev = arm_mean(df, 'C3_poc_pn_3x', 'syph_sti_prev_end')
    d_pev = arm_mean(df, 'D_poc_pn_3x_fsw_out', 'syph_sti_prev_end')
    if all(np.isfinite([a_pev, b_pev, c3_pev, d_pev])):
        md.append(f'  - **Syph sexually-transmissible prevalence at 2040** '
                  f'(primary + secondary + early latent — WHO early '
                  f'infectious syphilis): {fmt_pct(a_pev)} (A) → '
                  f'{fmt_pct(b_pev)} (B) → {fmt_pct(c3_pev)} (C3) → '
                  f'{fmt_pct(d_pev)} (D). Total syph prev not reported — '
                  f'the calibration ensemble overshoots total syph prev '
                  f'(latent/tertiary), so the policy-relevant slice is '
                  f'the sexually-transmissible fraction.')

    a_su = arm_mean(df, 'A_soc', 'syph_tx_unnec_2027_2040')
    b_su = arm_mean(df, 'B_poc_baseline', 'syph_tx_unnec_2027_2040')
    if all(np.isfinite([a_su, b_su])) and a_su > 0:
        md.append(f'  - **Unnecessary syph treatments A→B:** '
                  f'{a_su/1e6:.2f}M → {b_su/1e6:.2f}M '
                  f'({fmt_pct_change(b_su/a_su - 1)}) — POC dx specificity '
                  f'win still clean.')

    # BV prevalence — same across all arms (BV is in equilibrium; not
    # touched by NG/CT/TV interventions). Report from arm A as baseline.
    a_bv = arm_mean(df, 'A_soc', 'bv_prevalence_end')
    if np.isfinite(a_bv):
        md.append(f'  - **BV prevalence at 2040 (all arms):** '
                  f'~{fmt_pct(a_bv)}. BV is the dominant cause of VDS '
                  f'presentations — most women presenting with VDS-like '
                  f'symptoms in this model have BV, not NG/CT/TV. Under '
                  f'SOC syndromic management they get presumptively treated '
                  f'for NG/CT/TV and become PN indices.')

    # False-alarm-index PN: A is 10x worse than B because syndromic
    # over-treats most VDS presenters as NG/CT/TV when they actually
    # have BV-only. POC dx eliminates almost all of that.
    for arm, short in (('A_soc', 'A'), ('B_poc_baseline', 'B'),
                       ('C3_poc_pn_3x', 'C3'), ('D_poc_pn_3x_fsw_out', 'D'),
                       ('E2_d_careseek_2x', 'E2')):
        idx = arm_mean(df, arm, 'pn_index_no_sti_2027_2040')
        if np.isfinite(idx):
            md.append(f'  - **PN false-alarm indices ({short}):** '
                      f'{idx/1e6:.2f}M agents triggered PN despite having '
                      f'NO actual STI at the moment of treatment.')
    # Wasted PN attendance: per-attendee metric (paired with notifs/attends)
    a_att = arm_mean(df, 'A_soc', 'pn_attending_2027_2040')
    a_wasted = arm_mean(df, 'A_soc', 'pn_attended_no_sti_2027_2040')
    e3_att = arm_mean(df, 'E3_d_careseek_3x', 'pn_attending_2027_2040')
    e3_wasted = arm_mean(df, 'E3_d_careseek_3x', 'pn_attended_no_sti_2027_2040')
    if all(np.isfinite([a_att, a_wasted, e3_att, e3_wasted])) and a_att > 0:
        md.append(f'  - **Wasted PN attendance:** {a_wasted/1e6:.2f}M / '
                  f'{a_att/1e6:.2f}M ({fmt_pct(a_wasted/a_att)}) in A vs '
                  f'{e3_wasted/1e6:.2f}M / {e3_att/1e6:.2f}M '
                  f'({fmt_pct(e3_wasted/e3_att)}) in E3. Scaling PN volume '
                  f'reaches further into casual partnerships with lower '
                  f'STI co-prev → wasted-fraction creeps up.')

    # Strict 3-month cure rate vs lax event-ratio — the lax metric
    # overstated coverage because it counted re-infections and treatments
    # of pre-window infections. Highlight the gap.
    md.append('')
    md.append('Per-episode "treated within 3 months of acquisition" metric '
              '(`CareTimingAnalyzer`): much stricter than the lax '
              '`tx_success/new_inf` event-ratio (which double-counts '
              're-infections + pre-window cures). Compare A vs E3:')
    for d in ('ng', 'ct', 'tv', 'syph'):
        lax_a = arm_mean(df, 'A_soc', f'{d}_prop_treated')
        strict_a = arm_mean(df, 'A_soc', f'{d}_prop_cured_3mo')
        lax_e3 = arm_mean(df, 'E3_d_careseek_3x', f'{d}_prop_treated')
        strict_e3 = arm_mean(df, 'E3_d_careseek_3x', f'{d}_prop_cured_3mo')
        if all(np.isfinite([lax_a, strict_a, lax_e3, strict_e3])):
            md.append(f'  - **{d.upper()}:** A lax {fmt_pct(lax_a)} → '
                      f'strict {fmt_pct(strict_a)} ; E3 lax '
                      f'{fmt_pct(lax_e3)} → strict {fmt_pct(strict_e3)}.')

    md.append('')
    md.append('**Syph APO:** stisim\'s `new_congenital` ~33-36K cases per '
              'arm; `new_nnds` and `new_stillborns` are placeholder fields '
              'never written without FetalHealth wiring.')
    md.append('')

    # =========== Section: Per-disease infection + treatment ============
    md.append('## Per-disease summary, by arm')
    md.append('')
    md.append('Mean over draws+seeds. All counts in millions over 2027-2040.')
    md.append('`prop_treated` = `tx_success / new_inf` is the share of new '
              'infections that ended up cleared by a treatment. `prev_end` is '
              'point-prevalence at sim end (2040).')
    md.append('')
    for disease in DISEASES:
        md.append(f'### {disease.upper()}')
        header = '| Metric | ' + ' | '.join(ARM_SHORT[a] for a in arms) + ' |'
        sep    = '|' + '|'.join(['---'] * (len(arms) + 1)) + '|'
        md.append(header)
        md.append(sep)
        # For syph, report sexually_transmissible_prevalence
        # (primary + secondary + early latent, matches WHO 'early
        # infectious syphilis') instead of total prev (the latter
        # includes late latent + tertiary and is not on calibration
        # target).
        if disease == 'syph':
            prev_col   = 'syph_sti_prev_end'
            prev_label = 'Sexually transmissible prev (point, 2040)'
        else:
            prev_col   = f'{disease}_prevalence_end'
            prev_label = 'Prevalence (point, 2040)'
        for col, label, scale in [
            (f'{disease}_new_inf_2027_2040',  'New infections',          'M'),
            (f'{disease}_new_inf_f_2027_2040','  new inf — F',           'M'),
            (f'{disease}_new_inf_m_2027_2040','  new inf — M',           'M'),
            (f'{disease}_tx_total_2027_2040', 'Treatments — total',      'M'),
            (f'{disease}_tx_success_2027_2040', '  successful',          'M'),
            (f'{disease}_tx_unnec_2027_2040', '  unnecessary',           'M'),
            (f'{disease}_n_infected_end',     'n_infected (point, 2040)','K'),
            (prev_col,                        prev_label,                'prev'),
            (f'{disease}_prop_treated',       'Prop new inf treated (event-ratio, lax)','prev'),
            (f'{disease}_prop_treated_f',     '  — F',                   'prev'),
            (f'{disease}_prop_treated_m',     '  — M',                   'prev'),
            (f'{disease}_prop_cured_3mo',     'Prop new inf cured w/in 3mo (per-episode, strict)','prev'),
        ]:
            cells = [label]
            for a in arms:
                v = arm_mean(df, a, col)
                if scale == 'prev':
                    cells.append(fmt_pct(v))
                else:
                    cells.append(fmt_count(v, scale=scale))
            md.append('| ' + ' | '.join(cells) + ' |')
        md.append('')

    # =========== Section: Syph APO ============
    md.append('## Syph APO/ABO')
    md.append('')
    md.append('Native syph module results, summed over 2027-2040.')
    md.append('')
    header = '| Metric | ' + ' | '.join(ARM_SHORT[a] for a in arms) + ' |'
    sep    = '|' + '|'.join(['---'] * (len(arms) + 1)) + '|'
    md.append(header)
    md.append(sep)
    for col, label, scale in [
        ('syph_new_congenital_2027_2040',         'Congenital syph cases',      'K'),
        ('syph_new_congenital_deaths_2027_2040',  'Congenital deaths (=NND+stillborn)','K'),
        ('syph_new_nnds_2027_2040',               'Neonatal deaths (NND)*',     'K'),
        ('syph_new_stillborns_2027_2040',         'Stillbirths*',               'K'),
    ]:
        cells = [label]
        for a in arms:
            v = arm_mean(df, a, col)
            cells.append(fmt_count(v, scale=scale))
        md.append('| ' + ' | '.join(cells) + ' |')
    md.append('')
    md.append('*\\* NND/stillborn rely on `FetalHealth` to fire ti_nnd / '
              'ti_stillborn. Without FetalHealth wired (this pilot), those '
              'are 0 across all arms.*')
    md.append('')

    # =========== Section: HIV + PN cascade ============
    md.append('## HIV + partner notification')
    md.append('')
    header = '| Metric | ' + ' | '.join(ARM_SHORT[a] for a in arms) + ' |'
    sep    = '|' + '|'.join(['---'] * (len(arms) + 1)) + '|'
    md.append(header)
    md.append(sep)
    for col, label, scale in [
        ('hiv_new_inf_2027_2040',          'HIV new infections',  'M'),
        ('pn_notified_2027_2040',          'PN partners notified','M'),
        ('pn_attending_2027_2040',         'PN partners attending','M'),
        ('pn_attended_no_sti_2027_2040',   '  of which attendee had no STI (wasted attendance)','M'),
        ('pn_index_no_sti_2027_2040',      '  PN indices over-treated (no STI at moment of tx)','M'),
    ]:
        cells = [label]
        for a in arms:
            v = arm_mean(df, a, col)
            cells.append(fmt_count(v, scale=scale))
        md.append('| ' + ' | '.join(cells) + ' |')
    md.append('')

    # =========== Section: notes ============
    md.append('## Notes')
    md.append('')
    md.append('- **NG fix:** stisim ships `GonorrheaTreatment` with an AMR '
              'tracking state `rel_treat` declared `FloatArr(default=1)`, '
              'but starsim does not apply the default to `.raw`. Every '
              'agent\'s rel_treat sits at NaN, so '
              '`new_treat_eff = NaN * base_treat_eff = NaN` and the '
              '`treat_eff` bernoulli always rejects — 0% NG cures. '
              'Worked around locally by treating NaN as the documented '
              'default (1.0) in `GonorrheaTreatmentFixed.set_treat_eff`. '
              'Calibration baseline (with the bug) treated NG as effectively '
              'no-treatment, so NG prevalence in those calibrated draws is '
              'an over-estimate; the bug-fixed dynamics drive NG down across '
              'all arms.')
    md.append('- **`prop_treated` (event-ratio, lax)** can exceed 100% in '
              'the regime where the same agent gets infected and '
              'successfully treated more than once over 2027-2040. It is '
              'best read as a treatment-volume-per-infection ratio, not a '
              'literal patient coverage rate. Reported alongside '
              '`prop_cured_3mo` (per-episode, strict) which counts per-'
              'episode "newly infected at T0 and successfully treated '
              'within 3 months of T0" — implemented via the '
              '`CareTimingAnalyzer` in analyzers.py.')
    md.append('- **PN false-alarm index** is computed inside '
              '`PartnerNotificationNoCycle.step` by reading `tx.outcomes` '
              'across NG/CT/TV/syph treatments: an index UID is "false '
              'alarm" if it appears in `outcomes[d].unnecessary` for at '
              'least one STI AND does NOT appear in '
              '`outcomes[d].(successful|unsuccessful)` for any STI. BV is '
              'excluded — BV-only over-treatment that gets correctly '
              'caught by metronidazole still triggers PN, and that PN is '
              'false-alarm.')
    md.append('- **PN cascade**: still tracks anyone-treated-this-step as '
              'index pool, not stratified by which STI triggered treatment. '
              'Splitting PN by disease (which STI drove the index case) and '
              'by sex (M vs F index / attendee) requires bookkeeping inside '
              '`POCPN.notify_attendees` — TODO.')
    md.append('- **FetalHealth wiring** still off. Native syph module gives '
              '`new_congenital`; NND + stillborn require FetalHealth + '
              '`sti_fetal` connector. Numbers above let us decide whether '
              'to enable.')

    summary_path = HERE / 'SUMMARY.md'
    summary_path.write_text('\n'.join(md))
    print(f'\nWrote {summary_path}')

    # Also print to stdout
    print('\n' + '\n'.join(md))


def main():
    if not RESULTS.exists():
        print(f'No {RESULTS} found.', file=sys.stderr)
        sys.exit(1)
    df = load()
    arms = [a for a in ARM_ORDER if a in df['arm'].unique()]
    print(f'Arms: {arms}')
    write_summary(df, arms)


if __name__ == '__main__':
    main()
