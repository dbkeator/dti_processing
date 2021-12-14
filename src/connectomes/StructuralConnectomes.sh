#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
INSTALL_DIR=/Applications/StructuralConnectomes
${DIRNAME}/python ${INSTALL_DIR}/batch.py -dir $1 
