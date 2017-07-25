#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import print_function
from socket import *
import re
import netifaces

"""
Copyright © 2017 by Stephen Genusa

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""


BROADCAST_IP = '255.255.255.255'
CIP_PORT = 41794

crestron_devices = {}
formatting = " " * 5

UDP_MSG = \
    "\x14\x00\x00\x00\x01\x04\x00\x03\x00\x00\x66\x65\x65\x64" + \
    ("\x00" * 252)

for iface in netifaces.interfaces():
    # if interface has ipv4 address
    if netifaces.AF_INET in netifaces.ifaddresses(iface):
        # if addr attribute in interface dictionary
        if 'addr' in netifaces.ifaddresses(iface)[netifaces.AF_INET][0]:
            # get the ipv4 address
            cur_ip = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
            # tell user what we are testing
            print("Testing IP subnet", cur_ip)
            # set the UDP test up
            sock = socket(AF_INET, SOCK_DGRAM)
            sock.bind((cur_ip, CIP_PORT))
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            sock.sendto(UDP_MSG, (BROADCAST_IP, CIP_PORT))
            sock.settimeout(1.0)
            try:
                # we want a timeout exception to end the while True: loop based on timeout
                while True:
                    # get the response data
                    data, addr = sock.recvfrom(4096)
                    # find the device hostname in the response buffer
                    search = re.findall ('\x00([a-zA-Z0-9-]{2,30})\x00', data[9:40])
                    if search:
                        dev_name = search[0]
                        # get the ipv4 address taken from the sock.recvfrom function
                        dev_ip = addr[0]
                        # find if ver info is part of UDP packet
                        firmware_info = ""
                        search = re.findall ('\x00([\w].{10,80})\x00', data[265:350])
                        if search:
                            firmware_info = search[0]
                        # add only new devices and skip our own packet
                        if dev_name not in crestron_devices and dev_name != "feed":
                            print((formatting + dev_name + " located at " + dev_ip).ljust(35) + \
                                  "\n" + (formatting * 2) + firmware_info)
                            # save the device to a dictionary so we don't repeat it
                            crestron_devices[dev_name] = dev_ip
            except:
                pass
print("\nLocated a total of", len(crestron_devices), "Crestron devices")


