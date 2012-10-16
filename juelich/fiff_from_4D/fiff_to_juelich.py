#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>
#
#         simplified bsd-3 license

import os
from ConfigParser import ConfigParser
from datetime import datetime
from collections import OrderedDict

NAME = 'fiff_to_juelich'
VERSION = '0.0.1'
DESCRIPTION = 'Write fiff file to custom Juelich format'

DEF_MEGSYS = 'magnes3600'
DEF_NCHAN = 277
DEF_ORDER = 'little'
DEF_NMEG = 248
DEF_NREFERENCE = 23
DEF_NEEG = 3
DEF_NTRIGGER = 2
DEF_NUTILITY = 1

today = str(datetime.today())[:-7]


def write_hdr(raw, fname, study_name, pat_id, dtype='float',
              start_time=0, user=os.getlogin(), aq_mode='Continuous',
              today=today, meg_sys=DEF_MEGSYS, session=None, run=1,
              file_type='Bts', total_epochs=1,
              byte_order=DEF_ORDER):
    """ Juelich HDR Writer
    """
    cfp = ConfigParser()
    cfp.optionxform = str
    info = raw.info
    n_tsl = (raw.last_samp - raw.first_samp) + 1
    S = OrderedDict()
    S['GLOBAL'] = [('user', user), ('date', today), ('fname', fname + '.data'),
                  ('meg system', meg_sys)]

    S['DATAFILE'] = [('Patient-id', pat_id), ('Scan', study_name),
                     ('Session', session), ('Run', run)]

    S['FILEINFO'] = [('Sample Period ', str(1e3 / info['sfreq']) + ' S'),
                     ('Sample Frequency', str(info['sfreq']) + ' Hz'),
                     ('File Type', file_type), ('Acquisition Mode', aq_mode),
                     ('Total Epochs', total_epochs),
                     ('Start Time', start_time), ('Byte order', byte_order),
                     ('Longest Epoch in input PDF', str(n_tsl) + ' slices'),
                     ('Epoch Duration', str(info['sfreq'] * n_tsl) + ' S')]

    grads = [str(i) for i, e in enumerate(info['chs'])
             if e['coil_type'] == 3012]
    mags = [str(i) for i, e in enumerate(info['chs'])
            if e['coil_type'] == 3024]
    S['CHANNEL GROUPS'] = [('Number of channels', len(raw.ch_names)),
                           ('MEG', len([n for n in raw.ch_names
                                        if n.startswith('MEG')])),
                           ('REFERENCE', 0),
                           ('EEG', len([n for n in raw.ch_names
                                        if n.startswith('EEG')])),
                           ('TRIGGER', len([n for n in raw.ch_names
                                        if n.startswith('STI')])),
                           ('UTILITY', 0),
                           ('GRAD', '[' + ', '.join(grads) + ']'),
                           ('MAGS', '[' + ', '.join(mags) + ']')]

    # name index label no group scale unit min max
    mappings = []
    for i, ch in enumerate(info['chs']):
        name = ch['ch_name'].upper()
        if name.startswith('MEG'):
            group = 1
        elif name.startswith('EEG'):
            group = 2
        elif name[:3] in ('EOG', 'ECG'):
            group = 4
        elif name.startswith('STI'):
            group = 6

        value = [str(i), name, '0', str(group), str(ch['cal']),
                 str(ch['unit']), '0', '0']
        value = '\t\t'.join(value)
        mappings.append((name, value))

    S['CHANNEL INFO'] = mappings

    noisy_ch_idx = ', '.join([str(info['ch_names'].index(bad))
                                for bad in info['bads']])
    S['NOISY CHANNELS'] = [('name', ', '.join(raw.info['bads'])),
                           ('index', noisy_ch_idx)]

    for section, mappings in S.items():
        for name, value in mappings:
            if section not in cfp.sections():
                cfp.add_section(section)
            cfp.set(section, name, value)

    cfp.write(open(fname, 'w'))


def write_raw(raw, fname, picks=None, start=None, stop=None):
    """ Dump rawdata to file
    """
    data = raw[picks, start:stop][0]
    data.T.tofile(fname)
    print 'saved raw data (%i x %i) to %s' % data.shape + fname


if __name__ == '__main__':
    from optparse import OptionParser
    import sys

    argv = sys.argv[1:]

    # initialize the parser object:
    usage = "usage: fiff_to_juelich [options]"

    opp = OptionParser()
    opp.add_option('-f', '--fname', help='file name for data and header',
                   default=None)
    opp.add_option('-s', '--study_name', help='patient id', default=None)
    opp.add_option('-p', '--pat_id', help='patient id', default=None)
    opp.add_option('-r', '--raw', help='raw fiff to convert', default=None)

    opts, args = opp.parse_args()

    if not all([opts.raw, opts.fname, opts.study_name, opts.pat_id]):
        print "%s\n%s\n%s" % (NAME, VERSION, DESCRIPTION)
        opp.print_help()
        print "\n"
        sys.exit(0)

    write_hdr(opts.raw, opts.fname, opts.study_name, opts.pat_id)

    write_raw(opts.raw, opts.fname)

    sys.exit(0)
