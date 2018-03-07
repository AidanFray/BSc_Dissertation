#region Imports
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from BaseClasses.Base_Test import Base_Test
from Effects.Latency import Latency
#endregion Imports


class LatencyTimeOutTest(Base_Test):
    """Test that compares Latency with the number of retransmissions, it should at some point have a very
    large increase in the retransmissions when the latency timeout value is obtained """

    def __init__(self):
        super().__init__('LatencyTimeOutTest',
                         max_effect_value=10000,
                         start_effect_value=10,
                         effect_step=100,
                         repeat_tests=1,
                         data_headers=['Latency value (ms)', 'No Retransmissions', 'Total Packets', 'Ratio'],
                         max_test_time=60)

    def custom_test_behavior(self, effect_value, data):

        latency_obj = Latency(effect_value)
        self.run_test_TCP(latency_obj, 'TCP')

        # Grabs retransmissions
        retransmissions = latency_obj.retransmission
        total_packets = latency_obj.total_packets
        ratio = (retransmissions / total_packets) * 100

        #Saves data
        data.append(retransmissions)
        data.append(total_packets)
        data.append(ratio)

        for x in latency_obj.retransmissions_historical:
            data.append(x)

        print("Done")
        # Displays data
        # print('## Output: R:{} T:{} Ratio: {}'.format(retransmissions, total_packets, ratio))

        return data


test = LatencyTimeOutTest()
test.start()