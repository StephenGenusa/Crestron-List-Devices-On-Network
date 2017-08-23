# List Crestron Devices on All Network Interfaces #

Test via UDP or ICMP

If UDP routes are available, the -alc option uses a UDP broadcast message to locate all Crestron devices on all ipv4 subnets a computer is connected to. Shows device hostname, ipv4 address and ver info, if available in the UDP response.

If UDP is not available, if you are connecting via a VPN or router device that drops UDP packets use the -ala option along with the /24 subnet you wish to test. A ping is sent to each IP on the subnet locating all active IPs. Those IP's are tested for port 41795 and a Crestron console. If available, the device console prompt is printed.


## Example Program Usage ##

**List all Crestron devices on all PC connected subnets that respond to UDP:**
<pre>
List_Crestron_Devices -alc
</pre>

**List all Crestron devices that are active on 10.61.101.0/24 that provide a Crestron console:**
<pre>
List_Crestron_Devices -ala 10.61.101
</pre>


## ToDo ##
  - Add SSH support