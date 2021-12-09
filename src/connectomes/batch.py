#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 12:11:16 2021

@author: stevegranger
"""

import sys
import os

from os import system

from os.path import join,isfile,isdir
from argparse import ArgumentParser

try:
    import glob2
except ImportError:
    print("trying to install required module: glob2")
    system('python -m pip install --upgrade pip glob2')
    import glob2


import logging
import time
import copy




from utils import find_convert_images
from dti import process_dti



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
    

    #make args.dir absolute path 
   
    args.dir= os.path.abspath(args.dir)

    # get listing if args.dir
    # if this is a DICOM directory exported from OsiriX then it will have a DICOMDIR file.  Else it's
    # a directory containing subdirectories for participants so process them as separate directories

    files = os.listdir(args.dir)

    # if file DICOMDIR is in listing then args.dir is a directory containing DICOM images for a patient
    if ('DICOMDIR' in files):

        # find structural and DTI images
        image_dict = find_convert_images(source_dir=args.dir,out_dir=args.dir,logger=logger,convert=True)

        # check if image_dict does not contain valid images
        if image_dict == -1:
            exit(-1)

        # process DTI images
        process_dti(image_dict,logger,args)

    # else args.dir is a directory containing subdirectories for patients
    else:
        # get only directories
        directories = [d for d in files if isdir(join(args.dir, d))]

        for dir in directories:
            # ignore MAC directories we don't care about
            if '.DS_STORE' in dir:
                continue
            else:
                # process patient
                # find structural and DTI images
                image_dict = find_convert_images(source_dir=join(args.dir,dir), out_dir=join(args.dir,dir), logger=logger, convert=True)

                # check if image_dict does not contain valid images
                if image_dict == -1:
                    continue

                # set args.dir to new directory to process since we're looping through a directory with subdirectories
                args_copy =  copy.deepcopy(args)
                args_copy.dir = join(args.dir,dir)
                # process DTI images
                process_dti(image_dict, logger, args_copy)

    
if __name__ == "__main__":
    main(sys.argv[1:])
