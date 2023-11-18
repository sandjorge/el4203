#!/usr/bin/bash

# https://github.com/signetlabdei/quic
tic=$(date +%s)

# Set paths
ns3home="/home/jsandova/ns-3.37/"

# Start time
source quic-perf.lib

# Default values
serverType='Edge'
rlcBufferPer=200
tcpTypeId='TcpCubic'
speed=1
simTime=60
iniTime=37
ueNum=1
frequency=27.3e9
bandwidth=400e6
myscenario=0
AQM='None'


helpFunction()
{
   echo ""
   echo "Usage: $0 -t $tcpTypeId -s $serverType -r $rlcBufferPer"
   echo -e "\t-t 'TcpNewReno' or 'TcpBbr' or 'TcpCubic' or 'TcpHighSpeed' or 'TcpBic' or 'TcpLinuxReno' or 'UDP'"
   echo -e "\t-s 'Remote' or 'Edge'"
   echo -e "\t-r Percentage 10 o 100"
   echo -e "\t-n Number of UE"
   echo -e "\t-c Scenario 1 or 3"
   echo -e "\t-a 'None' or 'RED' "
   exit 1 # Exit script after printing help
}


while getopts "t:r:s:n:m:c:a:?" opt
do
   case "$opt" in
      t ) tcpTypeId="$OPTARG" ;;
      s ) serverType="$OPTARG" ;;
      r ) rlcBufferPer="$OPTARG" ;;
      n ) ueNum="$OPTARG" ;;
      c ) myscenario="$OPTARG" ;;
      a ) AQM="$OPTARG" ;;
      ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
   esac
done

if [ "$myscenario" != "0" ] && [ "$myscenario" != "3" ]
then
   echo "Scenario \"$myscenario\" no available";
   helpFunction
fi

if [ "$serverType" != "Remote" ] && [ "$serverType" != "Edge" ]
then
   echo "ServerType \"$serverType\" no available";
   helpFunction
fi

if [ $rlcBufferPer -gt 99999 ] || [ $rlcBufferPer -lt 1 ]
then
   echo "rlcBuffer \"$rlcBufferPer\" no available";
   helpFunction
fi

if [ $ueNum -gt 10 ] || [ $ueNum -lt 1 ]
then
   echo "rlcBuffer \"$rlcBufferPer\" no available";
   helpFunction
fi

if [ "$tcpTypeId" != "QUIC" ] && [ "$tcpTypeId" != "UDP" ] && [ "$tcpTypeId" != "TcpNewReno" ] && [ "$tcpTypeId" != "TcpBbr" ] && [ "$tcpTypeId" != "TcpCubic" ] && [ "$tcpTypeId" != "TcpHighSpeed" ] && [ "$tcpTypeId" != "TcpBic" ] && [ "$tcpTypeId" != "TcpLinuxReno" ]
then
   echo "tcpTypeId \"$tcpTypeId\" no available";
   helpFunction
fi

if [ "$AQM" != "None" ] && [ "$AQM" != "RED" ] 
then
   echo "AQM \"$AQM\" no available";
   helpFunction
fi
printf "\nRunning ${magenta}$0 -t ${tcpTypeId} -r ${rlcBufferPer} -s ${serverType} -n ${ueNum} -c ${myscenario} -a ${AQM} ${clear}\n"

if [ "$tcpTypeId" == "UDP" ]; then
   flowType='UDP'
elif [ "$tcpTypeId" == "QUIC"  ]; then
   flowType='QUIC'
else
   flowType='TCP'
fi

servertag=${serverType:0:1}

if [ $rlcBufferPer -lt 10 ]; then
    buffertag="00$rlcBufferPer"
elif [ $rlcBufferPer -lt 100 ]; then
    buffertag="0$rlcBufferPer"
else
    buffertag="$rlcBufferPer"
fi


echo
printf "\tRLCBuffer: ${green}${rlcBufferPer}${clear}\n"
printf "\ttcpTypeId: ${magenta}${tcpTypeId}${clear}\n"
printf "\tServer: ${green}${serverType}${clear}\n"
printf "\tScenario: ${green}${myscenario}${clear}\n"
echo

myhome="."
me=`basename "$0"`
myapp=`echo "$me" | cut -d'.' -f1`

#create out folder
outfolder="${myhome}/out"
if [ ! -d "$outfolder" ];
then
	mkdir $outfolder
fi

#create bk folder
bkfolder=${myscenario}"-"$tcpTypeId"-"$servertag"-"$buffertag"-UE"${ueNum}"-AQM_"${AQM}"-"`date +%Y%m%d%H%M`

if [ ! -d "$outfolder/$bkfolder" ];
then
	mkdir $outfolder/$bkfolder
fi

echo $outfolder/$bkfolder

#backup run-sim and cc
cp $me $outfolder/$bkfolder/$me.txt
cp ${myhome}/${myapp}.cc $outfolder/$bkfolder/${myapp}.cc.txt
cp packet-error-rate.sh $outfolder/$bkfolder/packet-error-rate.sh.txt
cp quic-perf-graph.py $outfolder/$bkfolder/quic-perf-graph.py.txt


$ns3home/ns3 run "`echo $myapp`
   --frequency=`echo $frequency`
   --bandwidth=`echo $bandwidth`
   --flowType=`echo $flowType`
   --tcpTypeId=`echo $tcpTypeId`
   --serverType=`echo $serverType`
   --rlcBufferPerc=`echo $rlcBufferPer`
   --speed=`echo $speed`
   --simTime=`echo $simTime`
   --iniTime=`echo $iniTime`
   --ueNum=`echo $ueNum`
   --phyDistro=`echo $myscenario`
   --AQM=`echo $AQM`
   " --cwd `echo $outfolder/$bkfolder` 


echo
printf "Running... Packet Error Rate Script\n"
echo

./packet-error-rate.sh $outfolder/$bkfolder

echo
printf "Running... Graph Script\n"
echo

echo "python3 quic-perf-graph.py $outfolder/$bkfolder"
python3 quic-perf-graph.py $outfolder/$bkfolder


echo
printf "Compressing files\n"
echo
gzip $outfolder/$bkfolder/*.txt &


source quic-sim-backup.sh $outfolder/$bkfolder

toc=$(date +%s)
printf "Simulation Processed in: "${magenta}$(($toc-$tic))${clear}" seconds\n"