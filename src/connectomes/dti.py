import sys
import os
from os import system

from utils import ants_registration,dsistudio,fsl,dcm2niix,find_convert_images
from __version__ import VERSION

import pandas as pd
import numpy as np
import json
import datetime
import glob
import seaborn as sns
from shutil import copy
import nibabel as nib
import shutil
from os.path import splitext,basename,join,isfile,isdir
import io

import time

try:
    import fury
except ImportError:
    print("trying to install required module: FURY")
    system("python -m pip install --upgrade pip FURY")

try:
    from dipy.viz import window, actor, ui
except ImportError:
    print("trying to install required module: dipy.viz")
    system("python -m pip install --upgrade pip dipy.viz")
    from dipy.viz import window, actor, ui
try:
    from dipy.io import read_bvals_bvecs
except ImportError:
    print("trying to install required module: dipy.io")
    system("python -m pip install --upgrade pip dipy.io")
    from dipy.io import read_bvals_bvecs
try:
    from dipy.core.gradients import gradient_table
except ImportError:
    print("trying to intsall required module: dipy.core.gradients")
    system("python -m pip install --upgrade pip dipy.core.gradients")
try:
    from dipy.reconst.dti import TensorModel, fractional_anisotropy, color_fa
except ImportError:
    print("trying to intsall required module: dipy.reconst.dti")
    system("python -m pip install --upgrade pip dipy.reconst.dti")
try:
    from scipy import ndimage
except ImportError:
    print("trying to install required module:scipy")
    system("python -m pip install --upgrade pip scipy")

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("trying to install required module: matplotlib")
    system("python -m pip install --upgrade pip matplotlib")
    import matplotlib.pyplot as plt

try:
    from PIL import Image
except ImportError:
    print("trying to install required module: PIL")
    system("python -m pip install --upgrade pip PIL")
    from PIL import Image

from pandas.plotting import table




key1 = {"FA" : "Fractional Anisotropy NIFTI Image",
       "MD" : "Mean Diffusivity NIFTI Image",
       "connectome_matrix_binary.csv": "Binary adjacency (connectivity) matrix of the atlas adjusted by 0.001 of the maximum",
       "connectome_matrix_weighted.csv":"Weighted adjacency (connectivity) matrix of the atlas where weights are equavalent to the number of streamlines connecting each node pair",
       "Connectometry_Report.html" : "Connectivity Analysis Report in html format",
       "connectome_matrix_normalized_weighted.csv":"Weighted adjacency (connectivity) matrix of the atlas where weights are normalized from a by the graph maximum and range from 0 to 1"
       }

key2 = {"input prefix" : "raw DWI file from given directory",
        "dti_eddycudanifti" : "FSLs eddy processed DWI file",
        "eddy_movement_rms" : "FSLs eddy motion file",
        "...eddy_c_dtifit.. files" : "All and Additional Eigenvector/Eigenvalue files from FSLs dtifit function",
        "count_connect.trk.gz" : "Whole brain tractography file used for adjacency matrix and graph measures calculation",
        "index.txt":"File equivalent to the number of subbricks in DWI file and used by FSLs eddy to reference lines on acqp_params.txt file",
        "acqp_params.txt": "File denoting the parameters for FSL eddy program",
        "globalefficiencyonly.txt":"File containing efficiency from networkmeasures.txt file generated from matlab toolbox used by DSI-Studio",
        "QC_Table.jpg":"Quality control table generated from src file from dsi studio",
        "bundle1.jpg bundle2.jpg tractography.jpg":"Renderings of whole brain tractography",
        "connectivity_countmeasures.txt":"File produced from DSI Studio Graph Theory Analysis",
        "*connectivity.mat":"Matlab version of the DSI-Studio-generated weighted adjacency matrix",
        "*.count.end.network_measures.txt":"Network measures generated from matlab toolbox used by DSI-Studio",
        "connectivity_matrix.jpg":"Visualization of the weighted network generated by DSI Studio and seaborn from python",
        "mosaic_FA.png mosaic_T1.png":"Mosaic visualization of the Fractional Anistropy images and T1-weighted image",
        "motion_relative_to_prior_volume.jpg cumulative_motion.jpg":"Motion plots with averages: one relative to the "
                                            "previous subbrick and one relative to the diplacement from scan start",
        "niftiname.txt":"Store the file path and name for the DWI file for html file and/or pdf file report",
        "src_base.qc.txt":"Text file version for the quality control report generated from DSI studio",
        "src_base.src.gz":"Preliminary DSI studio file that binds the bvalue and bvector information to the raw DWI file",
        "MPRAGE" : "T1 weighted image used in processing",
        "FAcolor.png": "Colored FA PNG Image"
        }

# minimum R-squared value to be considered a good fit of DTI to template
MIN_R2 = 60


def plot_df(df2, x, y, filename, Motion, plt, args,title="", xlabel='Time', ylabel='Motion', dpi=200):
    plt.figure(figsize=(7, 4), dpi=dpi)
    plt.plot(x, y, color='red', label="relative to prior volume")
    plt.hlines(y=Motion, xmin=0, xmax=len(df2), linestyles='dotted', label='Average Motion = ' + str(Motion))
    plt.gca().set(title=title, xlabel=xlabel, ylabel=ylabel)
    plt.yticks(fontsize=10, alpha=.7)
    plt.legend(loc="upper left")
    plt.savefig(join(args.dir, filename))


# load parameters file
# upload DSIParams file for reconstruction and tractography
def load_regparams(location):
    '''
    This function loads DSIParams.txt file and returns a dictionary of parameters
    :return:
    '''
    d = {}
    with open(join(location, "DSIParams.txt")) as f:
        for line in f:
            (key, val) = line.split()
            d[key] = val
    return d

def process_dti(image_dict, logger, args):

    logger.info("function: process_dti")

    # copy DSIParams.txt file to target directory
    copy(join(os.getcwd(), "DSIParams.txt"),args.dir)

    # load parameters
    regparams = load_regparams(args.dir)

    # run bet for eddy correction
    logger.info('Running BET for Diffusion Analysis')
    input_file = join("data", basename(image_dict["dti"]["nifti"]))
    output_file = join("output", splitext(basename(image_dict["dti"]["nifti"]))[0] + "_brain.nii.gz")
    bet_command = [
        "bet", input_file, output_file, "-f", "0.3", "-g", "0", "-m"
    ]

    fsl(source_dir=args.dir, out_dir=args.dir, input_file=input_file, logger=logger, output_file=output_file,
        kwargs=bet_command)

    ######create supplementary files to run eddy
    logger.info('Creating Supplementary Files for Eddy')
    file = open(image_dict["dti"]["json"], )
    data = json.load(file)
    df = pd.DataFrame.from_dict(data, orient='index')
    df.columns = ['info']
    echo_spacing = df.iloc[42]['info']
    EPIfacto = int(regparams['EPI_Factor:'])
    if df.iloc[47]['info'] == "j-":  # A to P
        Phase = "0 -1 0"
    elif df.iloc[47]['info'] == "j":  # P to A
        Phase = "0 1 0"
    elif df.iloc[47]['info'] == "i":  # L to R
        Phase = "-1 0 0"
    elif df.iloc[47]['info'] == "i-":  # R to L
        Phase = "1 0 0"
    else:
        logger.error("Phase encoding direction could not be found in json file...")
    acqpfourth = 0.001 * ((EPIfacto * (echo_spacing * 1000)) - 1)
    acqp_params = Phase + ' ' + str(acqpfourth)
    acqpparamfinal = str(acqp_params)
    acqpparamfinal = acqpparamfinal.replace('[', '').replace(']', '').replace("'", '')
    acqp = open(join(args.dir, "acqp_params.txt"), "w")
    acqp.write(acqpparamfinal)
    acqp.close()
    # create the index file
    with open(image_dict["dti"]["bval"], 'r') as file:
        datas = file.read().replace('\n', '')
    datah = io.StringIO(datas)
    df1 = pd.read_csv(datah, sep=" ")
    df1 = df1.columns.to_frame().T.append(df1, ignore_index=True)
    df1.columns = range(len(df1.columns))
    index = len(df1.columns)
    if len(df1.columns) < 30:
        logger.error('Too Few Directions to Reconstruct Images')
        return
    indexhere = [1] * index
    indexfinal = str(indexhere)
    indexfinal = indexfinal.replace(',', '').replace('[', '').replace(']', '')
    index = open(join(args.dir, "index.txt"), "w")
    index.write(indexfinal)
    index.close()

    # example of eddy
    logger.info('Running FSLs Eddy')
    mask_file = join("data", os.path.splitext(os.path.basename(image_dict["dti"]["nifti"]))[0] + "_brain_mask.nii.gz")
    out_file = join("output", splitext(basename(image_dict["dti"]["nifti"]))[0] +
                    "_brain.nii.gz")
    acq_eddy = join("data", "acqp_params.txt")
    index_file = join("data", "index.txt")
    out_file = join("output", "dti_eddycuda_corrected_data")
    bvec = join("data", basename(image_dict["dti"]["bvec"]))  # too long path cannot find
    bval = join("data", basename(image_dict["dti"]["bval"]))  # too long path cannot find

    eddy_command = [
        "eddy", "--imain=" + input_file, "--mask=" + mask_file, "--acqp=" + acq_eddy,
                "--index=" + index_file, "--bvecs=" + bvec, "--bvals=" + bval, "--out=" + out_file
    ]

    fsl(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=eddy_command)

    # dti fit for FA and MD maps
    logger.info('Running FSLs DTIfit')
    input_file = join("data", "dti_eddycuda_corrected_data.nii.gz")
    output_file = join("output", splitext(basename(image_dict["dti"]["nifti"]))[0] +
                       "eddy_c_dtifit.nii.gz")
    dti_fit_command = [
        "dtifit", "-k", input_file, "-r", bvec, "-b", bval, "-m", mask_file, "-o", output_file
    ]

    fsl(source_dir=args.dir, out_dir=args.dir, input_file=input_file, logger=logger, output_file=output_file,
        kwargs=dti_fit_command)

    # make src file for quality
    logger.info('Running Make SRC File')
    source_file = join("data", "dti_eddycuda_corrected_data.nii.gz")
    out_file = join("output", "src_base")
    newbvec = join("data", "dti_eddycuda_corrected_data.eddy_rotated_bvecs")

    dsi_src = ["dsi_studio", "--action=src",
               "--source=" + source_file, "--output=" + out_file,
               "--bval=" + bval, "--bvec=" + newbvec]

    dsistudio(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=dsi_src)

    # check src file for quality
    logger.info('Running Quality Control for SRC')
    source_file = join("data", "src_base.src.gz")
    dsiquality = ["dsi_studio", "--action=qc",
                  "--source=" + source_file]

    dsistudio(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=dsiquality)

    # reconstruct the images (create fib file; QSDR method=7,GQI method = 4)
    logger.info('Running QSDR Reconstruction')
    source_file = join("data", "src_base.src.gz")
    other_image = join("t1w:", "data/" + basename(image_dict["structural"]["nifti"]))
    dsirecon = ["dsi_studio", "--action=rec",
                "--source=" + source_file,
                "--method=" + regparams['method:'],
                "--param0=" + regparams['param0:'],
                "--param1=" + regparams['param1:'],
                "--half_sphere=" + regparams['half-shere:'],
                "--odf_order=" + regparams['odf_order:'],
                "--num_fiber=" + regparams['num_fiber:'],
                "--scheme_balance=" + regparams['scheme_balance:'],
                "--check_btable=" + regparams['check_btable:'],
                "--other_image=" + other_image]

    dsistudio(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=dsirecon)

    # run robust tractography whole brain
    logger.info('Running Whole Brain Tractography Analysis')
    source_file = glob.glob(join(args.dir, '*fib.gz'))
    source_file = basename(str(source_file)).replace("'", '').replace("]", '')
    source_file = join("data", source_file)
    output_file = join("output", "count_connect.trk.gz")
    dsiruntract = ["dsi_studio", "--action=trk",
                   "--source=" + source_file,
                   "--seed_count=" + regparams['seed_count:'],
                   "--threshold_index=" + regparams['threshold_index:'],
                   "--fa_threshold=" + regparams['fa_threshold:'],
                   "--initial_dir=" + regparams['initial_dir:'],
                   "--seed_plan=" + regparams['seed_plan:'],
                   "--interpolation=" + regparams['interpolation:'],
                   "--thread_count=" + regparams['thread_count:'],
                   "--step_size=" + regparams['step_size:'],
                   "--turning_angle=" + regparams['turning_angle:'],
                   "--smoothing=" + regparams['smoothing:'],
                   "--min_length=" + regparams['min_length:'],
                   "--max_length=" + regparams['max_length:'],
                   "--output=" + output_file]

    dsistudio(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=dsiruntract)

    # generate connectivity matrix and summary statistics
    logger.info('Running Generate Graph Theory Metrics')
    tract_file = join("data", "count_connect.trk.gz")
    atlas = join("opt", "dsi-studio", "dsi_studio_64", "atlas", "ICBM152", "AAL2.nii.gz")
    output_file = join("output", "connectivity_countmeasures.txt")
    dsi_conn_comp = ["dsi_studio", "--action=ana",
                     "--source=" + source_file,
                     "--tract=" + tract_file,
                     "--connectivity=" + atlas,
                     "--connectivity_threshold=" + regparams['Threshold:'],
                     "--connectivity_value=count",
                     "--connectivity_type=end",
                     "--output=" + output_file]

    dsistudio(source_dir=args.dir, out_dir=args.dir, logger=logger, kwargs=dsi_conn_comp)

    # Generate images of tractography
    logger.info('Creating Tractography Images')
    filename = join(args.dir, 'count_connect.trk.gz')
    S = nib.streamlines.load(filename)
    scene = window.Scene()
    stream_actor = actor.line(S.streamlines)
    scene.set_camera(position=(0, 118.52, 128.20), focal_point=(113.30, 128.31, 76.56), view_up=(0.18, 0.00, 0.98))
    scene.add(stream_actor)
    window.record(scene, out_path=join(args.dir, 'bundle1.png'), size=(5000, 5000))
    scene.camera_info()
    scene.set_camera(position=(180, 118.52, 128.20), focal_point=(113.30, 128.31, 76.56), view_up=(0.18, 0.00, 0.98))
    scene.add(stream_actor)
    window.record(scene, out_path=join(args.dir, 'bundle2.png'), size=(5000, 5000))
    images = [Image.open(x) for x in [join(args.dir, 'bundle1.png'), join(args.dir, 'bundle2.png')]]
    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]
    new_im.save(join(args.dir, 'tractography.jpg'))

    # Generate motion plots
    logger.info('Generating Motion Plots')
    df2 = pd.read_csv(join(args.dir, 'dti_eddycuda_corrected_data.eddy_movement_rms'),
                      delimiter=" ")
    df2.columns = ['a', 'b', 'c', 'd', 'e']
    df2['Time'] = np.arange(len(df2))
    df2.loc[0] = 0
    Motionprior = df2["c"].mean()
    Motioncum = df2["a"].mean()



    plot_df(df2, x=df2.Time, y=df2.c, Motion=Motionprior,plt=plt,args=args, filename= 'motion_relative_to_prior_volume.jpg',title='Subject Motion Relative To Prior Volume')
    plot_df(df2, x=df2.Time, y=df2.a,Motion=Motioncum, plt=plt, args=args, filename='cumulative_motion.jpg', title='Subject Motion Relative To Scan Start')


    images2 = [Image.open(x) for x in
               [join(args.dir, 'cumulative_motion.jpg'), join(args.dir, 'motion_relative_to_prior_volume.jpg')]]
    widths, heights = zip(*(i.size for i in images2))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in images2:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]
    new_im.save(join(args.dir, 'motioncombined.jpg'))
    ####Create Scan Name File
    niftiFilenamesList = str(image_dict["dti"]["nifti"])
    NIIname = open(join(args.dir, "niftiname.txt"), "w")
    k = NIIname.write('Scan Identity\n')
    k = NIIname.write(niftiFilenamesList)
    NIIname.close()
    ###########################Plot and Save Connectivity Matrix######
    logger.info('Generating Connectivity Matrix')
    conn = pd.read_csv(
        (str(glob.glob(join(args.dir, '*connectogram.txt'))).replace("'", '').replace("]", '').replace("[", '')),
        sep="\t")
    conn = conn.drop(['data'], axis=1)
    conn.columns = conn.iloc[0]
    conn = conn.set_index('data')
    conn = conn.drop(['data'], axis=0)
    conn = conn.iloc[:, :-1]
    conn = conn.apply(pd.to_numeric, errors='coerce')
    fig, ax = plt.subplots(figsize=(15, 15))
    mask = np.zeros_like(conn)
    mask[conn < 1] = 1
    maxi = conn.max(numeric_only=True).max()
    split = maxi / 2
    quart1 = maxi * .25
    quart2 = maxi * .75
    here = sns.heatmap(conn, mask=mask, square=True, cmap="jet", xticklabels=True, yticklabels=True,
                       cbar_kws={'label': 'Number of Streamlines',
                                 'ticks': [1, int(quart1), int(split), int(quart2), maxi]}, linewidths=.2)
    here.set_facecolor('xkcd:gray')
    sns.set(font_scale=1.4)
    figure = plt.gcf()
    figure.set_size_inches(20, 20)
    plt.savefig(join(args.dir, "connectivity_matrix.jpg"), dpi=1000, bbox_inches='tight')

    #############Save Efficiency data as file
    logger.info('Generating Efficiency Files')

    Eff = pd.read_csv((str(glob.glob(join(args.dir, '*count.end.network_measures.txt'))).replace("'", '').replace("]",
                                                                                                                  '').replace(
        "[", '')), sep=" ", header=None)
    Ecc = str(Eff.iloc[9:11])
    Ecc = str(Ecc)
    Ecc = Ecc.replace('\\t', ' ').replace('9', '').replace('0', '').replace('1', '')
    Ecc = Ecc.strip()
    NIIname = open(join(args.dir, "globalefficiencyonly.txt"), "w")
    k = NIIname.write('Efficiency Measures\n')
    k = NIIname.write(Ecc)
    NIIname.close()

    #############Save QC as Table
    logger.info('Create and Save Quality Control File')
    quality = pd.read_csv(join(args.dir, 'src_base.qc.txt'), sep='\t')
    quality.reset_index(inplace=True)
    quality = quality.set_axis(
        ['File', 'Image Dimension', 'Resolution', 'DWI Count', 'Max b-value', 'Neighboring DWI Correlation',
         '# Bad Slices', 'Extra'], axis=1, inplace=False)
    quality = quality.iloc[:, :-1]
    ax = plt.subplot(111, frame_on=False)  # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    table1 = table(ax, quality, rowLabels=[''] * quality.shape[0], loc='center')  # where df is your data frame
    table1.set_fontsize(300)
    table1.scale(8, 8)
    plt.savefig(join(args.dir, 'QC_Table.jpg'), bbox_inches='tight')

    # Create DIPY FA color image
    fname_t1 = join(args.dir, 'dti_eddycuda_corrected_data.nii.gz')
    img = nib.load(fname_t1)
    data = img.get_data()
    bval = join(args.dir, image_dict["dti"]["bval"])
    bvec = join(args.dir, 'dti_eddycuda_corrected_data.eddy_rotated_bvecs')
    bvals, bvecs = read_bvals_bvecs(bval, bvec)
    gtab = gradient_table(bvals, bvecs)
    ten = TensorModel(gtab)
    mask1 = str(glob.glob(join(args.dir, '*mask.nii.gz'))).replace("'", '').replace("]", '').replace("[", '')
    print(mask1)
    mask1 = nib.load(mask1)
    mask1 = mask1.get_data()
    tenfit = ten.fit(data, mask=mask1)
    fa = fractional_anisotropy(tenfit.evals)
    cfa = color_fa(fa, tenfit.evecs)
    fig, ax = plt.subplots(1, 2, figsize=(10, 10))
    ax[0].imshow(ndimage.rotate(cfa[:, :, cfa.shape[2] // 2, :], 90, reshape=False))
    fig.delaxes(ax[1])
    fig.savefig(join(args.dir, 'FAcolor.png'), dpi=700,
                bbox_inches="tight")

    ############Creat Mosaic of T1 image
    fname_t1 = join(args.dir, basename(image_dict["structural"]["nifti"]))
    img = nib.load(fname_t1)
    data = img.get_data()
    affine = img.affine
    Scene = window.Scene()
    Scene.background((0.5, 0.5, 0.5))
    mean, std = data[data > 0].mean(), data[data > 0].std()
    value_range = (mean - 3 * std, mean + 3 * std)
    slice_actor = actor.slicer(data, affine, value_range)
    Scene.add(slice_actor)
    slice_actor2 = slice_actor.copy()
    slice_actor2.display(slice_actor2.shape[0] // 2, None, None)
    Scene.add(slice_actor2)
    Scene.reset_camera()
    Scene.zoom(1.4)
    show_m = window.ShowManager(Scene, size=(1200, 900))
    show_m.initialize()
    label_position = ui.TextBlock2D(text='Position:')
    label_value = ui.TextBlock2D(text='Value:')
    result_position = ui.TextBlock2D(text='')
    result_value = ui.TextBlock2D(text='')
    panel_picking = ui.Panel2D(size=(250, 125),
                               position=(20, 20),
                               color=(0, 0, 0),
                               opacity=0,
                               align="left")
    panel_picking.add_element(label_position, (0.1, 0.55))
    panel_picking.add_element(label_value, (0.1, 0.25))
    panel_picking.add_element(result_position, (0.45, 0.55))
    panel_picking.add_element(result_value, (0.45, 0.25))
    Scene.add(panel_picking)
    Scene.clear()
    Scene.projection('parallel')
    result_position.message = ''
    result_value.message = ''
    # show_m_mosaic = window.ShowManager(Scene, size=(1200, 900))
    # show_m_mosaic.initialize()
    cnt = 100
    X, Y, Z = slice_actor.shape[:3]
    rows = 10
    cols = 4
    border = 70
    for j in range(rows):
        for i in range(cols):
            slice_mosaic = slice_actor.copy()
            slice_mosaic.display(None, None, cnt)
            slice_mosaic.SetPosition((X + border) * i,
                                     5 * cols * (Y + border) - (Y + border) * j,
                                     0)
            slice_mosaic.SetInterpolate(False)
            # slice_mosaic.AddObserver('LeftButtonPressEvent',left_click_callback_mosaic,1.0)
            Scene.add(slice_mosaic)
            cnt += 1
            if cnt > Z:
                break
        if cnt > Z:
            break
    Scene.reset_camera()
    Scene.zoom(1.0)
    window.record(Scene, out_path=join(args.dir, 'mosaic_T1.png'), size=(900, 600), reset_camera=False)

    # create FA image
    fname_t1 = glob.glob(join(args.dir, '*FA.nii.gz'))
    fname_t1 = str(fname_t1)
    fname_t1 = fname_t1.replace("'", '').replace("]", '').replace("[", '')
    img = nib.load(fname_t1)
    data = img.get_data()
    affine = img.affine
    Scene = window.Scene()
    Scene.background((0.5, 0.5, 0.5))
    mean, std = data[data > 0].mean(), data[data > 0].std()
    value_range = (mean - 3 * std, mean + 3 * std)
    slice_actor = actor.slicer(data, affine, value_range)
    Scene.add(slice_actor)
    slice_actor2 = slice_actor.copy()
    slice_actor2.display(slice_actor2.shape[0] // 2, None, None)
    Scene.add(slice_actor2)
    Scene.reset_camera()
    Scene.zoom(1.4)
    show_m = window.ShowManager(Scene, size=(1200, 900))
    show_m.initialize()
    label_position = ui.TextBlock2D(text='Position:')
    label_value = ui.TextBlock2D(text='Value:')
    result_position = ui.TextBlock2D(text='')
    result_value = ui.TextBlock2D(text='')
    panel_picking = ui.Panel2D(size=(250, 125),
                               position=(20, 20),
                               color=(0, 0, 0),
                               opacity=0.75,
                               align="left")
    panel_picking.add_element(label_position, (0.1, 0.55))
    panel_picking.add_element(label_value, (0.1, 0.25))
    panel_picking.add_element(result_position, (0.45, 0.55))
    panel_picking.add_element(result_value, (0.45, 0.25))
    Scene.add(panel_picking)
    Scene.clear()
    Scene.projection('parallel')
    result_position.message = ''
    result_value.message = ''
    cnt = 1
    X, Y, Z = slice_actor.shape[:3]
    Z = Z-2
    rows = 10
    cols = 4
    border = 70
    for j in range(rows):
        for i in range(cols):
            slice_mosaic = slice_actor.copy()
            slice_mosaic.display(None, None, cnt)
            slice_mosaic.SetPosition((X + border) * i,
                                     5 * cols * (Y + border) - (Y + border) * j,
                                     0)
            slice_mosaic.SetInterpolate(False)
            Scene.add(slice_mosaic)
            cnt += 1
            if cnt > Z:
                break
        if cnt > Z:
            break
    Scene.reset_camera()
    Scene.zoom(1.0)
    window.record(Scene, out_path=join(args.dir, 'mosaic_FA.png'), size=(900, 600),
                  reset_camera=False)

    # Create formatted Weighted and Binary Adjacency Matrix save as csv files
    conn = pd.read_csv(
        (str(glob.glob(join(args.dir, '*connectogram.txt'))).replace("'", '').replace("]", '').replace("[", '')),
        sep="\t")
    conn = conn.drop(['data'], axis=1)
    conn.columns = conn.iloc[0]
    conn = conn.set_index('data')
    conn = conn.drop(['data'], axis=0)
    conn = conn.iloc[:, :-1]
    conn = conn.apply(pd.to_numeric, errors='coerce')
    conn.to_csv(join(args.dir, 'connectome_matrix_weighted.csv'))
    maxi = conn.max(numeric_only=True).max()
    norm = conn/maxi
    norm.to_csv(join(args.dir, 'connectome_matrix_normalized_weighted.csv'))
    
    conn[conn < 0.001 * maxi] = 0
    conn[conn > 0.001 * maxi] = 1
    conn.to_csv(join(args.dir, 'connectome_matrix_binary.csv'))

    # add files an hyperlinks to keys
    my_dict = key2.copy()
    my_dict[str(glob.glob(join(args.dir, basename(image_dict["dti"]["nifti"]))))] = my_dict.pop("input prefix")
    my_dict[str(glob.glob(join(args.dir, "dti*nii.gz")))] = my_dict.pop("dti_eddycudanifti")
    my_dict[str(glob.glob(join(args.dir, "*eddy_movement_rms")))] = my_dict.pop("eddy_movement_rms")
    my_dict[str(glob.glob(join(args.dir, "*dtifit*")))] = my_dict.pop("...eddy_c_dtifit.. files")
    my_dict[str(glob.glob(join(args.dir, basename(image_dict["structural"]["nifti"]))))] = my_dict.pop("MPRAGE")

    file = open(join(args.dir, "key2.txt"), "w")
    for key, value in my_dict.items():
        file.write('%s  : \t%s\n\n' % (key, value))
    file.close()

    # write files for main directory
    my_dict1 = key1.copy()
    #my_dict1[str(glob.glob(join(args.dir, "*FA.nii.gz")))] = my_dict1.pop("FA")
    my_dict1["FA.nii.gz"] = my_dict1.pop("FA")
    #my_dict1[str(glob.glob(join(args.dir, "*MD.nii.gz")))] = my_dict1.pop("MD")
    my_dict1["MD.nii.gz"] = my_dict1.pop("MD")
    file = open(join(args.dir, "key1.txt"), "w")
    for key, value in my_dict1.items():
        file.write('%s  :  %s\n' % (key, value))
    file.close()

    # Sort files
    file_list = glob.glob(join(args.dir, '*jpg')) + glob.glob(join(args.dir, '*png')) + glob.glob(
        join(args.dir, '*txt*')) + glob.glob(join(args.dir, '*dti*')) + glob.glob(
        join(args.dir, '*src*gz')) + glob.glob(join(args.dir, '*trk.gz')) + glob.glob(join(args.dir, '*csv'))

    # if the output directory doesn't exist then create it.
    if not isdir (join(args.dir, 'Structural_Connectomes')):
        os.mkdir(join(args.dir, 'Structural_Connectomes'))
        os.mkdir(join(args.dir, 'Structural_Connectomes', 'Files'))

    # copy files to final destination
    for files in file_list:
        files = basename(str(files)).replace("'", '').replace("]", '').replace("[", '')
        shutil.move(join(args.dir, files), join(args.dir, 'Structural_Connectomes', 'Files', files))

    # move out MPRAGE, FA, MD, and weighted and  file to save as csv and add to 'key'
    outfile = [glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', "*FA.nii.gz")),
               glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', "*MD.nii.gz")),
               glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', 'key1.txt')),
               join(args.dir, 'Structural_Connectomes', 'Files', 'connectome_matrix_weighted.csv'),
               join(args.dir, 'Structural_Connectomes', 'Files', 'connectome_matrix_binary.csv'),
               join(args.dir, 'Structural_Connectomes', 'Files', 'connectome_matrix_normalized_weighted.csv')
               ]
    for files in outfile:
        files = basename(str(files)).replace("'", '').replace("]", '').replace("[", '')
        shutil.move(join(args.dir, 'Structural_Connectomes', 'Files', files),
                    join(args.dir, 'Structural_Connectomes', files))
    # copy key file to Files directory
    copy(str(join(os.path.abspath(os.getcwd()), 'DSIParams.txt')), join(args.dir, 'Structural_Connectomes', 'Files'))

    # Rename some files
    FA = glob.glob(join(args.dir, 'Structural_Connectomes', "*FA.nii.gz"))
    FA = str(FA).replace("'", '').replace("]", '').replace("[", '')
    MD = glob.glob(join(args.dir, 'Structural_Connectomes', "*MD.nii.gz"))
    MD = str(MD).replace("'", '').replace("]", '').replace("[", '')
    os.rename(FA,
              join(args.dir, 'Structural_Connectomes', "FA.nii.gz"))
    os.rename(MD,
              join(args.dir, 'Structural_Connectomes', "MD.nii.gz"))
    os.rename(join(args.dir, 'Structural_Connectomes', "key1.txt"),
              join(args.dir, 'Structural_Connectomes', 'key.txt'))
    os.rename(join(args.dir, 'Structural_Connectomes', 'Files', "key2.txt"),
              join(args.dir, 'Structural_Connectomes', 'Files', 'key.txt'))

    # create html report
    create_html(args, image_dict)



def create_html(args,image_dict):
    '''
    This function creates the html report called report.html and lives in the StructuralConnectomes
    folder.
    :param args: args structure
    :param image_dict: images dictionary
    :return: None
    '''

    # Create HTML report
    page_title_text = 'Connectometry Report'
    title_text = 'Structural Connectivity Report'
    patient_file = args.dir
    Date = str(datetime.datetime.now())
    ScanTime =  str(time.ctime(os.path.getctime(join(args.dir, basename(image_dict["structural"]["nifti"])))))


    Diff = str(basename(image_dict["dti"]["nifti"]))
    Bval = str(basename(image_dict["dti"]["bval"]))
    Bvec = str(basename(image_dict["dti"]["bvec"]))
    MPRAGE = str(basename(image_dict["structural"]["nifti"]))
    SoftwareVersion = 'Software Version: ' + VERSION
    QC = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'QC_Table.jpg')
    Motion = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'motioncombined.jpg')
    Tracts = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'tractography.jpg')
    Conn = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'connectivity_matrix.jpg')
    Bin = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'connectome_matrix_binary.csv')
    Weight = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'connectome_matrix_weighted.csv')
    FAcol = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'mosaic_FA.png')
    GraphTheoryMetrics = str(
        glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', '*count.end.network_measures.txt'))).replace("'",
                                                                                                                 '').replace(
        "]", '').replace("[", '')
    print(GraphTheoryMetrics)
    all_graph1 = pd.read_csv(
        str(glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', '*count.end.network_measures.txt'))).replace(
            "'", '').replace("]", '').replace("[", ''),
        error_bad_lines=False, delim_whitespace=True, header=None, warn_bad_lines=False)
    all_graph1_T = all_graph1.T
    new_header = all_graph1_T.iloc[0]
    all_graph1_T = all_graph1_T[1:]
    all_graph1_T.columns = new_header
    all_graph1_T.to_csv(join(args.dir, 'Structural_Connectomes', 'Graph_Theoretic_Measures.csv'), index=None)
    GraphSimp = join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Graph_Theoretic_Measures.csv')
    DSIparam = str(join(os.path.abspath(args.dir), 'Structural_Connectomes', 'Files', 'DSIParams.txt'))

    Atlas = str(glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', '*count.end.network_measures.txt')))
    start = Atlas.find("connectivity_countmeasures.txt.") + len("connectivity_countmeasures.txt.")
    end = Atlas.find(".count.end.network_measures.txt")
    Atlas = str(Atlas[start:end])
    Atlas = ('The number of streamlines connecting nodes of the ' + Atlas + ' atlas')
    Dens = all_graph1.iloc[0, 1]
    clust_b = all_graph1.iloc[1, 1]
    clust_w = all_graph1.iloc[2, 1]
    tran_b = all_graph1.iloc[3, 1]
    tran_w = all_graph1.iloc[4, 1]
    netch_b = all_graph1.iloc[5, 1]
    netch_w = all_graph1.iloc[6, 1]
    SW_b = all_graph1.iloc[7, 1]
    SW_w = all_graph1.iloc[8, 1]
    globe_b = all_graph1.iloc[9, 1]
    globe_w = all_graph1.iloc[10, 1]
    dia_b = all_graph1.iloc[11, 1]
    dia_w = all_graph1.iloc[12, 1]
    rad_b = all_graph1.iloc[13, 1]
    rad_w = all_graph1.iloc[14, 1]
    asso_b = all_graph1.iloc[15, 1]
    asso_w = all_graph1.iloc[16, 1]
    R2 = str(glob.glob(join(args.dir, 'Structural_Connectomes', 'Files', '*fib.gz')))  # get R2 for quality
    start = R2.find("R") + len("R")
    end = R2.find(".fib.gz")
    R2 = R2[start:end]
    R2 = int(R2)
    if R2 >= MIN_R2:
        Com = ('The R-squared value is ' + str(R2) + ' indicating good fit to the template')
    else:
        Com = ('WARNING PLEASE CHECK DATA: The R-squared value is ' + str(
            R2) + ' indicating a weak fit to the template space')

    html = f'''
                    <html>
                        <head>
                            <title>{page_title_text}</title>
                        </head>
                        <body>
                            <h2>{title_text}</h1>
                            <p><b>Scan Process Date:</b> {Date}</h1>
                            <p><b>Scan Date:</b> {ScanTime}</h1>
                            <p><b>DTI Scan:</b> {Diff}</p>
                            <p><b>DTI b-value:</b> {Bval}</p>
                            <p><b>DTI b-vector:</b> {Bvec}</p>
                            <p><b>Structural Scan:</b> {MPRAGE}</p>
                            <p><b>Patient Folder:</b> {patient_file}</p>
                            <p><b>{SoftwareVersion}</b></p>
                            <h2>Quality Control</h2>
                            <p>{Com}</p>
                            <img src='{QC}' width="1200"><br>
                            <a href="{QC}">Quality Control</a>
                            <h2>Subject Head Motion</h2>
                            <img src='{Motion}' width="1000"><br>
                            <a href="{Motion}">Motion Plots</a>
                            <h2>Fractional Anisotropy Mosaic</h2>
                            <img src='{FAcol}' width="800"><br>
                            <a href="{FAcol}">Fractional Anisotropy Mosaic</a>
                            <h2>Tractography Results</h2>
                            <img src='{Tracts}' width="1000"><br>
                            <a href="{Tracts}">Tractography Images</a>
                            <h2>Connectivity Matrix</h2>
                            <p>{Atlas}</p>
                            <img src='{Conn}' width="1500"><br>
                            <a href="{Conn}">Connectivity Matrix Image</a>
                            <h2>Network Measures</h2>
                            <a href="{GraphSimp}">Graph Density:<a> {Dens} <br>
                            <a href="{GraphSimp}">Clustering Coefficient Ave Binary:<a> {clust_b} <br>
                            <a href="{GraphSimp}">Clustering Coefficient Ave Weighted:<a> {clust_w} <br>
                            <a href="{GraphSimp}">Transitivity Binary:<a> {tran_b} <br>
                            <a href="{GraphSimp}">Transitivity Weighted:<a> {tran_w} <br>
                            <a href="{GraphSimp}">Network Characteristic Path Length Binary:<a> {netch_b} <br>
                            <a href="{GraphSimp}">Network Characteristic Path Length Weighted:<a> {netch_w} <br>
                            <a href="{GraphSimp}">Small Worldness Binary:<a> {SW_b} <br>
                            <a href="{GraphSimp}">Small Worldness Weighted:<a> {SW_w} <br>
                            <a href="{GraphSimp}">Global Efficiency Binary:<a> {globe_b} <br>
                            <a href="{GraphSimp}">Global Efficiency Weighted:<a> {globe_w} <br>
                            <a href="{GraphSimp}">Graph Diameter Binary:<a> {dia_b} <br>
                            <a href="{GraphSimp}">Graph Diameter Weighted:<a> {dia_w} <br>
                            <a href="{GraphSimp}">Graph Radius Binary:<a> {rad_b} <br>
                            <a href="{GraphSimp}">Graph Radius Weighted:<a> {rad_w} <br>
                            <a href="{GraphSimp}">Assortativity Coefficient Binary:<a> {asso_b} <br>
                            <a href="{GraphSimp}">Assortativity Coefficient Weighted:<a> {asso_w} <br>
                            <h2>Additional Files</h2><br>
                            <a href="{GraphTheoryMetrics}">All Graph Theory Metrics<a> <br>
                            <a href="{Bin}">Binary Adjacency Matrix<a> <br>
                            <a href="{DSIparam}">DSI Params File<a><br>
                            <a href="{Weight}">Weighted Adjacency Matrix</a>
                        </body>
                    </html>
                    '''
    # 3. Write the html string as an HTML file
    with open(join(args.dir, 'Structural_Connectomes', 'report.html'), 'w') as f:
        f.write(html)