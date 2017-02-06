#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# Create Dists for both REST and ASL

git status
repo_dir=`pwd`

for task in REST mbPCASL; do
  pushd /tmp > /dev/null
  if [ -d $task ]; then rm -rf $task; fi
  git clone $repo_dir $task
  cd $task
  #cp siteConfig.yaml.example siteConfig.yaml
  mv EyeCam_Scan.py ${task}_Scan.py
  sed -i '' "s/['SELECT SCAN TYPE', 'REST', 'mbPCASL']/['${task}', 'REST', 'mbPCASL']/"

  # if [ "${task}" = "mbPCASL" ]; then
  #   sed -i '' "s/['SELECT SCAN TYPE', 'REST', 'mbPCASL']/['${task}', 'REST', 'mbPCASL']/"
  # fi
  git rev-parse HEAD > VERSION
  shortHash=$(git rev-parse --short HEAD)
  cd ..
  date=`date +%Y-%m-%d`
  tar=${task}-${date}-${shortHash}.tar.gz
  tar -czvf $tar $task
  mv $tar $repo_dir/dist
  popd
done
