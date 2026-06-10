# Baseline partner notification — design

## Why

Real-world Zimbabwe has some background partner notification happening: when
someone gets treated for an STI, a fraction of them inform partner(s); some
of those partners attend follow-up and get evaluated. The *intervention*
analysis question is: how much "unnecessary" partner treatment can be
avoided by definitive diagnosis of the index case? That comparison only
makes sense if the **baseline** model includes the background PN behavior.

## Where the code lives

- **stisim** — extend the existing `PartnerNotification` class with two
  optional kwargs (`notify_rates`, `attendance_rates`) that turn on per-
  edge-type / per-(edge-type, partner-sex) stratification. Default
  behavior unchanged when both are omitted. Branch `feat/baseline-pn`
  off `feat/syph-detectable-state`.
- **sti_notification** wires multiple instances of this extended class,
  one per care-seeking pathway, each routing attendees through existing
  syndromic management.

## Stratification

| edge type | p_notify | p_attends (F) | p_attends (M) |
|---|---:|---:|---:|
| **stable** (= marital) | 0.20 | 0.80 | 0.50 |
| **casual** | 0.10 | 0.50 | 0.25 |
| one-off, sw | 0.00 | — | — |

Per-edge draws (a partner reachable via multiple edges gets multiple
independent chances — happens rarely; matches the existing
PartnerNotification dedup semantics applied to the final attending set).

**Channel:** current partners only (no previous-channel for baseline).

## Three index pathways (sti_notification wiring)

Each pathway gets its own `StratifiedPartnerNotification` instance with the
rates above. All three share the same downstream behavior (attendees go
through `SyndromicMgmt` for their sex — symptom check + empirical tx).

1. **GUD → presumptive syph tx.** Index cases: anyone whose GUD-syndromic
   pathway treats them for syph this timestep. Includes both true syph
   primary stage and non-syph GUD (chancroid, HSV, etc.) — both get
   presumptive penicillin and may notify.

2. **ANC syph dx + tx.** Index cases: pregnant women who test positive
   at ANC and receive tx. RPR-positive (true) and false-positive both
   notify if they get treated.

3. **Discharge → syndromic NG/CT/TV/BV tx.** Index cases: anyone whose
   discharge-syndromic pathway treats them this timestep. The discharge
   algorithm is complex (uses the SyndromicMgmt class); all paths that
   end in treatment count as PN triggers.

All three pathways trigger the SAME edge-type / sex stratified rates.
The downstream is the same too — attendees go through syndromic mgmt,
get treated if they have visible STI symptoms.

## Extended `PartnerNotification` API

Two new optional kwargs:

```python
class PartnerNotification(ss.Intervention):
    """...existing docstring..."""

    def __init__(self, eligibility, test=None, pars=None,
                 notify_rates=None, attendance_rates=None, **kwargs):
        """
        notify_rates: optional dict {edge_name: probability}, e.g.
            {'stable': 0.20, 'casual': 0.10}. When provided, the
            current-channel uses per-edge-type rates instead of the flat
            p_notify_current; edges not in the dict get notify prob 0.
            Names must match network.edge_types keys.

        attendance_rates: optional dict
            {edge_name: {'f': prob, 'm': prob}}. Required if notify_rates
            given. Attendance is then per-(edge-type, partner-sex).

        When both are None (default), unchanged behavior — flat
        p_notify_current / p_attends_current per the existing API.
        """
```

Internal mechanics when stratification is on:
- One Bernoulli per `edge_name` (notify) and one per `(edge_name, sex)`
  (attend) — registered through `define_pars` for CRN safety
- `step()` reads the network's `edge_type` array along with `p1/p2`,
  groups partner UIDs by edge type, and applies the per-bucket draws
- A partner reachable via multiple edges gets multiple independent
  chances; the final attending set is deduplicated

### Algorithm

```
1. index_uids = eligibility(sim)
2. find all edges where one endpoint is in index_uids
3. for each edge: read (partner_uid, edge_type_int)
4. group by edge_type:
     for each named edge type:
         pn_dist = notify_rate_bernoulli[edge_name]
         notified = pn_dist.filter(partners_of_this_type)
         f_attend = attendance_f_bernoulli[edge_name].filter(notified ∩ females)
         m_attend = attendance_m_bernoulli[edge_name].filter(notified ∩ males)
5. attending = dedup(union of all attendees across edge types)
6. notify_attendees(attending)
```

### CRN-safety

Each named edge × sex needs its own registered Bernoulli (six total in our
case: `p_notify_stable`, `p_notify_casual`, `p_attends_stable_f`,
`p_attends_stable_m`, `p_attends_casual_f`, `p_attends_casual_m`). The
`__init__` builds them via `define_pars` so starsim's CRN bookkeeping
applies normally.

## Calibration drift check (before re-running full ensemble)

Before re-running all 375 sims, run a 1-config probe to estimate drift:

1. Pick draw 51 (the cleanest 6/9 from exp 34) and one of the median
   ensemble draws.
2. Run each with 3 seeds × {PN off, PN on} = 12 sims (~3 min).
3. Compare on FSW prev, nontrep_f, trep_f, primary share, HIV ratio.
4. If max-shift on any metric is < 5%, proceed with the full re-run.
5. If shift is 5-15%, document and proceed with the caveat.
6. If shift is > 15%, pause and discuss recalibration options.

## Bundled re-run plan

After the design is approved:

1. **stisim:** branch + implement `StratifiedPartnerNotification` + a quick
   unit test for the per-edge-type / per-sex draws.
2. **sti_notification:** wire 3 PN instances in `make_sim`; add
   `total_pop=16e6` fix; add `prevalence_15_49` to exp 37 extraction.
3. **Drift check** (12 sims, ~3 min).
4. **Full re-run** of exp 37 (375 sims, ~17 min).
5. **Re-plot** publication figures.

## Resolved decisions

- **Discharge-syndromic trigger:** PN fires on "received any
  discharge-syndromic tx this timestep" regardless of which drug(s).
- **ANC-syph timing:** notification happens at the same step as the ANC
  tx.
- **Congenital tx:** does NOT trigger PN (index is a neonate; not in
  scope).
