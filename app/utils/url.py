import ipaddress
from urllib.parse import urlparse


def is_allowed_gym_url(url: str) -> bool:
    """Only public http(s) hosts: blocks SSRF into loopback/private/link-local targets."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True  # a normal DNS name
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
