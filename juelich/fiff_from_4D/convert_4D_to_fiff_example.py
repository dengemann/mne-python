#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>
#
#         simplified bsd-3 license

import mne
from fiff_handler import RawFrom4D
from mne.fiff import Raw
from ConfigParser import ConfigParser

hdr_4D = 'mydata.hdr'

parser = ConfigParser()
parser.read(hdr_4D)

raw = RawFrom4D(hdr_4D)

events = mne.find_events(raw)

picks = mne.fiff.pick_types(raw.info, meg=True, stim=False, ecg=True, eog=True, exclude=raw.info['ch_names'][248:271] + ['UCA 001'])

event_id = 999
ev = mne.merge_events(events, [53, 73, 55, 75, 54, 74, 56, 76], event_id)

epochs = mne.Epochs(raw, ev, event_id, tmin=-0.200, tmax=.600, picks=picks,
                    baseline=(None, 0), reject=None)

data = epochs.get_data()  # as 3D matrix
evoked = epochs.average()  # compute evoked fields
