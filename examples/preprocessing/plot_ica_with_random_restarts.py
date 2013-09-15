"""
==================================
Compute ICA components on raw data
==================================

ICA is used to decompose raw data in 49 to 50 sources.
The source matching the ECG is found automatically
and displayed. Subsequently, the cleaned data is compared
with the uncleaned data. The last section shows how to export
the sources into a fiff file for further processing and displaying, e.g.
using mne_browse_raw.

"""
print __doc__

# Authors: Denis Engemann <d.engemann@fz-juelich.de>
#
# License: BSD (3-clause)

import numpy as np

import mne
from mne.fiff import Raw
from mne.preprocessing import ICA
from mne.preprocessing import ica_with_restarts
from ctps import compute_ctps, plot_ctps_panel
from mne.datasets import sample

###############################################################################
# Setup paths and prepare raw data

data_path = sample.data_path()
raw_fname = data_path + '/MEG/sample/sample_audvis_filt-0-40_raw.fif'

raw = Raw(raw_fname, preload=True)

picks = mne.fiff.pick_types(raw.info, meg=True, eeg=False, eog=False,
                            stim=False, exclude='bads')

###############################################################################
# Setup ICA seed decompose data, then access and plot sources.
ica = ICA(n_components=50, max_pca_components=50, random_state=None)
icas = ica_with_restarts(ica, raw, picks=picks, randint=100, n_restarts=5,
                         decim=3, n_jobs=2)

for ii, this_ica in enumerate(icas):
    ecg_scores = this_ica.find_sources_raw(raw, target='MEG 1531',
                                           score_func='pearsonr')
    ecg_source_idx = np.abs(ecg_scores) > .1
    title = 'ECG sources | ICA #%i' % ii
    this_ica.plot_sources_raw(raw, ecg_source_idx, title=title, stop=3.0)
