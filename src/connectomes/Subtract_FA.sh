#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
user=`whoami`
INSTALL_DIR="/Users/$user/StructuralConnectomes"
${DIRNAME}/python ${INSTALL_DIR}/subtract_images.py -FA1 $1  -FA2 $2
