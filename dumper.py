#!/usr/bin/python
from __future__ import print_function

import struct
import sys
import usb.core
import usb.util
from intelhex import IntelHex

scrambleCode = (0x29, 0x52, 0x8C, 0x70)

stats = [0xff, 0x02, 0x00, 0xf5, 0xe5, 0x75, 0x03, 0x04,
         0x80, 0x05, 0xd2, 0x01, 0xe4, 0xef, 0x82, 0x83,
         0x08, 0x24, 0xc2, 0x60, 0xe0, 0x12, 0x7f, 0x34,
         0x10, 0x07, 0x22, 0x40, 0x54, 0x94, 0x30, 0x70,
         0xc0, 0xf0, 0xaf, 0xd0, 0x44, 0xa3, 0x36, 0x74,
         0x15, 0xc3, 0x09, 0x93, 0x53, 0xec, 0x48, 0x06,
         0x0a, 0x14, 0x20, 0x25, 0x50, 0x64, 0xd4, 0x16,
         0x43, 0x47, 0xd6, 0xe7, 0xea, 0x0c, 0x32, 0x3f,
         0x46, 0x90, 0xc8, 0xdf, 0x38, 0x45, 0xb4, 0xd3,
         0xfa, 0xa1, 0xc5, 0xca, 0xcc, 0xde, 0xfc, 0x0b,
         0x23, 0x37, 0x42, 0xed, 0xfb, 0x2f, 0x95, 0x55,
         0x85, 0xdc, 0x18, 0x26, 0x33, 0x7d, 0x89, 0xac,
         0xae, 0xfe, 0x0f, 0x17, 0x1b, 0x27, 0x35, 0x39,
         0x3e, 0x57, 0x78, 0x8f, 0xa9, 0xaa, 0xc1, 0xd9,
         0xdd, 0xe3, 0xf3, 0xf8, 0x0d, 0x21, 0x3b, 0x3c,
         0x73, 0x81, 0x87, 0x88, 0x8a, 0x99, 0xbf, 0xdb,
         0xf2, 0xfd, 0x1a, 0x1f, 0x31, 0x5f, 0x6c, 0x7a,
         0x7e, 0x8e, 0xbc, 0xd5, 0xd8, 0xda, 0xe9, 0xeb,
         0xee, 0xf6, 0x11, 0x1c, 0x29, 0x2d, 0x56, 0x58,
         0x7c, 0x8d, 0x91, 0x98, 0xb3, 0xb9, 0xd7, 0xe1,
         0xe6, 0xe8, 0xf9, 0x13, 0x1e, 0x28, 0x2e, 0x41,
         0x4e, 0x69, 0x79, 0x7b, 0x9e, 0x9f, 0xa0, 0xab,
         0xad, 0xcf, 0xe2, 0x0e, 0x19, 0x1d, 0x2a, 0x4b,
         0x52, 0x5b, 0x63, 0x84, 0x86, 0x8c, 0x9d, 0xa2,
         0xb1, 0xb2, 0xc4, 0x2b, 0x49, 0x4a, 0x4c, 0x4d,
         0x59, 0x61, 0x67, 0x68, 0x6b, 0x6d, 0x6e, 0x6f,
         0x77, 0x92, 0x96, 0x9a, 0xa6, 0xa8, 0xb0, 0xb5,
         0xbb, 0xc6, 0xc7, 0xc9, 0xcd, 0xd1, 0xf4, 0x2c,
         0x3a, 0x3d, 0x4f, 0x51, 0x5a, 0x5c, 0x5d, 0x5e,
         0x62, 0x65, 0x66, 0x6a, 0x71, 0x72, 0x76, 0x8b,
         0x97, 0x9b, 0x9c, 0xa4, 0xa5, 0xa7, 0xb6, 0xb7,
         0xb8, 0xba, 0xbd, 0xbe, 0xcb, 0xce, 0xf1, 0xf7]


def scramble(l):
    return [v ^ scrambleCode[i%4] for i, v in enumerate(l)]


def binStrOfList(l):
    return ''.join(chr(x) for x in l)


class WCHISP:
    def __init__(self):
        # find our device
        dev = usb.core.find(idVendor=0x4348, idProduct=0x55e0)
        if dev is None:
            raise ValueError('Device not found')

        dev.set_configuration()
        cfg = dev.get_active_configuration()
        intf = cfg[(0, 0)]

        self.epout = usb.util.find_descriptor(intf, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.epin = usb.util.find_descriptor(intf, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    def cmd(self, msg, length=64):
        self.writeb(msg)
        b = self.readb(length)
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
        v = self.cmd('\xa2\x13USB DBG CH559 & ISP' + '\0')
        self.cmd('\xbb\x00')
        return v

    def readb(self, size):
        return self.epin.read(size)

    def writeb(self, b):
        self.epout.write(b)

    def dump(self):
        # send the key
        b = '\xa6\x04' + struct.pack('BBBB', *scrambleCode)
        self.xcmd(b, 0)
        # find block of 16 0xFF at the end of the device memory
        block = [0xff] * 16
        found = False
        for address in range(0x3ff0, -1, -1):
            print('\rLooking for address 0x{:04X}'.format(address), end='')
            r = self.cmd('\xa7\16' + struct.pack('<H', address) +
                 binStrOfList(scramble(block)))
            if r == 0:
                print('\nFound 0xFF block at address 0x{:04X}'.format(address))
                found = True
                break
        if not found:
            print('\nUnable to find 0xFF block')
            return

        memdump = IntelHex()
        memdump.puts(address, binStrOfList(block))

        print('Starting flash dumping')
        base = [0xa7, 16, 0, 0]
        nTry = 0
        nBytes = 0
        for address in range(address - 1, - 1, -1):
            block[1:] = block[:-1]  # shift
            base[2:4] = address & 0xFF, address >> 8
            found = False
            for i in range(256):
                i = stats[i]
                block[0] = i
                nTry += 1
                r = self.cmd(binStrOfList(base + scramble(block)), 4)
                if r == 0:  # verification ok, we found the correct byte
                    print('{:02X} '.format(i), end='')
                    sys.stdout.flush()
                    found = True
                    nBytes += 1
                    memdump[address] = i
                    break
            if not found:
                raise ValueError('Unable to find correct '
                       'byte for address 0x{:04X}'.format(address))

        output_bin = 'out.bin'
        output_hex = 'out.hex'
        print('\nDone, writing output files {} and {}'. format(output_bin,
                                                               output_hex))
        print('Ntry = {} {:.2f}try/bytes'.format(nTry, float(nTry) / nBytes))
        memdump.tobinfile(output_bin)
        memdump.tofile(output_hex, format='hex')


isp = WCHISP()

# check chip ID and bootloader presence
if isp.info() != 0x52:
    raise IOError("not a CH552T device")

# dump flash
isp.dump()
