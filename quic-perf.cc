/* Include ns3 libraries */
#include "ns3/applications-module.h"
#include "ns3/config-store.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/quic-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/log.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/nr-helper.h"
#include "ns3/nr-mac-scheduler-tdma-rr.h"
#include "ns3/nr-module.h"
#include "ns3/nr-point-to-point-epc-helper.h"
#include "ns3/point-to-point-helper.h"
#include <ns3/antenna-module.h>
#include <ns3/buildings-helper.h>
#include <ns3/buildings-module.h>
#include <ns3/hybrid-buildings-propagation-loss-model.h>

/* Include systems libraries */
#include <sys/types.h>
#include <unistd.h>

/* Include custom libraries (aux files for the simulation) */
#include "cmdline-colors.h"
#include "quic-perf-apps.h"
#include "physical-scenarios.h"

using namespace ns3;
NS_LOG_COMPONENT_DEFINE ("quic-perf");

/* Global Variables */

auto itime = std::chrono::high_resolution_clock::now(); // Initial time
auto tic = std::chrono::high_resolution_clock::now();   // Initial time per cycle

const std::string LOG_FILENAME = "output.log";

static double SegmentSize = 1448.0;
double simTime = 60;           // in second
double iniTime = 0;           // in second


/* Noise vars */
// Mean chosen by https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/5g_nr_millimeter_wave_network_coverage_simulation_studies_for_global_cities.pdf page 4
const double NOISE_MEAN = 5;    // Default value is 5
const double NOISE_VAR = 1;     // Noise variance
const double NOISE_BOUND = 3;   // Noise bound, read NormalDistribution for info about the parameter.
const Time NOISE_T_RES = MilliSeconds(15); // Time to schedule the add noise function



// class MyAppTag : public Tag
// {
//     public:
//     MyAppTag ()
//     {
//     }

//     MyAppTag (Time sendTs) : m_sendTs (sendTs)
//     {
//     }

//     static TypeId GetTypeId (void)
//     {
//         static TypeId tid = TypeId ("ns3::MyAppTag")
//         .SetParent<Tag> ()
//         .AddConstructor<MyAppTag> ();
//         return tid;
//     }

//     virtual TypeId  GetInstanceTypeId (void) const
//     {
//         return GetTypeId ();
//     }

//     virtual void  Serialize (TagBuffer i) const
//     {
//         i.WriteU64 (m_sendTs.GetNanoSeconds ());
//     }

//     virtual void  Deserialize (TagBuffer i)
//     {
//         m_sendTs = NanoSeconds (i.ReadU64 ());
//     }

//     virtual uint32_t  GetSerializedSize () const
//     {
//         return sizeof (m_sendTs);
//     }

//     virtual void Print (std::ostream &os) const
//     {
//         std::cout << m_sendTs;
//     }

//     Time m_sendTs;
// };



/* Trace functions, definitions are at EOF */
static void CwndTracer(Ptr<OutputStreamWrapper> stream, uint32_t oldval, uint32_t newval);
static void RtoTracer(Ptr<OutputStreamWrapper> stream, Time oldval, Time newval);
static void RttTracer(Ptr<OutputStreamWrapper> stream, Time oldval, Time newval);
static void NextTxTracer(Ptr<OutputStreamWrapper> stream, SequenceNumber32 old [[maybe_unused]], SequenceNumber32 nextTx);
static void NextRxTracer(Ptr<OutputStreamWrapper> stream, SequenceNumber32 old [[maybe_unused]], SequenceNumber32 nextRx);
static void InFlightTracer(Ptr<OutputStreamWrapper> stream, uint32_t old [[maybe_unused]], uint32_t inFlight);
static void SsThreshTracer(Ptr<OutputStreamWrapper> stream, uint32_t oldval, uint32_t newval);
static void TraceTcp(uint32_t nodeId, uint32_t socketId);


/* Helper functions, definitions are at EOF */
static void InstallTCP2 (Ptr<Node> remoteHost, Ptr<Node> sender, uint16_t sinkPort, float startTime, float stopTime, float dataRate);
static void CalculatePosition(NodeContainer* ueNodes, NodeContainer* gnbNodes, std::ostream* os);
static void AddRandomNoise(Ptr<NrPhy> ue_phy);
static void PrintNodeAddressInfo(bool ignore_localh);
static void processFlowMonitor(Ptr<FlowMonitor> monitor, Ptr<ns3::FlowClassifier> flowmonHelper, double AppStartTime);

// connect to a number of traces
static void
CwndChange (Ptr<OutputStreamWrapper> stream, uint32_t oldCwnd, uint32_t newCwnd)
{
  *stream->GetStream () << Simulator::Now ().GetSeconds () << "\t" << oldCwnd << "\t" << newCwnd << std::endl;
}

static void
RttChange (Ptr<OutputStreamWrapper> stream, Time oldRtt, Time newRtt)
{
  *stream->GetStream () << Simulator::Now ().GetSeconds () << "\t" << oldRtt.GetSeconds () << "\t" << newRtt.GetSeconds () << std::endl;
}

static void
Rx (Ptr<OutputStreamWrapper> stream, Ptr<const Packet> p, const QuicHeader& q, Ptr<const QuicSocketBase> qsb)
{
  *stream->GetStream () << Simulator::Now ().GetSeconds () << "\t" << p->GetSize() << std::endl;
}

static void
Traces(uint32_t serverId, std::string pathVersion, std::string finalPart)
{
    std::cout << TXT_CYAN << "\nTrace QUIC: " << serverId << " at: "<<  
            1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(tic-itime).count()<< TXT_CLEAR << std::endl;

    AsciiTraceHelper asciiTraceHelper;

    std::ostringstream pathCW;
    pathCW << "/NodeList/" << serverId << "/$ns3::QuicL4Protocol/SocketList/0/QuicSocketBase/CongestionWindow";
    NS_LOG_INFO("Matches cw " << Config::LookupMatches(pathCW.str().c_str()).GetN());

    std::ostringstream fileCW;
    fileCW << pathVersion << "QUIC-cwnd-change"  << serverId << "" << finalPart;

    std::ostringstream pathRTT;
    pathRTT << "/NodeList/" << serverId << "/$ns3::QuicL4Protocol/SocketList/0/QuicSocketBase/RTT";

    std::ostringstream fileRTT;
    fileRTT << pathVersion << "QUIC-rtt"  << serverId << "" << finalPart;

    std::ostringstream pathRCWnd;
    pathRCWnd<< "/NodeList/" << serverId << "/$ns3::QuicL4Protocol/SocketList/0/QuicSocketBase/RWND";

    std::ostringstream fileRCWnd;
    fileRCWnd<<pathVersion << "QUIC-rwnd-change"  << serverId << "" << finalPart;

    std::ostringstream fileName;
    fileName << pathVersion << "QUIC-rx-data" << serverId << "" << finalPart;
    std::ostringstream pathRx;
    // pathRx << "/NodeList/" << serverId << "/$ns3::QuicL4Protocol/SocketList/*/QuicSocketBase/Rx";
    // NS_LOG_INFO("Matches rx " << Config::LookupMatches(pathRx.str().c_str()).GetN());

    // Ptr<OutputStreamWrapper> stream = asciiTraceHelper.CreateFileStream (fileName.str ().c_str ());
    // Config::ConnectWithoutContext (pathRx.str ().c_str (), MakeBoundCallback (&Rx, stream));

    // Ptr<OutputStreamWrapper> stream1 = asciiTraceHelper.CreateFileStream (fileCW.str ().c_str ());
    // Config::ConnectWithoutContext (pathCW.str ().c_str (), MakeBoundCallback(&CwndChange, stream1));

    // Ptr<OutputStreamWrapper> stream2 = asciiTraceHelper.CreateFileStream (fileRTT.str ().c_str ());
    // Config::ConnectWithoutContext (pathRTT.str ().c_str (), MakeBoundCallback(&RttChange, stream2));

    // Ptr<OutputStreamWrapper> stream4 = asciiTraceHelper.CreateFileStream (fileRCWnd.str ().c_str ());
    // Config::ConnectWithoutContextFailSafe (pathRCWnd.str ().c_str (), MakeBoundCallback(&CwndChange, stream4));
    std::cout << TXT_CYAN << "\nTrace QUIC: " << serverId << " at: "<<  
            1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(tic-itime).count()<< TXT_CLEAR << std::endl;
}

int main(int argc, char* argv[]) {
    std::cout << TXT_CYAN << "Start Over 3.39" << TXT_CLEAR << std::endl;
    double frequency = 27.3e9;      // central frequency 28e9
    double bandwidth = 400e6;       // bandwidth Hz
    double mobility = true;         // whether to enable mobility default: false
    double speed = 1;               // in m/s for walking UT.
    bool logging = true;            // whether to enable logging from the simulation, another option is by
                                    // exporting the NS_LOG environment variable
    bool shadowing = true;          // to enable shadowing effect
    bool addNoise = false;           // To enable/disable AWGN

    std::string AQM = "None";       // AQM 'None' or 'RED'
    

    // double hBS;                     // base station antenna height in meters
    // double hUE;                     // user antenna height in meters
    double txPower = 40;            // txPower [dBm] 40 dBm=10W
    uint16_t numerology = 3;        // 120 kHz and 125 microseg
    std::string scenario = "UMa";   // scenario
    enum BandwidthPartInfo::Scenario scenarioEnum = BandwidthPartInfo::UMa;

    double dataRate = 1000;         //Data rate Mbps
    double serverDelay = 0.01;      // remote 0.040 ; edge 0.004
    double rlcBufferPerc = 100;     // x*DBP
    double rlcBuffer = round(dataRate*1e6/8*serverDelay*rlcBufferPerc/100); // Bytes BDP=250Mbps*100ms default: 999999999

    // Trace activation
    bool NRTrace = true;    // whether to enable Trace NR
    bool TCPTrace = true;   // whether to enable Trace TCP

    // RB Info and position
    uint16_t gNbNum = 1;    // Numbers of RB
    double gNbX = 50.0;     // X position
    double gNbY = 50.0;     // Y position
    uint16_t gNbD = 80;     // Distance between gNb

    // UE Info and position
    uint16_t ueNumPergNb = 1; // Numbers of User per RB
    // double ueDistance = .10; //Distance between UE
    // double xUE=20; //Initial Position UE // JSA 20
    // double yUE=10; //Initial Position UE
    
    std::string ip_net_UE = "1.0.0.0";
    std::string ip_mask_UE = "255.0.0.0";
    std::string ip_net_Server = "7.0.0.0";
    std::string ip_mask_Server = "255.0.0.0";


    // BUILDING Position
    bool enableBuildings = true; // 
    uint32_t gridWidth = 3 ;//
    uint32_t numOfBuildings = 2;
    // uint32_t apartmentsX = 1;
    // uint32_t nFloors = 10;

    double buildX=37.0; // Initial Position
    double buildY=30.0; // 30
    double buildDx=10; // Distance between building
    double buildDy=10; //
    double buildLx=8; //4
    double buildLy=10;

    std::string serverType = "Remote"; // Transport Protocol
    std::string flowType = "QUIC"; // Transport Protocol
    std::string tcpTypeId = "QUIC";
    double AppStartTime = 0.2; // APP start time

    int phyDistro = (int)PhysicalDistributionOptions::DEFAULT;
    



    CommandLine cmd(__FILE__);
    cmd.AddValue("frequency", "The central carrier frequency in Hz.", frequency);
    cmd.AddValue("mobility",
                 "If set to 1 UEs will be mobile, when set to 0 UE will be static. By default, "
                 "they are mobile.",
                 mobility);
    cmd.AddValue("logging", "If set to 0, log components will be disabled.", logging);
    cmd.AddValue("simTime", "Simulation Time (s)", simTime);
    cmd.AddValue("iniTime", "Initial Time (s)", iniTime);
    cmd.AddValue("speed", "Speed m/s", speed);
    cmd.AddValue("bandwidth", "bandwidth in Hz.", bandwidth);
    cmd.AddValue("serverType", "Type of Server: Remote or Edge", serverType);
    cmd.AddValue("flowType", "Flow Type: UDP or TCP", flowType);
    cmd.AddValue("rlcBufferPerc", "Percent RLC Buffer", rlcBufferPerc);
    cmd.AddValue("tcpTypeId", "TCP flavor: TcpBbr , TcpNewReno, TcpCubic, TcpVegas, TcpIllinois, TcpYeah, TcpHighSpeed, TcpBic", tcpTypeId);
    cmd.AddValue("enableBuildings", "If set to 1, enable Buildings", enableBuildings);
    cmd.AddValue("shadowing", "If set to 1, enable Shadowing", shadowing);
    cmd.AddValue("AQM", "AQM: None, RED in RLC buffer", AQM);
    cmd.AddValue("ueNum", "Number of UE", ueNumPergNb);
    cmd.AddValue("phyDistro", "Physical distribution of the Buildings-UEs-gNbs. Options:\n\t0:Default\n\t1:Trees\n\t2:Indoor Router\n\t3:Neighborhood\nCurrent value: ", phyDistro);   
    cmd.Parse(argc, argv);

    AppStartTime = AppStartTime + iniTime;
    // simTime = simTime - iniTime;
    /********************************************************************************************************************
     * LOGS
    ********************************************************************************************************************/
    // Redirect logs to output file, clog -> LOG_FILENAME
    std::ofstream of(LOG_FILENAME);
    // auto clog_buff = std::clog.rdbuf();
    std::clog.rdbuf(of.rdbuf());

    // enable logging
    if (logging)
    {
        // LogComponentEnableAll (LOG_PREFIX_TIME);
        // LogComponentEnable ("LtePdcp", LOG_LEVEL_ALL);
        // LogComponentEnable ("LteRlcUm", LOG_LEVEL_ALL);
        // LogComponentEnable ("NrUeMac", LOG_LEVEL_ALL);
        // LogComponentEnable ("NrGnbMac", LOG_LEVEL_ALL);
        // LogComponentEnable ("NrMacSchedulerNs3", LOG_LEVEL_ALL);
        // LogComponentEnable ("NrUePhy", LOG_LEVEL_ALL);
        // LogComponentEnable ("NrGnbPhy", LOG_LEVEL_ALL);



        // LogComponentEnable ("ThreeGppSpectrumPropagationLossModel", LOG_LEVEL_ALL);
        // LogComponentEnable("ThreeGppPropagationLossModel", LOG_LEVEL_ALL);
        // LogComponentEnable ("ThreeGppChannelModel", LOG_LEVEL_ALL);
        // LogComponentEnable ("ChannelConditionModel", LOG_LEVEL_ALL);
        // LogComponentEnable("TcpCongestionOps",LOG_LEVEL_ALL);
        // LogComponentEnable("TcpBic",LOG_LEVEL_ALL);
        // LogComponentEnable("TcpBbr",LOG_LEVEL_ALL);
        // LogComponentEnable ("UdpClient", LOG_LEVEL_INFO);
        // LogComponentEnable ("UdpServer", LOG_LEVEL_INFO);
        // LogComponentEnable ("LteRlcUm", LOG_LEVEL_LOGIC);
        // LogComponentEnable ("LtePdcp", LOG_LEVEL_INFO);
    }

    /********************************************************************************************************************
     * Servertype, TCP config & settings, scenario definition
    ********************************************************************************************************************/

    /* Server type - Distance */
    if (serverType == "Remote")
    {
        serverDelay = 0.04; 
    }
    else
    {
        serverDelay = 0.004;
    }

    rlcBuffer = round(dataRate*1e6/8*serverDelay*rlcBufferPerc/100); // Bytes BDP=250Mbps*100ms default: 999999999
    // 
    /*
     * Default values for the simulation. We are progressively removing all
     * the instances of SetDefault, but we need it for legacy code (LTE)
     */
    
    std::cout << "rlcBuffer:" << rlcBuffer <<
                std::endl;

    Config::SetDefault("ns3::LteRlcUm::MaxTxBufferSize", UintegerValue(rlcBuffer));
    if (AQM == "RED"){
        Config::SetDefault("ns3::LteRlcUm::RED", BooleanValue(true));
        Config::SetDefault("ns3::LteRlcUm::redMinTh", UintegerValue(rlcBuffer*0.6));
        Config::SetDefault("ns3::LteRlcUm::redMaxTh", UintegerValue(rlcBuffer*1.0));
        Config::SetDefault("ns3::LteRlcUm::redMaxP", DoubleValue(0.5));
        

    }


    // TCP config
    // TCP Settig
    // attibutes in: https://www.nsnam.org/docs/release/3.27/doxygen/classns3_1_1_tcp_socket.html
    uint32_t delAckCount = 1;
    std::string queueDisc = "FifoQueueDisc";
    queueDisc = std::string("ns3::") + queueDisc;

    if (flowType =="TCP"){
        Config::SetDefault("ns3::TcpL4Protocol::SocketType", StringValue("ns3::" + tcpTypeId));
        Config::SetDefault("ns3::TcpSocket::SndBufSize", UintegerValue(4194304)); // TcpSocket maximum transmit buffer size (bytes). 4194304 = 4MB
        Config::SetDefault("ns3::TcpSocket::RcvBufSize", UintegerValue(4194304)); // TcpSocket maximum receive buffer size (bytes). 6291456 = 6MB
        Config::SetDefault("ns3::TcpSocket::InitialCwnd", UintegerValue(10)); // TCP initial congestion window size (segments). RFC 5681 = 10
        Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(SegmentSize)); // TCP maximum segment size in bytes (may be adjusted based on MTU discovery).
        Config::SetDefault("ns3::TcpSocket::TcpNoDelay", BooleanValue(false)); // Set to true to disable Nagle's algorithm


        // Config::SetDefault("ns3::TcpSocketBase::MinRto", TimeValue (MilliSeconds (200)));
        Config::SetDefault("ns3::TcpSocket::DelAckCount", UintegerValue(delAckCount));  // Number of packets to wait before sending a TCP ack
        Config::SetDefault("ns3::TcpSocket::DelAckTimeout", TimeValue (Seconds (.4))); // Timeout value for TCP delayed acks, in seconds. default 0.2 sec
        Config::SetDefault("ns3::TcpSocket::DataRetries", UintegerValue(50)); // Number of data retransmission attempts. Default 6
        // Config::SetDefault("ns3::TcpSocket::PersistTimeout", TimeValue (Seconds (60))); // Number of data retransmission attempts. Default 6

        Config::Set ("/NodeList/*/DeviceList/*/TxQueue/MaxSize", QueueSizeValue (QueueSize ("100p")));
        Config::Set ("/NodeList/*/DeviceList/*/RxQueue/MaxSize", QueueSizeValue (QueueSize ("100p")));

        Config::SetDefault("ns3::DropTailQueue<Packet>::MaxSize", QueueSizeValue(QueueSize("100p"))); //A FIFO packet queue that drops tail-end packets on overflow
        Config::SetDefault(queueDisc + "::MaxSize", QueueSizeValue(QueueSize("100p"))); //100p Simple queue disc implementing the FIFO (First-In First-Out) policy

        Config::SetDefault("ns3::TcpL4Protocol::RecoveryType",
                           TypeIdValue(TypeId::LookupByName("ns3::TcpClassicRecovery"))); //set the congestion window value to the slow start threshold and maintain it at such value until we are fully recovered
        Config::SetDefault ("ns3::RttEstimator::InitialEstimation", TimeValue (MilliSeconds (10)));

        if( tcpTypeId=="TcpCubic"){
            Config::SetDefault("ns3::TcpCubic::Beta", DoubleValue(0.9)); // Beta for multiplicative decrease. Default 0.7
  
        }
        else if( tcpTypeId=="TcpBic"){
            // Config::SetDefault("ns3::TcpBic::Beta", DoubleValue(1.5)); // Beta for multiplicative decrease. Default 0.8
            // Config::SetDefault("ns3::TcpBic::HyStart", BooleanValue(false)); // Enable (true) or disable (false) hybrid slow start algorithm. Default true
            
        }
        else if( tcpTypeId=="TcpBbr"){
            // Config::SetDefault("ns3::TcpBbr::Stream", UintegerValue(8)); // Random number stream (default is set to 4 to align with Linux results)
            // Config::SetDefault("ns3::TcpBbr::HighGain", DoubleValue(3)); // Value of high gain. Default 2.89
            // Config::SetDefault("ns3::TcpBbr::BwWindowLength", UintegerValue(5)); // Length of bandwidth windowed filter. Default 10
            // Config::SetDefault("ns3::TcpBbr::RttWindowLength", TimeValue(Seconds(1))); // Length of RTT windowed filter. Default 10
            // Config::SetDefault("ns3::TcpBbr::AckEpochAckedResetThresh", UintegerValue(1 << 12)); // Max allowed val for m_ackEpochAcked, after which sampling epoch is reset. Default 1 << 12
            // Config::SetDefault("ns3::TcpBbr::ExtraAckedRttWindowLength", UintegerValue(50)); // Window length of extra acked window. Default 5
            // Config::SetDefault("ns3::TcpBbr::ProbeRttDuration", TimeValue(MilliSeconds(400))); // Time to be spent in PROBE_RTT phase. Default 200
            // LogComponentEnable("TcpBbr",LOG_LEVEL_ALL);

        }

    }
    else if ( flowType == "QUIC")
    {
        Config::SetDefault ("ns3::QuicSocketBase::SocketSndBufSize", UintegerValue(400000000));
        Config::SetDefault ("ns3::QuicSocketBase::SocketRcvBufSize", UintegerValue(400000000));
        Config::SetDefault ("ns3::QuicStreamBase::StreamSndBufSize", UintegerValue(400000000));
        Config::SetDefault ("ns3::QuicStreamBase::StreamRcvBufSize", UintegerValue(400000000));
        Config::SetDefault ("ns3::QuicSocketBase::SchedulingPolicy", TypeIdValue(QuicSocketTxEdfScheduler::GetTypeId ()));
        std::string transport_prot = "TcpNewReno";
        transport_prot = std::string ("ns3::") + transport_prot;
        Config::SetDefault ("ns3::QuicL4Protocol::SocketType", TypeIdValue (TypeId::LookupByName (transport_prot)));

        // LogLevel log_precision = LOG_LEVEL_INFO;
        // LogComponentEnable ("QuicEchoClientApplication", log_precision);
        // LogComponentEnable ("QuicEchoServerApplication", log_precision);
        // //LogComponentEnable ("QuicSocketBase", log_precision);
        // LogComponentEnable ("QuicStreamBase", log_precision);
        // LogComponentEnable("QuicStreamRxBuffer", log_precision);
        // LogComponentEnable("QuicStreamTxBuffer", log_precision);
        // LogComponentEnable("QuicSocketTxScheduler", log_precision);
        // LogComponentEnable("QuicSocketTxEdfScheduler", log_precision);
        // //LogComponentEnable ("Socket", log_precision);
        // // LogComponentEnable ("Application", log_precision);
        // // LogComponentEnable ("Node", log_precision);
        // //LogComponentEnable ("InternetStackHelper", log_precision);
        // //LogComponentEnable ("QuicSocketFactory", log_precision);
        // //LogComponentEnable ("ObjectFactory", log_precision);
        // //LogComponentEnable ("TypeId", log_precision);
        // //LogComponentEnable ("QuicL4Protocol", log_precision);
        // LogComponentEnable ("QuicL5Protocol", log_precision);
        // //LogComponentEnable ("ObjectBase", log_precision);

        // //LogComponentEnable ("QuicEchoHelper", log_precision);
        // //LogComponentEnable ("UdpSocketImpl", log_precision);
        // //LogComponentEnable ("QuicHeader", log_precision);
        // //LogComponentEnable ("QuicSubheader", log_precision);
        // //LogComponentEnable ("Header", log_precision);
        // //LogComponentEnable ("PacketMetadata", log_precision);
        // LogComponentEnable ("QuicSocketTxBuffer", log_precision);

    }
    else{
        // TCPTrace=false;

    }


    /********************************************************************************************************************
    * Create base stations and mobile terminal
    * Define positions, mobility types and speed of UE and gNB.
    ********************************************************************************************************************/
    // create base stations and mobile terminals
    NodeContainer gnbNodes;
    NodeContainer ueNodes;
    gnbNodes.Create(gNbNum);
    ueNodes.Create(gNbNum*ueNumPergNb);

    switch ((PhysicalDistributionOptions)phyDistro)
    {
        case PhysicalDistributionOptions::NEIGHBORHOOD:
            NeighborhoodPhysicalDistribution(gnbNodes, ueNodes);
            break;

        case PhysicalDistributionOptions::IND_ROUTER:
            IndoorRouterPhysicalDistribution(gnbNodes, ueNodes);
            break;

        case PhysicalDistributionOptions::TREES:
            TreePhysicalDistribution(gnbNodes, ueNodes, mobility);
            break;

        case PhysicalDistributionOptions::DEFAULT:
        default:
            DefaultPhysicalDistribution(gnbNodes, ueNodes, mobility);
            break;
    }


    /********************************************************************************************************************
     * NR Helpers and Stuff
     ********************************************************************************************************************/
    
    /**
     * Setup the NR module. We create the various helpers needed for the
     * NR simulation:
     * - EpcHelper, which will setup the core network
     * - IdealBeamformingHelper, which takes care of the beamforming part
     * - NrHelper, which takes care of creating and connecting the various
     * part of the NR stack
     */
    /*
     * Create NR simulation helpers
     */
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
    // Configure ideal beamforming method
    idealBeamformingHelper->SetAttribute("BeamformingMethod",
                                         TypeIdValue(DirectPathBeamforming::GetTypeId()));// dir at gNB, dir at UE

    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
    nrHelper->SetBeamformingHelper(idealBeamformingHelper);
    nrHelper->SetEpcHelper(epcHelper);

    /*
     * Spectrum configuration. We create a single operational band and configure the scenario.
     */
    // Setup scenario depending if there are buildings or not
    if (enableBuildings)
    {
        scenarioEnum = BandwidthPartInfo::UMa_Buildings;
    } 
    else 
    {
        scenarioEnum = BandwidthPartInfo::UMa;
    }

    
    CcBwpCreator ccBwpCreator;
    const uint8_t numCcPerBand = 1; // in this example we have a single band, and that band is
                                    // composed of a single component carrier

    /* Create the configuration for the CcBwpHelper. SimpleOperationBandConf creates
     * a single BWP per CC and a single BWP in CC.
     *
     * Hence, the configured spectrum is:
     *
     * |---------------Band---------------|
     * |---------------CC-----------------|
     * |---------------BWP----------------|
     */
    CcBwpCreator::SimpleOperationBandConf bandConf(frequency,
                                                   bandwidth,
                                                   numCcPerBand,
                                                   scenarioEnum);
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

     // Initialize channel and pathloss, plus other things inside band.
     
    Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod", TimeValue(MilliSeconds(0)));

    std::string errorModel = "ns3::NrEesmIrT1"; //ns3::NrEesmCcT1, ns3::NrEesmCcT2, ns3::NrEesmIrT1, ns3::NrEesmIrT2, ns3::NrLteMiErrorModel
    // nrHelper->SetUlErrorModel(errorModel); 
    // nrHelper->SetDlErrorModel(errorModel);
    Config::SetDefault("ns3::NrAmc::ErrorModelType", TypeIdValue(TypeId::LookupByName(errorModel)));
    Config::SetDefault("ns3::NrAmc::AmcModel", EnumValue(NrAmc::ErrorModel )); // NrAmc::ShannonModel // NrAmc::ErrorModel

    // std::string pathlossModel="ns3::ThreeGppUmaPropagationLossModel";


    nrHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    nrHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(shadowing)); // false: allow see effect of path loss only

    // Ptr<HybridBuildingsPropagationLossModel> propagationLossModel =
    //     CreateObject<HybridBuildingsPropagationLossModel>();
    // cancel shadowing effect set 0.0

    // propagationLossModel->SetAttribute("ShadowSigmaOutdoor", DoubleValue(7.0)); // Standard deviation of the normal distribution used for calculate the shadowing for outdoor nodes
    // propagationLossModel->SetAttribute("ShadowSigmaIndoor", DoubleValue(8.0)); // Standard deviation of the normal distribution used for calculate the shadowing for indoor nodes
    // propagationLossModel->SetAttribute("ShadowSigmaExtWalls", DoubleValue(5.0)); // Standard deviation of the normal distribution used for calculate the shadowing due to ext walls
    // propagationLossModel->SetAttribute("InternalWallLoss", DoubleValue(5.7)); // Additional loss for each internal wall [dB]

    // Initialize channel and pathloss, plus other things inside band.
    nrHelper->InitializeOperationBand(&band);
    BandwidthPartInfoPtrVector allBwps = CcBwpCreator::GetAllBwps({band});

    // Configure scheduler
    nrHelper->SetSchedulerTypeId(NrMacSchedulerTdmaRR::GetTypeId());


    // Antennas for the UEs
    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(2));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(4));
    nrHelper->SetUeAntennaAttribute("AntennaElement",
                                    PointerValue(CreateObject<IsotropicAntennaModel>()));
    
    // Antennas for the gNbs
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(8));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(8));
    nrHelper->SetGnbAntennaAttribute("AntennaElement",
                                     PointerValue(CreateObject<IsotropicAntennaModel>()));

    // install nr net devices
    NetDeviceContainer gnbNetDev = nrHelper->InstallGnbDevice(gnbNodes, allBwps);
    NetDeviceContainer ueNetDev = nrHelper->InstallUeDevice(ueNodes, allBwps);

    int64_t randomStream = 1;
    randomStream += nrHelper->AssignStreams(gnbNetDev, randomStream);
    randomStream += nrHelper->AssignStreams(ueNetDev, randomStream);

    for (uint32_t u = 0; u < gnbNodes.GetN(); ++u)
    {
        nrHelper->GetGnbPhy(gnbNetDev.Get(u), 0)->SetTxPower(txPower);
        nrHelper->GetGnbPhy(gnbNetDev.Get(u), 0)
            ->SetAttribute("Numerology", UintegerValue(numerology));
    }

    if (addNoise) 
    {   
        for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
        {
            // Get the physical layer and add noise whenerver DlDataSinr is executed
            Ptr<NrUePhy> uePhy = nrHelper->GetUePhy(ueNetDev.Get(u), 0);
            uePhy->SetNoiseFigure(NOISE_MEAN);

            for (int i = 0; i < (Seconds(simTime) - Seconds(0.2)) / NOISE_T_RES; i++)
            {
                Simulator::Schedule(NOISE_T_RES * i + Seconds(0.1), &AddRandomNoise, uePhy);
            }
        }
    }
    // When all the configuration is done, explicitly call UpdateConfig ()
    for (auto it = gnbNetDev.Begin(); it != gnbNetDev.End(); ++it)
    {
        DynamicCast<NrGnbNetDevice>(*it)->UpdateConfig();
    }

    for (auto it = ueNetDev.Begin(); it != ueNetDev.End(); ++it)
    {
        DynamicCast<NrUeNetDevice>(*it)->UpdateConfig();
    }

    /********************************************************************************************************************
     * Setup and install IP, internet and remote servers
     ********************************************************************************************************************/

    std::cout << TXT_CYAN << "Install IP" << TXT_CLEAR << std::endl;
    // create the internet and install the IP stack on the UEs
    // get SGW/PGW and create a single RemoteHost
    std::cout << "\t- SGW/PGW" << std::endl;
    epcHelper->SetAttribute("S1uLinkDelay", TimeValue(MilliSeconds(0)));    // Core latency
    Ptr<Node> pgw = epcHelper->GetPgwNode();

    std::cout << "\t- Remote Server" << std::endl;
    NodeContainer remoteHostContainer;
    remoteHostContainer.Create(2);
    Ptr<Node> remoteHost = remoteHostContainer.Get(0);
    // Ptr<Node> remoteHost1 = remoteHostContainer.Get(1);

    InternetStackHelper internet;
    QuicHelper stack;
    if ( flowType == "QUIC")
    {
        stack.InstallQuic (remoteHostContainer);
    }
    else
    {
        internet.Install(remoteHostContainer);
    }

    // connect a remoteHost to pgw. Setup routing too
    std::cout << "\t- Connect remote Server to PGW" << std::endl;
    PointToPointHelper p2ph;
    p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("10Gb/s"))); //100Gb/s
    p2ph.SetDeviceAttribute("Mtu", UintegerValue(1500)); //2500
    p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(serverDelay)));
    NetDeviceContainer internetDevices = p2ph.Install(pgw, remoteHost);
    // NetDeviceContainer internetDevices1 = p2ph.Install(pgw, remoteHost1);


    Ipv4AddressHelper ipv4h;
    ipv4h.SetBase("1.0.0.0", "255.0.0.0");
    Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(internetDevices);
    // Ipv4InterfaceContainer internetIpIfaces1 = ipv4h.Assign(internetDevices1);


    std::cout << "\t- IP Routes" << std::endl;
    Ipv4StaticRoutingHelper ipv4RoutingHelper;
    Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
        ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
    // Ptr<Ipv4StaticRouting> remoteHostStaticRouting1 =
    //     ipv4RoutingHelper.GetStaticRouting(remoteHost1->GetObject<Ipv4>());
    remoteHostStaticRouting->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);
    // remoteHostStaticRouting1->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);


    if ( flowType == "QUIC")
    {
        stack.InstallQuic (ueNodes);
    }
    else
    {
        internet.Install(ueNodes);
    }
    

    Ipv4InterfaceContainer ueIpIface;
    ueIpIface = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueNetDev));


    // attach UEs to the closest eNB
    std::cout << "\t- UEs to eNb" << std::endl;
    nrHelper->AttachToClosestEnb(ueNetDev, gnbNetDev);

    // assign IP address to UEs
    for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
    {
        std::cout << "\t- IP to UE" << u << std::endl;
        Ptr<Node> ueNode = ueNodes.Get(u);
        // Set the default gateway for the UE
        Ptr<Ipv4StaticRouting> ueStaticRouting =
            ipv4RoutingHelper.GetStaticRouting(ueNode->GetObject<Ipv4>());
        ueStaticRouting->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);
    }



    std::cout << TXT_CYAN << "Install App: " << tcpTypeId << TXT_CLEAR << std::endl;
    if ( flowType == "UDP")
    {
        uint16_t dlPort = 1234;
        double interval = SegmentSize*8/dataRate; // MicroSeconds
        // install downlink applications
        ApplicationContainer clientApps;
        ApplicationContainer serverApps;

        for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
        {
            UdpServerHelper dlPacketSinkHelper(dlPort);
            serverApps.Add(dlPacketSinkHelper.Install(ueNodes.Get(u)));

            UdpClientHelper dlClient(ueIpIface.GetAddress(u), dlPort);
            dlClient.SetAttribute("Interval", TimeValue(MicroSeconds(interval)));
            dlClient.SetAttribute("MaxPackets", UintegerValue(0xFFFFFFFF));
            dlClient.SetAttribute("PacketSize", UintegerValue(SegmentSize));
            clientApps.Add(dlClient.Install(remoteHost));
        }
        // start server and client apps
        serverApps.Start(Seconds(AppStartTime));
        clientApps.Start(Seconds(AppStartTime));
        serverApps.Stop(Seconds(simTime));
        clientApps.Stop(Seconds(simTime - 0.02));
    }
    else if ( flowType == "TCP")
    {

        uint16_t sinkPort = 8080;
        uint16_t connNumPerUe = 1;
        

        for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
        {
            auto start = AppStartTime ;//+ 0.01 * u;
            auto end = std::max (start + 1., simTime - start);
            for (uint32_t c = 0; c < connNumPerUe; ++c){
                InstallTCP2 (remoteHostContainer.Get (0), ueNodes.Get (u), sinkPort++, start, end, dataRate);

            }
            
            std::cout << TXT_CYAN << 
                    "Install TCP between nodes: " << std::to_string(remoteHostContainer.Get (0)->GetId()) << "<->"<< std::to_string(ueNodes.Get (u)->GetId()) <<
                    TXT_CLEAR << std::endl;

            // Hook TRACE SOURCE after application starts
            // this work because u is identical to socketid in this case
            Simulator::Schedule(Seconds(AppStartTime) , 
                                &TraceTcp, remoteHostContainer.Get (0)->GetId(), u);

        
        }
    }
    else if ( flowType == "QUIC")
    {
        std::cout << "\tQUICHelper" << std::endl;
        // QuicHelper stack;
        // stack.InstallQuic (ueNodes);
        
        // QUIC client and server
        uint32_t dlPort = 1025;
        ApplicationContainer clientApps;
        ApplicationContainer serverApps;
        // double interPacketInterval = SegmentSize*8/dataRate; // MicroSeconds
        SegmentSize = 1200 ;
        double interPacketInterval = 40;  // 40; 125 => datarate=SegmentSize*8/interPacketInterval kbps

        for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
        {
            std::cout << "\tQuicServerHelper" << std::endl;
            QuicServerHelper dlPacketSinkHelper (dlPort);
            serverApps.Add (dlPacketSinkHelper.Install (ueNodes.Get(u)));

            std::cout << "\tQuicClientHelper" << std::endl;
            QuicClientHelper dlClient (ueIpIface.GetAddress(u), dlPort);
            dlClient.SetAttribute ("Interval", TimeValue (MicroSeconds(interPacketInterval)));
            dlClient.SetAttribute ("PacketSize", UintegerValue(SegmentSize));
            dlClient.SetAttribute ("MaxPackets", UintegerValue(0xFFFFFFFF));
            clientApps.Add (dlClient.Install (remoteHost));
  
        }
        // start server and client apps
        serverApps.Start(Seconds(0));
        clientApps.Start(Seconds(AppStartTime));
        serverApps.Stop(Seconds(simTime));
        clientApps.Stop(Seconds(simTime - 0.02));

        for (uint16_t u = 0; u < ueNodes.GetN(); u++)
        {
            auto ueNode = ueNodes.Get(u);
            Time t = Seconds(AppStartTime);
            Simulator::Schedule (t, &Traces, u, "./server", ".txt");
        }
        Simulator::Schedule (Seconds(AppStartTime), &Traces, remoteHost->GetId(), "./client", ".txt");

    }

    /********************************************************************************************************************
    * Trace and file generation
    ********************************************************************************************************************/
    // enable the traces provided by the nr module
    if (NRTrace)
    {
        std::cout << "NR Trace "<< std::endl ;
        nrHelper->EnableTraces();
    }

    // All tcp trace
    if(TCPTrace){
        std::cout << "TCP Trace "<< std::endl ;
        std::ofstream asciiTCP;
        Ptr<OutputStreamWrapper> ascii_wrap;
        asciiTCP.open("tcp-all-ascii.txt");
        ascii_wrap = new OutputStreamWrapper("tcp-all-ascii.txt", std::ios::out);
        internet.EnableAsciiIpv4All(ascii_wrap);
    }


    // Calculate the node positions
    std::cout << TXT_CYAN << "Install Position" << TXT_CLEAR << std::endl;
    std::cout <<  "ST:Simulation Time\t" << "PT: Process Time\t" << "ET: Elapsed Time\t"  << std::endl;
    std::string logMFile="mobilityPosition.txt";
    std::ofstream mymcf;
    mymcf.open(logMFile);
    mymcf  << "Time\t" << "UE\t" << "x\t" << "y\t"  << "D0" << std::endl;
    Simulator::Schedule(MilliSeconds(100), &CalculatePosition, &ueNodes, &gnbNodes, &mymcf);

    // 
    // generate graph.ini
    //
    std::string iniFile="graph.ini";
    std::ofstream inif;
    inif.open(iniFile);
    inif << "[general]" << std::endl;
    inif << "resamplePeriod = 100" << std::endl;
    inif << "simTime = " << simTime << std::endl;
    inif << "AppStartTime = " << AppStartTime << std::endl;
    inif << "NRTrace = " << NRTrace << std::endl;
    inif << "TCPTrace = " << TCPTrace << std::endl;
    inif << "flowType = " << flowType << std::endl;
    inif << "tcpTypeId = " << tcpTypeId << std::endl;
    inif << "frequency = " << frequency << std::endl;
    inif << "bandwidth = " << bandwidth << std::endl;
    inif << "serverID = " << (int)(ueNumPergNb+gNbNum+3) << std::endl;
    inif << "ip_net_Server = " << ip_net_Server << std::endl;
    inif << "ip_mask_Server = " << ip_mask_Server << std::endl;
    inif << "UENum = " << (int)(ueNumPergNb) << std::endl;
    inif << "SegmentSize = " << SegmentSize << std::endl;
    inif << "rlcBuffer = " << rlcBuffer << std::endl;
    inif << "rlcBufferPerc = " << rlcBufferPerc << std::endl;
    inif << "serverType = " << serverType << std::endl;
    inif << "dataRate = " << dataRate << std::endl;
    inif << "phyDistro = "   << phyDistro   << std::endl;
    
    inif << std::endl;
    inif << "[gNb]" << std::endl;
    inif << "gNbNum = " << gNbNum << std::endl;
    inif << "gNbX = "   << gNbX   << std::endl;
    inif << "gNbY = "   << gNbY   << std::endl;
    inif << "gNbD = "   << gNbD   << std::endl;
    inif << "ip_net_UE = "   << ip_net_UE   << std::endl;
    inif << "ip_mask_UE = "   << ip_mask_UE   << std::endl;

    inif << std::endl;
    inif << "[building]" << std::endl;
    inif << "enableBuildings = " << enableBuildings << std::endl;
    inif << "gridWidth = " << gridWidth << std::endl;
    inif << "buildN = " << numOfBuildings << std::endl;
    inif << "buildX = " << buildX << std::endl;
    inif << "buildY = " << buildY << std::endl;
    inif << "buildDx = " << buildDx << std::endl;
    inif << "buildDy = " << buildDy << std::endl;
    inif << "buildLx = " << buildLx << std::endl;
    inif << "buildLy = " << buildLy << std::endl;
    inif.close();


    PrintNodeAddressInfo(true);

    FlowMonitorHelper flowmonHelper;
    NodeContainer endpointNodes;
    endpointNodes.Add(remoteHost);
    endpointNodes.Add(ueNodes);

    Ptr<ns3::FlowMonitor> monitor = flowmonHelper.Install(endpointNodes);
    monitor->SetAttribute("DelayBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("JitterBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("PacketSizeBinWidth", DoubleValue(20));
    

    




    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    processFlowMonitor(monitor, flowmonHelper.GetClassifier(), AppStartTime);

    Simulator::Destroy();

    std::cout << "\nThis is The End" << std::endl;
    auto toc = std::chrono::high_resolution_clock::now();
    std::cout << "Total Time: " << "\033[1;35m"  << 1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(toc-itime).count() << "\033[0m"<<  std::endl;

    return 0;
}



// Trace congestion window
static void
CwndTracer(Ptr<OutputStreamWrapper> stream, uint32_t oldval, uint32_t newval)
{
    //*stream->GetStream() << Simulator::Now().GetSeconds() << " " << newval / SegmentSize << std::endl;
    *stream->GetStream() << Simulator::Now().GetSeconds() << "\t" << oldval  << "\t" << newval  << std::endl;
}


static void
RtoTracer(Ptr<OutputStreamWrapper> stream, Time oldval, Time newval)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << (float) oldval.GetSeconds()<< "\t" << (float) newval.GetSeconds() << std::endl;
}
/**
 * RTT tracer.
 *
 * \param context The context.
 * \param oldval Old value.
 * \param newval New value.
 */
static void
RttTracer(Ptr<OutputStreamWrapper> stream, Time oldval, Time newval)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << (float) oldval.GetSeconds()<< "\t" << (float) newval.GetSeconds() << std::endl;

}

/**
 * Next TX tracer.
 *
 * \param context The context.
 * \param old Old sequence number.
 * \param nextTx Next sequence number.
 */
static void
NextTxTracer(Ptr<OutputStreamWrapper> stream, SequenceNumber32 old [[maybe_unused]], SequenceNumber32 nextTx)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << old<< "\t" << nextTx << std::endl;
}

/**
 * Next RX tracer.
 *
 * \param context The context.
 * \param old Old sequence number.
 * \param nextRx Next sequence number.
 */
static void
NextRxTracer(Ptr<OutputStreamWrapper> stream, SequenceNumber32 old [[maybe_unused]], SequenceNumber32 nextRx)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << old<< "\t" << nextRx << std::endl;
}

/**
 * In-flight tracer.
 *
 * \param context The context.
 * \param old Old value.
 * \param inFlight In flight value.
 */
static void
InFlightTracer(Ptr<OutputStreamWrapper> stream, uint32_t old [[maybe_unused]], uint32_t inFlight)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << old<< "\t" << inFlight << std::endl;
}

/**
 * Slow start threshold tracer.
 *
 * \param context The context.
 * \param oldval Old value.
 * \param newval New value.
 */
static void
SsThreshTracer(Ptr<OutputStreamWrapper> stream, uint32_t oldval, uint32_t newval)
{
    *stream->GetStream()  << Simulator::Now().GetSeconds() << "\t" << oldval<< "\t" << newval << std::endl;
}


static void
TraceTcp(uint32_t nodeId, uint32_t socketId)
{
    std::cout << TXT_CYAN << "\nTrace TCP: " << nodeId << "<->" << socketId << " at: "<<  
            1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(tic-itime).count()<< TXT_CLEAR << std::endl;


    // Init Congestion Window Tracer
    AsciiTraceHelper asciicwnd;
    Ptr<OutputStreamWrapper> stream = asciicwnd.CreateFileStream( "tcp-cwnd-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *stream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;

    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/CongestionWindow",
                                    MakeBoundCallback(&CwndTracer, stream));

    // Init Congestion RTO
    AsciiTraceHelper asciirto;
    Ptr<OutputStreamWrapper> rtoStream = asciirto.CreateFileStream("tcp-rto-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *rtoStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/RTO",
                                    MakeBoundCallback(&RtoTracer,rtoStream));

    // Init Congestion RTT
    AsciiTraceHelper asciirtt;
    Ptr<OutputStreamWrapper> rttStream = asciirtt.CreateFileStream("tcp-rtt-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *rttStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/RTT",
                                    MakeBoundCallback(&RttTracer,rttStream));

    // Init Congestion NextTxTracer
    AsciiTraceHelper asciinexttx;
    Ptr<OutputStreamWrapper> nexttxStream = asciinexttx.CreateFileStream("tcp-nexttx-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *nexttxStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/NextTxSequence",
                                    MakeBoundCallback(&NextTxTracer,nexttxStream));

    // Init Congestion NextRxTracer
    AsciiTraceHelper asciinextrx;
    Ptr<OutputStreamWrapper> nextrxStream = asciinextrx.CreateFileStream("tcp-nextrx-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *nextrxStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/RxBuffer/NextRxSequence",
                                    MakeBoundCallback(&NextRxTracer,nextrxStream));

                                    
    // Init Congestion InFlightTracer
    AsciiTraceHelper asciiinflight;
    Ptr<OutputStreamWrapper> inflightStream = asciiinflight.CreateFileStream("tcp-inflight-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *inflightStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/BytesInFlight",
                                    MakeBoundCallback(&InFlightTracer,inflightStream));

    // Init Congestion SsThreshTracer
    AsciiTraceHelper asciissth;
    Ptr<OutputStreamWrapper> ssthStream = asciissth.CreateFileStream("tcp-ssth-"
                                    + std::to_string(nodeId) +"-"+std::to_string(socketId)+".txt");
    *ssthStream->GetStream() << "Time" << "\t" << "oldval" << "\t" << "newval" << std::endl;
    Config::ConnectWithoutContext("/NodeList/" + std::to_string(nodeId) +
                                    "/$ns3::TcpL4Protocol/SocketList/" +
                                    std::to_string(socketId) + "/SlowStartThreshold",
                                    MakeBoundCallback(&SsThreshTracer,ssthStream));

}



static void InstallTCP2 (Ptr<Node> remoteHost,
                        Ptr<Node> sender,
                        uint16_t sinkPort,
                        float startTime,
                        float stopTime, float dataRate)
{
    //Address sinkAddress (InetSocketAddress (ueIpIface.GetAddress (0), sinkPort));
    Address sinkAddress (InetSocketAddress (sender->GetObject<Ipv4> ()->GetAddress (1,0).GetLocal (), sinkPort));
    PacketSinkHelper packetSinkHelper ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), sinkPort));
    ApplicationContainer sinkApps = packetSinkHelper.Install (sender);

    sinkApps.Start (Seconds (0.));
    sinkApps.Stop (Seconds (simTime));

    Ptr<Socket> ns3TcpSocket = Socket::CreateSocket (remoteHost, TcpSocketFactory::GetTypeId ());
    Ptr<MyApp> app = CreateObject<MyApp> ();
    app->Setup (ns3TcpSocket, sinkAddress, SegmentSize, 1000000000, DataRate (std::to_string(dataRate) + "Mb/s"));

    remoteHost->AddApplication (app);

    app->SetStartTime (Seconds (startTime));
    app->SetStopTime (Seconds (stopTime));
    
}





/**
 * Calulate the Position
 */

static void
CalculatePosition(NodeContainer* ueNodes, NodeContainer* gnbNodes, std::ostream* os)
{
    auto toc = std::chrono::high_resolution_clock::now();
    Time now = Simulator::Now(); 
    
    pid_t pid = getpid();

    std::cout << "\r\e[K" << "pid: " << TXT_GREEN << pid << TXT_CLEAR << 
            " ST: " << "\033[1;32m["  << now.GetSeconds() << "/"<< simTime <<"] "<< "\033[0m"<<  
            " PT: " << 1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(toc-tic).count()<< " "
            " ET: " << "\033[1;35m"  << 1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(toc-itime).count() << "\033[0m"<< " " <<
            " RT: " << "\033[1;34m"  << 1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(toc-itime).count() * simTime / now.GetSeconds() - 1.e-9*std::chrono::duration_cast<std::chrono::nanoseconds>(toc-itime).count()<< "\033[0m"<< std::flush;
    
    for (uint32_t u = 0; u < ueNodes->GetN(); ++u)
    {
        Ptr<MobilityModel> modelu = ueNodes->Get(u)->GetObject<MobilityModel>();
        Ptr<MobilityModel> modelb = gnbNodes->Get(0)->GetObject<MobilityModel>();
        Vector position = modelu->GetPosition ();
        double distance = modelu->GetDistanceFrom (modelb);
        *os  << now.GetSeconds()<< "\t" << (u+1) << "\t"<< position.x << "\t" << position.y << "\t" << distance << std::endl;

        
    }
    tic=toc;

    Simulator::Schedule(MilliSeconds(100), &CalculatePosition, ueNodes, gnbNodes, os);
}

/**
 * Adds Normal Distributed Noise to the specified Physical layer (it is assumed that corresponds to the UE)
 * The function is implemented to be called at the same time as `DlDataSinrCallback`, this implies that unused arguments 
 * had to be added so it would function.
 * 
 * \example  Config::ConnectWithoutContext("/NodeList/.../DeviceList/.../ComponentCarrierMapUe/.../NrUePhy/DlDataSinr",
 *                  MakeBoundCallback(&AddRandomNoise, uePhy))
 * 
*/
static void AddRandomNoise(Ptr<NrPhy> ue_phy)
{
    Ptr<NormalRandomVariable> awgn = CreateObject<NormalRandomVariable>();
    awgn->SetAttribute("Mean", DoubleValue(NOISE_MEAN));
    awgn->SetAttribute("Variance", DoubleValue(NOISE_VAR));
    awgn->SetAttribute("Bound", DoubleValue(NOISE_BOUND));

    ue_phy->SetNoiseFigure(awgn->GetValue());

    /*
    Simulator::Schedule(MilliSeconds(1000),
                        &NrPhy::SetNoiseFigure,
                        ue_phy,
                        awgn->GetValue()); // Default ns3 noise: 5 dB
    */
}

/**
 * Prints info about the nodes, including:
 *  - SystemID (it assumed that 32uint_t <=> 4 chars)
 *  - NodeID
 *  - NetDevices ID
 *  - Address of each NetDevice
 * 
 * \param ignore_localh     if it ignores the LocalHost Adresses
*/
static void PrintNodeAddressInfo(bool ignore_localh)
{
    std::clog << "Debug info" << std::endl;
    if (ignore_localh) 
    {
        std::clog << "\tLocalhosts addresses were excluded." << std::endl;
    }

    for (uint32_t u = 0; u < NodeList::GetNNodes(); ++u) 
    {   
        Ptr<Node> node = NodeList::GetNode(u);
        uint32_t id = node->GetId();
        uint32_t sysid = node->GetSystemId();
        Ptr<Ipv4> node_ip = node->GetObject<Ipv4>();
        uint32_t ieN = node_ip->GetNInterfaces();  // interface number

        uint32_t a = (uint8_t)ignore_localh;     // Asumes that the 1st interface is localhost
        for (; a < ieN; ++a)
        {   
            uint32_t num_address = node_ip->GetNAddresses(a);

            for (uint32_t b = 0; b < num_address; b++)
            {
                Ipv4Address IeAddres = node_ip->GetAddress(a, b).GetAddress();
                std::clog << "\t " << (uint8_t)sysid << (uint8_t)(sysid >> 8) << (uint8_t)(sysid >> 16) << (uint8_t)(sysid >> 24)
                          << " id: " << id << " netdevice: " << +a << " addr: " << IeAddres << std::endl;
            }

            
        }
        
    }
}

static void
processFlowMonitor(Ptr<FlowMonitor> monitor, Ptr<ns3::FlowClassifier> flowClassifier, double AppStartTime)
{
    // Print per-flow statistics
    monitor->CheckForLostPackets();
    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowClassifier);
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    double averageFlowThroughput = 0.0;
    double averageFlowDelay = 0.0;

    std::ofstream outFile;
    std::string filename = "FlowOutput.txt";
    outFile.open(filename.c_str(), std::ofstream::out | std::ofstream::trunc);
    if (!outFile.is_open())
    {
        std::cerr << "Can't open file " << filename << std::endl;
        return;
    }

    outFile.setf(std::ios_base::fixed);

    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin();
         i != stats.end();
         ++i)
    {
        Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
        std::stringstream protoStream;
        protoStream << (uint16_t)t.protocol;
        if (t.protocol == 6)
        {
            protoStream.str("TCP");
        }
        if (t.protocol == 17)
        {
            protoStream.str("UDP");
        }
        outFile << "Flow " << i->first << " (" << t.sourceAddress << ":" << t.sourcePort << " -> "
                << t.destinationAddress << ":" << t.destinationPort << ") proto "
                << protoStream.str() << "\n";
        outFile << "  Tx Packets: " << i->second.txPackets << "\n";
        outFile << "  Tx Bytes:   " << i->second.txBytes << "\n";
        outFile << "  TxOffered:  "
                << i->second.txBytes * 8.0 / (simTime - AppStartTime) / 1000 / 1000 << " Mbps\n";
        outFile << "  Rx Bytes:   " << i->second.rxBytes << "\n";
        if (i->second.rxPackets > 0)
        {
            // Measure the duration of the flow from receiver's perspective
            // double rxDuration = i->second.timeLastRxPacket.GetSeconds () -
            // i->second.timeFirstTxPacket.GetSeconds ();
            double rxDuration = (simTime - AppStartTime);

            averageFlowThroughput += i->second.rxBytes * 8.0 / rxDuration / 1000 / 1000;
            averageFlowDelay += 1000 * i->second.delaySum.GetSeconds() / i->second.rxPackets;

            outFile << "  Throughput: " << i->second.rxBytes * 8.0 / rxDuration / 1000 / 1000
                    << " Mbps\n";
            outFile << "  Mean delay:  "
                    << 1000 * i->second.delaySum.GetSeconds() / i->second.rxPackets << " ms\n";
            // outFile << "  Mean upt:  " << i->second.uptSum / i->second.rxPackets / 1000/1000 << "
            // Mbps \n";
            outFile << "  Mean jitter:  "
                    << 1000 * i->second.jitterSum.GetSeconds() / i->second.rxPackets << " ms\n";
        }
        else
        {
            outFile << "  Throughput:  0 Mbps\n";
            outFile << "  Mean delay:  0 ms\n";
            outFile << "  Mean jitter: 0 ms\n";
        }
        outFile << "  Rx Packets: " << i->second.rxPackets << "\n";
        outFile << "  Lost Packets: " <<  (i->second.txPackets - i->second.rxPackets) << "\n";
    }

    outFile << "\n\n  Mean flow throughput: " << averageFlowThroughput / stats.size() << "\n";
    outFile << "  Mean flow delay: " << averageFlowDelay / stats.size() << "\n";

    outFile.close();
}