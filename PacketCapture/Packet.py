import logging
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)  # Suppresses the Scapy WARNING Message
import argparse
import signal
import threading
import textwrap
import Common_Connections
import parameters as Parameter
from netfilterqueue import NetfilterQueue
from scapy.all import *
from multiprocessing.dummy import Pool as ThreadPool
from Effects.Latency import Latency
from Effects.LimitBandwidth import Bandwidth
from Effects.PacketLoss import PacketLoss
from Effects.Throttle import Throttle
from Effects.OutOfOrder import Order


# Defines how many threads are in the pool
pool = ThreadPool(1000)

logo = """
==============================================================
Degraded Packet Simulation

    ██████╗ ██████╗ ███████╗
    ██╔══██╗██╔══██╗██╔════╝
    ██║  ██║██████╔╝███████╗
    ██║  ██║██╔═══╝ ╚════██║
    ██████╔╝██║     ███████║
    ╚═════╝ ╚═╝     ╚══════╝
"""

epilog = """
Aidan Fray
afray@hotmail.co.uk

==============================================================
"""


def map_thread(method, args):
    """Method that deals with the threading of the packet manipulation"""

    # If this try is caught, it occurs for every thread active so anything in the
    # except is triggered for all active threads
    try:
        pool.map_async(method, args)
    except ValueError:
        # Stops the program from exploding when he pool is terminated
        pass


def print_force(message):
    """This method is required because when this python file is called as a script
    the prints don't appear and a flush is required """
    print(message, flush=True)


def affect_packet(packet):
    """This function checks if the packet should be affected or not. This is part of the -t option"""

    # Saving packets
    if save_active:
        pktdump.write(IP(packet.get_payload()))

    if target_packet_type == "ALL":
        return True
    else:
        # Grabs the first section of the Packet
        packet_string = str(packet)
        split = packet_string.split(' ')

        # Checks for the target packet type
        if target_packet_type == split[0]:
            return True
        else:
            return False


def print_packet(packet, accept=True):
    """This function just prints the packet"""

    # Thread functionality
    def t_print(t_packet):
        """The functionality that will spawned in a thread from the Print_Packet mode"""

        if affect_packet(t_packet):
            print_force("[!] " + str(t_packet))

        if accept:
            t_packet.accept()

    map_thread(t_print, [packet])


def edit_packet(packet, accept=True):
    """This function will be used to edit sections of a packet, this is currently incomplete"""

    # Thread functionality
    def edit(t_packet):
        """Thread functionality"""

        if affect_packet(t_packet):
            pkt = IP(t_packet.get_payload())

            # Changes the Time To Live of the packet
            pkt.ttl = 150

            # Recalculates the check sum
            del pkt[IP].chksum

            # Sets the packet to the modified version
            t_packet.set_payload(bytes(pkt))

            if accept:
                t_packet.accept()
        else:
            t_packet.accept()

    try:
        map_thread(edit, [packet])
    except KeyboardInterrupt:
        clean_close()


def packet_latency(packet):
    """This function is used to incur latency on packets"""

    if affect_packet(packet):
        map_thread(latency_obj.effect, [packet])
    else:
        packet.accept()


def packet_loss(packet):
    """Function that performs packet loss on all packets"""
    if affect_packet(packet):
        map_thread(packet_loss_obj.effect, [packet])
    else:
        packet.accept()


def throttle(packet):
    """Mode assigned to throttle packets"""
    if affect_packet(packet):
        throttle_obj.effect(packet)
    else:
        packet.accept()


def duplicate(packet):
    """Mode that takes a full duplication"""
    global duplication_factor
    if affect_packet(packet):
        # TODO: Needs fixing

        # Get packet data
        pkt = IP(packet.get_payload())

        pkt[IP].dst = "192.168.1.1"

        del pkt[ICMP].chksum
        del pkt[IP].chksum

        send(pkt, verbose=1, count=duplication_factor)
    else:
        packet.accept()


def combination(packet):
    """This performs effects together"""
    packet_loss_obj.effect(packet)
    latency_obj.effect(packet)
    bandwidth_obj.limit(packet)


def combination_effect(packet):
    """The effect of having multiple effects on a """
    if affect_packet(packet):
        map_thread(combination, [packet])
    else:
        packet.accept()


def emulate_real_connection_speed(packet):
    """Used to emulate real world connections speeds"""
    global connection

    if affect_packet(packet):

        # Adjusts the values
        latency_obj.alter_latency_value(connection.rnd_latency())
        packet_loss_obj.alter_percentage(connection.rnd_packet_loss())
        bandwidth_obj.alter_bandwidth(connection.rnd_bandwidth())

        # Calls mode
        map_thread(combination, [packet])
    else:
        packet.accept()


def track_bandwidth(packet):
    """This mode allows for the tracking of rate of packets recieved"""
    if affect_packet(packet):
        bandwidth_obj.display(packet)
    else:
        packet.accept()


def limit_bandwidth(packet):
    """This is mode for limiting the rate of transfer"""
    if affect_packet(packet):
        bandwidth_obj.limit(packet)
    else:
        packet.accept()


def out_of_order(packet):
    """Mode that alters the order of packets"""
    if affect_packet(packet):
        order_obj.effect(packet)
    else:
        packet.accept()


def setup_packet_save(filename):
    """Sets up a global object that is used to save the files
    to a .pcap file"""

    global pktdump
    pktdump = PcapWriter(filename + '.pcap', append=False, sync=True)


def run_packet_manipulation():
    """The main method here, will issue a iptables command and construct the NFQUEUE"""

    try:
        global nfqueue

        # Packets for this machine
        os.system("iptables -A INPUT -j NFQUEUE")

        # Packets for forwarding or other routes
        os.system("iptables -t nat -A PREROUTING -j NFQUEUE")

        print_force("[*] Mode is: " + mode.__name__)

        # Setup for the NQUEUE
        nfqueue = NetfilterQueue()

        try:
            nfqueue.bind(0, mode)  # 0 is the default NFQUEUE
        except OSError:
            print_force("[!] Queue already created")

        # Shows the start waiting message
        print_force("[*] Waiting ")
        nfqueue.run()

    except KeyboardInterrupt:
        clean_close()


def parameters():
    """This function deals with parameters passed to the script"""

    # Defines globals to be used above
    global mode, target_packet_type, duplication_factor, arp_active, save_active

    global latency_obj, throttle_obj, packet_loss_obj, bandwidth_obj, order_obj
    latency_obj = None
    throttle_obj = None
    packet_loss_obj = None
    bandwidth_obj = None
    order_obj = None

    # Defaults
    mode = print_packet
    target_packet_type = 'ALL'
    arp_active = False
    save_active = False

    # Arguments
    parser = argparse.ArgumentParser(prog="Packet.py",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent(logo),
                                     epilog=textwrap.dedent(epilog),
                                     allow_abbrev=False)

    parser.add_argument_group('Arguments', description=Parameter.Usage())

    # Mode parameters
    effect = parser.add_mutually_exclusive_group(required=True,)

    effect.add_argument('--print', Parameter.cmd_print,
                        action='store_true',
                        help=argparse.SUPPRESS)

    effect.add_argument('--latency', Parameter.cmd_latency,
                        action='store',
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--packet-loss', Parameter.cmd_packetloss,
                        action='store',
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--throttle', Parameter.cmd_throttle,
                        action='store',
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--duplicate', Parameter.cmd_duplicate,
                        action='store',
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--combination', Parameter.cmd_combination,
                        action='store',
                        nargs=3,
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--simulate', Parameter.cmd_simulate,
                        action='store',
                        help=argparse.SUPPRESS)

    effect.add_argument('--display-bandwidth', Parameter.cmd_bandwidth,
                        action='store_true',
                        help=argparse.SUPPRESS)

    effect.add_argument('--rate-limit', Parameter.cmd_ratelimit,
                        action='store',
                        dest='rate_limit',
                        help=argparse.SUPPRESS,
                        type=int)

    effect.add_argument('--out-of-order', Parameter.cmd_outoforder,
                        action='store_true',
                        dest='order',
                        help=argparse.SUPPRESS)

    # Extra parameters
    parser.add_argument('--target-packet', Parameter.cmd_target_packet,
                        action='store',
                        help=argparse.SUPPRESS)

    parser.add_argument('--arp', Parameter.cmd_arp,
                        action='store',
                        nargs=3,
                        help=argparse.SUPPRESS)

    parser.add_argument('--save', Parameter.cmd_save,
                        nargs=1,
                        dest='save',
                        help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Modes
    if args.print:
        mode = print_packet

    elif args.latency:
        latency_obj = Latency(latency_value=args.latency, accept_packets=True)
        mode = packet_latency

    elif args.packet_loss:
        packet_loss_obj = PacketLoss(percentage=args.packet_loss, accept_packets=True)
        mode = packet_loss

    elif args.throttle:
        throttle_obj = Throttle(period=args.throttle)
        throttle_obj.start_purge_monitor()
        mode = throttle

    elif args.duplicate:
        local_args = args.duplicate

        duplication_factor = int(local_args)
        print_force('[*] Packet duplication set. Factor is: {}'.format(duplication_factor))
        mode = duplicate

    elif args.combination:
        latency_obj = Latency(latency_value=args.combination[0], accept_packets=False, show_output=False)
        bandwidth_obj = Bandwidth(bandwidth=args.combination[2], accept_packets=False, show_output=False)
        packet_loss_obj = PacketLoss(percentage=args.combination[1], accept_packets=True)
        mode = combination_effect

    elif args.simulate:
        global connection

        # Checks if the parameter is a valid connection
        connection = Nones
        for c in Common_Connections.connections:
            if c.name == str(args.simulate):
                connection = c

        # Could not find connection type
        if connection is None:
            print('Error: Could no find the \'{}\' connection entered'.format(args.simulate))
            sys.exit(0)

        print_force('[*] Connection type is emulating: {}'.format(connection.name))

        latency_obj = Latency(latency_value=0, accept_packets=False, show_output=False)
        bandwidth_obj = Bandwidth(bandwidth=0, accept_packets=False, show_output=False)
        packet_loss_obj = PacketLoss(percentage=0, accept_packets=True, show_output=False)
        mode = emulate_real_connection_speed

    elif args.display_bandwidth:
        bandwidth_obj = Bandwidth()
        mode = track_bandwidth

    elif args.rate_limit:
        # Sets the bandwidth object with the specified bandwidth limit
        bandwidth_obj = Bandwidth(args.rate_limit)
        mode = limit_bandwidth

    elif args.order:
        order_obj = Order()
        mode = out_of_order

    # Extra settings
    if args.target_packet:
        local_args = args.target_packet

        target_packet_type = local_args
        print_force('[!] Only affecting {} packets'.format(target_packet_type))

    if args.arp:
        global arp_process

        local_args = args.arp

        print_force("[*] ## ARP spoofing mode activated ## ")

        victim = local_args[0]
        router = local_args[1]
        interface = local_args[2]

        filepath = os.path.dirname(os.path.abspath(__file__))

        # Runs the arp spoofing
        arp_active = True
        cmd = ['pkexec', 'python', filepath + '/ArpSpoofing.py']
        cmd = cmd + ['-t', victim, '-r', router, '-i', interface]
        arp_process = subprocess.Popen(cmd)

    if args.save:
        print_force('[!] File saving on - Files will be saved under: \'{}.pcap\''.format(args.save[0]))

        save_active = True
        setup_packet_save(args.save[0])

    # When all parameters are handled
    run_packet_manipulation()


def stop_object(object):
    """This method attempts to stop an object, and
    catches the exception if it doesn't need closing"""

    try:
        object.stop()
    except AttributeError:
        pass


def clean_close(signum='', frame=''):
    """Used to close the script cleanly"""

    # Kills any threads running in objects
    stop_object(throttle_obj)
    stop_object(order_obj)

    print_force("\n[*] ## Close signal recieved ##")

    pool.close()
    print_force("[!] Thread pool killed")

    # Resets
    print_force("[!] iptables reverted")
    os.system("iptables -F INPUT")

    print_force("[!] NFQUEUE unbinded")
    nfqueue.unbind()

    if arp_active:
        print_force('[!] Arp Spoofing stopped!')
        arp_process.terminate()

    os._exit(0)


# Rebinds the all the close signals to clean_close the script
signal.signal(signal.SIGINT, clean_close)   # Ctrl + C
signal.signal(signal.SIGTSTP, clean_close)  # Ctrl + Z
signal.signal(signal.SIGQUIT, clean_close)  # Ctrl + \

# Check if user is root
if os.getuid() != 0:
    exit("Error: User needs to be root to run this script")

parameters()
