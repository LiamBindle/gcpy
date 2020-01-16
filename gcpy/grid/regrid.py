''' Functions for creating xesmf regridder objects '''

import os
import hashlib
import xesmf as xe
from .horiz import make_grid_LL, make_grid_CS, make_grid_SG

def make_regridder_L2L( llres_in, llres_out, weightsdir='.', reuse_weights=False ):
    llgrid_in = make_grid_LL(llres_in)
    llgrid_out = make_grid_LL(llres_out)
    weightsfile = os.path.join(weightsdir,'conservative_{}_{}.nc'.format(llres_in, llres_out))
    regridder = xe.Regridder(llgrid_in, llgrid_out, method='conservative', filename=weightsfile, reuse_weights=reuse_weights)
    return regridder

def make_regridder_C2L( csres_in, llres_out, weightsdir='.', reuse_weights=False, sg_params=None):
    weightsfilename_args={'csres_in': str(csres_in), 'llres_out': llres_out}
    if sg_params is None:
        csgrid, csgrid_list = make_grid_CS(csres_in)
        weightsfilename='conservative_c{csres_in}_{llres_out}_{face_num}.nc'
    else:
        csgrid, csgrid_list = make_grid_SG(csres_in, **sg_params)
        weightsfilename = 'conservative_sg{csres_in}_{sg_hash}_{llres_out}_{face_num}.nc'
        weightsfilename_args['sg_hash'] = hashlib.sha1(
            'sf={stretch_factor:.5f},tx={target_lon:.5f},ty={target_lat:.5f}'.format(**sg_params).encode()
        ).hexdigest()[:7]
    llgrid = make_grid_LL(llres_out)
    regridder_list = []
    for i in range(6):
        weightsfile = os.path.join(weightsdir, weightsfilename.format(**weightsfilename_args,face_num=str(i)))
        regridder = xe.Regridder(csgrid_list[i], llgrid, method='conservative', filename=weightsfile, reuse_weights=reuse_weights)
        regridder_list.append(regridder)
    return regridder_list


