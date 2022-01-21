#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
user=`whoami`
INSTALL_DIR="/Users/$user/StructuralConnectomes"
${DIRNAME}/python ${INSTALL_DIR}/batch.py -dir $1 -overwrite
