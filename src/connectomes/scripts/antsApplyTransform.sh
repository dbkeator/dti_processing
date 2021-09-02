# $1 = atlas labelmap
# $2 = subject's SPECT image in space we want to write labelmap
# $3 = warp field from antsRegistrationSyn
# $4 = affine matrix from antsRegistrationSyn
# $5 = output filename

$ANTSPATH/antsApplyTransforms -d 3 -e 0 -i $1 -r $2 -n Linear -t $3 -t $4 -o $5