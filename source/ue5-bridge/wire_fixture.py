"""Synthetic DAoC packet fixture, not a server emulator, account service or saved world."""
import math
import socket
import struct
import threading
import time

def frame(code,data):return struct.pack('>HB',len(data),code)+data
def pascal(text):
    raw=text.encode('cp1252');return bytes([len(raw)])+raw

def npc(oid,x,z,heading):
    # Fields follow the existing decoder's NPCCreate 1.124+ data contract.
    data=struct.pack('>HHHHIIHHBBBBBBH',oid,100,heading,5280,
                     round(35*8192+x/.025),round(51*8192+z/.025),0,500,50,1,128,0,0,0,0)
    return frame(0xDA,data+pascal(f'Synthetic wire NPC {oid}')+pascal('Bridge proof'))

def you(x,z,heading):
    data=struct.pack('<fff',35*8192+x/.025,51*8192+z/.025,5280)
    data+=struct.pack('>HHHHHB',900,heading,35,51,200,0)
    return frame(0x20,data)

def move(oid,x,z,heading):
    values=(100,heading,round(x/.025),0,round(z/.025),0,5280,0,oid,0)
    return frame(0xA1,struct.pack('>10H4B',*values,100,0,207,207))

class Fixture:
    def __init__(self):
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(1)
        self.listener.settimeout(.2);self.port=self.listener.getsockname()[1]
        self.stop_event=threading.Event();self.thread=threading.Thread(target=self.run,daemon=True)
        self.packets=0;self.error=None
    def start(self):self.thread.start()
    def close(self):
        self.stop_event.set();self.thread.join(3);self.listener.close()
    def run(self):
        try:
            connection=None
            while not self.stop_event.is_set():
                try:connection,_=self.listener.accept();break
                except socket.timeout:continue
            if connection is None:return
            with connection:
                connection.settimeout(.1)
                # Only the client's version handshake is sent; no login is requested or accepted.
                connection.recv(4096)
                began=time.monotonic();present=set()
                while not self.stop_event.is_set():
                    t=time.monotonic()-began;heading=round(t*400)%4096
                    packets=[you(1304+math.sin(t)*1.5,1245+math.cos(t)*1.5,heading)]
                    for i in range(1,4):
                        oid=1000+i;x=1304+i*2+math.sin(t)*1.5;z=1245+math.cos(t)*1.5
                        if i==3 and t%8>=4:
                            if oid in present:packets.append(frame(0xA2,struct.pack('>HH',oid,1)));present.remove(oid)
                            continue
                        if oid not in present:packets.append(npc(oid,x,z,heading));present.add(oid)
                        else:packets.append(move(oid,x,z,heading))
                    connection.sendall(b''.join(packets));self.packets+=len(packets)
                    if self.stop_event.wait(.1):break
        except (ConnectionError,OSError) as exc:
            if not self.stop_event.is_set():self.error=str(exc)
