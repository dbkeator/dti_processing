#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 12:11:16 2021

@author: stevegranger
"""

import sys
import os
import io
from os import system,makedirs
import pandas as pd
import numpy as np
import json
from os.path import dirname, splitext,basename,isfile,isdir,join
from argparse import ArgumentParser
import datetime
import glob
import seaborn as sns
try:
    import glob2
except ImportError:
    print("trying to install required module: glob2")
    system('python -m pip install --upgrade pip glob2')
    import glob2

import subprocess
from subprocess import PIPE
import csv
from shutil import copy
import logging
import time
import platform
from utils import ants_registration,dsistudio,fsl,dcm2niix,find_convert_images
import nibabel as nib

try:
    import FURY
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
try:
    from fpdf import FPDF
except ImportError:
    print("trying to install required module: fpdf")
    system("python -m pip install --upgrade pip fpdf")
    from fpdf import FPDF

from pandas.plotting import table
#from dti import process_dti




def main(argv):
    parser = ArgumentParser(description='This software will run structural connectome processing in batch mode')
    parser.add_argument('-dir', dest='dir', required=True, help="Directory to process images from")
    parser.add_argument('-overwrite', action='store_true', required=False,
                        help="If flag set, everything will be re-run")

    args = parser.parse_args()
    # open log file
    timestr = time.strftime("%Y%m%d-%H%M%S")
    logger = logging.getLogger(join(args.dir,'connectomes_batch'))
    #hdlr = logging.FileHandler(join(LOG_DIR, timestr + "_log.txt"))
    hdlr = logging.FileHandler(join(args.dir,'connectomes_batch_' + timestr + "_log.txt"))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

    # find structural and DTI images
    image_dict = find_convert_images(source_dir=args.dir,out_dir=args.dir,logger=logger,convert=False)
    
    # run bet for eddy correction
    logger.info('Running BET for Diffusion Analysis')
    input_file = join("data",basename(image_dict["dti"]["nifti"]))
    output_file = join("output",splitext(basename(image_dict["dti"]["nifti"]))[0] +
                       "_brain.nii.gz")
    bet_command = [
        "bet",input_file,output_file,"-f","0.3","-g","0","-m"
    ]

    #fsl(source_dir=args.dir,out_dir=args.dir,input_file=input_file,logger=logger,output_file=output_file,kwargs=bet_command)
    
    ######create supplementary files to run eddy
    logger.info('Creating Supplementary Files for Eddy')
    file = open(image_dict["dti"]["json"],)
    data = json.load(file)
    df = pd.DataFrame.from_dict(data,orient='index')
    df.columns = ['info']
    echo_spacing = df.iloc[42]['info']
    EPIfacto = 112
    if df.iloc[47]['info'] == "j-": #A to P
           Phase = "0 -1 0" 
    elif df.iloc[47]['info'] == "j": #P to A 
        Phase = "0 1 0"
    elif df.iloc[47]['info'] == "i": #L to R
        Phase = "-1 0 0"
    elif df.iloc[47]['info'] == "i-": #R to L
        Phase = "1 0 0"
    else:
        logger.error("Phase encoding direction could not be found in json file...")
    acqpfourth = 0.001*((EPIfacto*(echo_spacing*1000))-1)
    acqp_params = Phase + ' ' + str(acqpfourth)
    acqpparamfinal = str(acqp_params)
    acqpparamfinal = acqpparamfinal.replace('[', '')
    acqpparamfinal = acqpparamfinal.replace(']', '')
    acqpparamfinal = acqpparamfinal.replace("'", '')
    acqp = open(join(args.dir,"acqp_params.txt"),"w")
    acqp.write(acqpparamfinal)
    acqp.close()
    #create the 
    with open(image_dict["dti"]["bval"], 'r') as file:
         datas = file.read().replace('\n', '')
    datah = io.StringIO(datas)
    df1 = pd.read_csv(datah, sep=" ")
    df1 = df1.columns.to_frame().T.append(df1, ignore_index=True)
    df1.columns = range(len(df1.columns))
    index = len(df1.columns)
    if len(df1.columns) < 30:
       logger.error('Too Few Directions to Reconstruct Images') 
       print()
       print('System Failure...Too Few Directions to Reconstruct Images')
       sys.exit()
    indexhere = [1] * index
    indexfinal =str(indexhere)
    indexfinal = indexfinal.replace(',', '')
    indexfinal = indexfinal.replace('[', '')
    indexfinal = indexfinal.replace(']', '')
    index= open(join(args.dir,"index.txt"),"w")
    index.write(indexfinal)
    index.close()
    
    
    # example of eddy
    logger.info('Running FSLs Eddy')
    mask_file = join("data",os.path.splitext(os.path.basename(image_dict["dti"]["nifti"]))[0]+"_brain_mask.nii.gz")
    out_file =join("output",splitext(basename(image_dict["dti"]["nifti"]))[0] +
                      "_brain.nii.gz")
    acq_eddy = join("data", "acqp_params.txt") 
    index_file = join("data", "index.txt") 
    out_file = join("output","dti_eddycuda_corrected_data") 
    bvec = join("data", basename(image_dict["dti"]["bvec"])) #too long path cannot find
    bval = join("data", basename(image_dict["dti"]["bval"])) #too long path cannot find 
        
    eddy_command = [
            "eddy", "--imain="+input_file,"--mask="+mask_file,"--acqp="+acq_eddy,
                "--index="+index_file,"--bvecs="+bvec, "--bvals="+bval,"--out="+out_file
        ]
    
    #fsl(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=eddy_command)
    
    #dti fit for FA and MD maps
    logger.info('Running FSLs DTIfit')   
    input_file = join("data","dti_eddycuda_corrected_data.nii.gz")
    output_file = join("output",splitext(basename(image_dict["dti"]["nifti"]))[0] +
                       "eddy_c_dtifit.nii.gz")
    dti_fit_command = [
        "dtifit","-k",input_file,"-r",bvec,"-b",bval,"-m",mask_file,"-o",output_file
    ]

    #fsl(source_dir=args.dir,out_dir=args.dir,input_file=input_file,logger=logger,output_file=output_file,kwargs=dti_fit_command)
           
    
 # make src file for quality
    logger.info('Running Make SRC File')
    source_file = join("data","dti_eddycuda_corrected_data.nii.gz")
    out_file=join("output","src_base")
    
    dsi_src = ["dsi_studio","--action=src",
                "--source="+source_file,"--output="+out_file,
                "--bval="+bval,"--bvec="+bvec]

    #dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsi_src)
    
 # check src file for quality
    logger.info('Running Quality Control for SRC')
    source_file = join("data","src_base.src.gz")
    dsiquality = ["dsi_studio","--action=qc",
                "--source="+source_file]

    #dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsiquality)
    
    # reconstruct the images (create fib file; QSDR method=7,GQI method = 4)
    logger.info('Running QSDR Reconstruction')
    source_file = join("data","src_base.src.gz")
    other_image = join("t1w:","data/"+basename(image_dict["structural"]["nifti"]))
    dsirecon = ["dsi_studio","--action=rec",
                  "--source="+source_file,
                  "--method=7",
                  "--param0=1.25",
                  "--param1=1",
                  "--half_sphere=1",
                  "--odf_order=8",
                  "--num_fiber=10",
                  "--scheme_balance=1",
                  "--check_btable=1",
                  "--other_image="+other_image]

    #dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsirecon)
    
    # run robust tractography whole brain
    logger.info('Running Whole Brain Tractography Analysis')
    source_file = glob.glob(join(args.dir,'*fib.gz'))
    source_file= basename(str(source_file)).replace("'", '').replace("]", '')
    source_file = join("data",source_file)
    output_file = join("output","count_connect.trk.gz")
    dsiruntract = ["dsi_studio","--action=trk",
                    "--source="+source_file,
                    "--seed_count=100000",
                    "--threshold_index=qa",
                    "--fa_threshold=0.00",
                    "--initial_dir=0",
                    "--seed_plan=0",
                    "--interpolation=0",
                    "--thread_count=12",
                    "--step_size=0",
                    "--turning_angle=65",
                    "--smoothing=.6",
                    "--min_length=10",
                    "--max_length=600",
                    "--output="+output_file]

    #dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsiruntract)
    
    
    # generate connectivity matrix and summary statistics
    logger.info('Running Generate Graph Theory Metrics')
    tract_file = join("data","count_connect.trk.gz")
    atlas=join("data","FreeSurferDKT.nii.gz")
    output_file = join("output","connectivity_countmeasures.txt")
    dsi_conn_comp = ["dsi_studio", "--action=ana",
                     "--source="+source_file,
                      "--tract="+tract_file,
                      "--connectivity="+atlas,
                      "--connectivity_value=count",
                      "--connectivity_type=end",
                      "--output="+output_file]

    #dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsi_conn_comp)

    #Generate images of tractography 
    logger.info('Creating Tractography Images')
    filename = join(args.dir,'count_connect.trk.gz')
    S = nib.streamlines.load(filename)
    scene = window.Scene()
    stream_actor = actor.line(S.streamlines)
    scene.set_camera(position=(0, 118.52, 128.20),focal_point=(113.30, 128.31, 76.56),view_up=(0.18, 0.00, 0.98))
    scene.add(stream_actor)
    window.record(scene, out_path=join(args.dir,'bundle1.png'), size=(5000, 5000))
    scene.camera_info()
    scene.set_camera(position=(180, 118.52, 128.20),focal_point=(113.30, 128.31, 76.56),view_up=(0.18, 0.00, 0.98))
    scene.add(stream_actor)
    window.record(scene, out_path=join(args.dir,'bundle2.png'), size=(5000, 5000))    
    images = [Image.open(x) for x in [join(args.dir,'bundle1.png'),join(args.dir,'bundle2.png')]]
    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in images:
      new_im.paste(im, (x_offset,0))
      x_offset += im.size[0]
    new_im.save(join(args.dir,'tractography.jpg'))
    
    #Generate motion plots
    logger.info('Generating Motion Plots')
    df2 = pd.read_csv(join(args.dir,'dti_eddycuda_corrected_data.eddy_movement_rms'), 
                  delimiter = " ")
    df2.columns = ['a', 'b','c','d','e']
    df2['Time'] = np.arange(len(df2))
    df2.loc[0] = 0
    Motionprior = df2["c"].mean()
    Motioncum = df2["a"].mean()
    def plot_df(df2, x, y, title="", xlabel='Time', ylabel='Motion', dpi=200):
        plt.figure(figsize=(7,4), dpi=dpi)
        plt.plot(x, y, color='red',label="relative to prior volume")
        plt.hlines(y = Motionprior,xmin=0,xmax=len(df2),linestyles='dotted',label='Average Motion = '+ str(Motionprior))
        plt.gca().set(title=title, xlabel=xlabel, ylabel=ylabel)
        plt.yticks(fontsize=10, alpha=.7)
        plt.legend(loc="upper left")
        plt.savefig(join(args.dir,'motion_relative_to_prior_volume.jpg'))
    plot_df(df2, x=df2.Time, y=df2.c, title='Subject Motion Relative To Prior Volume')    
    def plot_df(df2, x, y, title="", xlabel='Time', ylabel='Motion', dpi=200):
        plt.figure(figsize=(7,4), dpi=dpi)
        plt.plot(x, y, color='red',label="relative to prior volume")
        plt.hlines(y = Motioncum,xmin=0,xmax=len(df2),linestyles='dotted',label='Average Motion = '+ str(Motioncum))
        plt.gca().set(title=title, xlabel=xlabel, ylabel=ylabel)
        plt.yticks(fontsize=10, alpha=.7)
        plt.legend(loc="upper left")
        plt.savefig(join(args.dir,'cumulative_motion.jpg'))
    plot_df(df2, x=df2.Time, y=df2.a, title='Subject Motion Relative To Scan Start')  
    images2 = [Image.open(x) for x in [join(args.dir,'cumulative_motion.jpg'),join(args.dir,'motion_relative_to_prior_volume.jpg')]]
    widths, heights = zip(*(i.size for i in images2))
    total_width = sum(widths)
    max_height = max(heights)
    new_im = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in images2:
      new_im.paste(im, (x_offset,0))
      x_offset += im.size[0]
    new_im.save(join(args.dir,'motioncombined.jpg'))
    ####Create Scan Name File
    niftiFilenamesList = str(image_dict["dti"]["nifti"])
    NIIname = open(join(args.dir,"niftiname.txt"),"w")
    k=NIIname.write('Scan Identity\n')
    k=NIIname.write(niftiFilenamesList)
    NIIname.close()
    ###########################Plot and Save Connectivity Matrix######
    logger.info('Generating Connectivity Matrix')
    conn = pd.read_csv(join(args.dir,'connectivity_countmeasures.txt.FreeSurferDKT.count.end.connectogram.txt'),
                       sep="\t")
    conn = conn.drop(['data'],axis=1)
    conn.columns = conn.iloc[0]
    conn = conn.set_index('data')
    conn = conn.drop(['data'],axis=0)
    conn = conn.iloc[:, :-1]
    conn = conn.apply( pd.to_numeric, errors='coerce')
    fig, ax = plt.subplots(figsize=(15,15))
    here = sns.heatmap(conn,square=True)
    sns.set(font_scale=1.4)
    figure = plt.gcf()
    figure.set_size_inches(20, 20)
    plt.savefig(join(args.dir,"connectivity_matrix.jpg"), dpi=200,bbox_inches='tight')
    
    #############Save Efficiency data as file
    logger.info('Generating Efficiency Files')
    Eff = pd.read_csv(join(args.dir,'connectivity_countmeasures.txt.FreeSurferDKT.count.end.network_measures.txt'),
                        sep=" ",header=None)                 
    Ecc = str(Eff.iloc[9:11])
    Ecc = str(Ecc)
    Ecc = Ecc.replace('\\t', ' ')
    Ecc = Ecc.replace('9', '')
    Ecc = Ecc.replace('0', '')
    Ecc = Ecc.replace('1', '')
    Ecc = Ecc.strip()
    NIIname = open(join(args.dir,"globalefficiencyonly.txt"),"w")
    k=NIIname.write('Efficiency Measures\n')
    k=NIIname.write(Ecc)
    NIIname.close()

    #############Save QC as Table
    logger.info('Create and Save Quality Control File')
    quality = pd.read_csv(join(args.dir,'src_base.qc.txt'),sep='\t')
    quality.reset_index(inplace=True)
    quality = quality.set_axis(['File', 'Image Dimension', 'Resolution', 'DWI Count', 'Max b-value','Neighboring DWI Correlation','# Bad Slices','Extra'], axis=1,inplace=False)
    quality = quality.iloc[: , :-1]
    ax = plt.subplot(111, frame_on=False) # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis
    table1 = table(ax, quality,rowLabels=['']*quality.shape[0], loc='center')  # where df is your data frame
    table1.set_fontsize(300)
    table1.scale(8, 8)
    plt.savefig(join(args.dir,'QC_Table.jpg'),bbox_inches='tight')
    
    ############Creat Mosaic of T1 image
    fname_t1 = join(args.dir,image_dict["structural"]["nifti"])
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
    slice_actor2.display(slice_actor2.shape[0]//2, None, None)
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
    #show_m_mosaic = window.ShowManager(Scene, size=(1200, 900))
    #show_m_mosaic.initialize()
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
            #slice_mosaic.AddObserver('LeftButtonPressEvent',left_click_callback_mosaic,1.0)
            Scene.add(slice_mosaic)
            cnt += 1
            if cnt > Z:
                break
        if cnt > Z:
            break
    Scene.reset_camera()
    Scene.zoom(1.0)
    window.record(Scene, out_path=join(args.dir,'mosaic_T1.png'), size=(900, 600),reset_camera=False)
    
    
    #create FA image 
    fname_t1 = glob.glob(join(args.dir,'*FA.nii.gz'))
    print(fname_t1)
    fname_t1= str(fname_t1)
    fname_t1 = fname_t1.replace("'", '').replace("]", '').replace("[", '')
    print(fname_t1)
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
    slice_actor2.display(slice_actor2.shape[0]//2, None, None)
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
    cnt = 0
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
            Scene.add(slice_mosaic)
            cnt += 1
            if cnt > Z:
                break
        if cnt > Z:
            break
    Scene.reset_camera()
    Scene.zoom(1.0)
    window.record(Scene, out_path=join(args.dir,'mosaic_FA.png'), size=(900, 600),
                  reset_camera=False)

    
    #Generate PDF File
    ##############create the pdf report
    logger.info('Create PDF Report')
    title = 'Connectivity Analysis Report'
    today = datetime.date.today()
    class PDF(FPDF):
        def header(self):
            # Arial bold 15
            self.set_font('Times', 'B', 15)
            # Calculate width of title and position
            w = self.get_string_width(title) + 3
            self.set_x(10)
            # Colors of frame, background and text
            self.set_draw_color(0, 0, 150)
            self.set_fill_color(0, 0, 150)
            self.set_text_color(255)
            # Thickness of frame (1 mm)
            self.set_line_width(1)
            # Title
            self.cell(w, 9, title, 1, 1, 'L', 1)
            self.ln(1)
            self.cell(180, 0.2, '', 1, 1, 'C')
            # Line break
            self.ln(10)
        def chapter_body(self, name):
            self.set_font('Times', '', 10)
            self.text(175,18,str(today))
            # Read text file
            with open(join(args.dir,'niftiname.txt'), 'rb') as fh:
                txt = fh.read().decode('latin-1')
            # Times 12
            self.set_font('Times', '', 9)
            # Output justified text
            self.multi_cell(0, 5, txt)
            self.ln()
            self.image(join(args.dir,'QC_Table.jpg'),10,45,150)
            self.ln()
            # Mention in italics
            #self.set_font('', 'I')
            #self.text(10,40,'Subject Motion Report')
            self.image(join(args.dir,'motioncombined.jpg'), 10, 70, 200)
            self.set_font('Arial', 'B', 10)
            # Move to the right
            self.cell(80)
            # Line break
            self.ln(20)
            self.text(10,135,'Tractography Results')
            self.set_font('Times', '', 9)
            self.image(join(args.dir,'tractography.jpg'), 10, 140, 180)
            self.set_font('Arial', 'B', 10)
            # Move to the right
            self.cell(80)
            # Line break
            self.ln(20)
            self.text(10,195,'Connectivity Matrix')
            self.image(join(args.dir,'connectivity_matrix.jpg'), 10, 200, 100)
            self.set_font('Arial', 'B', 10)
            # Move to the right
            self.cell(80)
            # Line break
            self.ln(220)
            with open(join(args.dir,'globalefficiencyonly.txt'), 'rb') as fh:
                info = fh.read().decode('latin-1')
            self.set_font('Times', '', 9)
            self.multi_cell(0, 5, info)
        def print_chapter(self, num, title, name):
            self.add_page()
            self.chapter_body(name)
    pdf = PDF()
    pdf.print_chapter(1, '', '20k_c1.txt')
    pdf.output(join(args.dir,'Report.pdf'), 'F')
    

if __name__ == "__main__":
    main(sys.argv[1:])