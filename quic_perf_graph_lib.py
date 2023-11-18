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


# Set text colors
clear='\033[0m'
red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
blue='\033[0;34m'
magenta='\033[0;35m'
cyan='\033[0;36m'

# Set Background colors
bg_red='\033[0;41m'
bg_green='\033[0;42m'
bg_yellow='\033[0;43m'
bg_blue='\033[0;44m'
bg_magenta='\033[0;45m'
bg_cyan='\033[0;46m'

colors=['blue', 'green', 'red', 'orange', 'magenta', 'cyan', 'yellow', 'lightblue', 'pink', 'purple', 'lime']
show_title=0
# # Set graph 
# plt.rc('font', size=16)       # Set the default text font size
# plt.rc('axes', titlesize=18)  # Set the axes title font size
# plt.rc('axes', labelsize=18)  # Set the axes labels font size
# plt.rc('xtick', labelsize=18) # Set the font size for x tick labels
# plt.rc('ytick', labelsize=18) # Set the font size for y tick labels
# plt.rc('legend', fontsize=18) # Set the legend font size
# plt.rc('figure', titlesize=22)# Set the font size of the figure title
plt.rc('lines', linewidth=2)



def graph_mobility(myhome):
    tic=time.time()
    file="mobilityPosition.txt"
    title="Mobility"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        mob = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        mob = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)
    mob.set_index('Time', inplace=True)

    print('plotting', end=".", flush=True)
    fig, ax = plt.subplots()
    for ue in mob['UE'].unique():
        ax1= mob[mob['UE']==ue].plot.scatter( x='x',y='y', ax=ax,c=colors[ue-1])
    gNbicon=plt.imread(get_sample_data(myhome + '../../img/gNb.png'))
    gNbbox = OffsetImage(gNbicon, zoom = 0.25)
    for g in range(gNbNum):
        gNbPos=[gNbX,(gNbY+g*gNbD)*1.1]
        gNbab=AnnotationBbox(gNbbox,gNbPos, frameon = False)
        ax.add_artist(gNbab)

    if (enableBuildings):
        for b in range(buildN):
            row, col = divmod(b,gridWidth)
            rect=mpatches.Rectangle((buildX+(buildLx+buildDx)*col,buildY+(buildLy+buildDy)*row),buildLx,buildLy, alpha=0.5, facecolor="red")
            plt.gca().add_patch(rect)

    UEicon=plt.imread(get_sample_data(myhome + '../../img/UE.png'))
    UEbox = OffsetImage(UEicon, zoom = 0.02)

    for ue in mob['UE'].unique():
        print(ue, end=".", flush=True)
        UEPos=mob[mob['UE']==ue][['x','y']].iloc[-1:].values[0]*1.01
        UEab=AnnotationBbox(UEbox,UEPos, frameon = False)
        ax.add_artist(UEab)

    plt.xlim([min(0, mob['x'].min()) , (100 if max(10,mob['x'].max()+1)>10 else 10) ])
    plt.ylim([min(0, mob['y'].min()) , (100 if max(10,mob['y'].max()+1)>10 else 10) ])
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel("Distance [m]")
    fig.savefig(myhome+prefix +file+'.png')
    plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))


def graph_SINR(myhome):
    files={'Control':'DlCtrlSinr.txt',
            'Data': 'DlDataSinr.txt'}
    for key, value in files.items():
        tic=time.time()
        title="SINR " + key
        file=value
        print(cyan + title + clear, end="...", flush=True)
        print('load', end="", flush=True)
        if os.path.exists(myhome+file):
            SINR = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
        else:
            SINR = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip')
        print('ed', end=".", flush=True)
        SINR.set_index('Time', inplace=True)
        SINR = SINR[SINR['RNTI']!=0]

        print('plotting', end=".", flush=True)
        fig, ax = plt.subplots()
        SINR.groupby('RNTI')['SINR(dB)'].plot(legend=True, title=title)
        plt.ylim([min(15, SINR['SINR(dB)'].min()) , max(30,SINR['SINR(dB)'].max())])
        ax.set_ylabel("SINR(dB)")
        ax.set_xlabel("Time(s)")
        plt.suptitle(title)
        plt.title(subtitle)
        fig.savefig(myhome+prefix +'SINR-'+key+'.png')
        plt.close()
        toc=time.time()
        print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_CQI_BLER(myhome):
    tic=time.time()
    file="RxPacketTrace.txt"
    title="CQI"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        CQI = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        CQI = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    CQI.set_index('Time', inplace=True)
    CQI = CQI[CQI['rnti']!=0]
    CQI = CQI[CQI['direction']=='DL']

    print('plotting', end=".", flush=True)
    fig, ax = plt.subplots()
    CQI.groupby('rnti')['CQI'].plot(legend=True, title=title)
    plt.ylim([0, 16])
    ax.set_ylabel("CQI")
    ax.set_xlabel("Time(s)")
    plt.suptitle(title)
    plt.title(subtitle)
    fig.savefig(myhome+prefix +'CQI'+'.png')
    plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

    # BLER
    title="BLER"
    print(cyan + title + clear, end="...", flush=True)
    CQI['Time']=CQI.index
    CQI.index=pd.to_datetime(CQI['Time'],unit='s')
    BLER=pd.DataFrame(CQI.groupby('rnti').resample(str(resamplePeriod)+'ms').TBler.mean())

    BLER=BLER.reset_index(level=0)
    BLER = BLER[~BLER['TBler'].isna()]

    BLER['Time']=BLER.index
    BLER['Time']=BLER['Time'].astype(np.int64)/1e9
    BLER=BLER.set_index('Time')

    print('plotting', end=".", flush=True)
    fig, ax = plt.subplots()
    for ue in BLER['rnti'].unique():
        print(ue, end=".", flush=True)
        plt.semilogy(BLER[BLER['rnti']==ue].index, BLER[BLER['rnti']==ue].TBler, label='UE '+str(ue))

    plt.xlabel("Time(s)")
    plt.ylabel("BLER")
    # ax.set_ylim([abs(min([(1e-20) ,BLER.TBler.min()*0.9])) , 1])
    ax.set_ylim([1e-20 , 1e0])
    if len(BLER['rnti'].unique())>1:
        plt.legend(ncol=len(BLER['rnti'].unique())//3)

    plt.title(title)
    plt.grid(True, which="both", ls="-")
    plt.suptitle(title)
    plt.title(subtitle)
    fig.savefig(myhome+prefix +'BLER'+'.png')
    plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_path_loss(myhome):
    tic=time.time()
    file="DlPathlossTrace.txt"
    title="Path Loss"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        PLOSS = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        PLOSS = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    PLOSS.set_index('Time(sec)', inplace=True)
    PLOSS = PLOSS.loc[PLOSS['IMSI']!=0]
    PLOSS = PLOSS[PLOSS['pathLoss(dB)'] < 0]

    # PLOSS['IMSI']='UE '+ str(PLOSS['IMSI'])

    print('plotting', end=".", flush=True)
    fig, ax = plt.subplots()
    PLOSS.groupby(['IMSI'])['pathLoss(dB)'].plot(legend=True,title=file)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("pathLoss [dB]")
    plt.suptitle(title)
    plt.title(subtitle)
    fig.savefig(myhome+prefix +'PATH_LOSS'+'.png')
    plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))


def graph_thr_tx(myhome):
    tic=time.time()
    title=tcpTypeId[3:] + " "
    title=title+"Throughput TX"
    file="NrDlPdcpTxStats.txt"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        thrtx = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        thrtx = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    thrtx=thrtx.groupby(['time(s)','rnti'])['packetSize'].sum().reset_index()
    thrtx.index=pd.to_datetime(thrtx['time(s)'],unit='s')

    thrtx=pd.DataFrame(thrtx.groupby('rnti').resample(str(resamplePeriod)+'ms').packetSize.sum())
    thrtx=thrtx.reset_index(level=0)

    thrtx['InsertedDate']=thrtx.index
    thrtx['deltaTime']=thrtx['InsertedDate'].astype(np.int64)/1e9
    thrtx['Time']=thrtx['deltaTime']
    thrtx['deltaTime']=thrtx.groupby('rnti').diff()['deltaTime']

    thrtx.loc[~thrtx['deltaTime'].notnull(),'deltaTime']=thrtx.loc[~thrtx['deltaTime'].notnull(),'InsertedDate'].astype(np.int64)/1e9
    thrtx['throughput']= thrtx['packetSize']*8 / thrtx['deltaTime']/1e6
    thrtx=thrtx.set_index('Time')

    print('plotting', end=".", flush=True)
    fig, ax = plt.subplots()
    thrtx.groupby(['rnti'])['throughput'].plot()

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [Mb/s]")
    ax.set_ylim([0 , max([thr_limit ,thrtx['throughput'].max()*1.1])])
    if show_title:
        plt.suptitle(title, y=0.99)
        plt.title(subtitle)
    if len(thrtx['rnti'].unique())>1:
        plt.legend(ncol=len(thrtx['rnti'].unique())//3)


    fig.savefig(myhome + prefix + 'ThrTx' + '.png')
    plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_thr_rlcbuffer(myhome):
    tic=time.time()
    title=tcpTypeId[3:] + " "
    title=title+"Throughput vs RLC Buffer"
    file="NrDlPdcpRxStats.txt"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        thrrx = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        thrrx = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    thrrx=thrrx.groupby(['time(s)','rnti'])['packetSize'].sum().reset_index()
    thrrx.index=pd.to_datetime(thrrx['time(s)'],unit='s')

    thrrx=pd.DataFrame(thrrx.groupby('rnti').resample(str(resamplePeriod)+'ms').packetSize.sum())
    thrrx=thrrx.reset_index(level=0)

    thrrx['InsertedDate']=thrrx.index
    thrrx['deltaTime']=thrrx['InsertedDate'].astype(np.int64)/1e9
    thrrx['Time']=thrrx['deltaTime']

    thrrx['deltaTime']=thrrx.groupby('rnti').diff()['deltaTime']

    thrrx.loc[~thrrx['deltaTime'].notnull(),'deltaTime']=thrrx.loc[~thrrx['deltaTime'].notnull(),'InsertedDate'].astype(np.int64)/1e9
    thrrx['throughput']= thrrx['packetSize']*8 / thrrx['deltaTime']/1e6
    thrrx['throughput'] = thrrx['throughput'].astype(float)

    thrrx=thrrx.set_index('Time')
    if flowType=='TCP':
        print('load', end="", flush=True)
        file="RlcBufferStat.txt"
        if os.path.exists(myhome+file):
            rlcdrop = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
        else:
            rlcdrop = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
        print('ed', end=".", flush=True)
        rlcdrop['direction']='UL'
        rlcdrop.loc[rlcdrop['PacketSize'] > 1500,'direction']='DL'
        rlc = rlcdrop[rlcdrop['direction'] =='DL']
        rlc.index=pd.to_datetime(rlc['Time'],unit='s')
        print(".", end="", flush=True)
        rlcdrop=pd.DataFrame(rlc.resample(str(resamplePeriod)+'ms').dropSize.sum())
        rlcdrop['Time']=rlcdrop.index.astype(np.int64)/1e9
        rlcdrop=rlcdrop.set_index('Time')
        rlcdrop['state']=0
        rlcdrop.loc[rlcdrop['dropSize'] > 0,'state']=1
        rlcbuffer=pd.DataFrame(rlc.resample(str(resamplePeriod)+'ms').txBufferSize.max())
        rlcbuffer['Time']=rlcbuffer.index.astype(np.int64)/1e9
        rlcbuffer=rlcbuffer.set_index('Time')
        rlcbuffer['txBufferSize']=rlcbuffer['txBufferSize']/rlcBuffer
        rlcdrop['state']=rlcdrop['state']*rlcbuffer['txBufferSize']
        rlcbuffer.loc[rlcdrop['state'] > 0,'txBufferSize']=0
    print('plotting', end=".", flush=True)
    thrrx['t']=thrrx.index
    rlcdrop['t']=rlcdrop.index
    rlcbuffer['t']=rlcbuffer.index
    for p in range(parts.shape[0] ):
        [x, y, z] = parts[p,:]
        print(z, end=".", flush=True)
        fig, ax = plt.subplots()
        ax1 = thrrx[(thrrx['t']>=int(x)) & (thrrx['t']<=int(y))].groupby(['rnti'])['throughput'].plot( ax=ax)
        text_legend=thrrx['rnti'].drop_duplicates().sort_values().unique()
        text_legend=[ 'UE ' + str(i)  for i in text_legend]
        if (UENum>1):
            plt.legend(text_legend, loc='upper left',ncol=2)

        
        if p<parts.shape[0]-1:
            for d in range(points.shape[0]):
                if (points[d]>=int(x)) & (points[d] <= int(y)):
                    mytext="("+str(points[d])+","+str(round(thrrx.loc[points[d]]['throughput'],2)) +")"
                    ax.annotate( mytext, (points[d] , thrrx.loc[points[d]]['throughput']))

        if flowType=='TCP':
            ax2 = rlcdrop[(rlcdrop['t']>=int(x)) & (rlcdrop['t']<=int(y))]['state'].plot.area( secondary_y=True,
                                                                                            ax=ax,
                                                                                            alpha=0.2,
                                                                                            color="red",
                                                                                            legend=False)
            ax2.set_ylabel("RLC Buffer [%]", loc='bottom')
            ax2.set_ylim(0,4)
            ax2.set_yticks([0,0.5,1])
            ax2.set_yticklabels(['0','50','100' ])
            
            ax3 = rlcbuffer[(rlcbuffer['t']>=int(x)) & (rlcbuffer['t']<=int(y))]['txBufferSize'].plot.area( secondary_y=True,
                                                                                                ax=ax,  
                                                                                                alpha=0.2, 
                                                                                                color="green", 
                                                                                                legend=False)
            ax3.set_ylim(0,rlcbuffer[(rlcbuffer['t']>=int(x)) & (rlcbuffer['t']<=int(y))]['txBufferSize'].max()*4)

        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Throughput [Mb/s]")
        ax.set_ylim([0 , max([thr_limit,thrrx[(thrrx['t']>=int(x)) & (thrrx['t']<=int(y))]['throughput'].max()*1.1])])
        # ax.set_ylim([0, 750])
        if show_title:
            plt.suptitle(title, y=0.99)
            plt.title(subtitle)
        # if (UENum>1):
        #     plt.legend()
        plotfile=myhome + prefix + 'ThrRx' +'-'+ z + '.png'
        fig.savefig(plotfile)
        plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_thr_packetdrop(myhome):
    tic=time.time()
    title=tcpTypeId[3:] + " "
    title=title+"Throughput vs PER"
    file="tcp-per.txt"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(file):
        tx_ = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
        tx_ = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)
    tx_.index=pd.to_datetime(tx_['Time'],unit='s')
    tx_thr=pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').BytesTx.sum())
    tx_drp=pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').BytesDroped.sum())

    tx_drp['PacketsTx']=pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').PacketsTx.sum())
    tx_drp['PacketsDroped']=pd.DataFrame(tx_.resample(str(resamplePeriod)+'ms').PacketsDroped.sum())

    tx_thr=tx_thr.reset_index(level=0)
    tx_thr['Throughput']= tx_thr['BytesTx']*8 / 0.1/1e6
    tx_thr['Time']=tx_thr['Time'].astype(np.int64)/1e9
    tx_thr=tx_thr.set_index('Time')

    tx_drp=tx_drp.reset_index(level=0)
    tx_drp['Throughput']= tx_drp['BytesDroped']*8 / 0.1/1e6
    tx_drp['PER']= tx_drp['PacketsDroped']/tx_drp['PacketsTx']
    tx_drp['Time']=tx_drp['Time'].astype(np.int64)/1e9
    tx_drp=tx_drp.set_index('Time')
    for p in range(parts.shape[0] ):
        
        [x, y, z] = parts[p,:]
        fig, ax = plt.subplots()
        if p<parts.shape[0]-1:
            # plt.plot(tx_thr.loc[x:y].index, tx_thr['Throughput'].loc[x:y], '-o', markevery=tx_thr.loc[x:y].index.get_indexer(points, method='nearest'))
            ax1 = tx_thr['Throughput'].loc[x:y].plot(ax=ax, markevery=tx_thr.loc[x:y].index.get_indexer(points, method='nearest'))
            for d in range(points.shape[0]):
                if (points[d]>=int(x)) & (points[d] <= int(y)):
                    mytext="("+str(points[d])+","+str(round(tx_thr.loc[points[d]]['Throughput'],2)) +")"
                    ax.annotate( mytext, (points[d] , tx_thr.loc[points[d]]['Throughput']))
        else:
            ax1 = tx_thr['Throughput'].loc[x:y].plot(ax=ax)
        ax2 = tx_drp['PER'].loc[x:y].plot.area(  secondary_y=True, ax=ax,  alpha=0.2, color="red")
        # ax3 = tx_drp['Throughput'].plot.area(  ax=ax,  alpha=0.2, color="red")

        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Throughput [Mb/s]")
        ax.set_ylim([0 , max([thr_limit,tx_thr['Throughput'].loc[x:y].max()*1.1])])

        ax2.set_ylabel("PER [%]", loc='bottom')
        ax2.set_ylim(0,4)

        ax2.set_yticks([0,0.5,1])
        ax2.set_yticklabels(['0','50','100' ])

        if show_title:
            plt.suptitle(title, y=0.99)
            plt.title(subtitle)
        fig.savefig(myhome + prefix + 'ThrDrp' +'-'+ z+ '.png')
        plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

def graph_rtt(myhome):
    tic=time.time()
    title=tcpTypeId[3:] + " "
    title=title+"RTT"
    file="tcp-delay.txt"
    print(cyan + title + clear, end="...", flush=True)
    print('load', end="", flush=True)
    if os.path.exists(myhome+file):
        ret = pd.read_csv(myhome + file, sep = "\t", on_bad_lines='skip' )
    else:
         ret = pd.read_csv(myhome + file + ".gz", compression='gzip', sep = "\t", on_bad_lines='skip' )
    print('ed', end=".", flush=True)

    ret=ret.groupby(['Time','UE'])['rtt'].mean().reset_index()

    ret.index=pd.to_datetime(ret['Time'],unit='s')

    ret = ret[(ret['Time']>=AppStartTime) & (ret['Time']<=simTime - AppStartTime)]

    ret=pd.DataFrame(ret.groupby(['UE']).resample(str(resamplePeriod)+'ms').rtt.mean())

    ret=ret.reset_index(level=0)
    ret['Time']=ret.index.astype(np.int64)/1e9

    ret=ret.set_index('Time')
    ret['rtt']=ret['rtt']*1000
    ret['t']=ret.index
    for p in range(parts.shape[0] ):
        
        [x, y, z] = parts[p,:]
        fig, ax = plt.subplots()
      
        
        if p<parts.shape[0]-1:
            if len(ret[(ret['t']>=int(x)) & (ret['t']<=int(y))]['UE'].unique()>1):
                ret[(ret['t']>=int(x)) & (ret['t']<=int(y))].groupby('UE')['rtt'].plot()
            else:
                ret[(ret['t']>=int(x)) & (ret['t']<=int(y))]['rtt'].plot()
            # plt.plot(ret.loc[x:y].index, ret['rtt'].loc[x:y], '-o',markevery=ret.loc[x:y].index.get_indexer(points, method='nearest'))
            
            for d in range(points.shape[0]):
                if (points[d]>=int(x)) & (points[d] <= int(y)):
                    try:
                        mytext="("+str(points[d])+","+str(round(ret.loc[points[d]]['rtt'],2)) +")"
                        ax.annotate( mytext, (points[d] , ret.loc[points[d]]['rtt']))
                    except KeyError:
                        print(d)
        else:
            ret[(ret['t']>=int(x)) & (ret['t']<=int(y))].groupby('UE')['rtt'].plot()
            # ret['rtt'].loc[x:y].plot()

        ax.set_ylabel("RTT [ms]")
        ax.set_ylim(0, max([rtt_limit, ret[(ret['t']>=int(x)) & (ret['t']<=int(y))]['rtt'].mean()*2]))
        ax.set_ylim(0, 40)
        if show_title:
            plt.suptitle(title, y=0.99)
            plt.title(subtitle)
        fig.savefig(myhome + prefix + 'RTT' +'-'+ z+ '.png')
        plt.close()
    toc=time.time()
    print(f"\tProcessed in: %.2f" %(toc-tic))

