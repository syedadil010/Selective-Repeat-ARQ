import argparse
import collections
import socket
import sys
import ipaddress
import threading
import time
from multiprocessing import Lock
#from python.httpfs import httpfs
from python.packet import Packet
class server:
    def __init__(self):
        self.clientport=int()
        self.RseqNo = 0
        self.rData = 0
        self.recievedata = False
        self.transdelay=0.01
        self.recieved_Allpackets=collections.OrderedDict()
        self.recieve_window=collections.OrderedDict()
        self.send_window=collections.OrderedDict()
        self.send_Allpackets=collections.OrderedDict()
        self.windowacks=collections.OrderedDict()
        self.send_window_size=0
        self.dataReceived=False
        self.recievedata=False
        self.final=set()
        self.rData=0
        self.window_size=0
        self.recieved_packets=0
        self.window_start=0
        self.window_end=0
        self.syn_received=False
        self.final=''
        self.delay=self.transdelay+0.05
        self.listensynack=True
        self.listen=True
        self.conn=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.router_addr='localhost'
        self.server_addr='localhost'
        self.router_port=int(0)
        self.server_port=int(0)
        self.thread_lock=Lock()
        self.sender=tuple()

    #listen from client
    def run_server(self,port):
            listen=True
            self.conn.bind(('', port))
            print('Echo server is listening at', port)
            while self.listen:
                    data, self.sender = self.conn.recvfrom(1024)
                    p = Packet.from_bytes(data)
                    server_port=p.peer_port
                    if(p.packet_type==0 and self.dataReceived==True):
                        p.packet_type=4
                        self.conn.sendto(p.to_bytes(), self.sender)
                    elif(p.packet_type==5):
                        self.listen=False
                    if(self.recievedata==True and p.packet_type==0):
                        self.handle_data(self.conn, p, self.sender)
                    else:
                        #handle data depending on packet type
                        self.handle_client(self.conn, p, self.sender)
            return self.final
    # handle packets with packet type=0 (data)
    def handle_data(self,conn, p,sender):
            if(p.seq_num==6):
                print("")
            #if received data packet not in window then add to window
            if (len(self.recieve_window)==self.window_size and p.seq_num>=self.window_end+1):
                str=''
                print(sorted(self.recieve_window))
                for i in sorted(self.recieve_window.keys()):
                    str=str+self.recieve_window[i].payload.decode("utf-8")
                self.final=self.final+str
                self.recieve_window.clear()
                self.window_start=self.window_end+1
                self.window_end=self.window_start+self.window_size

            if(p.seq_num in range(self.window_start,self.window_end+1)):
                if(not self.recieve_window.__contains__(p.seq_num)):
                    self.recieve_window[p.seq_num]=p
                    self.recieved_packets+=1
                    p.packet_type=4
                    print('sending ack for packet:',p.seq_num)
                    conn.sendto(p.to_bytes(), sender)
                else:
                    p.packet_type = 4
                    print('sending ack for packet:', p.seq_num)
                    conn.sendto(p.to_bytes(), sender)
            #if window full combine to form msg
            if (self.recieved_packets == self.rData):
                str = ''
                for i in sorted(self.recieve_window.keys()):
                    str = str + self.recieve_window[i].payload.decode("utf-8")
                self.final = self.final + str
                print('complete string received', self.final)
                self.dataReceived=True
                return False
            return True
    def SYNack(self,conn):
        while self.listensynack:
            response, self.sender = conn.recvfrom(1024)
            p = Packet.from_bytes(response)
            self.thread_lock.acquire()
            if (p.packet_type == 3):
                self.syn_received = True
                self.listensynack=False
                print('SYN ack received from client')
                self.thread_lock.release()
                return
            self.thread_lock.release()
    def acks(self,conn,port):
        listenack=True
        while listenack:
                response, sender = conn.recvfrom(1024)
                p = Packet.from_bytes(response)
                self.thread_lock.acquire()
                if(p.packet_type==5):
                    listenack=False
                # if packet type=4 then it is ack, removing packet from window
                if(p.packet_type==4):
                    p.packet_type=0
                    print('recieved ack for packet:',p.seq_num)
                    self.windowacks[p.seq_num]=p.payload
                self.thread_lock.release()

    def resend_packet(self,conn,router_addr, router_port,peer_ip,server_port):
        while(len(self.windowacks)!=len(self.send_window)):
            for i in self.send_window:
                if not self.windowacks.keys().__contains__(i):
                    p = Packet(packet_type=0,
                            seq_num=i,
                            peer_ip_addr=peer_ip,
                            peer_port=self.clientport,
                            payload=bytes(self.send_window[i]))
                    print('retransmitting packet:', p.seq_num)
                    conn.sendto(p.to_bytes(),self.sender)
            time.sleep(self.delay)
        if(len(self.windowacks)==len(self.send_window)):
            self.send_window.clear()
            self.windowacks.clear()
            return

    def server_send(self,conn,peer_ip):
        threading.Thread(target=self.acks, args=(conn, 1024)).start()
        # window size is half the number of packets
        if (len(self.send_Allpackets) > 1):
            send_window_size = int(len(self.send_Allpackets) / 2)
        else:
            send_window_size = len(self.send_Allpackets)
        windowcount = 0
        while (len(self.send_Allpackets) != 0):
            while (len(self.send_window) < send_window_size and len(self.send_Allpackets) != 0):
                j = 0
                windowcount = windowcount + 1
                for i in self.send_Allpackets:
                    self.send_window[i] = self.send_Allpackets[i]
                    j = j + 1
                    if len(self.send_window) == send_window_size:
                        break
                for i in self.send_window.keys():
                    del self.send_Allpackets[i]
                    # packet format
                    p = Packet(packet_type=0,
                               seq_num=i,
                               peer_ip_addr=peer_ip,
                               peer_port=self.clientport,
                               payload=self.send_window[i])
                    print('sending packet:', p.seq_num)
                    conn.sendto(p.to_bytes(), self.sender)
                time.sleep(self.delay)
                self.resend_packet(conn,self.router_addr, self.router_port, peer_ip, self.server_port)

    def resend_SYN(self,conn,p):
        while(not self.syn_received):
            if(not self.listensynack):
                return
            print('resending SYN')
            self.conn.sendto(p.to_bytes(), self.sender)
            time.sleep(self.delay)
        return

    def server_message(self,message):
        peer_ip = ipaddress.ip_address(socket.gethostbyname(self.server_addr))
        contents = bytearray(message.encode())
        no_packets=0
        if (sys.getsizeof(contents) < 1013):
            self.send_Allpackets[no_packets] = contents
            no_packets = +1
        else:
            # read 1013 bytes for each packet
            for i in range(0, sys.getsizeof(contents), 100):
                self.send_Allpackets[no_packets] = contents[i:i + 100]
                no_packets = no_packets + 1
        p = Packet(packet_type=1,
                   seq_num=0,
                   peer_ip_addr=peer_ip,
                   peer_port=self.clientport,
                   payload=str(len(self.send_Allpackets)).encode("utf-8"))
        threading.Thread(target=self.SYNack, args=(self.conn,)).start()
        self.conn.sendto(p.to_bytes(), self.sender)
        print('Send "{}" to client'.format("SYN"))
        time.sleep(self.delay)
        if(self.syn_received==False):
            self.resend_SYN(self.conn,p)
        if(self.syn_received):
            print('Begin transmission of packets to Router: ', self.sender)
            self.server_send(self.conn,peer_ip)
        else:
            print('Unknown response: ', self.sender)

    def handle_client(self,conn,p, sender):
        try:
            print("Packet type:",p.packet_type)
            print("Packet sequence:", p.seq_num)
            #print("Payload: ", p.payload.decode("utf-8"))

            #type=1 SYN from client
            if(p.packet_type==1):
                self.clientport=p.peer_port
                self.first_seqNo=p.seq_num
                print('SYN received')
                #type=2 SYN+ACK for client
                p.packet_type=2
                conn.sendto(p.to_bytes(), sender)
                print('SYN+ACK sent')
            #type=3 ACK from client for TCP
            if(p.packet_type==3):
                print("ACK received-TCP handshake successful\n")
                self.rData=int(p.payload.decode("utf-8"))
                if(self.rData>1):
                    self.window_size=int(self.rData/2)
                else:
                    self.window_size=self.rData
                self.window_start=0
                self.window_end=self.window_size-1
                self.recievedata=True
            # if(p.packet_type==0):
            #     handle_data(conn,p,sender)
        except Exception as e:
            print("Error: ", e)


# Usage python udp_server.py [--port port-number]

parser = argparse.ArgumentParser()
parser.add_argument("--port", help="echo server port", type=int, default=8007)
args = parser.parse_args()
contents=''
#if(not run_server(args.port)):
#    reply=httpfs(final)
#    server_message(conn,reply)
#serv=server()
#serv.run_server(8007)
