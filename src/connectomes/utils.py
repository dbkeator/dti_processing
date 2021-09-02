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
    DSSTUDIO_DOCKER = join("dsistudio/dsistudio:latest")

elif platform.system() == 'Linux':
    INSTALL_DIR = "/usr/local/bin/connectomes"
    LOG_DIR = join(INSTALL_DIR, "temp")
    ANTS_DOCKER = join("dbkeator/roiextract:latest")
    SCRIPTS_DIR = join(INSTALL_DIR,"scripts")
    ANTS_REG = "antsRegistrationSyn.sh"
    ANTS_APPLYWARP = "antsApplyTransform.sh"
    DSSTUDIO_DOCKER = join("dsistudio/dsistudio:latest")

else:
    print("ERROR: Unsupported Platform: %s" % platform.system())


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
    :return:
    '''



    cmd = ["docker", "run", "-v", source_dir + ":/data", "-v",
           SCRIPTS_DIR + ":/scripts", "-v",
           out_dir + ":/output", ANTS_DOCKER, "sh", join("scripts", ANTS_REG),
           join("data", fixed_image),
           join("data", moving_image), join("output", output_prefix + "_")]

    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not isfile(join(out_dir, output_prefix + "_Warped.nii.gz")):
        logger.error("ERROR: registration failure for file: %s"
            % join(source_dir, output_prefix + "_Warped.nii.gz"))


def dsistudio(source_dir,out_dir,logger,kwargs):
    '''
    This function runs dsistudio using the Docker image and given the keyword arguments in **kwargs
    :param source_dir: source directory to mount into Docker image
    :param out_dir: output directory to mount into Docker image
    :param kwargs: keyworded arguments to dsistudio
    :return:
    '''

    # begin building docker command string
    cmd = ["docker", "run", "-v", source_dir + ":/data", "-v",
           out_dir + ":/output", DSSTUDIO_DOCKER]

    # add dsistudio-specific keyword arguments
    for key,val in kwargs.items():
        cmd.append(key)
        if key == "--source":
            cmd.append(join("data",val))
        


    logger.info("command: %s" % subprocess.list2cmdline(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

