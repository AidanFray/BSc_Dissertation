from BaseClasses.Base_Test import Base_Test
from Effects.PacketLoss import PacketLoss


class PacketLossRetranTest(Base_Test):
    """Test that increases the packet loss and obtains the values for retransmissions"""

    def __init__(self):
        super().__init__('PacketLossRetran',
                         max_effect_value=100,
                         start_effect_value=1,
                         effect_step=1,
                         repeat_tests=1,
                         data_headers=['Packet loss (%)', 'No Retransmissions', 'Total Packets', 'Ratio'],
                         max_test_time=120)

    def custom_test_behavior(self, packetLoss_value, data):
        """This is run from the start() method in the Base_Test.py"""

        packetLoss_obj = PacketLoss(packetLoss_value)
        self.run_test_TCP(packetLoss_obj, 'TCP')

        # Grabs data
        retransmissions = packetLoss_obj.retransmission
        total_packets = packetLoss_obj.total_packets
        ratio = (retransmissions / total_packets) * 100

        # Saves data
        data.append(retransmissions)
        data.append(total_packets)
        data.append(ratio)

        # Displays data
        print('## Output: R:{} T:{} Ratio: {}'.format(retransmissions, total_packets, ratio))

        return data


test = PacketLossRetranTest()
test.start()
