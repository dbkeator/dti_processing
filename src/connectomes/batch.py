import sys
import os
from os import system,mkdir,remove
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
from connectomes.utils import ants_registration,dsistudio
from connectomes.utils import INSTALL_DIR,LOG_DIR,ANTS_APPLYWARP,ANTS_DOCKER,ANTS_REG,DSSTUDIO_DOCKER,SCRIPTS_DIR


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
    hdlr = logging.FileHandler(timestr + "_log.txt")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)


    # example running registration
    ants_registration(source_dir=args.dir,out_dir=args.dir,logger=logger,
                      moving_image="T1.nii.gz",fixed_image="ch2.nii.gz",output_prefix="test_")

    # example running dsistudio
    kwargs = {
        "dsi_studio --action=":"atk",
        "--source=":join("data","dwi.nii.gz"),
        "--bval=":join("data","dwi.bval"),
        "--bvec=":join("data","dwi.bvec")
    }
    # create source file
    dsisource = {"dsi_studio --action=":"src",
              "--source=":join("data","dwi.nii.gz"),
              "--output=":join("data","src_base.src.gz") ,
              "--bval=":join("data","dwi.bval"),
              "--bvec=":join("data","dwi.bvec")
              }
    # check src file for quality
    dsiquality = {"dsi_studio --action=":"qc",
              "--source=":join("data","src_base_src.gz")
              }
    # reconstruct the images (create fib file; QSDR method=7,GQI method = 4)
    dsirecon = {"dsi_studio --action=":"rec",
              "--source=":join("data","src_base.src.gz"),
              "--method=":join("data:","7"),
              "--param0=":join("data","1.25"),
              "--param1=":join("data","1"),
              "--half_sphere=":join("data","1"),
              "--odf_order=":join("data","8"),
              "--num_fiber=":join("data","10"),
              "--interpo_method=":join("data","0"),
              "--scheme_balance=":join("data","1"),
              "--check_btable=":join("data","1"), 
              "--other_image=":joint("data","1w:T1.nii.gz")
              }
    # run robust tractography whole brain
    dsiruntract = {"dsi_studio --action=":"trk",
                   
                   
   
  ##############Run whole brain Tractography with 10 million seeds 
    dsi_studio --action= trk --method=0 --seed_count=10000000--threshold_index=qa --fa_threshold=0.00--initial_dir=0--seed_plan=0--interpolation=0--thread_count=12--step_size=0 --turning_angle=65 --smoothing=.6 --min_length=10 --max_length=600 --output=count_connect.trk.gz
    ##############Run connectivity analysis with AAL atlas counting streamlines ending in regions 
    dsi_studio --action= ana --tract=count_connect.trk.gz --connectivity=aal --connectivity_value=count --connectivity_type=end --output=connectivity_countmeasures.txt
    ##############################################Visualize tracts
    dsi_studio --action=vis --source=$arr --track="count_connect.trk.gz" --cmd="set_view,2+save_image,tractography1.jpg,1024 800"
    dsi_studio --action=vis --source=$arr --track="count_connect.trk.gz" --cmd="slice_off+set_view,2+save_image,tractography2.jpg,1024 800"	
    dsi_studio --action=vis --source=$arr --track="count_connect.trk.gz" --cmd="set_view,1+save_image,tractography3.jpg,1024 800"
    dsi_studio --action=vis --source=$arr --track="count_connect.trk.gz" --cmd="slice_off+set_view,1+save_image,tractography4.jpg,1024 800"
    ########################################################################################################
    ####################################################Prepare data for FA Difference Maps (Longitudinal Data)####################################################
    ########################################################################################################
    #produce FA maps here
    dtifit --data <scan.ii> -o FAdata -m <brain_mask.nii> -bvec *bvec -bval *bval

    dsistudio(source_dir=args.dir,out_dir=args.dir,logger=logger,kwargs=kwargs)


if __name__ == "__main__":
    main(sys.argv[1:])