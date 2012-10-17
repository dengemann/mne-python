from mne.fiff.constants import FIFF
from mne.fiff.raw import Raw
from ConfigParser import ConfigParser
from .parsers import BtiParser
import time
import os.path as op
from datetime import datetime
import numpy as np


FIFF_INFO_CHS_FIELDS = ('loc', 'ch_name', 'unit_mul', 'coil_trans',
    'coord_frame', 'coil_type', 'range', 'unit', 'cal', 'eeg_loc',
    'scanno', 'kind', 'logno')
FIFF_INFO_CHS_DEFAULTS = (
    np.array([0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1], dtype=np.float32), None, 0,
              None, 0, 0, 1.0, 107, 1.0, None, None, 402, None)
FIFF_INFO_DIG_FIELDS = ("kind", "ident", "r", "coord_frame")
FIFF_INFO_DIG_DEFAULTS = (None, None, None, FIFF.FIFFV_COORD_HEAD)

ROT_NMAG = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]])

LOC_TO_COIL = ((0, 3), (1, 3), (2, 3), (0, 0), (1, 0), (2, 0), (0, 1), (1, 1),
               (0, 2), (2, 1), (1, 2), (2, 2))


class RawFromJuelich(Raw):
    """Alternative Constructor for Raw object

    Parameters
    ----------

    data : np.array
        2D array with channels by timeslices

    conf : string
        absolute path to the config or ini file that contains
        the channel and measurment info

    Attributes
    ----------

    See docstring for Raw object

    """
    def __init__(self, conf, data=None):
        """ Alternative fiff file constructor
        """
        # intitalize configparser for Juelich-4D header file
        self.conf = conf
        self._root, self._hdr_name = op.split(self.conf)
        self.hdr_4D = ConfigParser()
        self.hdr_4D.read(self.conf)
        self._data_file = op.join(self._root, self.hdr_4D.get('GLOBAL', 'fname'))
        print ("Initializing RawObject from custom 4D data " +
               "file %s ..." % self._data_file)
        info = self._create_raw_info()
        self.info = info

        self._data = self._read_4D_data() if not data else data
        self.first_samp, self.last_samp = 0, self._data.shape[1] - 1
        cals = np.zeros(info['nchan'])
        for k in range(info['nchan']):
            cals[k] = info['chs'][k]['range'] * \
                      info['chs'][k]['cal']

        self.cals = cals
        self.rawdir = None
        self.proj = None
        self.comp = None

        self.verbose = True
        if self.verbose:
            print '    Range : %d ... %d =  %9.3f ... %9.3f secs' % (
                       self.first_samp, self.last_samp,
                       float(self.first_samp) / info['sfreq'],
                       float(self.last_samp) / info['sfreq'])
            print 'Ready.'
        self.fid = None
        self._preloaded = True
        self._projectors = []
        self._times = np.arange(self.first_samp,
            self.last_samp + 1) / info['sfreq']

    def _init_chan_info(self):
        """ Initializes and returns struct for channel information
        """
        return dict((field, val) for field, val
            in zip(FIFF_INFO_CHS_FIELDS, FIFF_INFO_CHS_DEFAULTS))

    def _init_dig_info(self):
        """ Initializes and returns struct for digitization information
        """
        return dict((field, val) for field, val in zip(FIFF_INFO_DIG_FIELDS,
            FIFF_INFO_DIG_DEFAULTS))

    def _create_raw_info(self):
        """ Fills list of dicts for initializing empty fiff with 4D data
        """
        # intialize to_fiff info dicitonary and populate it
        info = {}
        d = datetime.strptime(self.hdr_4D.get("GLOBAL", "date"),
                              "%d-%m-%Y %H:%M:%S")
        sec = time.mktime(d.timetuple())
        info['projs'] = []
        info['comps'] = []
        info['meas_date'] = np.array([sec, 0], dtype=np.int32)
        info['sfreq'] = float(self.hdr_4D.get("FILEINFO",
            "Sample Frequency")[:-2])
        info['nchan'] = int(self.hdr_4D.get('CHANNEL GROUPS',
            'Number of channels'))
        channels_4D = [(i[1].split()[1], int(i[1].split()[2]) + 1) for i
            in self.hdr_4D.items("CHANNEL INFO")]
        channels_4D.sort(key=lambda x: x[1], reverse=False)
        ch_names = [name for name, _ in channels_4D]
        ch_lognos = [logno for _, logno in channels_4D]
        info['ch_names'] = self._rename_4D_channels(ch_names)
        meg_channels = [n for n in info['ch_names'] if n.startswith('MEG')]
        ref_magnetometers = [n for n in info['ch_names'] if n.startswith('RFM')]
        ref_gradiometers = [n for n in info['ch_names'] if n.startswith('RFG')]
        print meg_channels[:5], ref_magnetometers[:5], ref_gradiometers[:5]

        sensor_trans = {}
        info_4D = op.join(self._root, self.hdr_4D.get("GLOBAL", "4Dinfo"))
        with open(info_4D, "r") as f:
            idx = 0
            for line in f:
                if "|" in line:
                    k, d, _ = line.strip().split("|")
                    if k.strip().isalnum():
                        # don't take the names from the file, go whith the renamed
                        # cave, this will break as the file strucutre changes
                        current_chan = info['ch_names'][idx]  # k.strip()
                        sensor_trans[current_chan] = d.strip()
                        idx += 1
                    else:
                        sensor_trans[current_chan] += ", " + d.strip()

        print sensor_trans.keys()[0:5],

        info['bads'] = []  # TODO
        bads = self.hdr_4D.get("NOISY CHANNELS", "noisy channel name")
        if bads:
            if bads in meg_channels:
                info['bads'] = bads
            if "," in bads:
                bads = [bad for bad in bads.split(",") if bad in meg_channels]
                if bads:
                    info['bads'] = bads

        try:
            head2mr = op.join(self._root, self.hdr_4D.get("GLOBAL", "meg2mr"))
            info['dev_head_t'] = {'from': FIFF.FIFFV_COORD_HEAD,
                                  'to': FIFF.FIFFV_COORD_MRI}
            with open(head2mr, "r") as f:
                h2m_trans = np.array([l.strip().split() for l in
                                      f.readlines()[:4]]).astype(np.float32)
                dev_head_t = np.vstack([np.roll(h2m_trans.T, 1, 1),
                                       [0, 0, 0, 1]])
                info['dev_head_t']['trans'] = dev_head_t
        except:
            print "Could not find the head to MR matrix." \
                  "\n I'm skipping this step."

        info['meas_id'] = None  # dict(machid=None, secs=None, usecs=None,
            # version=None) # if needed, supply info layrt on
        info['file_id'] = None  # dict(machid=None, secs=None, usecs=None,
            # version=None) #ok
        info['dig'] = []

        try:
            head_shape = op.join(self._root, self.hdr_4D.get("GLOBAL",
                                                             "head_shape"))
            with open(head_shape) as f:
                dig_points = [np.array(l.strip().split(), dtype=np.float32)
                          for l in f.readlines() if not l.startswith("#")]

        except:
            print "Could not find the head shape file." \
                  "\n I'm skipping this step"
            dig_points = None

        if dig_points:
            fiducials_idents = (0, 1, 2, 0, 1)
            for idx, point in enumerate(dig_points):
                point_info = self._init_dig_info()
                point_info['r'] = point
                if idx < 3:
                    point_info['kind'] = FIFF.FIFFV_POINT_CARDINAL
                    point_info['ident'] = fiducials_idents[idx]
                if 2 < idx < 5:
                    point_info['kind'] = FIFF.FIFFV_POINT_HPI
                    point_info['ident'] = fiducials_idents[idx]
                elif idx > 4:
                    point_info['kind'] = FIFF.FIFFV_POINT_EXTRA
                    point_info['ident'] = idx - len(fiducials_idents)
                info['dig'].append(point_info)

        try:
            fspec = self.hdr_4D.get('DATAFILE', 'PDF').split(',')[2].split('ord')[0]
            ffreqs = fspec.replace('fwsbp', '').split("-")
        except:
            print "Cannot read any filter specifications." \
                  "\n No filter info will be set."
            ffreqs = 0, 300

        info['highpass'], info['lowpass'] = ffreqs
        info['acq_pars'], info['acq_stim'] = None, None  # both ok
        info['filename'] = None  # set later on
        info['ctf_head_t'] = None  # ok like that
        info['dev_ctf_t'] = []  # ok like that
        chs = []

        for idx, (chan, logno) in enumerate(zip(info['ch_names'], ch_lognos)):
            chan_info = self._init_chan_info()
            chan_info['ch_name'] = chan
            chan_info['logno'] = logno
            chan_info['scanno'] = idx + 1

            if chan in meg_channels + ref_magnetometers + ref_gradiometers:
                chan_info['loc'] = self._get_loc(sensor_trans[chan])
                coil_trans = np.zeros([4, 4])
                for i, loc in enumerate(chan_info['loc']):
                    coil_trans[LOC_TO_COIL[i]] = loc
                coil_trans[3, 3] = 1.
                chan_info['coil_trans'] = coil_trans

            if chan in meg_channels:
                chan_info['kind'] = FIFF.FIFFV_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_MAGNES_MAG
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_HEAD
                chan_info['unit'] = FIFF.FIFF_UNIT_T

            elif chan in ref_magnetometers:
                chan_info['kind'] = FIFF.FIFFV_REF_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_POINT_MAGNETOMETER
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
                chan_info['unit'] = FIFF.FIFF_UNIT_T

            elif chan in ref_gradiometers:
                chan_info['kind'] = FIFF.FIFFV_REF_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_AXIAL_GRAD_5CM
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
                chan_info['unit'] = FIFF.FIFF_UNIT_T_M

            elif chan in "STI 014":
                chan_info['kind'] = FIFF.FIFFV_STIM_CH
            elif chan in ("EOG 001", "EOG 002"):
                chan_info['kind'] = FIFF.FIFFV_EOG_CH
            elif chan in "ECG 001":
                chan_info['kind'] = FIFF.FIFFV_ECG_CH
            elif chan in "RSP 001":
                chan_info['kind'] = FIFF.FIFFV_RESP_CH

            # other channels implicitly covered
            chs.append(chan_info)

        info['chs'] = chs
        return info

    def _get_loc(self, channel_pos_4D):
        """ transforms 4D coil position to fiff / Neuromag
        """
        # get the geometries
        geom_4D = np.array(channel_pos_4D.split(', ')[:12], dtype=np.float32)
        # reshape for convenience
        geom_4D = geom_4D.reshape([3, 4])
        # get rotation as vector
        rot_4D = geom_4D[:, :3]
        # flip x and z
        rot_4D = np.rot90(rot_4D)
        # get translation as vector
        trans_4D = geom_4D[:, 3:].flatten()
        # transpose and flatten
        rot_4D = rot_4D.T.flatten()
        return  np.r_[rot_4D, trans_4D]

    def _read_4D_data(self, count=-1, dtype=np.float32):
        """ Reads data from the Juelich 4D format
        """
        ntsl = int(self.hdr_4D.get('FILEINFO',
            'longest epoch in input pdf').replace(' slices', ''))
        cnt, dtp = count, dtype
        with open(self._data_file, 'rb') as f:
            data = np.fromfile(file=f, dtype=dtp,
                               count=cnt).reshape((ntsl,
                                                   self.info['nchan']))
            data[:, :248] *= 1e-15  # put data in Tesla
            #TODO Gradiometers?
            data[:, 253:271] *= 1e-15  # put data in Tesla
        return data.T

    def _rename_4D_channels(self, names):
        """Renames appropriately ordered list of channel namaes
        """
        renamed = []
        count_ref_mag = 0
        count_ref_grad = 0
        count_eog = 0
        for name in names:
            if name.startswith("A"):
                name = name.replace("A", "MEG ")
                name = list(name)
                if len(name) == 5:
                    name.insert(4, "0" * 2)
                elif len(name) == 6:
                    name.insert(4, "0")
                name = "".join(name)
            elif name == "TRIGGER":
                name = "STI 014"
            elif name == "RESPONSE":
                name = "RSP 001"
            elif name.startswith("EOG"):
                count_eog += 1
                name = "EOG 00%i" % count_eog
            elif name == "ECG":
                name = "ECG 001"
            elif name == 'UACurrent':
                name = "UCA 001"
            elif name.startswith("M"):
                count_ref_mag += 1
                extra_zero = "0" if count_ref_mag < 10 else ""
                name = "RFM 0%s%i" % (extra_zero, count_ref_mag)
            elif name.startswith("G"):
                count_ref_grad += 1
                name = "RFG 00%i" % count_ref_grad
            renamed.append(name)
        return names, renamed


class RawFrom4D(RawFromJuelich):
    """ intializes object from 4D asicii exported data
    """
    def __init__(self, hdr_fname, data_fname, head_shape_fname, data=None,
                 sep='-'):
        """ Alternative fiff file constructor
        """
        # intitalize configparser for Juelich-4D header file
        self.hdr = BtiParser(hdr_fname)
        self._root, self._hdr_name = op.split(hdr_fname)
        self._data_file = data_fname
        self.head_shape_fname = head_shape_fname
        self.sep = sep

        print ("Initializing RawObject from custom 4D data " +
               "file %s ..." % self._data_file)
        info = self._create_raw_info()
        self.info = info

        self._data = self._read_4D_data() if not data else data
        self.first_samp, self.last_samp = 0, self._data.shape[1] - 1
        cals = np.zeros(info['nchan'])
        for k in range(info['nchan']):
            cals[k] = info['chs'][k]['range'] * \
                      info['chs'][k]['cal']

        self.cals = cals
        self.rawdir = None
        self.proj = None
        self.comp = None

        self.verbose = True
        if self.verbose:
            print '    Range : %d ... %d =  %9.3f ... %9.3f secs' % (
                       self.first_samp, self.last_samp,
                       float(self.first_samp) / info['sfreq'],
                       float(self.last_samp) / info['sfreq'])
            print 'Ready.'
        self.fid = None
        self._preloaded = True
        self._times = np.arange(self.first_samp,
            self.last_samp + 1) / info['sfreq']
        self._projectors = [None]
        self._projector_hashes = [None]

    def _create_raw_info(self):
        """ Fills list of dicts for initializing empty fiff with 4D data
        """
        # intialize to_fiff info dicitonary and populate it
        info = {}
        sep = self.sep
        d = datetime.strptime(self.hdr['DATAFILE']['Session'],
                              '%d' + sep + '%y' + sep + '%m %H:%M')
        sec = time.mktime(d.timetuple())
        info['projs'] = []
        info['comps'] = []
        info['meas_date'] = np.array([sec, 0], dtype=np.int32)
        info['sfreq'] = float(self.hdr["FILEINFO"]["Sample Frequency"][:-2])
        info['nchan'] = int(self.hdr["CHANNEL GROUPS"]["CHANNELS"])
        channels_4D = np.array([(e[0], i + 1) for i, e in
                                enumerate(self.hdr["CHANNEL LABELS"])])
        ch_names = channels_4D[:, 0].tolist()
        ch_lognos = channels_4D[:, 1].tolist()
        info['ch_names'] = self._rename_4D_channels(ch_names)[1]
        ch_mapping = dict(zip(* self._rename_4D_channels(ch_names)))
        meg_channels = [n for n in info['ch_names'] if n.startswith('MEG')]
        ref_magnetometers = [n for n in info['ch_names'] if n.startswith('RFM')]
        ref_gradiometers = [n for n in info['ch_names'] if n.startswith('RFG')]
        print meg_channels[:5], ref_magnetometers[:5], ref_gradiometers[:5]

        sensor_trans = dict((ch_mapping[k], v) for k, v in
                            self.hdr['CHANNEL XFM'].items())
        print sensor_trans.keys()[0:5]

        info['bads'] = []  # TODO

        try:  # TODO
            head2mr = op.join(self._root, self.hdr_4D.get("GLOBAL", "meg2mr"))
            info['dev_head_t'] = {'from': FIFF.FIFFV_COORD_HEAD,
                                  'to': FIFF.FIFFV_COORD_MRI}
            with open(head2mr, "r") as f:
                h2m_trans = np.array([l.strip().split() for l in
                                      f.readlines()[:4]]).astype(np.float32)
                dev_head_t = np.vstack([np.roll(h2m_trans.T, 1, 1),
                                       [0, 0, 0, 1]])
                info['dev_head_t']['trans'] = dev_head_t
        except:
            print "Could not find the head to MR matrix." \
                  "\n I'm skipping this step."
            info['dev_head_t'] = None

        info['meas_id'] = None  # dict(machid=None, secs=None, usecs=None,
            # version=None) # if needed, supply info layrt on
        info['file_id'] = None  # dict(machid=None, secs=None, usecs=None,
            # version=None) #ok
        info['dig'] = []

        try:  # TODO
            head_shape = self.head_shape_fname
            with open(head_shape) as f:
                dig_points = [np.array(l.strip().split(), dtype=np.float32)
                          for l in f.readlines() if not l.startswith("#")]

        except:
            print "Could not find the head shape file." \
                  "\n I'm skipping this step"
            dig_points = None

        if dig_points:
            fiducials_idents = (0, 1, 2, 0, 1)
            for idx, point in enumerate(dig_points):
                point_info = self._init_dig_info()
                point_info['r'] = point
                if idx < 3:
                    point_info['kind'] = FIFF.FIFFV_POINT_CARDINAL
                    point_info['ident'] = fiducials_idents[idx]
                if 2 < idx < 5:
                    point_info['kind'] = FIFF.FIFFV_POINT_HPI
                    point_info['ident'] = fiducials_idents[idx]
                elif idx > 4:
                    point_info['kind'] = FIFF.FIFFV_POINT_EXTRA
                    point_info['ident'] = idx - len(fiducials_idents)
                info['dig'].append(point_info)

        try:  # TODO
            fspec = self.hdr_4D.get('DATAFILE', 'PDF').split(',')[2].split('ord')[0]
            ffreqs = fspec.replace('fwsbp', '').split("-")
        except:
            print "Cannot read any filter specifications." \
                  "\n No filter info will be set."
            ffreqs = 0, 300

        info['highpass'], info['lowpass'] = ffreqs
        info['acq_pars'], info['acq_stim'] = None, None  # both ok
        info['filename'] = None  # set later on
        info['ctf_head_t'] = None  # ok like that
        info['dev_ctf_t'] = []  # ok like that
        info['filenames'] = []
        chs = []

        for idx, (chan, logno) in enumerate(zip(info['ch_names'], ch_lognos)):
            chan_info = self._init_chan_info()
            chan_info['ch_name'] = chan
            chan_info['logno'] = logno
            chan_info['scanno'] = idx + 1

            if chan in meg_channels + ref_magnetometers + ref_gradiometers:
                chan_info['loc'] = self._get_loc(sensor_trans[chan])
                coil_trans = np.zeros([4, 4])
                for i, loc in enumerate(chan_info['loc']):
                    coil_trans[LOC_TO_COIL[i]] = loc
                coil_trans[3, 3] = 1.
                chan_info['coil_trans'] = coil_trans

            if chan in meg_channels:
                chan_info['kind'] = FIFF.FIFFV_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_MAGNES_MAG
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_HEAD
                chan_info['unit'] = FIFF.FIFF_UNIT_T

            elif chan in ref_magnetometers:
                chan_info['kind'] = FIFF.FIFFV_REF_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_POINT_MAGNETOMETER
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
                chan_info['unit'] = FIFF.FIFF_UNIT_T

            elif chan in ref_gradiometers:
                chan_info['kind'] = FIFF.FIFFV_REF_MEG_CH
                chan_info['coil_type'] = FIFF.FIFFV_COIL_AXIAL_GRAD_5CM
                chan_info['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
                chan_info['unit'] = FIFF.FIFF_UNIT_T_M

            elif chan in "STI 014":
                chan_info['kind'] = FIFF.FIFFV_STIM_CH
            elif chan in ("EOG 001", "EOG 002"):
                chan_info['kind'] = FIFF.FIFFV_EOG_CH
            elif chan in "ECG 001":
                chan_info['kind'] = FIFF.FIFFV_ECG_CH
            elif chan in "RSP 001":
                chan_info['kind'] = FIFF.FIFFV_RESP_CH

            # other channels implicitly covered
            chs.append(chan_info)

        info['chs'] = chs
        return info

    def _read_4D_data(self, count=-1, dtype=np.float32):
        """ Reads data from the Juelich 4D format
        """
        ntsl = int(self.hdr['FILEINFO']['Time slices'].replace(' slices', ''))
        cnt, dtp = count, dtype
        with open(self._data_file, 'rb') as f:
            data = np.fromfile(file=f, dtype=dtp,
                               count=cnt).reshape((ntsl,
                                                   self.info['nchan']))
            data[:, :248] *= 1e-15  # put data in Tesla
            #TODO Gradiometers?
            data[:, 253:271] *= 1e-15  # put data in Tesla
        return data.T


class RawMerged(RawFromJuelich):
    """ initializes object from exisiting and custom raw data
    """
    def __init__(self, raw_fname, hdr_4D):
        self.conf = hdr_4D
        self._root, self._hdr_name = op.split(self.conf)
        self.hdr_4D = ConfigParser()
        self.hdr_4D.read(self.conf)

        self._data_file = op.join(self._root, self.hdr_4D.get('GLOBAL', 'fname'))
        print ("Initializing merging custom 4D data with existing fiff" +
               "file %s ..." % self._data_file)
        raw = Raw(raw_fname)
        info = raw.info
        self.info = info
        self._data = self._merge_4D_data()
        self.first_samp, self.last_samp = 0, self._data.shape[1] - 1
        cals = np.zeros(info['nchan'])
        for k in range(info['nchan']):
            cals[k] = info['chs'][k]['range'] * \
                      info['chs'][k]['cal']

        self.cals = raw.cals
        self.rawdir = raw.rawdir
        self.proj = raw.proj
        self.comp = raw.comp

        self.verbose = True
        if self.verbose:
            print '    Range : %d ... %d =  %9.3f ... %9.3f secs' % (
                       self.first_samp, self.last_samp,
                       float(self.first_samp) / info['sfreq'],
                       float(self.last_samp) / info['sfreq'])
            print 'Ready.'
        self.fid = None
        self._preloaded = True
        self._times = np.arange(self.first_samp,
            self.last_samp + 1) / info['sfreq']
        raw.close()

    def _merge_4D_data(self, count=-1, dtype=np.float32):
        """ Reads data from the Juelich 4D format
        """
        ntsl = int(self.hdr_4D.get('FILEINFO',
            'longest epoch in input pdf').replace(' slices', ''))
        cnt, dtp = count, dtype
        n_chan = int(self.hdr_4D.items('CHANNEL GROUPS')[0][1])
        # pick all but ref channels
        keep = [int(e.split()[0]) for _, e in self.hdr_4D.items('CHANNEL INFO')
                if not e.split()[1][0] in ['M', 'G', 'U']]
        with open(self._data_file, 'rb') as f:
            data = np.fromfile(file=f, dtype=dtp,
                               count=cnt).reshape((ntsl,
                                                   n_chan))[:, keep]
            data[:, :248] *= 1e-15  # put data in Tesla
            #TODO Gradiometers?
            data[:, 253:271] *= 1e-15  # put data in Tesla
        return data.T
