import argparse
import collections
import ipaddress
import socket
import sys
import threading
import time
import threading
from multiprocessing import Lock
from packet import Packet

class clientcl:
    def __init__(self):
        self.packetsize=20
        self.transdelay=0.01

        self.final=''
        self.recieve_window=collections.OrderedDict()
        self.window=collections.OrderedDict()
        self.Allpackets=collections.OrderedDict()
        self.windowacks=collections.OrderedDict()
        self.thread_lock=Lock()
        self.listenack=True
        self.received_packets=0
        self.sender=tuple()
        self.receive_window_size=0
        self.window_start=0
        self.window_end=0
        self.conn=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.delay=self.transdelay+0.05
#handle acks
    def acks(self,conn,port):
        while self.listenack:
                response, sender = self.conn.recvfrom(1024)
                p = Packet.from_bytes(response)
                #self.thread_lock.acquire()
                # if packet type=4 then it is ack, removing packet from window
                if(p.packet_type==4):
                    p.packet_type=0
                    print('recieved ack for packet:',p.seq_num)
                    self.windowacks[p.seq_num]=p.payload
                 #   self.thread_lock.release()
        return

    #send packets data in Allpackets to server
    def client_send(self,conn,Allpackets,router_addr,router_port,peer_ip,server_port):
        #window size is half the number of packets
        if(len(Allpackets)>1):
            window_size=int(len(Allpackets)/2)
        else:
            window_size = len(Allpackets)
        windowcount=0
        while(len(Allpackets)!=0):
            while(len(self.window)<window_size and len(Allpackets)!=0):
                    j=0
                    windowcount=windowcount+1
                    for i in Allpackets:
                        self.window[i]=Allpackets[i]
                        j=j+1
                        if len(self.window)==window_size:
                            break
                    for i in self.window.keys():
                        del self.Allpackets[i]
                        #packet format
                        p = Packet(packet_type=0,
                                   seq_num=i,
                                   peer_ip_addr=peer_ip,
                                   peer_port=server_port,
                                   payload=bytes(self.window[i]))
                        print('sending packet:', p.seq_num)
                        self.conn.sendto(p.to_bytes(), (router_addr, router_port))
                    time.sleep(self.delay)
                    self.resend_packet(conn,router_addr, router_port,peer_ip,server_port)
                    #delay to wait for acks to arrive
                    #threading.sleep(0.5)
        print('data transmission finished')
        self.listenack=False
        p.packet_type=5
        self.conn.sendto(p.to_bytes(), (router_addr, router_port))
        return

    # def client_send(conn,Allpackets,router_addr,router_port,peer_ip,server_port):
    #     #window size is half the number of packets
    #     buff=list()
    #     if(len(Allpackets)>1):
    #         window_size=int(len(Allpackets)/2)
    #     else:
    #         window_size = len(Allpackets)
    #     windowcount=0
    #     while(len(Allpackets)!=0):
    #         while(len(window)<window_size and len(Allpackets)!=0):
    #                 j=0
    #                 windowcount=windowcount+1
    #                 for i in Allpackets:
    #                     window[j]=Allpackets[i]
    #                     j=j+1
    #                     if len(window)==window_size:
    #                         break
    #                 for i in window:
    #                     Allpackets.popitem(window[i])
    #                     #packet format
    #                     p = Packet(packet_type=0,
    #                                seq_num=i,
    #                                peer_ip_addr=peer_ip,
    #                                peer_port=server_port,
    #                                payload=bytes(window[i]))
    #                     print('sending packet:', p.seq_num)
    #                     buff.append(p.to_bytes())
    #                 conn.sendall(bytearray(buff),(router_addr, router_port))
    #                 t = threading.Timer(0.5, resend_packet,[conn,router_addr, router_port,peer_ip,server_port])
    #                 t.start()
    #                 #delay to wait for acks to arrive
    #                 #threading.sleep(0.5)
    #                 #retransmit if ack not received
    #                 #todo : add timers and retransmit when timer expires

    def resend_packet(self,conn,router_addr, router_port,peer_ip,server_port):
        while(len(self.windowacks)!=len(self.window)):
            for i in self.window:
                if not self.windowacks.keys().__contains__(i):
                    p = Packet(packet_type=0,
                            seq_num=i,
                            peer_ip_addr=peer_ip,
                            peer_port=server_port,
                            payload=bytes(self.window[i]))
                    print('retransmitting packet:', p.seq_num)
                    self.conn.sendto(p.to_bytes(), (router_addr, router_port))
            time.sleep(self.delay)
        if (len(self.windowacks) == len(self.window)):
            self.window.clear()
            self.windowacks.clear()
            return


    def handshake(self,conn,router_addr,peer_ip,server_port, router_port,len_packets):
            #packet type=1 denotes SYN initial sequence number is noted
            p = Packet(packet_type=1,
                       seq_num=0,
                       peer_ip_addr=peer_ip,
                       peer_port=server_port,
                       payload=''.encode("utf-8"))
            self.conn.sendto(p.to_bytes(), (router_addr, router_port))
            print('Sending "{}" '.format("SYN"))
            time.sleep(self.delay)
            # Try to receive a response within timeout
            # t = threading.Timer(0.5, resend_syn, [conn, router_addr, router_port, peer_ip, server_port])
            # t.start()
            print('Waiting for a response')
            response, sender = self.conn.recvfrom(1024)
            p1 = Packet.from_bytes(response)
            print('Router: ', sender)
            # server responds with packet_type=2 so we respond with packet_type=3
            #and send number of packets to expect
            if(p1.packet_type==2):
                print('Recieved SYN+ACK from server')
                p1.packet_type=3
                p1.payload=str(len_packets).encode("utf-8")
                print('Sending ACK for Handshake')
                self.conn.sendto(p1.to_bytes(),sender)
                sendData=True
            return True



    def client_receive(self,conn,router_addr,router_port,peer_ip,server_port):
        listen = True
        while listen:
            print('waiting for server to to send reply')
            data, sender = self.conn.recvfrom(1024)
            p = Packet.from_bytes(data)
            print("recevied packet type and sequence No.",p.packet_type,p.seq_num)
            if (p.packet_type ==1):
                expected_packets=int(p.payload)
                if (expected_packets > 1):
                    receive_window_size = int(expected_packets / 2)
                else:
                    receive_window_size = expected_packets
                    window_end = receive_window_size
                window_start = 0
                p.packet_type=3
                self.conn.sendto(p.to_bytes(),sender)
            elif(p.packet_type ==0):
                if (len(self.recieve_window) == receive_window_size and p.seq_num >= window_end + 1):
                    str = ''
                    for i in sorted(self.recieve_window.keys()):
                        str = str + self.recieve_window[i].payload.decode("utf-8")
                    self.final = self.final + str
                    self.recieve_window.clear()
                    window_start = window_end + 1
                    window_end = window_start + receive_window_size

                if (p.seq_num in range(window_start, window_end + 1)):
                    if (not self.recieve_window.__contains__(p.seq_num)):
                        self.recieve_window[p.seq_num] = p
                        self.received_packets += 1
                        p.packet_type = 4
                        print('sending ack for packet:', p.seq_num)
                        self.conn.sendto(p.to_bytes(), sender)
                    else:
                        p.packet_type = 4
                        print('sending ack for packet:', p.seq_num)
                        self.conn.sendto(p.to_bytes(), sender)
                # if window full combine to form msg
                if (self.received_packets == expected_packets ):
                    str = ''
                    for i in sorted(self.recieve_window.keys()):
                        str = str + self.recieve_window[i].payload.decode("utf-8")
                    self.final = self.final + str
                    p.packet_type=5
                    self.conn.sendto(p.to_bytes(), sender)
                    #print('Message received from server: ', final)
                    listen=False
                    return self.final

    def client(self,inputline,router_addr, router_port, server_addr, server_port,cli_port):
        contents=bytearray(inputline.encode())
        peer_ip = ipaddress.ip_address(socket.gethostbyname(server_addr))
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        no_packets=0
        #if size less than 1 packet then fit everything in one packet
        if(sys.getsizeof(contents)<self.packetsize):
            self.Allpackets[no_packets]=contents
            no_packets=+1
        else:
            #read 1013 bytes for each packet
            for i in range(0,sys.getsizeof(contents),self.packetsize):
                self.Allpackets[no_packets]=contents[i:i + self.packetsize]
                no_packets=no_packets+1

        self.conn.bind(('',cli_port))
        #make handshake
        if(self.handshake(self.conn,router_addr,peer_ip,server_port, router_port,len(self.Allpackets))):
            # start thread for receiving acks
            threading.Thread(target=self.acks, args=(self.conn, 1024)).start()
            #put packets into window and send to server
            self.client_send(self.conn,self.Allpackets,router_addr,router_port,peer_ip,server_port)
            return self.client_receive(self.conn,router_addr,router_port,peer_ip,server_port)
        else:
            print("Handshake unsuccessful")

parser = argparse.ArgumentParser()
parser.add_argument("--routerhost", help="router host", default="localhost")
parser.add_argument("--routerport", help="router port", type=int, default=3000)

parser.add_argument("--serverhost", help="server host", default="localhost")
parser.add_argument("--serverport", help="server port", type=int, default=8007)
args = parser.parse_args()
# a=clientcl()
# a.client('gaejgg',args.routerhost, args.routerport, args.serverhost, args.serverport,8099)
