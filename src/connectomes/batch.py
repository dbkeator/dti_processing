#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  2 12:11:16 2021

@author: stevegranger
"""

import sys
import os

from os import system

from os.path import join
from argparse import ArgumentParser

try:
    import glob2
except ImportError:
    print("trying to install required module: glob2")
    system('python -m pip install --upgrade pip glob2')
    import glob2


import logging
import time




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


    # find structural and DTI images
    image_dict = find_convert_images(source_dir=args.dir,out_dir=args.dir,logger=logger,convert=False)
    
    # process DTI images
    process_dti(image_dict,logger,args)

    
if __name__ == "__main__":
    main(sys.argv[1:])
