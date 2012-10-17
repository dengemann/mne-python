#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>
#
#         simplified bsd-3 license

#  Bunch class taken from mne.fiff


class Bunch(dict):
    """ Container object for datasets: dictionnary-like object that
        exposes its keys as attributes.
    """

    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
        self.__dict__ = self

BTI4D = Bunch()

BTI4D.HDR_FILEINFO = 'FILEINFO'
BTI4D.HDR_DATAFILE = 'DATAFILE'
BTI4D.HDR_EPOCH_INFORMATION = 'EPOCH INFORMATION'
BTI4D.HDR_LONGEST_EPOCH = 'LONGEST EPOCH'
BTI4D.HDR_FIXED_EVENTS = 'FIXED EVENTS'
BTI4D.HDR_CH_CAL = 'CHANNEL SENSITIVITIES'
BTI4D.HDR_CH_NAMES = 'CHANNEL LABELS'
BTI4D.HDR_CH_GROUPS = 'CHANNEL GROUPS'
BTI4D.HDR_CH_TRANS = 'CHANNEL XFM'


class BtiParser(object):
    """BTI Magnes 3600 HEader Parser
    """
    def __init__(self, bti_info):

        self.bti_info = bti_info
        self._parse()

    def _parse(self):
        f = open(self.bti_info, "r").read()
        info = [l for l in f.split("\n") if not l.startswith("#")]
        self._raw_parsed = {}
        current_key = None
        for line in info:
            if line.isupper() and line.endswith(":"):
                current_key = line.strip(":")
                self._raw_parsed[current_key] = []
            else:
                self._raw_parsed[current_key].append(line)

        info = {}
        for field, params in self._raw_parsed.items():
            if field in [BTI4D.HDR_FILEINFO, BTI4D.HDR_CH_NAMES,
                         BTI4D.HDR_DATAFILE]:
                if field == BTI4D.HDR_DATAFILE:
                    sep = " : "
                elif field == BTI4D.HDR_FILEINFO:
                    sep = ":"
                else:
                    sep = None
                mapping = [i.strip().split(sep) for i in params]
                mapping = [(k.strip(), v.strip()) for k, v in mapping]

                if field == BTI4D.HDR_CH_NAMES:
                    info[field] = mapping
                else:
                    info[field] = dict(mapping)

            if field == BTI4D.HDR_CH_GROUPS:
                ch_groups = {}
                for p in params:
                    if p.endswith("channels"):
                        ch_groups['CHANNELS'] = int(p.strip().split(' ')[0])
                    elif "MEG" in p:
                        ch_groups['MEG'] = int(p.strip().split(' ')[0])
                    elif "REFERENCE" in p:
                        ch_groups['REF'] = int(p.strip().split(' ')[0])
                    elif "EEG" in p:
                        ch_groups['EEG'] = int(p.strip().split(' ')[0])
                    elif "TRIGGER" in p:
                        ch_groups['TRIGGER'] = int(p.strip().split(' ')[0])
                    elif "UTILITY" in p:
                        ch_groups['UTILITY'] = int(p.strip().split(' ')[0])
                info[BTI4D.HDR_CH_GROUPS] = ch_groups
            elif field == BTI4D.HDR_CH_CAL:
                ch_cal = []
                ch_fields = ["ch_name", "group", "cal", "unit"]
                for p in params:
                    this_ch_info = p.strip().split()
                    ch_cal.append(dict(zip(ch_fields, this_ch_info)))
                info[BTI4D.HDR_CH_CAL] = ch_cal

        for field, params in self._raw_parsed.items():
            if field == BTI4D.HDR_CH_TRANS:
                sensor_trans = {}
                idx = 0
                for p in params:
                    if "|" in p:
                        k, d, _ = p.strip().split("|")
                        if k.strip().isalnum():
                            current_chan = info[BTI4D.HDR_CH_NAMES][idx][0]  # k.strip()
                            sensor_trans[current_chan] = d.strip()
                            idx += 1
                        else:
                            sensor_trans[current_chan] += ", " + d.strip()
            info[BTI4D.HDR_CH_TRANS] = sensor_trans

        self.info = info
