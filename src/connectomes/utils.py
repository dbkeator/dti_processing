import os,sys
from os.path import join,isfile
import subprocess
from subprocess import PIPE

import platform

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

def dcm2niix(source_dir,out_dir,logger,source_file=None):
    '''
        This function will run dcm2niix on the source_dir if source_file == None else it
        will run dcm2niix on the source_file.
        :param source_dir: directory containing images to convert to nifti
        :param out_dir: directory where results will be written
        :param logger: log to write information to
        :param source_file: if this is defined then the source_file will be converted not the whole
        source_dir.
        :return: Result of command
    '''


    # running dcm2niix on whole directory
    if source_file == None:

        cmd = ["docker", "run", "--rm","-v", source_dir + ":/data", "-v",
               out_dir + ":/output", DCM2NIIX,"dcm2niix", "data","output"]
    # else running it on a file
    else:
        cmd = ["docker", "run", "--rm", "-v", source_dir + ":/data", "-v",
               out_dir + ":/output", DCM2NIIX, "dcm2niix", join("data",source_file), "output"]


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

    # begin building docker command string
    cmd = ["docker", "run", "--rm", "-v", source_dir + ":/data", "-v",
           out_dir + ":/output", FSL]

    # add fsl-specific keyword arguments
    for val in kwargs:
        cmd.append(val)



    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return result
