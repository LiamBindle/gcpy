import argparse
import hashlib
import os.path

import numpy as np
import xarray as xr
import xesmf as xe

from gcpy.grid.horiz import make_grid_LL, make_grid_SG


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
    parser = argparse.ArgumentParser(description='Create a restart file for GCHP')
    parser.add_argument('-i', '--filein',
                        metavar='FILEIN',
                        type=str,
                        required=True,
                        help='input file')
    parser.add_argument('-o', '--fileout',
                        metavar='RES',
                        type=str,
                        required=True,
                        help='output file name')
    parser.add_argument('--cs_res',
                        metavar='RES',
                        type=int,
                        required=True,
                        help='cube-sphere resolution')
    parser.add_argument('--stretch_factor',
                        metavar='SF',
                        type=float,
                        required=False,
                        default=1.0,
                        help='stretch factor')
    parser.add_argument('--target_lat',
                        metavar='Y',
                        type=float,
                        required=False,
                        default=-90.0,
                        help='target latitude')
    parser.add_argument('--target_lon',
                        metavar='X',
                        type=float,
                        required=False,
                        default=170.0,
                        help='target latitude')
    parser.add_argument('--input_grid',
                        metavar='GRID',
                        type=str,
                        required=False,
                        choices=['2x2.5', '4x5'],
                        default=None,
                        help='input grid')
    parser.add_argument('--input_lev_positive',
                        metavar='DIRECTION',
                        type=str,
                        required=False,
                        choices=['up', 'down'],
                        default=None,
                        help='positive direction in lev coordinate')
    args = parser.parse_args()

    print(f'- Opening {args.filein}')
    ds_in = xr.open_dataset(args.filein, decode_cf=False)

    # Determine filein's grid
    input_grid = args.input_grid
    if args.input_grid is None:
        im_world = ds_in.dims['lon']
        jm_world = ds_in.dims['lat']
        if im_world == 144 and jm_world == 91:
            input_grid = "2x2.5"
        else:
            print("error: Couldn't determine the input grid! You should explicitly specify --inpute_grid")
            exit(1)

    lev_positive = args.input_lev_positive
    if lev_positive is None:
        if 'positive' in ds_in.lev.attrs:
            lev_positive = ds_in.lev.attrs['positive']
        elif 'long_name' in ds_in.lev.attrs and ds_in.lev.attrs['long_name'] == 'GEOS-Chem level':
            lev_positive = 'up'
            del ds_in.lev.attrs['long_name']
        else:
            print("error: Couldn't determine positive direction of levels in the input file! You should "
                  "explicitly specify --input_lev_positive")
            exit(1)
    ds_in.lev.attrs['positive'] = lev_positive

    # Make regridders
    print(f'- Regridding the input file ({input_grid}) ...')
    regridders = make_regridder_L2S(input_grid, args.cs_res, args.stretch_factor, args.target_lat, args.target_lon)
    ds_out = [regridder(ds_in, keep_attrs=True) for regridder in regridders]
    ds_out = xr.concat(ds_out, 'face')
    print(f'- Regridding is finished')

    print(f'- Reshaping the restart file ...')
    # Drop lat and lon
    ds_out = ds_out.drop(['lat', 'lon'])
    # Stack face and y coordinates
    ds_out = ds_out.stack(newy=['face', 'y'])
    ds_out = ds_out.assign_coords(
        newy=np.linspace(1.0, 6*args.cs_res, 6*args.cs_res), x=np.linspace(1.0, args.cs_res, args.cs_res)
    )
    ds_out = ds_out.rename({'newy': 'lat', 'x': 'lon'})

    # Transpose
    ds_out = ds_out.transpose('time', 'lev', 'lat', 'lon')

    # Sort so that lev is in descending order
    if lev_positive == 'up':
        print('- Flipping vertical coordinate')
        ds_out = ds_out.assign_coords({'lev': len(ds_out.lev) - ds_out.lev + 1})
    else:
        print('- The vertical coordinate does not need to be flipped')
    ds_out = ds_out.sortby(['lev'], ascending=True)

    # Change to float32
    for v in ds_out.variables:
        ds_out[v].values = ds_out[v].values.astype(np.float32)

    # Rename variables
    rename = {}
    for v in ds_out.variables:
        rename[v] = v.replace('SpeciesConc_', 'SPC_')
    ds_out = ds_out.rename(rename)

    ds_out['lev'].attrs = ds_in['lev'].attrs
    ds_out['lat'].attrs = ds_in['lat'].attrs
    ds_out['lon'].attrs = ds_in['lon'].attrs
    ds_out['time'].attrs = ds_in['time'].attrs

    # Write dataset
    ds_out.to_netcdf(
        args.fileout,
        format='NETCDF4_CLASSIC'
    )

    print(ds_out)
