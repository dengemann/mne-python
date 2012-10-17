import os.path as op
from fiff_handler import RawFrom4D

fpath = '/Users/user/Downloads/data'

hdr_fname = op.join(fpath, 'fname.hdr')
data_fname = op.join(fpath, 'fname.data')
head_shape_fname = op.join(fpath, 'fname.hs')

raw = RawFrom4D(hdr_fname=hdr_fname, data_fname=data_fname,
                head_shape_fname=head_shape_fname, data=None, sep='.')

raw.save('mynew.fif')
