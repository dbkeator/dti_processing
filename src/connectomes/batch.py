import sys
import os
from os import system,makedirs
from os.path import dirname, splitext,basename,isfile,isdir,join
from argparse import ArgumentParser
import datetime
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
from connectomes.utils import ants_registration,dsistudio,fsl,dcm2niix,find_convert_images
from connectomes.dti import process_dti

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


    # start diffusion processing
    process_dti(image_dict=image_dict,logger=logger)


    # example running registration
    ants_registration(source_dir=args.dir,out_dir=args.dir,logger=logger,
                      moving_image="T1.nii.gz",fixed_image="ch2.nii.gz",output_prefix="test_")


    # check src file for quality
    source_file = join("data","src_base_src.gz")
    dsiquality = ["dsi_studio","--action=qc",
                "--source="+source_file
    ]

    # reconstruct the images (create fib file; QSDR method=7,GQI method = 4)
    source_file = join("data","src_base.src.gz")
    other_image = join("data","1w:T1.nii.gz")
    dsirecon = ["dsi_studio","--action=rec",
                  "--source="+source_file,
                  "--method=7",
                  "--param0=1.25",
                  "--param1=1",
                  "--half_sphere=1",
                  "--odf_order=8",
                  "--num_fiber=10",
                  "--interpo_method=0",
                  "--scheme_balance=1",
                  "--check_btable=1",
                  "--other_image="+other_image
    ]
    # run robust tractography whole brain
    source_file = join("data","src_base.src.fib.gz")
    output_file = join("data","count_connect.trk.gz")
    dsiruntract = ["dsi_studio","--action=trk",
                    "--source="+source_file,
                    "--seed_count=10000000",
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
                    "--output="+output_file
    ]
    # generate connectivity matrix and summary statistics
    tract_file = join("data","count_connect.trk.gz")
    output_file = join("data","connectivity_countmeasures.txt")
    dsiruntract = ["dsi_studio", "--action=ana",
                      "-tract="+tract_file,
                      "--connectivity=aal",
                      "--connectivity_value=count",
                      "--connectivity_type=end",
                      "--output="+output_file
    ]
                  
    # visualize tractography first
    source_file = join("data","src_base.src.fib.gz")
    tract_file = join("data","count_connect.trk.gz")
    dsivisualize = ["dsi_studio","--action=vis",
            "--source="+source_file,
            "--track="+tract_file,
            "--cmd=set_view,2+save_image,tractography1.jpg,1024 800"
    ]
    
    dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=kwargs)

    # set up arguments to dsi_studio
    dsistudio_commands = [

        "dsi_studio", "--action=atk",
        "--source="+join("data", "dwi.nii.gz"),
        "--bval="+join("data", "dwi.bval"),
        "--bvec="+join("data", "dwi.bvec")
    ]

    dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=dsistudio_commands)


    # example running fsl
    # set up arguments to FSL
    # this gets a little tricky because of different FSL commands
    input_file = join("data",image_dict["structural"]["nifti"])
    output_file = join("output",splitext(basename(image_dict["structural"]["nifti"]))[0] +
                       "_brain.nii.gz")
    bet_command = [
        "bet",input_file,output_file,"-f",0.3,"-g",0,"-m"
    ]

    fsl(source_dir=args.dir,out_dir=args.dir,input_file=input_file,logger=logger,
        output_file=output_file,kwargs=bet_command)

    # example of eddy
    input_file = join("data", "niftifile.nii")
    mask_file = join("data", "brain_mask.nii")
    acq_eddy = join("data", "acq_eddy.txt")
    index_file = join("data", "index.txt")
    out_file = join("output","dti_eddycuda_corrected_data")
    bvec = join("data", "bvec")
    bval = join("data", "bval")
    eddy_command = [
        "eddy", "--imain",input_file,"--mask",mask_file,"--acqp",acq_eddy,
            "--index",index_file,"--bvecs",bvec, "--bvals",bval,"--out",out_file
    ]


    fsl(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=eddy_command)

if __name__ == "__main__":
    main(sys.argv[1:])