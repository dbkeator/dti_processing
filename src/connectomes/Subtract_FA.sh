#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
INSTALL_DIR=/Applications/StructuralConnectomes
${DIRNAME}/python ${INSTALL_DIR}/subtract_images.py -FA1 $1  -FA2 $2
