#!/usr/bin/python

import usb.core
import usb.util
import sys, struct

class WCHISP:
    def __init__(self):
        # find our device
        dev = usb.core.find(idVendor=0x4348, idProduct=0x55e0)
        if dev is None:
            raise ValueError('Device not found')
        
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]
        
        self.epout = usb.util.find_descriptor(intf, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.epin = usb.util.find_descriptor(intf, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    def cmd(self, msg):
        self.writeb(msg)
        b = self.readb(64)
        if len(b) == 2:
            return struct.unpack('<H', b)[0]
        return b

    def xcmd(self, msg, exp):
        #xmsg = map(lambda x: hex(ord(x))[2:], msg)
        #print ' '.join(xmsg)
        #return 0

        ret = self.cmd(msg)
        if ret != exp: 
            xmsg = map(lambda x: hex(ord(x)), msg[0:4])
            raise Exception('cmd[%s] return %d != %d' % (','.join(xmsg), ret, exp)) 

    def info(self):
        v = self.cmd('\xa2\x13USB DBG CH559 & ISP' + '\0'*42)
        self.cmd('\xbb\x00')
        return v

    def readb(self, size):
        return self.epin.read(size)

    def writeb(self, b):
        self.epout.write(b)

    def program(self, hexfile):
        def readhex():
            lno = 0
            mem = []
            with open(hexfile, 'r') as f:
                for line in f:
                    lno += 1
                    line = line.strip()
                    if len(line)<6 or line[0] != ':': continue
                    if line[7:9] == '01': break
                    if line[7:9] != '00': 
                        raise ValueException('unknown data type @ %s:%d' % (hexfile, lno))
                    n = int(line[1:3], 16)
                    addr = int(line[3:7], 16)
                    if n + addr > len(mem): 
                        mem.extend([255] * (n+addr-len(mem)))
                    i = 9
                    while n > 0:
                        mem[addr] = int(line[i:i+2], 16)
                        i += 2
                        addr += 1
                        n -= 1
            return mem

        def wv(mode):
            if mode == '\xa7':
                print 'Verifying ',
            else:
                print 'Programming ',
            sys.stdout.flush()

            addr = 0
            while addr < len(mem):
                b = mode
                sz = len(mem) - addr
                if sz > 0x3c: sz = 0x3c
                b += struct.pack('<BH', sz, addr)
                for i in range(sz):
                    b += chr(mem[addr+i]^rand[i%4])
                self.xcmd(b, 0)
                addr += sz
                sys.stdout.write('#')
                sys.stdout.flush()
            print ''

        rand = (0x29, 0x52, 0x8C, 0x70)
        mem = readhex()
        if len(mem) < 256 or len(mem) > 16384: 
            raise "hexfile codesize %d not in (256, 16384)" % len(mem)

        b = '\xa6\x04' + struct.pack('BBBB', *rand)
        self.xcmd(b, 0)
        for page in range(0, 0x40, 4):
            b = '\xa9\x02\x00' + chr(page)
            self.xcmd(b, 0)

        wv('\xa8')

        self.cmd('\xb8\x02\xff\xf6')
        self.cmd('\xb9\x00')

        wv('\xa7')
        self.writeb('\xa5\x02\x00\x00')
        

if len(sys.argv) != 2:
    print 'wchprog hexfile'
    sys.exit(1)

isp = WCHISP()
if isp.info() != 0x52:
    raise IOException("not a CH552T device")

isp.program(sys.argv[1])

