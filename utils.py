"""
Utils and defaults
"""
import sciris as sc
import numpy as np

# Define percentiles
percentile_pairs = [[.01, .99], [.1, .9], [.25, .75]]  # Order by wide to narrow (for alpha shading in plots)
percentiles = [percentile for percentile_pair in percentile_pairs for percentile in percentile_pair]

# Set scenarios and labels
scenlabels = {'treat50': 'Treat-half', 'treat80': 'Treat-most', 'treat100':'Treat-all'}
txscenarios = ['treat50poc', 'treat80poc', 'treat100poc']
txscenlabels = sc.mergedicts(scenlabels, {'treat50poc': 'Treat-half (POC)', 'treat80poc': 'Treat-most (POC)', 'treat100poc': 'Treat-all (POC)'})
treatments = ['ng_tx', 'ct_tx', 'metronidazole']
tx_labels = {'ng_tx':'NG', 'ct_tx':'CT', 'metronidazole':'MTNZ'}
scenarios = scenlabels.keys()

unneeded_results = [
    'pregnancy', 'deaths', 'structuredsexual', 'maternalnet', 'new_deaths', 'cum_deaths',
    'fsw_testing', 'other_testing', 'low_cd4_testing', 'art', 'vmmc', 'hivdx'
]

# Helper functions
def set_font(size=None, font='Libertinus Sans'):
    sc.fonts(add=sc.thisdir(aspath=True) / 'assets' / 'LibertinusSans-Regular.otf')
    sc.options(font=font, fontsize=size)
    return

def count(arr):
    return np.count_nonzero(arr)

def get_y(df, which, rname):
    if which == 'single': y = df[rname]
    elif which == 'multi': y = df[(rname, '50%')]
    return y

