#!/bin/bash
# get path to python
DIR=$(which python)
DIRNAME=$(dirname ${DIR})
${DIRNAME}/python /Volumes/homes/dbkeator/Consulting/Shankle/DTI_Project/Code/StructuralConnectomes/src/connectomes/batch.py -dir $1 
