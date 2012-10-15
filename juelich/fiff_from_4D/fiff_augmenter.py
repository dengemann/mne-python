#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>

import os.path as op
import numpy as np
import os
import sys
import subprocess
from optparse import OptionParser
from mne.fiff import Raw
from mne.fiff.constants import FIFF

NAME = 'fiff_augmenter'
VERSION = '0.0.1'
DESCRIPTION = 'augments fiff files as exported by 4D software'
MAGNES_EDIT_LIST = 'EEG 001', 'EEG 002', 'EEG 003', 'STI 001', 'STI 002'
EMPTY_ARRAY = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
RESP_YES = 'y', 'yes'
RESP_NO = 'n', 'no'
RESP_VALID = RESP_YES + RESP_NO


def process_cmd_line(argv=None):
    """
        Return a 2-tuple: (settings object, args list).
        `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    usage = "usage: fiff_augmenter [options]"

    parser = OptionParser(usage)

    curdir = os.path.abspath(os.curdir)
    # define options here:
    parser.set_defaults(vebrose=True, outdir=curdir, targetstr='20',
                        interactive=False, inplace=False)

    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
                      help='Set the verbose mode', default=False)

    parser.add_option('-f', '--files', dest='files', action='store',
                      help='List of files, absolute paths')

    parser.add_option('-s', '--search_path', dest='search_path',
                      action='store',
                      help='Searches fiff files under the subject directory',
                      default=False)

    parser.add_option('-t', '--targetstr', dest='targetstr', action='store',
                      help=('Additional criterion for identifying '
                            'subject files'),
                      default='20')

    parser.add_option('-i', '--interactive', dest='interactive',
                      action='store_true',
                      help='Allows to check the list of files befor running',
                      default=False)

    parser.add_option('-p', '--inplace', dest='inplace',
                      action='store_true',
                      help=('This will overwrite the existing fiff file. '
                            'Otherwise the postfix _aug will be included '
                            'in the file name.'),
                      default=False)

    for option in parser.option_list:
        if option.default != ('NO', 'DEFAULT'):
            option.help += (' ' if option.help else '') + '[default: %default]'

    opts, args = parser.parse_args()

    if opts == parser.defaults:
        print "\n%s %s\n%s\n" % (NAME, VERSION, DESCRIPTION)
        parser.print_help()
        print "\n"
        sys.exit(0)
    else:
        return opts, args


def find_fiffs(root_dir, targetstr):
    """ Find fiff files under a a root directory
    """
    fiff_files = []
    for r, d, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".fif") and \
                "eve.fif" not in f and f.startswith(targetstr):
                fpath = op.join(r, f)
                fiff_files.append(fpath)
    return fiff_files


def get_feedback(subj_list):
    """ Iterate over list of selected files and get user feedback
    """
    for subj in subj_list:
        path, fname = op.split(subj)
        ans = ""
        print "\n\nFILENAME: %s" % fname
        print "\nPATH: %s" % path
        while ans not in RESP_VALID:
            print "\n\tDo you want to includen this file?"
            ans = raw_input("\n\t==> Say yes (y)/ no (n) : ").lower()
            if ans not in RESP_VALID:
                print "\n\t%s is not a valid choice!" % ans

        if ans in RESP_NO:
            subj_list.remove(subj)


def _edit_raw_info(info):
    """ Helper function for editing the raw measurement info
    """
    no_success = []
    for ch in MAGNES_EDIT_LIST:
        try:
            idx = info['ch_names'].index(ch)  # get index for channel name
        except:
            no_success.append(0)
            print ('\n\t ==> could not find a channel labled'
                   ' %s in the measurment info.'
                   '\n\t     Did you already augment this file? '
                   'Please check!' % ch)
            break
        try:
            if ch not in ('STI 001', 'STI 002'):
                info['chs'][idx]['eeg_loc'] = None
                info['chs'][idx]['loc'] = EMPTY_ARRAY
                info['chs'][idx]['coil_type'] = FIFF.FIFFV_COIL_NONE
        except:
            raise ValueError('Something went wrong with reassigning'
                             ' the measurment info! to %s' % ch)
        try:
            if ch == 'EEG 001':
                info['chs'][idx]['ch_name'] = "ECG 001"
                info['ch_names'][idx] = "ECG 001"
                info['chs'][idx]['kind'] = FIFF.FIFFV_ECG_CH
                info['chs'][idx]['coord_frame'] = FIFF.FIFFV_COORD_UNKNOWN
        except:
            raise ValueError('Something went wrong with reassigning'
                             ' the measurment info to %s !' % ch)
        try:
            if ch in ('EEG 002', 'EEG 003'):
                info['chs'][idx]['kind'] = FIFF.FIFFV_EOG_CH
                name = "EOG 001" if ch == 'EEG 002' else 'EOG 002'
                info['chs'][idx]['ch_name'] = name
                info['ch_names'][idx] = name
        except:
            raise ValueError('Something went wrong with reassigning'
                             ' the measurment info to %s !' % ch)
        try:
            if ch == 'STI 001':
                info['chs'][idx]['ch_name'] = "STI 013"
                info['ch_names'][idx] = "STI 013"
                info['chs'][idx]['kind'] = FIFF.FIFFV_RESP_CH
        except:
            raise ValueError('Something went wrong with reassigning'
                             ' the measurment info to %s !' % ch)
        try:
            if ch == 'STI 002':
                info['chs'][idx]['ch_name'] = "STI 014"
                info['ch_names'][idx] = "STI 014"
        except:
            raise ValueError('Something went wrong with reassigning'
                             ' the measurment info to %s !' % ch)

    msg = 'unsuccsessfull' if no_success else 'successfull'
    print 'Augmenting Fiff %s was %s.' % (info['filename'], msg)


def edit_fiff(raw_fname, inplace):
    """ Edits raw fiff files
    """
    try:
        raw = Raw(raw_fname)
        try:
            intersection = [ch_name for ch_name in raw.info if ch_name
                            in MAGNES_EDIT_LIST]
            if intersection:
                print ("\n ==> The file %s has already bean edited."
                       % raw_fname)
            else:
                _edit_raw_info(raw.info)
                for i, ch in enumerate(raw.info['ch_names']):
                        raw.ch_names[i] = ch
                new_fname = raw_fname.replace('.fif', '_aug.fif')
                raw.save(new_fname)
                if inplace:
                    subprocess.call(['mv', new_fname, raw_fname])
        except:
            print "\n\t==> Could not augment %s" % raw_fname
        finally:
            raw.close()
    except:
        print "\n\t==> Could not open file %s . Skipping this one." % raw_fname


def main():
    """ Main routine
    """
    opts, args = process_cmd_line()

    if opts.files:
        subj_list = opts.files.split()

    subj_list = find_fiffs(opts.search_path, opts.targetstr)

    if not subj_list:
        print 'No files specified. use option -s or -f'
        sys.exit(1)

    if opts.interactive:
        get_feedback(subj_list)

    n_files = len(subj_list)
    for i, f in enumerate(subj_list):
        print ("\n\nI'm now running the edits on"
               " %s \n(%i out of %i files)" % (f, i + 1, n_files))
        edit_fiff(f, opts.inplace)

    print "\n done."
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
