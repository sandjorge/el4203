#!/usr/bin/bash
tic=$(date +%s)
source quic-perf.lib

if [ "$#" -eq 1 ]; then
   if [ -d "$1" ]; then
      printf "Starting to backup folder ${magenta}$1${clear}\n"
   else
      printf "Folder ${red}$1${clear} does not exist.\n"
      exit
   fi
else
   echo "Bye"
   exit
fi

bkfolder="s3://jsandova-uchile-cl/2023-sim/lenovo/ns-3.39/scratch/quic/$1/"
orifolder=$1
s3cmd put ${orifolder}/quic-perf.*  $bkfolder
s3cmd put ${orifolder}/*.ini  $bkfolder
s3cmd put ${orifolder}/*.json  $bkfolder
s3cmd put ${orifolder}/output.log  $bkfolder

toc=$(date +%s)
printf "Backup Processed in: "${magenta}$(($toc-$tic))${clear}" seconds\n"
