# check if destination directory exists and if not make it
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
user=`whoami`
install_dir="/Users/$user/StructuralConnectomes"
structural_connectomes_app="$install_dir/StructuralConnectomes.app"
fa_app="$install_dir/Subtract_FA.app"

if [[ ! -e $install_dir ]]; then
    mkdir $install_dir
elif [[ ! -d $install_dir ]]; then
    echo "$install_dir already exists but is not a directory" 1>&2
fi

# copy source files into install_dir
cp ${SCRIPT_DIR}/dti.py ${SCRIPT_DIR}/__version__.py ${SCRIPT_DIR}/batch.py  ${SCRIPT_DIR}/utils.py ${SCRIPT_DIR}/StructuralConnectomes.sh ${SCRIPT_DIR}/DSIParams.txt  ${SCRIPT_DIR}/Install.sh ${SCRIPT_DIR}/Subtract_FA.sh ${SCRIPT_DIR}/subtract_images.py ${SCRIPT_DIR}/Install.docx ${SCRIPT_DIR}/Tractography_Visualization_Instructions.docx $install_dir

# copy scripts directory to install_dir
cp -R ${SCRIPT_DIR}/Install.app ${SCRIPT_DIR}/StructuralConnectomes.app ${SCRIPT_DIR}/scripts ${SCRIPT_DIR}/Subtract_FA.app  $install_dir

# make symbolic link to StructuralConnectomes.app on desktop
command="osascript -e 'tell application \"Finder\"' -e 'make new alias to file (posix file \"$structural_connectomes_app\") at desktop' -e 'end tell'"
echo $command
eval "$command"

# make symbolic link to Subtract_FA.app on desktop
command="osascript -e 'tell application \"Finder\"' -e 'make new alias to file (posix file \"$fa_app\") at desktop' -e 'end tell'"
echo $command
eval "$command"

# set $PATH environment variable so it includes /Users/$user/StructuralConnectomes folder
export PATH="/Users/$user/StructuralConnectomes":$PATH

# make entry script executable
chmod 755 "/Users/$user/StructuralConnectomes/StructuralConnectomes.sh"
chmod 755 "/Users/$user/StructuralConnectomes/Subtract_FA.sh"

echo "StructuralConnectomes successfully installed!"