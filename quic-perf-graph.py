import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cbook import get_sample_data
from matplotlib.offsetbox import AnnotationBbox,OffsetImage
import matplotlib.patches as mpatches
from scipy import special
import math
import pandas as pd
from datetime import datetime
import time
import sys
import configparser
import os , zipfile
from os import listdir
import json

# Set text colors
clear = '\033[0m'
red = '\033[0;31m'
green = '\033[0;32m'
yellow = '\033[0;33m'
blue = '\033[0;34m'
magenta = '\033[0;35m'
cyan = '\033[0;36m'

# Set Background colors
bg_red = '\033[0;41m'
bg_green = '\033[0;42m'
bg_yellow = '\033[0;43m'
bg_blue = '\033[0;44m'
bg_magenta = '\033[0;45m'
bg_cyan = '\033[0;46m'

colors = ['blue', 'green', 'red', 'orange', 'magenta', 'cyan', 'yellow', 'lightblue', 'pink', 'purple', 'lime']
show_title = 0
# Set graph 
plt.rc('font', size = 12)       # Set the default text font size
plt.rc('axes', titlesize = 16)  # Set the axes title font size
plt.rc('axes', labelsize = 16)  # Set the axes labels font size
plt.rc('xtick', labelsize = 14) # Set the font size for x tick labels
plt.rc('ytick', labelsize = 14) # Set the font size for y tick labels
plt.rc('legend', fontsize = 14) # Set the legend font size
plt.rc('figure', titlesize = 18)# Set the font size of the figure title
plt.rc('lines', linewidth = 2)



tic = time.time()
myhome = os.path.dirname(os.path.realpath(__file__))+"/"
# myhome="/home/jsandova/ns-3.39/scratch/quic-perf/"

if (len(sys.argv)>1):
    myhome = myhome + sys.argv[1] + "/"
    print(f"Processing: {cyan}{myhome}{clear}\n")
else:
    print(red + "bye" + clear)
    exit()

if ( not os.path.exists(myhome) ):
    print(f"Folder No Found: {red}{myhome}{clear}")
    exit()


# Read parameters of the simulation
config = configparser.ConfigParser()
config.read(myhome + 'graph.ini')

NRTrace = config['general']['NRTrace']
TCPTrace = config['general']['TCPTrace']
flowType = config['general']['flowType']
tcpTypeId = config['general']['tcpTypeId']
resamplePeriod=int(config['general']['resamplePeriod'])
simTime = float(config['general']['simTime'])
AppStartTime = float(config['general']['AppStartTime'])
rlcBuffer = float(config['general']['rlcBuffer'])
rlcBufferPerc = int(config['general']['rlcBufferPerc'])
serverType = config['general']['serverType']
myscenario = config['general']['myscenario'] if config.has_option('general', 'myscenario') else 'outdoor'
phyDistro = config['general']['phyDistro'] if config.has_option('general', 'phyDistro') else '1'
serverID = config['general']['serverID']
UENum = int(config['general']['UENum'])
SegmentSize = float(config['general']['SegmentSize']) 
dataRate = float(config['general']['dataRate']) if config.has_option('general', 'dataRate') else 1000
gNbNum = int(config['gNb']['gNbNum'])
gNbX = float(config['gNb']['gNbX'])
gNbY = float(config['gNb']['gNbY'])
gNbD = float(config['gNb']['gNbD'])
enableBuildings = int(config['building']['enableBuildings'])
gridWidth = int(config['building']['gridWidth'])
buildN = int(config['building']['buildN'])
buildX = float(config['building']['buildX'])
buildY = float(config['building']['buildY'])
buildDx = float(config['building']['buildDx'])
buildDy = float(config['building']['buildDy'])
buildLx = float(config['building']['buildLx'])
buildLy = float(config['building']['buildLy'])


# Max limit in plot
thr_limit = dataRate*1.1
thr_limit = 200
rtt_limit = 100



points=np.array([])
parts=np.array([[]])
myscenario = config['general']['myscenario'] if config.has_option('general', 'myscenario') else 'outdoor'

if phyDistro == "3":
    parts=np.array([[ 0, 3, "0-3"],
                    [ 3, 7,"3-7"],
                    [ 7, 17.4,"7-17"],
                    [ 17.4, 19.9,"17-20"],
                    [ 19.9, 28.4,"20-28"],
                    [ 28.4, 31,"28-31"],
                    [ 31, 39.4,"32-39"],
                    [ 39.4, 43.6,"39-44"],
                    [ 43.6, 51,"44-51"],
                    [ 51, 60,"51-60"],
                    [ 0, 60,"0-60"],
                ])
else:
    parts=np.array([[ 0, 20, "0-20"],
                    [ 20, 40,"20-40"],
                    [ 40, 60,"40-60"],
                    [ 0, 60,"0-60"],
                ])
    parts=np.array([[ 0, 60,"0-60"],
                ])

if tcpTypeId=="TcpCubic" or tcpTypeId=="TcpBbr":
    tcpTypeId= tcpTypeId[0:3]+tcpTypeId[3:].upper()

subtitle = str(rlcBufferPerc) + '% BDP - Server: ' + serverType
prefix = tcpTypeId + '-'+ serverType + '-' + str(rlcBufferPerc) + '-' + 'UE' + str(UENum) + '-'

def main():
    tic = time.time()
    remove_graph(myhome)
    graph_mobility(myhome)
    graph_SINR(myhome)
    graph_CQI_BLER(myhome)
    graph_path_loss(myhome)
    graph_thr_tx(myhome)
    if flowType=="TCP":
        graph_tcp(myhome)
        rtt = graph_rtt(myhome)

    graph_thr_rlcbuffer(myhome)
    graph_thr_packetdrop(myhome)
    calculate_metrics(myhome)

    results = configparser.ConfigParser()
    results.read(myhome + 'results.ini')

    for p in range(parts.shape[0]-1):
        rtt_part=rtt[p]
        for ue in range(len(rtt_part)):
            results['part-'+str(p+1)]['RTT_MEAN-'+str(ue+1)]= str(rtt_part[ue][0])
            results['part-'+str(p+1)]['RTT_STD-'+str(ue+1)]= str(rtt_part[ue][1])
        
    with open(myhome + 'results.ini', 'w') as configfile:
        results.write(configfile)

    toc = time.time()
    print(f"\nAll Processed in: %.2f" %(toc-tic))






def remove_graph(myhome):
    #delete all png
    for item in os.listdir(myhome):
        if item.endswith(".png"):
            os.remove(os.path.join(myhome, item))

def graph_mobility(myhome):
    tic = time.time()
    file = "mobilityPosition.txt"
    jsonfile="PhysicalDistribution.json"
    title = "Mobility"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        mob = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        mob = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)
    mob.set_index('Time', inplace = True)

    print('plotting', end = ".", flush = True)
    fig, ax = plt.subplots()
    for ue in mob['UE'].unique():
        ax1= mob[mob['UE'] == ue].plot.scatter( x = 'x',y = 'y', ax = ax,c = colors[ue-1])
    gNbicon=plt.imread(get_sample_data(myhome + '../../img/gNb.png'))
    gNbbox = OffsetImage(gNbicon, zoom = 0.25)

    if os.path.exists(myhome + jsonfile):
        with open(myhome + jsonfile) as json_file:
            data = json.load(json_file)

        for g in data['gnb']:
            gNbPos=[ g['x'] , g['y']*1.1 ]
            gNbab=AnnotationBbox(gNbbox,gNbPos, frameon = False)
            ax.add_artist(gNbab)

        if (enableBuildings):
            for b in data['Buildings']:
                if ("ExternalWallsType" in b) and (b['ExternalWallsType'] == 0) :
                    buildcolor = "green"
                else:
                    buildcolor = "red"

                rect=mpatches.Rectangle(( int(b['xmin']), int(b['ymin']) ),
                                        float(b['xwidth']), 
                                        float(b['ywidth']), 
                                        alpha = 0.5, 
                                        facecolor=buildcolor)
                plt.gca().add_patch(rect)

    else:
        if (enableBuildings):
            for b in range(buildN):
                row, col = divmod(b,gridWidth)
                rect=mpatches.Rectangle((buildX+(buildLx+buildDx)*col,buildY+(buildLy+buildDy)*row),buildLx,buildLy, alpha = 0.5, facecolor="red")
                plt.gca().add_patch(rect)
        for g in range(gNbNum):
            gNbPos=[gNbX,(gNbY+g*gNbD)*1.1]
            gNbab=AnnotationBbox(gNbbox,gNbPos, frameon = False)
            ax.add_artist(gNbab)

    UEicon=plt.imread(get_sample_data(myhome + '../../img/UE.png'))
    UEbox = OffsetImage(UEicon, zoom = 0.02)

    for ue in mob['UE'].unique():
        print(ue, end = ".", flush = True)
        UEPos = mob[mob['UE'] == ue][['x','y']].iloc[-1:].values[0]*1.01
        UEab = AnnotationBbox(UEbox,UEPos, frameon = False)
        ax.add_artist(UEab)

    plt.xlim([min(0, mob['x'].min()) , (100 if max(10,mob['x'].max()+1)>10 else 10) ])
    plt.ylim([min(0, mob['y'].min()) , (100 if max(10,mob['y'].max()+1)>10 else 10) ])
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel("Distance [m]")
    fig.savefig(myhome + prefix + file + '.png')
    plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))


def graph_SINR(myhome):
    files={'Control':'DlCtrlSinr.txt',
            'Data': 'DlDataSinr.txt'}
    for key, value in files.items():
        tic = time.time()
        title = "SINR " + key
        file = value
        print(cyan + title + clear, end = "...", flush = True)
        print('load', end = "", flush = True)
        if os.path.exists(myhome + file):
            SINR = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
        else:
            SINR = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip')
        print('ed', end = ".", flush = True)
        SINR.set_index('Time', inplace = True)
        SINR = SINR[SINR['RNTI'] != 0]

        print('plotting', end = ".", flush = True)
        fig, ax = plt.subplots()
        SINR.groupby('RNTI')['SINR(dB)'].plot(legend=True, title = title)
        plt.ylim([min(15, SINR['SINR(dB)'].min()) , max(30,SINR['SINR(dB)'].max())])
        ax.set_ylabel("SINR(dB)")
        ax.set_xlabel("Time(s)")
        plt.suptitle(title)
        plt.title(subtitle)
        fig.savefig(myhome + prefix +'SINR-'+key+'.png')
        plt.close()
        toc = time.time()
        print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_CQI_BLER(myhome):
    tic = time.time()
    file = "RxPacketTrace.txt"
    title = "CQI"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        CQI = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        CQI = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    CQI.set_index('Time', inplace = True)
    CQI = CQI[CQI['rnti'] != 0]
    CQI = CQI[CQI['direction'] =='DL']

    print('plotting', end = ".", flush = True)
    fig, ax = plt.subplots()
    CQI.groupby('rnti')['CQI'].plot(legend=True, title = title)
    plt.ylim([0, 16])
    ax.set_ylabel("CQI")
    ax.set_xlabel("Time(s)")
    plt.suptitle(title)
    plt.title(subtitle)
    fig.savefig(myhome + prefix +'CQI'+'.png')
    plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

    # BLER
    title = "BLER"
    print(cyan + title + clear, end = "...", flush = True)
    CQI['Time'] = CQI.index
    CQI.index = pd.to_datetime(CQI['Time'],unit = 's')
    BLER = pd.DataFrame(CQI.groupby('rnti').resample(str(resamplePeriod)+'ms').TBler.mean())

    BLER = BLER.reset_index(level = 0)
    BLER = BLER[~BLER['TBler'].isna()]

    BLER['Time'] = BLER.index
    BLER['Time'] = BLER['Time'].astype(np.int64)/1e9
    BLER = BLER.set_index('Time')

    print('plotting', end = ".", flush = True)
    fig, ax = plt.subplots(constrained_layout=True)

    for ue in BLER['rnti'].unique():
        print(ue, end = ".", flush = True)
        plt.semilogy(BLER[BLER['rnti'] == ue].index, BLER[BLER['rnti'] == ue].TBler, label='UE '+str(ue))

    plt.xlabel("Time(s)")
    plt.ylabel("BLER")
    # ax.yaxis.labelpad = 50
    # ax.set_ylim([abs(min([(1e-20) ,BLER.TBler.min()*0.9])) , 1])
    ax.set_ylim([1e-20 , 1e0])
    if len(BLER['rnti'].unique())>1:
        plt.legend(ncol = len(BLER['rnti'].unique())//3)

    plt.title(title)
    plt.grid(True, which="both", ls="-")
    plt.suptitle(title)
    plt.title(subtitle)
    
    fig.savefig(myhome + prefix +'BLER'+'.png')
    plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_path_loss(myhome):
    tic = time.time()
    file = "DlPathlossTrace.txt"
    title = "Path Loss"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        PLOSS = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        PLOSS = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    PLOSS.set_index('Time(sec)', inplace = True)
    PLOSS = PLOSS.loc[PLOSS['IMSI'] != 0]
    PLOSS = PLOSS[PLOSS['pathLoss(dB)'] < 0]

    # PLOSS['IMSI'] = 'UE '+ str(PLOSS['IMSI'])

    print('plotting', end = ".", flush = True)
    fig, ax = plt.subplots(constrained_layout=True)
    PLOSS.groupby(['IMSI'])['pathLoss(dB)'].plot(legend=True,title = file)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("pathLoss [dB]")
    plt.suptitle(title)
    plt.title(subtitle)
    fig.savefig(myhome + prefix +'PATH_LOSS'+'.png')
    plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))


def graph_thr_tx(myhome):
    tic = time.time()
    title = tcpTypeId[3:] if (tcpTypeId[:3] == "Tcp") else tcpTypeId
    title = tcpTypeId + " "
    title = title+"Throughput TX"
    file = "NrDlPdcpTxStats.txt"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        thrtx = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        thrtx = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    thrtx = thrtx.groupby(['time(s)','rnti'])['packetSize'].sum().reset_index()
    thrtx.index = pd.to_datetime(thrtx['time(s)'],unit='s')

    thrtx = pd.DataFrame(thrtx.groupby('rnti').resample(str(resamplePeriod)+'ms').packetSize.sum())
    thrtx = thrtx.reset_index(level = 0)

    thrtx['InsertedDate'] = thrtx.index
    thrtx['deltaTime'] = thrtx['InsertedDate'].astype(np.int64)/1e9
    thrtx['Time'] = thrtx['deltaTime']
    thrtx['deltaTime'] = thrtx.groupby('rnti').diff()['deltaTime']

    thrtx.loc[~thrtx['deltaTime'].notnull(),'deltaTime'] = thrtx.loc[~thrtx['deltaTime'].notnull(),'InsertedDate'].astype(np.int64)/1e9
    thrtx['throughput'] = thrtx['packetSize']*8 / thrtx['deltaTime']/1e6
    thrtx = thrtx.set_index('Time')

    print('plotting', end = ".", flush = True)
    fig, ax = plt.subplots(constrained_layout=True)
    thrtx.groupby(['rnti'])['throughput'].plot()

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [Mb/s]")
    ax.set_ylim([0 , max([thr_limit ,thrtx['throughput'].max()*1.1])])
    if show_title:
        plt.suptitle(title, y = 0.99)
        plt.title(subtitle)
    if len(thrtx['rnti'].unique())>1:
        plt.legend(ncol = len(thrtx['rnti'].unique())//3)


    fig.savefig(myhome + prefix + 'ThrTx' + '.png')
    plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_thr_rlcbuffer(myhome):
    tic = time.time()
    title = tcpTypeId[3:] if (tcpTypeId[:3] == "Tcp") else tcpTypeId
    title = tcpTypeId + " "
    title = title + "Throughput vs RLC Buffer"
    file = "NrDlPdcpRxStats.txt"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        thrrx = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        thrrx = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    thrrx = thrrx.groupby(['time(s)','rnti'])['packetSize'].sum().reset_index()
    thrrx.index = pd.to_datetime(thrrx['time(s)'],unit='s')

    thrrx = pd.DataFrame(thrrx.groupby('rnti').resample(str(resamplePeriod)+'ms').packetSize.sum())
    thrrx = thrrx.reset_index(level = 0)

    thrrx['InsertedDate'] = thrrx.index
    thrrx['deltaTime'] = thrrx['InsertedDate'].astype(np.int64)/1e9
    thrrx['Time'] = thrrx['deltaTime']

    thrrx['deltaTime'] = thrrx.groupby('rnti').diff()['deltaTime']

    thrrx.loc[~thrrx['deltaTime'].notnull(),'deltaTime'] = thrrx.loc[~thrrx['deltaTime'].notnull(),'InsertedDate'].astype(np.int64)/1e9
    thrrx['throughput'] =  thrrx['packetSize']*8 / thrrx['deltaTime']/1e6
    thrrx['throughput'] = thrrx['throughput'].astype(float)

    thrrx = thrrx.set_index('Time')
    if (flowType=='TCP') or (flowType=='QUIC'):
        print('load', end = "", flush = True)
        file = "RlcBufferStat.txt"
        if os.path.exists(myhome + file):
            rlcdrop = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
        else:
            rlcdrop = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
        print('ed', end = ".", flush = True)
        rlcdrop['direction'] = 'UL'
        rlcdrop.loc[rlcdrop['PacketSize'] > 1500,'direction'] = 'DL'
        rlc = rlcdrop[rlcdrop['direction'] =='DL']
        rlc.index = pd.to_datetime(rlc['Time'],unit='s')
        print(".", end = "", flush = True)
        rlcdrop = pd.DataFrame(rlc.resample(str(resamplePeriod)+'ms').dropSize.sum())
        rlcdrop['Time'] = rlcdrop.index.astype(np.int64)/1e9
        rlcdrop = rlcdrop.set_index('Time')
        rlcdrop['state'] = 0
        rlcdrop.loc[rlcdrop['dropSize'] > 0,'state'] = 1
        rlcbuffer = pd.DataFrame(rlc.resample(str(resamplePeriod)+'ms').txBufferSize.max())
        rlcbuffer['Time'] = rlcbuffer.index.astype(np.int64)/1e9
        rlcbuffer = rlcbuffer.set_index('Time')
        rlcbuffer['txBufferSize'] = rlcbuffer['txBufferSize']/rlcBuffer
        rlcdrop['state'] = rlcdrop['state']*rlcbuffer['txBufferSize']
        rlcbuffer.loc[rlcdrop['state'] > 0,'txBufferSize'] = 0

    print('plotting', end = ".", flush = True)
    thrrx['t'] = thrrx.index
    rlcdrop['t'] = rlcdrop.index
    rlcbuffer['t'] = rlcbuffer.index
    for p in range(parts.shape[0] ):
        [x, y, z] = parts[p,:]
        print(z, end = ".", flush = True)
        fig, ax = plt.subplots(constrained_layout=True)
        ax1 = thrrx[(thrrx['t'] >= float(x)) & (thrrx['t'] <= float(y))].groupby(['rnti'])['throughput'].plot( ax=ax)
        text_legend = thrrx['rnti'].drop_duplicates().sort_values().unique()
        text_legend = [ 'UE ' + str(i)  for i in text_legend]
        if (UENum>1):
            plt.legend(text_legend, loc = 'upper left',ncol = 2)

        
        if p<parts.shape[0]-1:
            for d in range(points.shape[0]):
                if (points[d] >= float(x)) & (points[d] <= float(y)):
                    mytext = "("+str(points[d])+","+str(round(thrrx.loc[points[d]]['throughput'],2)) +")"
                    ax.annotate( mytext, (points[d] , thrrx.loc[points[d]]['throughput']))

        ax2 = rlcdrop[(rlcdrop['t'] >= float(x)) & (rlcdrop['t'] <= float(y))]['state'].plot.area( secondary_y=True,
                                                                                        ax=ax,
                                                                                        alpha = 0.2,
                                                                                        color="red",
                                                                                        legend=False)
        ax2.set_ylabel("RLC Buffer [%]", loc = 'bottom')
        ax2.set_ylim(0,4)
        ax2.set_yticks([0,0.5,1])
        ax2.set_yticklabels(['0','50','100' ])
        
        ax3 = rlcbuffer[(rlcbuffer['t'] >= float(x)) & (rlcbuffer['t'] <= float(y))]['txBufferSize'].plot.area( secondary_y=True,
                                                                                            ax=ax,  
                                                                                            alpha = 0.2, 
                                                                                            color="green", 
                                                                                            legend=False)
        ax3.set_ylim(0,np.nanmax([ rlcbuffer[(rlcbuffer['t'] >= float(x)) & (rlcbuffer['t'] <= float(y))]['txBufferSize'].max()*4, 4]))

        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Throughput [Mb/s]")
        ax.set_ylim([0 , max([thr_limit,thrrx[(thrrx['t'] >= float(x)) & (thrrx['t'] <= float(y))]['throughput'].max()*1.1])])
        # ax.set_ylim([0, 750])
        if show_title:
            plt.suptitle(title, y = 0.99)
            plt.title(subtitle)
        # if (UENum>1):
        #     plt.legend()
        plotfile = myhome + prefix + 'ThrRx' +'-'+ z + '.png'
        fig.savefig(plotfile)
        plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_thr_packetdrop(myhome):
    tic = time.time()
    title = tcpTypeId[3:] if (tcpTypeId[:3] == "Tcp") else tcpTypeId
    title = tcpTypeId + " "
    title = title+"Throughput vs PER"
    file = "tcp-per.txt"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        tx_ = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        tx_ = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)
    tx_.index = pd.to_datetime(tx_['Time'],unit='s')
    tx_thr = pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').BytesTx.sum())
    tx_drp = pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').BytesDroped.sum())

    tx_drp['PacketsTx'] = pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').PacketsTx.sum())
    tx_drp['PacketsDroped'] = pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').PacketsDroped.sum())

    tx_thr = tx_thr.reset_index(level = 0)
    tx_thr['Throughput'] =  tx_thr['BytesTx']*8 / 0.1 / 1e6
    tx_thr['Time'] = tx_thr['Time'].astype(np.int64) / 1e9
    tx_thr = tx_thr.set_index('Time')

    tx_drp = tx_drp.reset_index(level = 0)
    tx_drp['Throughput'] =  tx_drp['BytesDroped']*8 / 0.1/1e6
    tx_drp['PER'] = tx_drp['PacketsDroped']/tx_drp['PacketsTx']
    tx_drp['Time'] = tx_drp['Time'].astype(np.int64)/1e9
    tx_drp = tx_drp.set_index('Time')
    for p in range(parts.shape[0] ):
        
        [x, y, z] = parts[p,:]
        fig, ax = plt.subplots(constrained_layout=True)
        if p<parts.shape[0]-1:
            # plt.plot(tx_thr.loc[x:y].index, tx_thr['Throughput'].loc[x:y], '-o', markevery=tx_thr.loc[x:y].index.get_indexer(points, method='nearest'))
            ax1 = tx_thr['Throughput'].loc[x:y].plot(ax=ax, markevery=tx_thr.loc[x:y].index.get_indexer(points, method='nearest'))
            for d in range(points.shape[0]):
                if (points[d] >= float(x)) & (points[d] <= float(y)):
                    mytext = "("+str(points[d])+","+str(round(tx_thr.loc[points[d]]['Throughput'],2)) +")"
                    ax.annotate( mytext, (points[d] , tx_thr.loc[points[d]]['Throughput']))
        else:
            ax1 = tx_thr['Throughput'].loc[x:y].plot(ax=ax)
        ax2 = tx_drp['PER'].loc[x:y].plot.area(  secondary_y=True, ax=ax,  alpha = 0.2, color="red")
        # ax3 = tx_drp['Throughput'].plot.area(  ax=ax,  alpha = 0.2, color="red")

        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Throughput [Mb/s]")
        ax.set_ylim([0 , max([thr_limit,tx_thr['Throughput'].loc[x:y].max()*1.1])])

        ax2.set_ylabel("PER [%]", loc = 'bottom')
        ax2.set_ylim(0,4)

        ax2.set_yticks([0,0.5,1])
        ax2.set_yticklabels(['0','50','100' ])

        if show_title:
            plt.suptitle(title, y = 0.99)
            plt.title(subtitle)
        fig.savefig(myhome + prefix + 'ThrDrp' +'-'+ z+ '.png')
        plt.close()
    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_rtt(myhome):
    tic = time.time()
    title = tcpTypeId[3:] + " "
    title = title+"RTT"
    file = "tcp-delay.txt"
    print(cyan + title + clear, end = "...", flush = True)
    print('load', end = "", flush = True)
    if os.path.exists(myhome + file):
        ret = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
         ret = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    ret = ret.groupby(['Time','UE'])['rtt'].mean().reset_index()

    ret.index = pd.to_datetime(ret['Time'],unit='s')

    ret = ret[(ret['Time'] >= AppStartTime) & (ret['Time'] <= simTime - AppStartTime)]

    ret = pd.DataFrame(ret.groupby(['UE']).resample(str(resamplePeriod)+'ms').rtt.mean())

    ret = ret.reset_index(level = 0)
    ret['Time'] = ret.index.astype(np.int64) / 1e9

    ret = ret.set_index('Time')
    ret['rtt'] = ret['rtt']*1000
    ret['t'] = ret.index
    rtt=[]
    for p in range(parts.shape[0] ):
        
        [x, y, z] = parts[p,:]
        fig, ax = plt.subplots()
      
        
        if p<parts.shape[0]-1:
            if len(ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['UE'].unique()>1):
                ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))].groupby('UE')['rtt'].plot()
            else:
                ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['rtt'].plot()
            # plt.plot(ret.loc[x:y].index, ret['rtt'].loc[x:y], '-o',markevery = ret.loc[x:y].index.get_indexer(points, method='nearest'))
            
            for d in range(points.shape[0]):
                if (points[d] >= float(x)) & (points[d] <= float(y)):
                    try:
                        mytext = "("+str(points[d])+","+str(round(ret.loc[points[d]]['rtt'],2)) +")"
                        ax.annotate( mytext, (points[d] , ret.loc[points[d]]['rtt']))
                    except KeyError:
                        print(d)
            rtt_part = []
            for ue in ret['UE'].drop_duplicates().sort_values().unique():
                rtt_part.append([ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))  & (ret['UE'] ==ue) ]['rtt'].mean(), 
                                ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))  & (ret['UE'] ==ue) ]['rtt'].std() ])
            rtt.append(rtt_part)

        else:
            ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))].groupby('UE')['rtt'].plot()
            # ret['rtt'].loc[x:y].plot()

        ax.set_ylabel("RTT [ms]")
        ax.set_ylim(0, max([rtt_limit, ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['rtt'].mean()*2]))
        # ax.set_ylim(0, 40)
        if show_title:
            plt.suptitle(title, y = 0.99)
            plt.title(subtitle)
        fig.savefig(myhome + prefix + 'RTT' +'-'+ z+ '.png')
        plt.close()

    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))
    return rtt


def graph_tcp(myhome):
    files={'Congestion Window':'tcp-cwnd-',
           'Inflight Bytes':'tcp-inflight-',}
    for key, value in files.items():
        tic = time.time()
        title = key
        print(cyan + title + clear, end = "...", flush = True)
        print('load', end = "", flush = True)

        DF = pd.DataFrame()
        for u in range(UENum):
            # print(u)
            file = value+serverID+"-"+str(u)+".txt"
            if os.path.exists(myhome + file):
                TMP = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
            else:
                file =  file + ".gz"
                TMP = pd.read_csv(myhome + file, compression='gzip', sep = "\t", on_bad_lines='skip' )
            TMP['rnti'] = u+1
            DF = pd.concat([DF,TMP], sort=False)

        print("ed", end = ".", flush = True)
        DF.index = pd.to_datetime(DF['Time'],unit='s')

        DF = DF[(DF['Time'] >= AppStartTime) & (DF['Time'] <= simTime - AppStartTime)]
        DF = pd.DataFrame(DF.groupby('rnti').resample(str(resamplePeriod)+'ms').newval.mean())
        DF = DF.reset_index(level = 0)

        DF['Time'] = DF.index.astype(np.int64)/1e9

        DF = DF.set_index('Time')
        DF['newval'] = DF['newval']/1024
        DF['t'] = DF.index
        for p in range(parts.shape[0] ):
            [x, y, z] = parts[p,:]
            if (len(DF[(DF['t'] >= float(x)) & (DF['t'] <= float(y))].index)>0):
                fig, ax = plt.subplots(constrained_layout=True)
                ax1 = DF[(DF['t'] >= float(x)) & (DF['t'] <= float(y))].groupby(['rnti'])['newval'].plot( ax=ax)

                if len(DF['rnti'].unique())>1:
                    plt.legend(ncol = len(DF['rnti'].unique())//3)
                plt.suptitle(title)
                plt.title(subtitle)
                ax.set_ylabel(key+" [KBytes]")

                fig.savefig(myhome + prefix + value + z+'.png')

                plt.close()
        toc = time.time()
        print(f"\tProcessed in: %.2f" %(toc-tic))

def calculate_metrics(myhome):
    conv_thresh=0.10
    tic = time.time()
    DEBUG=0
    title = "Convergence Time"
    file = "NrDlPdcpRxStats.txt"
    print(cyan + title + clear, end = "...", flush = True)

    print('load', end="", flush=True)
    if os.path.exists(myhome+file):
        tmp = pd.read_csv(myhome+file, sep = "\t", on_bad_lines='skip' )
    else:
        tmp = pd.read_csv(myhome+file+ ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    tmp=tmp.groupby(['time(s)','rnti'])['packetSize'].sum().reset_index()
    tmp.index=pd.to_datetime(tmp['time(s)'],unit='s')

    # results file
    results = configparser.ConfigParser()
    results['DEFAULT'] = {'UENum': UENum,
                            'Sec': parts.shape[0]-1}
    for p in range(parts.shape[0]-1):
        [x, y, z] = parts[p,:]
        results['part-'+str(p+1)]= {'x':x,
                                    'y':y}

    for ue in tmp['rnti'].drop_duplicates().sort_values().unique():
        thrrx=pd.DataFrame(tmp.groupby('rnti').resample(str(resamplePeriod)+'ms').packetSize.sum())
        thrrx=thrrx.reset_index(level=0)
        thrrx=thrrx[thrrx['rnti']==ue]
        thrrx['InsertedDate']=thrrx.index
        thrrx['deltaTime']=thrrx['InsertedDate'].astype(np.int64)/1e9
        thrrx['Time']=thrrx['deltaTime']

        thrrx['deltaTime']=abs(thrrx.diff()['deltaTime'])

        thrrx.loc[~thrrx['deltaTime'].notnull(),'deltaTime']=thrrx.loc[~thrrx['deltaTime'].notnull(),'InsertedDate'].astype(np.int64)/1e9
        thrrx['throughput']= thrrx['packetSize']*8 / thrrx['deltaTime']/1e6

        thrrx=thrrx.set_index('Time')
        if (DEBUG==1): print(thrrx)
        print('prepare', end=".", flush=True)

        thr=thrrx
        thr['Time']=thr.index
        if (DEBUG==1): print(thr)
        for p in range(parts.shape[0]-1):
            print(f"p{p}",  end=":", flush=True)

            [x, y, z] = parts[p,:]
            if (DEBUG==1): print(green + "Range: ["+ x+","+ y+"]" + clear)
            deltat=max([1.6,(float(y)-float(x))/5])
            
            # Throughput > Zero
            xi=float(x)
            if (DEBUG==1): print("["+ str(xi)+","+ str(xi+deltat)+"]")
            if (DEBUG==1): print(magenta + "UE:"+ str(ue) + " Finding Throughput Zero in: ["+ str(xi)+","+ str(xi+deltat)+"]" + clear)
            if (DEBUG==1): print(f"First xi: %f" % xi)
            # Min time in this range when thr>0
            if (len(thr[((thr['Time']>= float(x) ) & (thr['Time']<=float(y)) & (thr['throughput']>0) )]['throughput'].index)>0):
                xi=thr[((thr['Time']>= float(x) ) & (thr['Time']<=float(y))  & (thr['throughput']>0) )]['throughput'].index.values.min()
            else:
                xi=float(y)
            if (DEBUG==1): print(f"Sec xi: %f" % xi)

            # Thr mean
            throughput=np.array(thr[(thr['Time']>= float(x) ) & (thr['Time']<= float(y))]['throughput'].values)
            thr_mean = throughput.mean()

            # Threshhold
            while xi < float(y)-deltat:
                if (DEBUG==1): print(magenta + "UE:"+ str(ue) + " Finding stability in: ["+ str(xi)+","+ str(xi+deltat)+"]" + clear)

                # range to analize
                throughput=np.array(thr[(thr['Time']>= xi ) & (thr['Time']<=xi+deltat)]['throughput'].values)
                mytime=np.array(thr[(thr['Time']>= xi ) & (thr['Time']<=xi+deltat )]['throughput'].index.values)
                if (DEBUG==1): print(mytime)
                if (DEBUG==1): print(throughput)
                

                # Criteria thr.min <= conv_thresh * thr.mean
                if len(throughput)>1:
                    goal = throughput.mean()
                    if (DEBUG==1): print(f"THR: [%f - %f]" % (goal*(1-conv_thresh), goal*(1+conv_thresh)))
                    if(throughput.min()<=goal*(1-conv_thresh)):
                        i=min([np.where(throughput==throughput[throughput<=goal*(1-conv_thresh)].max())[0][0] +1 , len(throughput) -1])
                        xi=mytime[i]
                    elif (throughput.max()>=goal*(1+conv_thresh)):
                        xi=xi+resamplePeriod/1000
                    else:
                        if (DEBUG==1): print(red + "Convergence" + clear)
                        break
                else:
                    xi=xi+resamplePeriod/1000
            if (DEBUG==1): print(f"Final xi: %f" % xi)
            if (DEBUG==1): print(f"Final: %f" % (float(y)-deltat))
            if xi>=float(y)-deltat:
                if (DEBUG==1): print(cyan +  "UE:"+ str(ue) + " NO Convergence in: ["+ str(x)+","+ str(y)+"]" + clear)
                throughput=np.array(thr[(thr['Time']>= float(x) ) & (thr['Time']<=float(y) )]['throughput'].values)
                mytime=np.array(thr[(thr['Time']>= float(x) ) & (thr['Time']<=float(y) )]['throughput'].index.values)
                
                ct0=float(y)
                convergence_time=float(y)
                if len(throughput)>1:
                    goal = throughput.mean()
                    smooth=abs(throughput.max()-throughput.min())/throughput.mean()
                else:
                    goal=0
                    smooth=0
            else:
                if (DEBUG==1): print(cyan +  "UE:"+ str(ue) + " Convergence in: ["+ str(xi)+","+ str(xi+deltat)+"]" + clear)

                throughput=np.array(thr[(thr['Time']>= xi ) & (thr['Time']<=xi+deltat)]['throughput'].values)
                mytime=np.array(thr[(thr['Time']>= xi ) & (thr['Time']<=xi+deltat )]['throughput'].index.values)
                goal = throughput.mean()
                if (DEBUG==1): print(mytime)
                if (DEBUG==1): print(throughput)
                if (DEBUG==1): print(f"Goal: %f" % goal)
                # convergence time
                if len(throughput)>1:
                    if throughput[0]< goal:
                        i=np.where (throughput== throughput[throughput <= goal].max() )[0][0]
                    else:
                        i=np.where (throughput== throughput[throughput >= goal].max() )[0][0]
                    convergence_time=mytime[i] 
                    
                else:
                    if (DEBUG==1): print(red+ "Does Not converge" + clear)
                    throughput=np.array(thr['throughput'].values[-1:])
                    mytime=np.array(thr.index.values[-1:])
                    if (DEBUG==1): print(mytime)
                    if (DEBUG==1): print(throughput)
                    convergence_time=float(y)

                if (DEBUG==1): print(mytime)
                if (DEBUG==1): print(throughput)

    
                # usamos como referencia para calcular el throughput objetivo
                if(convergence_time>=mytime.max()):
                    i=len(mytime)-1
                else:
                    i = np.where(mytime==mytime[mytime>convergence_time][0])[0][0]

                if (DEBUG==1): print(f"convergence_time: %f" % convergence_time)
                if (DEBUG==1): print(f"i: %f" % i)

                if(i==0):
                    goal_max=0
                    goal_max=0
                else:
                    goal_max = throughput[i:].max()
                    goal_min = throughput[i:].min()

                if (DEBUG==1): print(f"i: {i} - {i+round(deltat/(resamplePeriod/1000))}")
                if (DEBUG==1): print(magenta + "Goal: " + str(goal) +"\t" + "["+ str(goal_min) +","+str(goal_max) + "]"+ clear )

                # finding contact point
                if(goal>=throughput.max()):
                    convergence_time=mytime.max()
                else:
                    if throughput[:i].mean() <= goal :
                        j = np.where(throughput==throughput[throughput>goal][0])[0][0] -1
                    else:
                        j = np.where(throughput==throughput[throughput<=goal][0])[0][0] -1
                    if (j<0): j=0
                    while (throughput[j]==throughput[j+1]): j=j+1
                    
                    convergence_time = mytime[j] + abs((mytime[j+1]-mytime[j])/(throughput[j+1]-throughput[j])*(goal-throughput[j]))

                if (DEBUG==1): print(magenta + "CT:" + str(convergence_time) + clear)

                # smoothness
                if goal==0:
                    smooth=0
                else:
                    smooth=abs(goal_max-goal_min)/goal            

                # print(f"El tiempo de convergencia de {t} en {p} es: {convergence_time-float(x)}")
                
            if (DEBUG==1): print("Plotting")
            if (DEBUG==1): print("CT: %f" %convergence_time)
            if (DEBUG==1): print("smooth: %f" %smooth)

            # Graphics
            fig, ax = plt.subplots()
            title="Convergence Time " + serverType
            subtitle= str(rlcBufferPerc) + '% BDP - Server: ' + serverType

            throughput=np.array(thr[(thr['Time']>= float(x) ) & (thr['Time']<= float(y)) ]['throughput'].values)
            mytime=np.array(thr[(thr['Time']>= float(x) ) & (thr['Time']<= float(y) ) ]['throughput'].index.values)

            # Original Curve
            ax.plot(mytime, throughput)

            # Polynomial
            # time_curve = np.linspace(float(x), min([ max([ct0, convergence_time])+ deltat, float(y) ]), 100)
            # throughput_curve = polynomial(time_curve)
            
            # # Crear el grafico comparado con los datos originales recortados
            # ax.plot(time_curve, throughput_curve)
            
            # Goal Line
            # ax.plot(time_curve,time_curve*0+goal, 'r--')
            # ax.annotate( "Goal", (max([0, time_curve[0]-10]) , goal ))
            # Goal Line
            if convergence_time< float(y):
                time_curve = np.linspace(float(x), convergence_time, 100)
                ax.plot(time_curve,time_curve*0+goal, 'r--')
                ax.annotate( "Goal", (time_curve[0] , goal*(1+conv_thresh/4) ))

            # Convergence Threshhold
            if (DEBUG==1): print(goal*(1-conv_thresh))
            ax.plot(mytime, mytime*0+goal*(1-conv_thresh), '--', color='orange')
            ax.plot(mytime, mytime*0+goal*(1+conv_thresh), '--', color='orange')
            # ax.annotate( "conv_thresh_min", (max([float(x), mytime[0]-10]) , goal*(1-conv_thresh) ))
            # ax.annotate( "conv_thresh_max", (max([float(x), mytime[0]-10]) , goal*(1+conv_thresh) ))

            # Min/max Line
            # time_curve = np.linspace(ct0, min([ max([ct0, convergence_time])+ deltat, float(y) ]), 100)
            # ax.plot(time_curve,time_curve*0+goal_min, color='red')
            # ax.plot(time_curve,time_curve*0+goal_max, color='red')
            
            # Convergence Time
            if convergence_time< float(y):
                if (float(x)<AppStartTime):
                    convergence_time=convergence_time-AppStartTime
                ax.plot([convergence_time]*10, np.linspace(goal, goal*(1-conv_thresh) *0.9, 10), '--', color='red')
                ax.annotate( "CT: " + str(round(convergence_time-float(x),2)) + "[s]", (convergence_time , goal*(1-conv_thresh)*0.9 ))
                rect=mpatches.Rectangle((xi,goal*(1-conv_thresh)),deltat,goal*(conv_thresh)*2, alpha=0.2, facecolor="orange")
                plt.gca().add_patch(rect)

            ax.set_xlabel('Time [s]')
            ax.set_ylabel('Throughput [Mb/s]')
            fig.set_tight_layout(True)
            if show_title:
                plt.suptitle(title, y=0.99)
                plt.title(subtitle)
            if (len(throughput)>0):
                ax.set_ylim([0, max([0,throughput.max()*1.1])])

            plotfile=myhome + prefix +'CT-'+str(z)+'-'+'UE'+ str(ue) +'.png'
            fig.savefig(plotfile)
            if (DEBUG==1): print(plotfile)
            plt.close()

            convergence_time=min([convergence_time-float(x), float(y)])
            if (convergence_time>=float(y)-float(x)):
                if len(throughput)>1:
                    smooth=abs(throughput.max()-throughput.min())/throughput.mean()
                else:
                    smooth=0
            if (DEBUG==1): print("CT: %f" %convergence_time)
            if (DEBUG==1): print("smooth: %f" %smooth)
            if (DEBUG==1): print("goal: %f" %goal)
            results['part-'+str(p+1)]['CT-'+str(ue)]= str(convergence_time)
            results['part-'+str(p+1)]['SMOOTH-'+str(ue)]= str(smooth)
            results['part-'+str(p+1)]['GOAL-'+str(ue)]= str(goal)
            results['part-'+str(p+1)]['THR-'+str(ue)]= str(thr_mean)
            


    with open(myhome + 'results.ini', 'w') as configfile:
        results.write(configfile)


    toc = time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))




if __name__ == '__main__':
    main()


exit ()




if flowType=='UDP':
    ###############
    ## Delay
    ###############
    fig, ax = plt.subplots()
    title = tcpTypeId + " "
    title = title+"Delay RX"
    print(cyan + title + clear, end = "...", flush = True)

    file = "NrDlPdcpRxStats.txt"
    if os.path.exists(myhome + file):
        RXSTAT = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        file =  file + ".gz"
        RXSTAT = pd.read_csv(myhome + file, compression='gzip', sep = "\t", on_bad_lines='skip' )

    rx=RXSTAT.groupby(['time(s)','rnti'])['delay(s)'].mean().reset_index()
    rx.rename(
        columns={ "delay(s)":"delay"},
        inplace = True,
    )
    rx.index = pd.to_datetime(rx['time(s)'],unit='s')

    ret = pd.DataFrame(rx.groupby('rnti').resample(str(resamplePeriod)+'ms').delay.mean())
    ret = ret.reset_index(level = 0)

    ret['InsertedDate'] = ret.index
    ret['Time'] = ret['InsertedDate'].astype(np.int64)/1e9

    ret = ret.set_index('Time')
    ret.groupby(['rnti'])['delay'].plot(legend=True,title = title)
    ax.set_ylabel("delay(s)")
    if show_title:
        plt.suptitle(title, y = 0.99)
        plt.title(subtitle)
    fig.savefig(myhome + prefix + 'Delay1' + '.png')
    plt.close()

else:
    ###############
    ## Delay 2
    ###############
    fig, ax = plt.subplots()
    title = tcpTypeId[3:] + " "

    title = title+"RTT"
    print(cyan + title + clear, end = "...", flush = True)

    print('load', end = "", flush = True)
    file = "tcp-delay.txt"
    if os.path.exists(myhome + file):
        RXSTAT = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        file =  file + ".gz"
        RXSTAT = pd.read_csv(myhome + file, compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end = ".", flush = True)

    rx=RXSTAT.groupby(['Time','UE'])['rtt'].mean().reset_index()

    rx.index = pd.to_datetime(rx['Time'],unit='s')

    rx = rx[(rx['Time'] >= AppStartTime) & (rx['Time'] <= simTime - AppStartTime)]

    ret = pd.DataFrame(rx.groupby(['UE']).resample(str(resamplePeriod)+'ms').rtt.mean())

    ret = ret.reset_index(level = 0)
    ret['Time'] = ret.index.astype(np.int64)/1e9

    ret = ret.set_index('Time')
    ret['rtt'] = ret['rtt']*1000
    ret['t'] = ret.index
    for p in range(parts.shape[0] ):
        
        [x, y, z] = parts[p,:]
        fig, ax = plt.subplots()
      
        
        if p<parts.shape[0]-1:
            if len(ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['UE'].unique()>1):
                ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))].groupby('UE')['rtt'].plot()
            else:
                ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['rtt'].plot()
            # plt.plot(ret.loc[x:y].index, ret['rtt'].loc[x:y], '-o',markevery = ret.loc[x:y].index.get_indexer(points, method='nearest'))
            
            for d in range(points.shape[0]):
                if (points[d] >= float(x)) & (points[d] <= float(y)):
                    try:
                        mytext = "("+str(points[d])+","+str(round(ret.loc[points[d]]['rtt'],2)) +")"
                        ax.annotate( mytext, (points[d] , ret.loc[points[d]]['rtt']))
                    except KeyError:
                        print(d)
        else:
            ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))].groupby('UE')['rtt'].plot()
            # ret['rtt'].loc[x:y].plot()

        ax.set_ylabel("RTT [ms]")
        ax.set_ylim(0, max([rtt_limit, ret[(ret['t'] >= float(x)) & (ret['t'] <= float(y))]['rtt'].mean()*2]))
        ax.set_ylim(0, 40)
        if show_title:
            plt.suptitle(title, y = 0.99)
            plt.title(subtitle)
        fig.savefig(myhome + prefix + 'RTT' +'-'+ z+ '.png')
        plt.close()

toc = time.time()
print(f"\tProcessed in: %.2f" %(toc-tic))
tic = toc
