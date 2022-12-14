from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return (None, None)

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        #Fill in start
        # Fetch the ICMP header from the IP packet
        
        # ICMP header is 8 bytes long and starts after bit 160 of the IP header (starts at byte 20)
        type, code, checksum, id, sequence = struct.unpack("bbHHh", recPacket[20:28])
        
        if type == 0 and id == ID:
            data = struct.unpack("d", recPacket[28:])[0]   # data in ICMP reply is time that ICMP request was sent
            timeDelay = timeReceived - data
            
            return (timeDelay, (type, code, checksum, id, sequence, data))
            
        #Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return (None, None)


def sendOnePing(mySocket, destAddr, ID):
# Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())

    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data  
    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details: http://sockraw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    result = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return result


def ping(host, timeout=1):
# timeout=1 means: If one second goes by without a reply from the server,
# the client assumes that either the client's ping or the server's pong is lost

    dest = gethostbyname(host)
    resps = []
    print("Pinging " + dest + " using Python:")
    print("")
    
    # Ping statistics
    maxRTT = averageRTT = packetLoss = packetReceived = 0
    minRTT = sys.maxsize

    # Calculate vars values and return them
    # Send ping requests to a server separated by approximately one second
    for i in range(0, 5):
        result = doOnePing(dest, timeout)
        resps.append(result)
        
        if result[0] != None:
            minRTT = min(minRTT, result[0])
            maxRTT = max(maxRTT, result[0])
            averageRTT += result[0]
            packetReceived += 1
        else:
            packetLoss += 1
        
        time.sleep(1)  # one second
        
    packetLoss = (packetLoss / len(resps)) * 100
    
    if packetLoss == 100:
        minRTT = 0
    else:
        averageRTT = (averageRTT / packetReceived) * 1000
        maxRTT *= 1000
        minRTT *= 1000
        
    print("{} packets transmitted, {} packets received, {:.1f}% packet loss".format(len(resps), packetReceived, packetLoss))
    print("rtt min/avg/max = {:.3f}/{:.3f}/{:.3f} ms".format(minRTT, averageRTT, maxRTT))

    return resps


if __name__ == '__main__':
    ping("google.co.il")
