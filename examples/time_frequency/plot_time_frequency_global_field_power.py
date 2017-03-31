"""
=============================================
Explore oscillatory activity in sensor space
=============================================

The objective is to show you how to explore spectrally localized
effects. For this purpose we adapt the method described in [1] and use it on
the somato dataset. The idea is to track the band-limited temporal evolution
of spatial patterns by using the Global Field Power (GFP).
We first bandpass filter the signals and then apply a Hilbert transform. To
reveal oscillatory activity the evoked response is then subtracted from every
single trial. Finally, we rectify the signals prior to averaging across trials
by taking the magniude of the Hilbert.
Then the GFP is computed as described in [2], using the sum of the squares
but without normalization by the rank.
Baselining is subsequently applied to make the GFPs comparable between
frequencies.
The procedure is then repeated for each frequency band of interest and
all GFPs are visualized. To estimate uncertainty, non-parametric confidence
intervals are computed as described in [3] across channels.
The advantage of this method over summarizing the Space x Time x Frequency
output of a Morlet Wavelet in frequency bands is relative speed and, more
importantly, the clear-cut comparability of the spectral decomposition (the
same type of filter is used across all bands).

References
----------
.. [1]_ Hari R. and Salmelin R. Human cortical oscillations: a neuromagnetic
        view through the skull (1997). Trends in Neuroscience 20 (1),
        pp. 44-49.
.. [2]_ Engemann D. and Gramfort A. (2015) Automated model selection in
        covariance estimation and spatial whitening of MEG and EEG signals,
        vol. 108, 328-342, NeuroImage.
.. [3]_ Efron B. and Hastie T. Computer Age Statistical Inference (2016).
        Cambrdige University Press, Chapter 11.2.
"""
# Authors: Denis A. Engemann <denis.engemann@gmail.com>
#
# License: BSD (3-clause)

import numpy as np
import matplotlib.pyplot as plt

import mne
from mne.datasets import somato

###############################################################################
# Set parameters
data_path = somato.data_path()
raw_fname = data_path + '/MEG/somato/sef_raw_sss.fif'

# let's explore some frequency bands
iter_freqs = [
    ('Theta', 4, 7),
    ('Alpha', 8, 12),
    ('Beta', 13, 25),
    ('Gamma', 30, 45)
]

###############################################################################
# We create average power time courses for each frequency band

# set epoching parameters
event_id, tmin, tmax = 1, -1., 3.
baseline = None

# get the header to extract events
raw = mne.io.read_raw_fif(raw_fname, preload=False)
events = mne.find_events(raw, stim_channel='STI 014')

frequency_map = list()

for band, fmin, fmax in iter_freqs:
    # (re)load the data to save memory
    raw = mne.io.read_raw_fif(raw_fname, preload=True)
    raw.pick_types(meg='grad', eog=True)  # we just look at gradiometers

    # bandpass filter and compute Hilbert
    raw.filter(fmin, fmax, n_jobs=1,  # use more jobs to speed up.
               l_trans_bandwidth=1,  # make sure filter params are the same
               h_trans_bandwidth=1)  # in each band and skip "auto" option.
    raw.apply_hilbert(n_jobs=1, envelope=False)

    epochs = mne.Epochs(raw, events, event_id, tmin, tmax, baseline=baseline,
                        reject=dict(grad=4000e-13, eog=350e-6), preload=True)
    # remove evoked response and get analytic signal (envelope)
    epochs.subtract_evoked()  # for this we need to construct new epochs.
    epochs = mne.EpochsArray(
        data=np.abs(epochs.get_data()), info=epochs.info, tmin=epochs.tmin)
    # now average and move on
    frequency_map.append(((band, fmin, fmax), epochs.average()))

###############################################################################
# Now we can compute the Global Field Power

# We first estimate the rank as this data is rank-reduced as SSS was applied.
# Therefore the degrees of freedom are less then the number of sensors.

rng = np.random.RandomState(42)

# Then we prepare a bootstrapping function to estimate confidence intervals


def get_gfp_ci(average, n_bootstraps=2000):
    """get confidence intervals from non-parametric bootstrap"""
    indices = np.arange(len(average.ch_names), dtype=int)
    gfps_bs = np.empty((n_bootstraps, len(average.times)))
    for iteration in range(n_bootstraps):
        bs_indices = rng.choice(indices, replace=True, size=len(indices))
        gfps_bs[iteration] = np.sum(average.data[bs_indices] ** 2, 0)
    gfps_bs = mne.baseline.rescale(gfps_bs, average.times, baseline=(None, 0))
    ci_low, ci_up = np.percentile(gfps_bs, (2.5, 97.5), axis=0)
    return ci_low, ci_up


# Now we can track the emergence of spatial patterns compared to baseline
# for each frequency band

# We see dominant responses in the Alpha and Beta bands.
fig, axes = plt.subplots(4, 1, figsize=(10, 7), sharex=True, sharey=True)
colors = plt.cm.viridis((0.1, 0.35, 0.75, 0.95))
for ((freq_name, fmin, fmax), average), color, ax in zip(
        frequency_map, colors, reversed(axes.ravel())):
    times = average.times * 1e3
    gfp = np.sum(average.data ** 2, 0)
    gfp = mne.baseline.rescale(gfp, times, baseline=(None, 0))
    ax.plot(times, gfp, label=freq_name, color=color, linewidth=2.5)
    ax.plot(times, np.zeros_like(times), linestyle='--', color='red',
            linewidth=1)
    ci_low, ci_up = get_gfp_ci(average)
    ax.fill_between(times, gfp + ci_up, gfp - ci_low, color=color,
                    alpha=0.3)
    ax.grid(True)
    ax.set_ylabel('GFP')
    ax.annotate('%s (%d-%dHz)' % (freq_name, fmin, fmax),
                xy=(0.95, 0.8),
                horizontalalignment='right',
                xycoords='axes fraction')
    ax.set_xlim(-1050, 3050)
axes.ravel()[-1].set_xlabel('Time [ms]')
