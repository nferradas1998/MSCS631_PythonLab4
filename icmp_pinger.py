from socket import *
import os
import sys
import struct
import time
import select

ICMP_ECHO_REQUEST = 8

def checksum(source_bytes: bytes) -> int:
    csum = 0
    count_to = (len(source_bytes) // 2) * 2
    count = 0

    while count < count_to:
        this_val = source_bytes[count + 1] * 256 + source_bytes[count]
        csum += this_val
        csum &= 0xffffffff
        count += 2

    if count_to < len(source_bytes):
        csum += source_bytes[-1]
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum += (csum >> 16)
    answer = ~csum & 0xffff
    answer = (answer >> 8) | ((answer << 8) & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = time.time() - startedSelect

        if whatReady[0] == []:
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        ip_header = recPacket[:20]
        iph = struct.unpack("!BBHHHBBHII", ip_header)
        ttl = iph[5]

        icmp_header = recPacket[20:28]
        icmpType, code, checksum_recv, packetID, sequence = struct.unpack("!BBHHH", icmp_header)

        if icmpType == 0 and packetID == ID:  
            timeSent = struct.unpack("!d", recPacket[28:36])[0]
            rtt_ms = (timeReceived - timeSent) * 1000.0
            icmp_bytes = len(recPacket) - 20
            return f"Reply from {destAddr}: bytes={icmp_bytes} time={rtt_ms:.2f}ms TTL={ttl}"

        timeLeft -= howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    myChecksum = 0
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("!d", time.time())

    myChecksum = checksum(header + data)

    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay

def ping(host, timeout=1):
    dest = gethostbyname(host)
    print(f"Pinging {dest} using Python:\n")
    delay = doOnePing(dest, timeout)
    print(delay)
    time.sleep(1)
    return delay

if __name__ == "__main__":
    ping("uni.edu.pe", timeout=1)
