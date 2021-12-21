import sys
import os

from os import system

from os.path import join,isfile,basename,dirname,splitext
from argparse import ArgumentParser
from utils import ants_registration,fsl


try:
    import glob2
except ImportError:
    print("trying to install required module: glob2")
    system('python -m pip install --upgrade pip glob2')
    import glob2


import logging
import time
import copy
from shutil import copyfile




def main(argv):
    parser = ArgumentParser(description='This software will register and subtract two NIfTI-formatted '
                            'FA images and then display the difference on a template MRI.')
    parser.add_argument('-FA1', dest='FA1', required=True, help="FA Image 1")
    parser.add_argument('-FA2', dest='FA2', required=True, help="FA Image 2")
    parser.add_argument('-outdir',dest='outdir',required=False,help="if defined then"
                            "both FA1 and FA2 will be copied to outdir along with "
                            "result of subtraction.")

    args = parser.parse_args()


    # open log file
    timestr = time.strftime("%Y%m%d-%H%M%S")
    logger = logging.getLogger(join(dirname(args.FA1), 'connectomes_subtract_images'))
    # hdlr = logging.FileHandler(join(LOG_DIR, timestr + "_log.txt"))
    hdlr = logging.FileHandler(join(dirname(args.FA1), 'connectomes_subtract_images_' + timestr + "_log.txt"))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

    # check if these are NIfTI files by simply looking at extension
    if (".nii" not in args.FA1) or (".nii" not in args.FA2):
        logger.error("Both -FA1 and -FA2 need to be NIfTI files.  No .nii extension"
                     "found in one or both parameters.")
        exit(-1)

    # step 1: if FA1 and FA2 aren't in the same directory copy FA2 to location of FA1,
    # renaming if necessary
    logger.info("source -FA1=%s" %args.FA1)
    logger.info("source -FA2=%s" %args.FA2)

    # if images are not in the same directory then copy FA2 to FA1's location or args.outdir if defined
    if not (dirname(args.FA1) == dirname(args.FA2)):
        # check if args.FA1 == args.FA2
        if basename(args.FA1) == basename(args.FA2):
            # copy FA2 to FA1 location and rename
            if "gz" in args.FA2:
                logger.info("copyfile("+args.FA2+", "+join(dirname(args.FA1),"FA2.nii.gz")+")")
                copyfile(args.FA2, join(dirname(args.FA1),"FA2.nii.gz"))
                FA2 = join(dirname(args.FA1), "FA2.nii.gz")
                FA2_basename = "FA2"

            else:
                logger.info("copyfile("+args.FA2+", "+join(dirname(args.FA1),"FA2.nii")+")")
                copyfile(args.FA2, join(dirname(args.FA1), "FA2.nii"))
                FA2 = join(dirname(args.FA1), "FA2.nii")
                FA2_basename = "FA2"

            FA1 = args.FA1
            if ".gz" in FA1:
                FA1_basename = splitext(splitext(basename(FA1))[0])[0]
            else:
                FA1_basename = splitext(basename(FA1))[0]

        else:
            # just copy FA2 to FA1's location
            copyfile(args.FA2, dirname(args.FA1))
            FA2 = join(dirname(args.FA1),basename(args.FA2))
            if ".gz" in FA2:
                FA2_basename = splitext(splitext(basename(FA2))[0])[0]
            else:
                FA2_basename = splitext(basename(FA2))[0]

            FA1 = args.FA1
            if ".gz" in FA1:
                FA1_basename = splitext(splitext(basename(FA1))[0])[0]
            else:
                FA1_basename = splitext(basename(FA1))[0]
    else:
        # images are already in same directory so just set filenames
        FA2 = args.FA2
        if ".gz" in FA2:
            FA2_basename = splitext(splitext(basename(FA2))[0])[0]
        else:
            FA2_basename = splitext(basename(FA2))[0]

        FA1 = args.FA1
        if ".gz" in FA1:
            FA1_basename = splitext(splitext(basename(FA1))[0])[0]
        else:
            FA1_basename = splitext(basename(FA1))[0]

    # step 2: register FA2 to FA1 using ANTS

    # if user didn't define an output directory then just use the location of -FA1
    if not args.outdir:
        ants_registration(source_dir=dirname(args.FA1),out_dir=dirname(args.FA1),
            logger=logger, moving_image = basename(FA2),
            fixed_image=basename(FA1),
            output_prefix=FA2_basename+ "_to_" + FA1_basename + "_")

    else:
        ants_registration(source_dir=dirname(args.FA1), out_dir=args.outdir,
            logger=logger, moving_image=basename(FA2),
            fixed_image=basename(FA1),
            output_prefix=FA2_basename + "_to_" + FA1_basename + "_")

    # step 3 subtract FA1 - FA2
    logger.info('Running FSLs fslmaths')
    input_file = join("data", FA1_basename)
    input_file2 = join("data", FA2_basename + "_to_" + FA1_basename + "__Warped.nii.gz")
    output_file = join("output", FA1_basename + "_minus_" + FA2_basename)
    dti_fit_command = [
        "fslmaths", input_file, "-sub", input_file2, output_file
    ]

    if not args.outdir:
        fsl(source_dir=dirname(args.FA1), out_dir=dirname(args.FA1),
            input_file=input_file, logger=logger, output_file=output_file,
            kwargs=dti_fit_command)
    else:
        fsl(source_dir=dirname(args.FA1), out_dir=args.outdir,
            input_file=input_file, logger=logger, output_file=output_file,
            kwargs=dti_fit_command)


if __name__ == "__main__":
    main(sys.argv[1:])
