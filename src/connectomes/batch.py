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
from connectomes.utils import ants_registration,dsistudio,fsl
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
    input_file = join("data","T1.nii.gz")
    output_file = join("output","T1_brain.nii.gz")
    bet_command = [
        "bet",input_file,output_file
    ]

    fsl(source_dir=args.dir,out_dir=args.dir,input_file=input_file,logger=logger,
        output_file=output_file,kwargs=bet_command)




if __name__ == "__main__":
    main(sys.argv[1:])