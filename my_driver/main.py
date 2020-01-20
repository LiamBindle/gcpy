import gcpy

from gcpy import core, make_benchmark_conc_plots, make_benchmark_emis_plots

# make_benchmark_conc_plots(
#     ref='/extra-space/sgv/level-1/C48-control/GCHP.SpeciesConc.20160716_1200z.nc4',
#     # dev='/extra-space/sgv/level-1/C48-control-my-restart-file/GCHP.SpeciesConc.20160716_1200z.nc4',
#     dev='/extra-space/sgv/level-1/C34xSqrt2/GCHP.SpeciesConc.20160716_1200z.nc4',
#     refstr='Standard',
#     devstr='My Restart',
#     dst='Output',
#     restrict_cats=['Oxidants'],
#     plots=['sfc'],
#     overwrite=True,
#     use_cmap_RdBu=True,
#     dev_sg_params={'stretch_factor': 1.4141, 'target_lat': 33.75, 'target_lon': -84.39}
# )

make_benchmark_conc_plots(
    ref='/extra-space/restart-file-comparison/v2018-11/initial_GEOSChem_rst.2x25_benchmark.nc',
    #dev='/extra-space/restart-file-comparison/v2016-07/initial_GEOSChem_rst.4x5_benchmark.nc',
    dev='/extra-space/restart-file-comparison/mine/C48-control-restart.nc',
    refstr='v2018-11 Restart',
    devstr='My C48-control Restart',
    dst='Output',
    overwrite=True,
    use_cmap_RdBu=False,
    restrict_cats=['Oxidants'],
    ref_species_prefix='SpeciesRst_',
    dev_species_prefix='SPC_',
    plots=['sfc'],
    # dev_sg_params={'stretch_factor': 1.4141, 'target_lat': 33.75, 'target_lon': -84.39},
    # x_extent=[-84.39-15, -84.39+15],
    # y_extent=[33.75-7.5, 33.75+7.5],
)

# make_benchmark_emis_plots(
#     ref='/extra-space/sgv/level-1/C48-control/GCHP.Emissions.20160716_1200z.nc4',
#     dev='/extra-space/sgv/level-1/C48-control/GCHP.Emissions.20160716_1200z.nc4',
#     # dev='/extra-space/sgv/level-1/C34xSqrt2/GCHP.SpeciesConc.20160716_1200z.nc4',
#     refstr='Standard',
#     devstr='My Restart',
#     dst='Output',
#     plot_by_benchmark_cat=True,
#     plot_by_hco_cat=True,
#     overwrite=True,
#     flip_ref=True,
#     flip_dev=True,
#     # dev_sg_params={'stretch_factor': 1.4141, 'target_lat': 33.75, 'target_lon': -84.39}
# )