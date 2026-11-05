import ipaddress

from fastapi import Request
from fastapi.routing import iter_route_contexts
from starlette.requests import HTTPConnection
from starlette.routing import Match

UNKNOWN_CLIENT_IP_ADDRESS = "unknown"


def read_client_ip_address(connection: HTTPConnection, *, trusted_proxy_addresses: frozenset[str]) -> str:
    peer_host = connection.client.host if connection.client is not None else ""
    try:
        peer_address = ipaddress.ip_address(peer_host)
    except ValueError:
        return UNKNOWN_CLIENT_IP_ADDRESS
    if str(peer_address) not in trusted_proxy_addresses:
        return str(peer_address)
    forwarded_address = connection.headers.get("x-real-ip")
    if forwarded_address is None:
        return str(peer_address)
    try:
        return str(ipaddress.ip_address(forwarded_address.strip()))
    except ValueError:
        return str(peer_address)


def find_route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None:
        return route.path
    for route_context in iter_route_contexts(request.app.router.routes) if "app" in request.scope else ():
        if route_context.path is not None and route_context.matches(request.scope)[0] == Match.FULL:
            return route_context.path
    return f"{request.method} (unrouted)"
