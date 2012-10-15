import os
import os.path as op
import sys
import subprocess
from optparse import OptionParser

NAME = 'mne_create_forward_model'
VERSION = '0.0.1'
DESCRIPTION = 'run mne forward model routines.'


# MNE commands before coord alignment

SETUP_MRI = ['mne_setup_mri', '--overwrite']

SETUP_SOURCE_SPACE = ['mne_setup_source_space', '--ico', '-6', '--cps',
                      '--overwrite']

# make bem
MAKE_BEM = ['mne_watershed_bem', '--atlas', '--overwrite']

# surfaces in freesurfer format

SETUP_FORWARD_MODEL = ['mne_setup_forward_model', '--surf', '--ico 4',
                       '--overwrite']

# acutal forward model computation

DO_FWD = ['mne_do_forward_solution', '--spacing oct-6', 'mindist',
          '--overwrite', '--meas %s', '--megonly']

# inverse operator caluclation

DO_INV = ['mne_do_inverse_operator', '--fwd %s', '--deep', '--loose 0.2',
          '--meg']

# some constants for handling

SUBJID_PATTERN = '^[0-9]{1,6}$'
SUBJSEL_PATTERN = '(\d{1,3}(?:\s*\d{3})*)'
RESP_YES = 'y', 'yes'
RESP_QUIT = 'n', 'no', 'q', 'quit'
RESP_VALID = RESP_YES + RESP_QUIT
SURF_DIRS = ['bem', 'stats', 'touch', 'morph', 'trash', 'tiff', 'mpg', 'tmp',
             'surf', 'scripts', 'mri', 'rgb', 'src', 'label']


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

    parser.add_option('-v', '--verbose', dest='verbose',
                      help='Set the verbose mode', default=False)

    parser.add_option('-f', '--files', dest='files',
                      help='List of files, absolute paths')

    parser.add_option('-s', '--subjects_dir', dest='subjects_dir',
                      help='Sets the subjects directory',
                      default=False)

    parser.add_option('-d', '--dig_subjects', dest='dig_subjects',
                      help='Searches subjects in the directory specified',
                      default=False)

    parser.add_option('-i', '--interactive', dest='interactive',
                      help='Allows to check the list of files befor running',
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


def _interactive_edit(subj_list, pat_int):
    """ Helper function
    """
    done = False
    first = True
    while not done:
        listed = ['%i)     %s' % (i + 1, sub) if i <= 8 else
                  '%i)    %s' % (i + 1, sub) for i, sub
                  in enumerate(subj_list)]

        found = 'I found these guys' if first else 'These guys remain'

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
        elif pat_int.match(ans):
            subj_numbers = pat_int.findall(ans)
            if subj_numbers:
                idxs = [(int(i) - 1) for i in subj_numbers]
                invalid = [str(i) for i in idxs if i > len(subj_list)]
                if invalid:
                    print ('\n==> This input is invalid: \n'
                           '    %s' % '     %s'.join(invalid))
                    print ('\n    Please say it again.')
                else:
                    remove = [sub for i, sub in enumerate(subj_list)
                              if i in idxs]
                    subj_list = [sub for i, sub in enumerate(subj_list)
                                 if i not in idxs]
                    plural = "s" if len(subj_numbers) > 1 else ""
                    print "\n    ...removing subject%s %s" % (plural,
                                                              ",".join(remove))

        elif ans not in RESP_VALID or not pat_int.match(ans):
            print "\n\t%s is not a valid choice!\n" % ans

    return subj_list


def find_subjects(root_dir, pattern=SUBJID_PATTERN, interactive=True):
    """ Find fiff files under a a root directory
    """
    import re
    os.environ['SUBJECTS_DIR'] = root_dir
    pat = re.compile(pattern)
    pat_int = re.compile(SUBJSEL_PATTERN)
    subj_list = [d for d in os.listdir(root_dir) if pat.match(d)
                 and op.isdir(d)]

    if interactive and subj_list:
        subj_list = _interactive_edit(subj_list, pat_int=pat_int)

    if subj_list:
        for subject in subj_list:
            path = os.environ['SUBJECTS_DIR']
            subj_dir = op.join(path, subject)
            contents = os.listdir(subj_dir)
            surf_dirs = [c for c in contents if c in SURF_DIRS]
            if surf_dirs != SURF_DIRS:
                print ('\n    Incomplete freesurfer directory tree!'
                       '\n==> Subject %s will be excluded' % subject)
                subj_list.remove(subject)
            else:
                surface_dir = os.listdir(op.join(subj_dir, 'surf'))
                if not surface_dir:
                    print ('\n    Incomplete surface directory!'
                       '\n==> Subject %s will be excluded' % subject)
                    subj_list.remove(subject)
                mr_dir = os.listdir(op.join(subj_dir, 'surf'))
                if not mr_dir:
                    print ('\n    Incomplete MRI directory!'
                       '\n==> Subject %s will be excluded' % subject)
                    if subject in subj_list:
                        subj_list.remove(subject)

    return subj_list


def prepare_source_space(subjects):
    """ Run steps necessary before coordinate alignment
    """
    failure = []
    for i, subject in enumerate(subjects):
        os.environ['SUBJECT'] = subject
        setup_mri = SETUP_MRI
        mri_fail = subprocess.call(setup_mri)
        source_fail = 0
        bem_fail = 0
        ws_failure = []

        if mri_fail:
            print ('\n    running mne_setup_mri was not successful\n'
                   '      for %s' % subject)
            failure.append(subject)

        elif not mri_fail:
            setup_source_space = SETUP_SOURCE_SPACE
            source_fail = subprocess.call(setup_source_space)

        if source_fail:
            print ('\n    running mne_setup_source_space was not successful\n'
                   '      for %s' % subject)
            failure.append(subject)

        elif not source_fail:
            make_bem = MAKE_BEM
            bem_fail = subprocess.call(make_bem)

        if bem_fail:
            print ('\n    running mne_setup_mri was not successful'
                   '      for %s\n' % subject)
            failure.append(subject)

        elif not bem_fail:
            bem_dir = op.join(os.environ['SUBJECTS_DIR'], subject, 'bem')
            watershed_dir = op.join(bem_dir, 'watershed')
            watersheds = [f for f in os.listdir(watershed_dir)
                           if f.endswith('_surface')]
            for watershed in watersheds:
                watershed = watershed.replace('_surface', '.surf')
                watershed = watershed.replace("_" + subject, "-" + subject)
                mne_surf = op.join(bem_dir, )
                watershed = op.join(watershed_dir, watershed)
                res = subprocess.call(['ln', '-s', watershed, mne_surf])
                failure.append(res)

        if ws_failure:
            print ('\n    creating symlinks for watershed surfaces'
                   'was not successful for %s\n' % subject)
            failure.append(subject)

        elif not ws_failure:
            set_fwd = SETUP_FORWARD_MODEL
            set_fwd_fail = subprocess.call(set_fwd)

        if set_fwd_fail:
            print ('\n    Setting up the forward model'
                   'was not successful for %s\n' % subject)
            failure.append(subject)

        if subject not in failure:
            print ('\n\n    Preparing the source model for %s '
                   'successful.' % subject)

    return failure


def run_forward(subjects, file_pattern='ave.fif'):
    """ Make the forward model
    """
    failure = []
    for i, subject in enumerate(subjects):
        os.environ['SUBJECT'] = subject
        subj_dir = op.join(os.environ['SUBJECTS_DIR'], subject,)
        meas_files = [f for f in os.listdir(subj_dir) if f.endswith(file_pattern)]
        for meas_file in meas_files:
            meas_file = op.join(subj_dir, meas_file)
            do_fwd_cmd = (" ".join(DO_FWD) % meas_file).split()
            fail_forward = subprocess.call(do_fwd_cmd)
            msg = 'failed' if fail_forward else 'successful'
            print '\n    calculating forward model for %s %s' % (subject, msg)
            if fail_forward and subject not in failure:
                failure.append(subject)

    return failure


def run_inverse(subjects, file_pattern='oct-6-fwd.fif'):
    """ Make the forward model
    """
    failure = []
    for i, subject in enumerate(subjects):
        os.environ['SUBJECT'] = subject
        subj_dir = op.join(os.environ['SUBJECTS_DIR'], subject,)
        fwd_files = [f for f in os.listdir(subj_dir) if f.endswith(file_pattern)]
        for fwd_file in fwd_files:
            fwd_file = op.join(subj_dir, fwd_file)
            do_inv_cmd = (" ".join(DO_INV) % fwd_file).split()
            fail_forward = subprocess.call(do_inv_cmd)
            msg = 'failed' if fail_forward else 'successful'
            print '\n    calculating forward model for %s %s' % (subject, msg)
            if fail_forward and subject not in failure:
                failure.append(subject)

    return failure


if __name__ == '__main__':
    opts, args = process_cmd_line()

    if opts.p and opts.f:
        print ('You cannot run the preparation and the forwad model'
               ' in one step.\nPlease  make a choice.')
        status = 1

    if opts.s:
        subjects = find_subjects(opts.s, interactive=opts.i)

    if opts.p:
        failure = prepare_source_space(subjects=subjects)

    if opts.f:
        failure = run_forward(subjects=subjects)

    if failure:
        print ('\n\n    For the following subjects the proccessing'
               ' requested could not be completed:\n'
               '\n        %s'
               '\n\n    You should revist these subjects.\n'
               % '\n        '.join(failure))
        status = 1

    else:
        print 'Preparation for coordinate alignment completed'
        status = 0

    sys.exit(status)
