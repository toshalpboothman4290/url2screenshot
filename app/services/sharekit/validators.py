import ipaddress
from urllib.parse import urlparse

PRIVATE_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_public_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ("http","https"):
            return False
        host = p.hostname
        if not host:
            return False
        try:
            ip = ipaddress.ip_address(host)
            for net in PRIVATE_NETS:
                if ip in net:
                    return False
        except ValueError:
            # hostname, allow
            pass
        return True
    except Exception:
        return False
