import sys
import os
from os import makedirs
from os.path import dirname, splitext,basename,isfile,isdir,join
import subprocess
from shutil import copyfile
from connectomes.utils import ants_registration,dsistudio,fsl,dcm2niix,find_convert_images


def process_dti(image_dict, logger):

    logger.info("function: process_dti")

    # set output directory to be same directory as where we find the nifti images + "connetomes"
    output_dir = join(dirname(image_dict["structural"]["nifti"]),"connetomes")

    # check if output directory exists, if not create it
    if not isdir(output_dir):
        makedirs(output_dir)

    # copyfile(image_dict["structural"]["nifti"],output_dir)
    for key,value in image_dict["structural"].items():
        copyfile(image_dict["structural"][key], output_dir)
    for key, value in image_dict["dti"].items():
        copyfile(image_dict["dti"][key], output_dir)

    input_file = join("data", image_dict["structural"]["nifti"])
    output_file = join("output", splitext(basename(image_dict["structural"]["nifti"]))[0] +
                       "_brain.nii.gz")
    bet_command = [
        "bet", input_file, output_file, "-f", 0.3, "-g", 0, "-m"
    ]

    logger.info("command: %s" % subprocess.list2cmdline(bet_command))

    fsl(source_dir=dirname(image_dict["structural"]["nifti"]),
        out_dir=output_dir,
        input_file=input_file, logger=logger,
        output_file=output_file, kwargs=bet_command)
