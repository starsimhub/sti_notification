"""Quick trajectory figure for exp 31."""
import pickle
from pathlib import Path
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
s = pickle.load(open(HERE / 'outputs' / 'series.pkl', 'rb'))
fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharex=True)
for seed, srs in s.items():
    yrs = srs['years']
    axes[0].plot(yrs, srs['fsw_prev'], label=f'seed {seed}', alpha=0.8)
    axes[1].plot(yrs, srs['nontrep_f'], alpha=0.8)
    axes[2].plot(yrs, srs['trep_f'], alpha=0.8)
axes[0].axhspan(0.20, 0.40, color='C2', alpha=0.2)
axes[1].axhspan(0.01, 0.03, color='C2', alpha=0.2)
axes[2].axhspan(0.05, 0.10, color='C2', alpha=0.2)
for ax, t in zip(axes, ['FSW prev', 'nontrep_f', 'trep_f']):
    ax.set_xlabel('year'); ax.set_title(t); ax.set_xlim(1985, 2040)
axes[0].legend(fontsize=8)
fig.suptitle('Exp 31 — draw 74 + rel_trans_primary=4 + half-life=1.2y: hotter than draw 74, FSW above band')
fig.tight_layout()
fig.savefig(HERE / 'figures' / 'trajectories.png', dpi=130)
print('wrote figures/trajectories.png')
