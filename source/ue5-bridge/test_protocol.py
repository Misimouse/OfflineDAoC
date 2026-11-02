import copy
import json
import math
import unittest
from protocol import Decoder,validate_snapshot,to_unreal,from_unreal,yaw_degrees,MAX_FRAME

def sample():
    return dict(type='snapshot',protocol='daoc-visual-bridge',version=1,session='test',seq=1,
                zone_id=207,origin_m=[1364,130,1263],entities=[dict(id='npc:1',kind='npc',
                position_m=[1304,132,1245],forward_xz=[0,1])])

class ProtocolTests(unittest.TestCase):
    def test_chunked_utf8_and_coalesced_messages(self):
        messages=[dict(type='hello',text='Árbol'),sample()]
        data=b''.join((json.dumps(m,ensure_ascii=False)+'\n').encode() for m in messages)
        decoder=Decoder();actual=[]
        for i in range(0,len(data),3):actual+=decoder.feed(data[i:i+3])
        self.assertEqual(actual,messages)
        self.assertEqual(decoder.buffer,b'')
    def test_oversized_frame(self):
        with self.assertRaises(ValueError):Decoder().feed(b'x'*(MAX_FRAME+1))
    def test_wrong_zone_or_calibration(self):
        for key,value in [('zone_id',209),('origin_m',[0,0,0]),('version',2)]:
            message=sample();message[key]=value
            with self.assertRaises(ValueError):validate_snapshot(message)
    def test_untrusted_nonfinite_and_duplicate_data(self):
        for value in [float('nan'),float('inf'),True,'100']:
            message=sample();message['entities'][0]['position_m'][0]=value
            with self.assertRaises(ValueError):validate_snapshot(message)
        message=sample();message['entities']*=2
        with self.assertRaises(ValueError):validate_snapshot(message)
    def test_calibration_and_round_trip(self):
        self.assertEqual(to_unreal([1364,130,1263]),(0,0,0))
        self.assertEqual(to_unreal([1304,132,1245]),(-6000,-1800,200))
        for point in [(0,0,0),(1638.4,300,1638.4),(1348.775,132.75,1265.62)]:
            self.assertLess(math.dist(point,from_unreal(to_unreal(point))),1e-10)
        for vector,yaw in [([1,0],0),([0,1],90),([-1,0],180),([0,-1],-90)]:
            self.assertAlmostEqual(yaw_degrees(vector),yaw)
    def test_sequence_and_capacity(self):
        for value in [0,-1,1.5,True,float('nan')]:
            message=sample();message['seq']=value
            with self.assertRaises(ValueError):validate_snapshot(message)
        message=sample();message['entities']=[copy.deepcopy(message['entities'][0]) for _ in range(2049)]
        with self.assertRaises(ValueError):validate_snapshot(message)

if __name__=='__main__':unittest.main()
