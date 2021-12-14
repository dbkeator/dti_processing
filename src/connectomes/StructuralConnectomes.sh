#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
${DIRNAME}/python /Applications/StructuralConnectomes/batch.py -dir $1 
