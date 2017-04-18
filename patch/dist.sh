#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# Create Dists for both REST and ASL

# git status
repo_dir=`pwd`
task=REST_mbPCASL_Combined

pushd /tmp > /dev/null
if [ -d $task ]; then rm -rf $task; fi
git clone $repo_dir $task
cd $task
for taskscript in REST mbPCASL; do
  cp EyeCam_Scan.py ${taskscript}_Scan.py
  if [ "$taskscript" = REST ]; then
    select="\[\'REST\', \'mbPCASL\'\]"
  else
    select="\[\'mbPCASL\', \'REST\'\]"
  fi
  sed -i '' "s/\[\'SELECT SCAN TYPE\', \'REST\', \'mbPCASL\'\]/$select/" ${taskscript}_Scan.py
  if [ ! -e siteConfig.yaml ]; then
    cp siteConfig.yaml.example siteConfig.yaml
  fi
  git rev-parse HEAD > VERSION
  shortHash=$(git rev-parse --short HEAD)
done
rm EyeCam_Scan.py
rm siteConfigUMN.yaml
cd ..

date=`date +%Y-%m-%d`
tar=${task}-${date}-${shortHash}.tar.gz
tar -czvf $tar $task
if [ ! -d $repo_dir/dist ]; then mkdir $repo_dir/dist; fi
mv $tar $repo_dir/dist
popd
