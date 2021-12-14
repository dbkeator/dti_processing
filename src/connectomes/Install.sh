# check if destination directory exists and if not make it
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
install_dir="/Applications/StructuralConnectomes"
if [[ ! -e $install_dir ]]; then
    mkdir $install_dir
elif [[ ! -d $install_dir ]]; then
    echo "$install_dir already exists but is not a directory" 1>&2
fi

# copy source files into install_dir
cp ${SCRIPT_DIR}/dti.py ${SCRIPT_DIR}/__version__.py ${SCRIPT_DIR}/batch.py  ${SCRIPT_DIR}/utils.py ${SCRIPT_DIR}/StructuralConnectomes.sh ${SCRIPT_DIR}/DSIParams.txt  ${SCRIPT_DIR}/Install.sh $install_dir

# copy scripts directory to install_dir
cp -R ${SCRIPT_DIR}/Install.app ${SCRIPT_DIR}/StructuralConnectomes.app ${SCRIPT_DIR}/scripts $install_dir

# make symbolic link to StructuralConnectomes.app on desktop
osascript -e 'tell application "Finder"' -e 'make new alias to file (posix file "/Applications/StructuralConnectomes/StructuralConnectomes.app") at desktop' -e 'end tell'

# set $PATH environment variable so it includes /Applications/StructuralConnectomes folder
export PATH=/Applications/StructuralConnectomes:$PATH

# make entry script executable
chmod 755 /Appliations/StructuralConnectomes/StructuralConnectomes.sh