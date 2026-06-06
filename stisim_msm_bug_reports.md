# stisim MSM module — bug reports

Four blocking/silent issues + one minor doc issue, surfaced while
trying to add a 0.5% MSM network to the Zimbabwe heterosexual +
sex-work model for a sustainability sensitivity check. All three MSM
variants in `stisim/networks/msm.py` failed in different ways for a
standard "small MSM share, plug into existing MF network" use case;
and even after working around the network-side bugs, the disease side
silently zeroed out MSM transmission.

stisim commit: `7c2feb8` (branch `feat/syph-detectable-state`).

---

## Bug 1 — `AgeApproxMSM` does not accept `msm_share`

**Severity:** blocking.

**Repro:**

```python
import starsim as ss
import stisim as sti
msm = sti.AgeApproxMSM(msm_share=ss.bernoulli(p=0.005))
# ValueError: 1 unrecognized arguments for msm: msm_share
```

**Root cause:** `AgeApproxMSM.__init__` forwards `**kwargs` directly
to `MFNetwork.__init__`, which doesn't define `msm_share`. Only
`AgeMatchedMSM.__init__` calls `self.define_pars(msm_share=...)`.

```python
# AgeMatchedMSM (works):
def __init__(self, pars=None, **kwargs):
    super().__init__(name='msm')
    self.define_pars(msm_share=ss.bernoulli(p=0.015))
    self.update_pars(pars=pars, **kwargs)

# AgeApproxMSM (broken):
def __init__(self, **kwargs):
    super().__init__(name='msm', **kwargs)  # no msm_share defined here
```

**Expected:** API consistency between the two MSM variants. If
`msm_share` is the canonical knob on `AgeMatchedMSM` it should also
be available on `AgeApproxMSM`.

**Fix sketch:** Mirror `AgeMatchedMSM`'s init in `AgeApproxMSM`:

```python
def __init__(self, pars=None, **kwargs):
    super().__init__(name='msm')
    self.define_pars(msm_share=ss.bernoulli(p=0.015))
    self.update_pars(pars=pars, **kwargs)
```

And add a `set_msm` method (copying `AgeMatchedMSM.set_msm`) so the
participant filter is applied at init.

---

## Bug 2 — `AgeMatchedMSM` crashes at sim init with NaN in age-difference preferences

**Severity:** blocking.

**Repro:**

```python
msm = sti.AgeMatchedMSM(msm_share=ss.bernoulli(p=0.005))
sim.pars.networks.append(msm)
sim.init()
sim.run()
# ValueError: Invalid entries for age difference preferences.
# Raised from stisim/networks/mf.py:163
```

**Root cause:** `AgeMatchedMSM` extends `MFNetwork`, which initialises
F–M age-difference preference (`age_diff_pars`) tables in
`get_age_risk_pars` ([mf.py:140-165](/home/robyn/stisim/stisim/networks/mf.py#L140-L165)).
The default `age_diff_pars` table is keyed by `(sex_of_p1, risk_group_p1, risk_group_p2)`
or similar F–M risk-group combinations. With a male-only pool the
female-side entries are NaN, the check at line 162–164 fires:

```python
if np.isnan(scale).any() or np.isnan(loc).any():
    errormsg = 'Invalid entries for age difference preferences.'
    raise ValueError(errormsg)
```

**Expected:** MSM matching should not require F–M age difference
preferences. `AgeMatchedMSM.match_pairs` sorts males by age (line 66-72)
and never consults `age_diffs` — but the inherited init still does.

**Fix sketch (one of):**
- Override `set_network_states` in `AgeMatchedMSM` to skip the F–M
  age-diff init for MSM-only networks.
- Or initialise the M-M entries of `age_diff_pars` to safe defaults
  (`loc=0.0, scale=2.0`) inside `AgeMatchedMSM.__init__`.

---

## Bug 3 — `MSMScaleFreeNetwork` has no participation filter; defaults to 100% of post-debut males

**Severity:** blocking for realistic-share use.

**Repro:**

```python
msm = sti.MSMScaleFreeNetwork(target_mean_degree=5.0)
sim.pars.networks.append(msm)
# Runs, but every post-debut male is now in the MSM pool — not a
# realistic MSM-population share.
```

**Root cause:** `MSMScaleFreeNetwork._get_pool` ([msm.py:170-173](/home/robyn/stisim/stisim/networks/msm.py#L170-L173))
returns `over_debut & male` with no participant filter:

```python
def _get_pool(self):
    """Eligible agents the kernel operates on. Default: post-debut males."""
    return self.over_debut & self.sim.people.male
```

`AgeMatchedMSM` uses `msm_share` and `set_msm` to flip `self.participant`
off for non-MSM males; `MSMScaleFreeNetwork` does neither. Result: a
sim with 50/50 sex ratio and `n_agents=10_000` puts ~5000 males in
the MSM network, regardless of intended share.

**Expected:** consistent API with `AgeMatchedMSM`. A `msm_share`
parameter (or similar) that controls the fraction of males flagged
as MSM participants.

**Fix sketch:**

```python
class MSMScaleFreeNetwork(BaseNetwork):
    def __init__(self, pars=None, name=None, **kwargs):
        super().__init__(name=name)
        self.define_pars(
            msm_share=ss.bernoulli(p=0.015),  # match AgeMatchedMSM default
            target_mean_degree=2.0,
            target_mean_dur=ss.years(2),
            max_edge_dur=ss.years(10),
            phi=1.0,
        )
        self.update_pars(pars, **kwargs)
        ...

    def set_network_states(self, upper_age=None):
        super().set_network_states(upper_age=upper_age)
        # Flip participant off for non-MSM males + all females.
        ppl = self.sim.people
        m_uids = ppl.male.uids
        self.participant[m_uids] = self.pars.msm_share.rvs(m_uids)
        self.participant[(~ppl.male).uids] = False

    def _get_pool(self):
        return self.over_debut & self.sim.people.male & self.participant
```

Verified workaround (currently used as a local subclass in
`/tmp/msm_sustainability_check.py`):

```python
class ScaleFreeMSMShare(sti.MSMScaleFreeNetwork):
    def __init__(self, msm_share=0.005, **kwargs):
        super().__init__(**kwargs)
        self._msm_share = float(msm_share)

    def init_post(self):
        ppl = self.sim.people
        rng = np.random.default_rng(int(self.sim.pars.rand_seed) + 7001)
        m_uids = ppl.male.uids
        if len(m_uids) > 0:
            keep = rng.random(len(m_uids)) < self._msm_share
            self.participant[m_uids[~keep]] = False
        f_uids = (~ppl.male).uids
        if len(f_uids) > 0:
            self.participant[f_uids] = False
        super().init_post()

    def _get_pool(self):
        return self.over_debut & self.sim.people.male & self.participant
```

---

## Bug 4 — `Syphilis.pars.beta_m2m` defaults to `None`, causing silent zero MSM transmission

**Severity:** silent footgun. **Highest impact** because there is no error
message — the MSM network simply has no effect on syphilis dynamics, which
looks like a "no signal" finding rather than a configuration bug.

**Repro (first version of our scratch):**

```python
# Add MSM network with non-zero edges and reasonable parameters.
msm = ScaleFreeMSMShare(msm_share=0.005, target_mean_degree=5.0,
                        target_mean_dur=ss.years(0.5), name='msm')
sim.pars.networks.append(msm)
# DO NOT explicitly set syph.pars.beta_m2m.
sim.run()
# Result: MSM and no-MSM runs produce IDENTICAL syph trajectories across 3
# parameter draws (extinct, marginal, healthy) — sero/detect/prev all match
# to 4 decimal places. No error, no warning.
```

**Root cause:** [stisim/diseases/sti.py:39](/home/robyn/stisim/stisim/diseases/sti.py#L39)
defines `self.beta_m2m = None` as the default. The override in
[sti.py:210-212](/home/robyn/stisim/stisim/diseases/sti.py#L210-L212) only
copies `beta_m2m` into the MSM betamap entry if it's not None:

```python
if self.pars.beta_m2m is not None and 'msm' in betamap:
    betamap['msm'][0] = self.pars.beta_m2m
    betamap['msm'][1] = self.pars.beta_m2m
```

Otherwise the parent `validate_beta` in
[starsim/diseases.py:191](/home/robyn/starsim/starsim/diseases.py#L191) falls
back to the scalar default `pars.beta = 0` (set in
[stisim/diseases/sti.py:34](/home/robyn/stisim/stisim/diseases/sti.py#L34)),
which is bidirectionally applied to MSM edges. Net effect: MSM beta = 0,
no transmission, no warning.

**Expected:** when a user adds an MSM network, either:
- The disease should warn loudly that `beta_m2m` is unset and MSM
  transmission will be zero;
- Or `beta_m2m` should default to something sensible like `beta_m2f`
  (with a docstring note that this is a placeholder).

For syphilis specifically, receptive anal sex is well-documented to have
higher per-act transmission probability than vaginal — a sensible default
would be `beta_m2m = beta_m2f * receptive_anal_multiplier`, where the
multiplier is a separate parameter with a literature-anchored prior.

**Fix sketch — minimal version:**

```python
# stisim/diseases/sti.py validate_beta()
if 'msm' in betamap:
    if self.pars.beta_m2m is None:
        ss.warn(f'{self.name}: msm network present but beta_m2m is None; '
                f'falling back to beta_m2f. Set syph.pars.beta_m2m explicitly '
                f'to silence this warning.')
        if self.pars.beta_m2f is not None:
            betamap['msm'][0] = self.pars.beta_m2f
            betamap['msm'][1] = self.pars.beta_m2f
    else:
        betamap['msm'][0] = self.pars.beta_m2m
        betamap['msm'][1] = self.pars.beta_m2m
```

**Why this is the worst of the four bugs:** bugs 1–3 fail with clear
errors at init or run time. Bug 4 produces a clean-looking simulation
with no signal that anything is wrong — researcher concludes "MSM has no
effect at 0.5% share" when in fact MSM had no opportunity to have an
effect. Caught in this case only by checking the source after the
all-zero deltas raised suspicion.

---

## Bug 5 (minor) — Docstring inaccuracy

Both `AgeMatchedMSM` and `AgeApproxMSM` docstrings say *"Extends
`StructuredSexual` for MSM partnerships"* but they actually extend
`MFNetwork`. The module docstring at the top of `msm.py` has the
correct lineage. Worth fixing for consistency.

---

## Summary

The three MSM variants have inconsistent APIs:

| Variant | `msm_share` param | Participation filter at init | Works as-is on small share? |
|---|---|---|---|
| `AgeMatchedMSM` | yes | yes (via `set_msm`) | no — crashes on F-M age-diff init (bug 2) |
| `AgeApproxMSM` | no (bug 1) | no | no — `msm_share` rejected |
| `MSMScaleFreeNetwork` | no (bug 3) | no | no — defaults to 100% of males |

The combined effect is that no MSM variant can be used out-of-the-box
to add a small (~0.5–5%) MSM subpopulation to an existing MF network
without subclassing or patching. Given MSM is a typical layered-network
use case for STI work, harmonising the three APIs around the
`AgeMatchedMSM` pattern (msm_share param + participant filter applied
at init) would close bugs 1–3.

And even after closing those — bug 4 (silent zero `beta_m2m`) will
still bite anyone who adds an MSM network without explicitly setting
the disease's `beta_m2m` parameter. The disease-side default needs to
either warn or fall back to `beta_m2f`.
