import os,sys
from os import system
from os.path import join,isfile
import subprocess
from subprocess import PIPE

import platform
import glob2
import json

try:
    import nibabel as nib
except ImportError:
    print("trying to install required module: nibabel")
    system('python -m pip install --upgrade pip nibabel')
    import nibabel as nib

if platform.system() == 'Darwin':
    #INSTALL_DIR = "/Applications/connectomes"
    INSTALL_DIR = os.getcwd()
    LOG_DIR = join(INSTALL_DIR, "temp")
    ANTS_DOCKER = join("dbkeator/roiextract:latest")
    SCRIPTS_DIR = join(INSTALL_DIR,"scripts")
    ANTS_REG = "antsRegistrationSyn.sh"
    ANTS_APPLYWARP = "antsApplyTransform.sh"
    DSSTUDIO_DOCKER = "dsistudio/dsistudio:latest"
    FSL = "brainlife/fsl"
    DCM2NIIX = "xnat/dcm2niix"

elif platform.system() == 'Linux':
    INSTALL_DIR = "/usr/local/bin/connectomes"
    LOG_DIR = join(INSTALL_DIR, "temp")
    ANTS_DOCKER = join("dbkeator/roiextract:latest")
    SCRIPTS_DIR = join(INSTALL_DIR,"scripts")
    ANTS_REG = "antsRegistrationSyn.sh"
    ANTS_APPLYWARP = "antsApplyTransform.sh"
    DSSTUDIO_DOCKER = "dsistudio/dsistudio:latest"
    FSL = "brainlife/fsl"
    DCM2NIIX = "xnat/dcm2niix"

else:
    print("ERROR: Unsupported Platform: %s" % platform.system())


def find_convert_images(source_dir, out_dir, logger,convert=False):
    '''
    This function will convert all the DICOM images in source_dir and store them in out_dir. It will
    then figure out which images are the best structural scan and DTI scan with the most directions
    and return the associated filenames as a dictionary.
    :param source_dir: directory containing DICOM images or sub-directories with DICOM images
    :param out_dir: directory to store NifTI images
    :param logger: log file
    :param convert: optional parameter which will do dcm2niix conversion if True
    :return: dictionary: dict['structural']['nifti'],dict['structural']['json'], dict['dti']['nifti'],
        dict['dti']['json'], dict['dti']['bval'], dict['dti']['bvec']
    '''

    # set up output dictionary
    output_dict = {}
    output_dict['structural']={}
    output_dict['dti'] = {}

    logger.info("function: find_convert_images")

    if convert:
        logger.info("converting dicom images with dcm2niix...")
        # convert all images in source_dir
        dcm2niix(source_dir=source_dir,logger=logger)
    else:
        logger.info("skipping dicom conversion...")

    # get list of json, nifti, and bval/bvec options
    logger.info("getting list of nifti, bval, bvec, and json files...")
    json_files = glob2.glob(join(out_dir,"*.json"))
    bval_files = glob2.glob(join(out_dir,"*.bval"))
    bvec_files = glob2.glob(join(out_dir,"*.bvec"))
    nifti_files = glob2.glob(join(out_dir, "*.nii" or "*.nii.gz"))


    # find MPRAGE with smallest voxel size and as close to isotropic as possible
    json_mprage = [s for s in json_files if ("MPRAGE" or "mprage") in s]

    # loop through json files, load them and ignore ones that don't have "ShimSetting" key. These
    # are NeuroQuant processed MPRAGE scans
    image_matrix= {}
    for file in json_mprage:
        with open(file) as fp:
            file_json = json.load(fp)
        if int(file_json["SeriesNumber"]) > 50:
            continue
        else:
            # load NIfTI header and get voxel and image dimensions
            nifti_img = nib.load(os.path.splitext(file)[0]+'.nii')

            # store matrix x image name
            image_matrix[os.path.splitext(file)[0]+'.nii'] = ((nifti_img.header.get_data_shape()[0] *
                    nifti_img.header.get_zooms()[0])*(nifti_img.header.get_data_shape()[1] * nifti_img.header.get_zooms()[1])
                    * (nifti_img.header.get_data_shape()[2] * nifti_img.header.get_zooms()[2]))
    # pick which entry in image_matrix is largest
    max_volume = 0
    for key,value in image_matrix.items():
        if image_matrix[key] > max_volume:
            # store dictionary entry for structural scan and associated json file
            output_dict['structural']['nifti'] = key
            output_dict['structural']['json'] = os.path.splitext(key)[0]+'.json'
            max_volume = image_matrix[key]

    # loop through json files and find best dti scan
    json_dti = [s for s in bval_files if ("bval" or "BVAL") in s]

    # loop through json_dti bval files and store one with most directions
    bval_max = 0
    for file in json_dti:
        fp = open(file, "r")
        content = fp.read()
        content_list = content.split(" ")
        if len(content_list) > bval_max:
            # make sure all the other necessary files we need exist else skip
            bvec_file = os.path.splitext(file)[0] + '.bvec'
            nifti_file = os.path.splitext(file)[0] + '.nii'
            json_file = os.path.splitext(file)[0] + '.json'

            if (not isfile(bvec_file)) or (not isfile(nifti_file)):
                continue
            else:
                # store dictionary entry for structural scan and associated json file
                output_dict['dti']['bval'] = file
                output_dict['dti']['bvec'] = bvec_file
                output_dict['dti']['nifti'] = nifti_file
                output_dict['dti']['json'] = json_file

                bval_max = len(content_list)

    if (len(output_dict['dti'])==0) or (len(output_dict['structural'])==0):
        logger.error("No DTI or structural scans found in: %s" %source_dir)
        logger.error("Unable to continue...")
        return -1
    else:
        return output_dict


def dcm2niix(source_dir,logger,source_file=None):
    '''
        This function will run dcm2niix on the source_dir if source_file == None else it
        will run dcm2niix on the source_file.
        :param source_dir: directory containing images to convert to nifti
        :param logger: log to write information to
        :param source_file: if this is defined then the source_file will be converted not the whole
        source_dir.
        :return: Result of command
    '''

    logger.info("function: dcm2niix")

    # running dcm2niix on whole directory
    if source_file == None:

        cmd = ["docker", "run", "--rm","-v", source_dir + ":/data", DCM2NIIX,"dcm2niix",
               "data"]
    # else running it on a file
    else:
        cmd = ["docker", "run", "--rm", "-v", source_dir + ":/data", "-v",
               DCM2NIIX, "dcm2niix", join("data",source_file)]


    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)




def ants_registration(source_dir,out_dir,logger,moving_image,fixed_image,output_prefix):
    '''
    This function will execute the ANTS registration Docker image using the variable key word arguments
    stored in **kwargs.
    :param source_dir: directory to set as place registration code will find the images
    :param out_dir: directory where results will be written
    :param logger: log to write information to
    :param moving_image: NIfTI formatted image to register
    :param fixed_image: NIfTI formatted target image
    :param output_prefix: ANTS prefix to add to output of registration
    :return: Result of command
    '''

    logger.info("function: ants_registration")


    cmd = ["docker", "run", "--rm","-v", source_dir + ":/data", "-v",
           SCRIPTS_DIR + ":/scripts", "-v",
           out_dir + ":/output", ANTS_DOCKER, "sh", join("scripts", ANTS_REG),
           join("data", fixed_image),
           join("data", moving_image), join("output", output_prefix + "_")]

    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # checks if the output files were created else writes and error to the logger
    if not isfile(join(out_dir, output_prefix + "_Warped.nii.gz")):
        logger.error("registration failure for file: %s"
            % join(source_dir, output_prefix + "_Warped.nii.gz"))

    return result


def dsistudio(source_dir,out_dir,logger,kwargs):
    '''
    This function runs dsistudio using the Docker image and given the keyword arguments in **kwargs
    :param source_dir: source directory to mount into Docker image
    :param out_dir: output directory to mount into Docker image
    :param logger: log file object
    :param kwargs: keyworded arguments to dsistudio
    :return:Result of command
    '''
    logger.info("function: dsistudio")

    # begin building docker command string
    cmd = ["docker", "run", "--rm","-v", source_dir + ":/data", "-v",
           out_dir + ":/output", DSSTUDIO_DOCKER]

    # add dsistudio-specific keyword arguments
    for val in kwargs:
        cmd.append(val)


    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return result

def fsl(source_dir,out_dir, logger,kwargs,input_file=None,output_file=None):
    '''
    This function will run a Docker FSL container and run the commands with arguments in kwargs
    :param source_dir: source directory to mount into Docker image
    :param out_dir: output directory to mount into Docker image
    :param input_file: input file name which is located in source_dir
    :param output_file: (optional) output file name which is written to out_dir
    :param logger: log file object
    :param kwargs: keyworded arguments to dsistudio
    :return: Result of command
    '''

    logger.info("function: fsl")


    # begin building docker command string
    cmd = ["docker", "run", "--rm", "-v", source_dir + ":/data", "-v",
           out_dir + ":/output", FSL]

    # add fsl-specific keyword arguments
    for val in kwargs:
        cmd.append(val)

    print()
    print(cmd)
    print(source_dir)
    print(out_dir)
    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return result
