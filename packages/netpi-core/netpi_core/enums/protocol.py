from enum import Enum
class Protocol(str, Enum):
    ETHERNET = "ethernet"; ARP = "arp"; IPV4 = "ipv4"; IPV6 = "ipv6"
    TCP = "tcp"; UDP = "udp"; ICMP = "icmp"; CDP = "cdp"; LLDP = "lldp"
    DNS = "dns"; DHCP = "dhcp"; STP = "stp"; UNKNOWN = "unknown"
