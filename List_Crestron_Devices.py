#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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

from __future__ import print_function
import argparse
import os
import re
import socket
import subprocess
import sys
from time import sleep
#
import netifaces


MAX_RETRIES = 3
CR = "\r"
BUFF_SIZE = 2000
CIP_PORT = 41794
BROADCAST_IP = '255.255.255.255'
FORMATTING = " " * 5

UDP_MSG = \
    "\x14\x00\x00\x00\x01\x04\x00\x03\x00\x00\x66\x65\x65\x64" + \
    ("\x00" * 252)


class CrestronDeviceFinder(object):
    def __init__(self, args):
        """
        initialize internal properties
        """
        self.active_ips_to_check = []
        self.args = args
        self.crestron_devices = {}


    def initialize_run_variables(self):
        self.console_prompt = ""


    # Print iterations progress
    def print_progress(self, iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
        """
        From https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a w/mod
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            bar_length  - Optional  : character length of bar (Int)
        """
        str_format = "{0:." + str(decimals) + "f}"
        percents = str_format.format(100 * (iteration / float(total)))
        filled_length = int(round(bar_length * iteration / float(total)))
        bar = chr(178) * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

        if iteration == total:
            sys.stdout.write('\n')
        sys.stdout.flush()


    def open_device_connection(self):
        """
        Open the device connection, attempting port 41795
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = (self.device_ip_address, 41795)
            self.sock.settimeout(2.0)
            self.sock.connect(server_address)
            return True
        except:
            pass
        return False


    def close_device_connection(self):
        """
        Close the socket
        """
        try:
            self.sock.close()
        except:
            pass


    def get_console_prompt(self):
        """
        Determine the device console prompt
        """
        data = ""
        for _unused in range(0, MAX_RETRIES):
            try:
                self.sock.sendall(CR)
                data += self.sock.recv(BUFF_SIZE)
                sleep(.25)
                search = re.findall("[\n\r]([\w-]{3,30})>", data, re.MULTILINE)
                if search:
                    self.console_prompt = search[0]
                    print("{0} \t is a {1}".format(self.device_ip_address, self.console_prompt))
                    return True
            except:
                pass
            return False


    def show_devices_using_icmp(self, subnet):
        """
        Build a list of devices that respond to ping for a /24 subnet like 17.1.6.{1}:
        """
        print ("Building list of active IP addresses on subnet {0}.0/24\nPlease wait. This will take about two minutes...".format(subnet))
        with open(os.devnull, "wb") as limbo:
            for last_octet in xrange(1, 255):
                ip = "{0}.{1}".format(subnet, last_octet)
                result=subprocess.Popen(["ping", "-n", "1", "-w", "200", ip],
                        stdout=limbo, stderr=limbo).wait()
                if not result:
                    self.active_ips_to_check.append(ip)
                self.print_progress (last_octet, 254, bar_length = 70)
            if self.active_ips_to_check:
                print("Located {0} active IPs on subnet. Now testing for console on each IP.".format(len(self.active_ips_to_check)))
                for self.device_ip_address in self.active_ips_to_check:
                    if self.open_device_connection():
                        if self.get_console_prompt():
                            print((FORMATTING + self.console_prompt + " located at " + self.device_ip_address).ljust(35))
                        self.close_device_connection()


    def show_devices_using_udp(self):
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
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    # bind the socket to the local IP:CIP_PORT
                    sock.bind((cur_ip, CIP_PORT))
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    # send the UDP message to the broadcast IP:CIP_PORT
                    sock.sendto(UDP_MSG, (BROADCAST_IP, CIP_PORT))
                    # we want an exception to end the while True: loop below, 
                    #   based on the following timeout
                    sock.settimeout(3.0)
                    try:
                        while True:
                            # get a UDP response packet and store in buffer
                            data, addr = sock.recvfrom(4096)
                            # find the device hostname in the response buffer
                            search = re.findall ('\x00([a-zA-Z0-9-]{2,30})\x00', data[9:40])
                            if search:
                                dev_name = search[0]
                                # get the ipv4 address received from sock.recvfrom()
                                dev_ip = addr[0]
                                # find if ver info is part of UDP packet
                                firmware_info = ""
                                search = re.findall ('\x00([\w].{10,80})\x00', data[265:350])
                                if search:
                                    firmware_info = search[0]
                                # add only new devices and skip our own packet
                                if dev_name not in self.crestron_devices and dev_name != "feed":
                                    print((FORMATTING + dev_name + " located at " + dev_ip).ljust(35) + \
                                          "\n" + (FORMATTING * 2) + firmware_info)
                                    # save the device to a dictionary so we don't repeat it
                                    self.crestron_devices[dev_name] = dev_ip
                    except:
                        pass
                    print()
        print("\nLocated a total of", len(self.crestron_devices), "Crestron devices")

                
    def find_devices(self):
        if self.args.autolocatecrestron:
            self.show_devices_using_udp()
        elif self.args.autolocateactiveips:
            self.show_devices_using_icmp(self.args.autolocateactiveips)
            
    
    
if __name__ == "__main__":
    # pylint: disable-msg=C0103
    print("\nStephen Genusa's Crestron Device Locator\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("-ala", "--autolocateactiveips", default="", type=str,
                    help="Automatically locate active IPs on a subnet and look for Crestron devices. \n  Example: 174.209.101 as an argument will check 174.209.101.0/24")
    parser.add_argument("-alc", "--autolocatecrestron", action="store_true",
                    help="Automatically locate Crestron devices on all connected subnets and build documentation")
    args = parser.parse_args()
    
    if not args.autolocatecrestron and not args.autolocateactiveips:
        parser.print_help()
        exit()
    
    documenter = CrestronDeviceFinder(args)
    documenter.find_devices()
