#!/usr/bin/env python

# Author: Denis A. Engemann  <d.engemann@fz-juelich.de>
#
#         simplified BSD3 license

import os
import os.path as op
import sys
import re
from commands import getoutput
from optparse import OptionParser

NAME = 'bti_utility'
VERSION = '0.0.1'
DESCRIPTION = 'batch process meg raw files as exported by 4D software'

TARGET = '/export/raid_meg1/exp/SOMO/MNE_CAU/101611'

MEG_SEL = 'A*,E*,TRIGGER,RESPONSE'

FIND_CMD = 'find %s | grep %s'

EXPORT_RAW_CMD = ['export_data', '-P %s', '-S "%s"', '-s "%s"', '-r %s',
                  '-p %s', '-o %s', '-l -t -v -e -D PC -O float']

COMP_CMD = ['noisereducer', '-P %s', '-S "%s"', '-s "%s"', '-r %s', '-p %s']

FIFF_EXPORT_CMD = ['export_fiff', '-P %s', '-S "%s"', '-s "%s"', '-r %s',
                   '-p %s', '-o %s', '-c "%s"', "-Osh -vbtd -Rx0"]

RESP_YES = 'y', 'yes'
RESP_NO = 'n', 'no'
RESP_VALID = RESP_YES + RESP_NO
RESP_QUIT = 'n', 'no', 'q', 'quit'
RESP_PATT = '(\d{1,3}(?:\s*\d{3})*)'
DEF_PATH = '/export/raid_meg2/megdaw_data21'

RAW_STR = 'rfDC'


def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True


def any(iterable):
    for element in iterable:
        if element:
            return True
    return False


def _interactive_edit(flist, pat_int=RESP_PATT):
    """ Helper function
    """
    pat = re.compile(pat_int)
    done = False
    first = True
    while not done:
        listed = []
        for i, sub in enumerate(flist):
            idx = (i + 1, sub)
            if i <= 8:
                listed.append('%i)     %s' % idx)
            else:
                listed.append('%i)    %s' % idx)

        if first:
            found = 'I found these guys'
        else:
            found = 'These guys remain'

        print '\n==>  %s:\n\n     %s' % (found, "\n     ".join(listed))
        print ('\n==> Do you want to keep them?'
               '\n'
               '\n    Press y (yes) to accept,'
               '\n    press q (quit) to quit,'
               '\n    or tell me the number(s) of the subject'
               ' you would like to remove\n')
        ans = ''
        ans = raw_input("==> ").lower()
        first = False
        if ans in RESP_YES:
            done = True
        elif ans in RESP_QUIT:
            sys.exit(1)
        elif pat.match(ans):
            file_numbers = pat.findall(ans)
            if file_numbers:
                idxs = [(int(i) - 1) for i in file_numbers]
                invalid = [str(i) for i in idxs if i > len(flist)]
                if invalid:
                    print ('\n==> This input is invalid: \n'
                           '    %s' % '     %s'.join(invalid))
                    print ('\n    Please say it again.')
                else:
                    remove = [sub for i, sub in enumerate(flist)
                              if i in idxs]
                    flist = [sub for i, sub in enumerate(flist)
                                 if i not in idxs]
                    if len(file_numbers) > 1:
                        plural = "s"
                    else:
                        print "\n    ...removing subject%s %s" % (plural,
                                                              ",".join(remove))

        elif ans not in RESP_VALID or not pat.match(ans):
            print "\n\t%s is not a valid choice!\n" % ans

    return flist


def find_meas(root_dir, study, subject=None, specs='.'):
    """ Find fiff files under a a root directory
    """
    meas_files = []

    print 'Please be patient. I\'m searching for matching data sets.'
    results = getoutput(FIND_CMD % (root_dir, study)).split('\n')
    terms = [term for term in [subject, specs] if term]
    for res in results:
        if all([term in res for term in terms]):
                meas_files.append(res)
    return meas_files


def export_bti(bti_files, ext, target_path, meg_sel=MEG_SEL, data_path=DEF_PATH):
    """ Exports bti_files files from a list of bti files

    Parameters
    ----------
    bti_files : list of str
        bti_file names as displayed by ls
    ext : str
        extension used for filtering the list
    target_path : str
        export path
    data_path : str
        path to bti file

    """
    for f in bti_files:
        if f.strip('\n').endswith(ext):
            export_cmd = EXPORT_RAW_CMD
            subj_path = f.replace(data_path, '')
            args = subj_path.replace('\n', '').replace('/', ' ').split()
            P, S, s, r, p = args
            name = [P, 'SOMO01', s.replace('@', '_'), 'run%s' % r, 'bti']
            name = '_'.join(name)
            target = op.join(target_path, P, 'MEG', name)
            export_cmd = ' '.join(export_cmd)
            export_cmd %= (P, S, s.replace('@', ' '), r, p, target)
            parent = op.split(target)[0]
            if not op.exists(target):
                os.system('mkdir -p %s' % parent)
            if p.endswith(ext):
                os.system(export_cmd)


def run_compensation(bti_files, ext, target_path, meg_sel=MEG_SEL, data_path=DEF_PATH):
    """ Run noise compensation on a list of bti files

    Parameters
    ----------
    bti_files : list of str
        bti_file names as displayed by ls
    ext : str
        extension used for filtering the list
    data_path : str
        path to bti file
    """
    for f in bti_files:
        if f.endswith('\n'):
            f = f.strip('\n')
        if f.startswith('.'):
            f = f.lstrip('.')
        if f.endswith(ext):
            comp_cmd = COMP_CMD
            subj_path = f.replace(data_path, '')
            args = subj_path.replace('\n', '').replace('/', ' ').split()
            P, S, s, r, p = args
            comp_cmd = ' '.join(comp_cmd) % (P, S, s.replace('@', ' '), r, p)
            os.system(comp_cmd)


def export_fiff(bti_files, ext, target_path, meg_sel=MEG_SEL, data_path=DEF_PATH):
    """ Exports fiff files from a list of bti files

    Parameters
    ----------
    bti_files : list of str
        bti_file names as displayed by ls
    ext : str
        extension used for filtering the list
    target_path : str
        export path
    data_path : str
        path to bti file

    """
    for f in bti_files:
        if f.endswith('\n'):
            f = f.strip('\n')
        if f.startswith('.'):
            f = f.lstrip('.')
        if f.endswith(ext):
            export_cmd = FIFF_EXPORT_CMD
            subj_path = f.replace(data_path, '')
            args = subj_path.replace('\n', '').replace('/', ' ').split()
            P, S, s, r, p = args
            name = '_'.join([P, 'SOMO01', s.replace('@', '_'), 'run%s' % r])
            target = op.join(target_path, P, 'MEG', name)
            export_cmd = ' '.join(export_cmd)
            export_cmd %= (P, S, s.replace('@', ' '), r, p, target, meg_sel)
            parent = op.split(target)[0]
            if not op.exists(target):
                os.system('mkdir -p %s' % parent)
            if p.endswith(ext):
                os.system(export_cmd)
                print export_cmd
                target_path, _ = op.split(target)
                open(op.join(target_path,
                     "_".join(('orginal_path', P, '.txt'))), 'w').write(f)


if __name__ == '__main__':
    #  run program

    argv = sys.argv[1:]

    # initialize the parser object:
    usage = "usage: meg_bti_utility [options]"

    parser = OptionParser(usage)

    parser.add_option('-d', '--dir',
                      help='root directory to search under',
                      default=DEF_PATH)
    parser.add_option('-s', '--study',
                      help='study name', default=None)
    parser.add_option('-p', '--patient',
                      help='patient id', default=None)
    parser.add_option('-f', '--file_spec',
                      help='Searches subjects in the directory specified',
                      default='rfDC')
    parser.add_option('-c', '--command',
                      help=('the command to run: export_data |'
                            ' noisereducer |'
                            ' export_fiff'),
                      default='noisereducer')
    parser.add_option('-i', '--interactive',
                      help='Allows to check the list of files before running',
                      default=True)
    parser.add_option('-m', '--meg_select', help='Selection of MEG channels',
                      default=MEG_SEL)
    parser.add_option('-t', '--target_path', help='target path', default=None)

    for option in parser.option_list:
        if option.default != ('NO', 'DEFAULT'):
            if option.help:
                option.help += ' '
            else:
                option.help += ''
            option.help += '[default: %default]'

    opts, args = parser.parse_args()

    command_dir = {'noisereducer': run_compensation,
                   'export_data': export_bti,
                   'export_fiff': export_fiff}

    if not any([opts.study, opts.patient]):
        print "%s\n%s\n%s" % (NAME, VERSION, DESCRIPTION)
        parser.print_help()
        print "\n"
        sys.exit(0)

    if opts.target_path is None:
        print 'You must name the target path. Please specify option -t'
        sys.exit(1)

    files = find_meas(opts.dir, opts.study, subject=opts.patient, specs=opts.file_spec)

    if opts.interactive:
        files = _interactive_edit(files)
    if not files:
        print 'No files found.'
        sys.exit(1)
    command = command_dir.get(opts.command)
    if command is None:
        print '%s is not a valid command option.'
        sys.exit(1)
    command(files, opts.f, opts.t)

    sys.exit(0)

