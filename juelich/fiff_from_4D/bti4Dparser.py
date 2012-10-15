#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>
#
#         simplified bsd-3 license


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
        raw_parsed = {}
        current_key = None
        for line in info:
            if line.isupper() and line.endswith(":"):
                current_key = line.strip(":")
                raw_parsed[current_key] = []
            else:
                raw_parsed[current_key].append(line)

        info = {}
        for field, params in raw_parsed.items():
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
                for p in params:
                    ch_groups = {}
                    if p.endswith("channels"):
                        ch_groups['n_ch'] = int(p.strip().split(' ')[0])
                    elif "MEG" in p:
                        ch_groups['n_meg_ch'] = int(p.strip().split(' ')[0])
                    elif "REFERENCE" in p:
                        ch_groups['n_ref_ch'] = int(p.strip().split(' ')[0])
                    elif "EEG" in p:
                        ch_groups['n_eeg_ch'] = int(p.strip().split(' ')[0])
                    elif "TRIGGER" in p:
                        ch_groups['n_trigger_ch'] = int(p.strip().split(' ')[0])
                    elif "UTILITY" in p:
                        ch_groups['n_misc_ch'] = int(p.strip().split(' ')[0])
                info[field] = ch_groups
            elif field == BTI4D.HDR_CH_CAL:
                ch_cal = []
                ch_fields = ["ch_name", "group", "cal", "unit"]
                for p in params:
                    this_ch_info = p.strip().split()
                    ch_cal.append(dict(zip(ch_fields, this_ch_info)))

            self.info = info

        for field, params in raw_parsed.items():
            if field == BTI4D.HDR_CH_TRANS:
                sensor_trans = {}
                idx = 0
                for p in params:
                    if "|" in p:
                        k, d, _ = p.strip().split("|")
                        if k.strip().isalnum():
                            # don't take the names from the file, go whith the renamed
                            # cave, this will break as the file strucutre changes
                            current_chan = info[BTI4D.HDR_CH_NAMES][idx][1]  # k.strip()
                            sensor_trans[current_chan] = d.strip()
                            idx += 1
                        else:
                            sensor_trans[current_chan] += ", " + d.strip()
