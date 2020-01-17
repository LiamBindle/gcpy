import sys
import hashlib
import os.path
import argparse
from datetime import datetime

import numpy as np
import xarray as xr
import xesmf as xe


from .grid.horiz import make_grid_LL,  make_grid_SG


def sg_hash(stretch_factor: float, target_lat: float, target_lon: float):
    return hashlib.sha1('sf={stretch_factor:.5f},tx={target_lon:.5f},ty={target_lat:.5f}'.format(
        stretch_factor=stretch_factor,
        target_lat=target_lat,
        target_lon=target_lon,
    ).encode()).hexdigest()[:7]


def make_regridder_L2S(llres_in, csres_out, stretch_factor, target_lat, target_lon, weightsdir='.'):
    csgrid, csgrid_list = make_grid_SG(csres_out, stretch_factor=stretch_factor, target_lat=target_lat, target_lon=target_lon)
    llgrid = make_grid_LL(llres_in)
    regridder_list = []
    for i in range(6):
        weightsfile = os.path.join(weightsdir, 'conservative_{llres_in}_sg{csres_out}_{sg_hash}_{face_num}.nc'.format(
            llres_in=llres_in,
            csres_out=csres_out,
            sg_hash=sg_hash(stretch_factor, target_lat, target_lon),
            face_num=i
        ))
        reuse_weights = os.path.exists(weightsfile)
        regridder = xe.Regridder(llgrid,
                                 csgrid_list[i],
                                 method='conservative',
                                 filename=weightsfile,
                                 reuse_weights=reuse_weights)
        regridder_list.append(regridder)
    return regridder_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generates a stretched grid initial restart file for GCHP.')
    parser.add_argument('--stretch-factor',
                        metavar='S',
                        nargs=1,
                        type=float,
                        required=True,
                        help='stretching factor')
    parser.add_argument('--target-lon',
                        metavar='X',
                        nargs=1,
                        type=float,
                        required=True,
                        help='target longitude')
    parser.add_argument('--target-lat',
                        metavar='Y',
                        nargs=1,
                        type=float,
                        required=True,
                        help='target latitude')
    parser.add_argument('--cs-res',
                        metavar='R',
                        nargs=1,
                        type=int,
                        required=True,
                        help='cube-sphere resolution')
    parser.add_argument('--llres',
                        metavar='R',
                        nargs=1,
                        type=str,
                        default=['2x2.5'],
                        choices=['2x2.5', '4x5'],
                        help='lat x lon resolution of input restart file')
    parser.add_argument('file_in',
                        type=str,
                        nargs=1,
                        help='path to the input restart file')
    args = parser.parse_args()

    stretch_factor = args.stretch_factor[0]
    csres = args.cs_res[0]
    target_lat = args.target_lat[0]
    target_lon = args.target_lon[0]
    llres = args.llres[0]

    # Open the input dataset
    ds_in = xr.open_dataset(args.file_in[0], decode_cf=False)

    # Regrid
    regridders = make_regridder_L2S(llres, csres, stretch_factor, target_lat, target_lon)
    ds_out = [regridder(ds_in, keep_attrs=True) for regridder in regridders]
    ds_out = xr.concat(ds_out, 'face')

    # Add standard names
    for v in ds_out:
        ds_out[v].attrs['standard_name'] = v

    ds_out.attrs['history'] = datetime.now().strftime('%c:') + ' '.join(sys.argv) + '\n' + ds_out.attrs['history']

    # Drop variables depending on simulation type
    if 'AREA' in ds_in.variables:
        ds_out = ds_out.drop(['AREA'])

    # Drop lat and lon
    ds_out = ds_out.drop(['lat', 'lon'])

    # Stack face and y coordinates
    ds_out = ds_out.stack(newy=['face', 'y'])
    ds_out = ds_out.assign_coords(newy=np.linspace(1.0, 6*csres, 6*csres), x=np.linspace(1.0, csres, csres))
    ds_out = ds_out.rename({'newy': 'lat', 'x': 'lon'})

    # Transpose
    ds_out = ds_out.transpose('time', 'lev', 'lat', 'lon')

    # Sort so that lev is in ascending order
    ds_out = ds_out.sortby(['lev'], ascending=True)

    # Change to float32
    for v in ds_out.variables:
        ds_out[v].values = ds_out[v].values.astype(np.float32)

    ds_out['lev'].attrs = ds_in['lev'].attrs
    ds_out['lat'].attrs = ds_in['lat'].attrs
    ds_out['lon'].attrs = ds_in['lon'].attrs
    ds_out['time'].attrs = ds_in['time'].attrs

    # Write dataset
    ds_out.to_netcdf(
        'initial_restart_file.nc',
        format='NETCDF4_CLASSIC'
    )