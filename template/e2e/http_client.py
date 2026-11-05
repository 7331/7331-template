from collections.abc import Mapping
from dataclasses import dataclass
from email.message import Message
import json
import urllib.error
import urllib.request

REQUEST_TIMEOUT_SECONDS = 5


@dataclass(frozen=True, kw_only=True)
class HttpReply:
    status: int
    headers: Message
    body: bytes

    def find_set_cookie_value(self, cookie_name: str) -> str | None:
        for set_cookie_header in self.headers.get_all("Set-Cookie") or []:
            name, separator, value = set_cookie_header.split(";", 1)[0].partition("=")
            if separator and name.strip() == cookie_name:
                return value.strip()
        return None


def send_http_request(
    path: str, *, api_publish_port: int, method: str, headers: Mapping[str, str], body: bytes | None
) -> HttpReply:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                f"http://127.0.0.1:{api_publish_port}{path}", data=body, headers=dict(headers), method=method
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            return HttpReply(status=response.status, headers=response.headers, body=response.read())
    except urllib.error.HTTPError as error_response:
        return HttpReply(status=error_response.code, headers=error_response.headers, body=error_response.read())


def send_json_request(
    path: str, *, api_publish_port: int, method: str, headers: Mapping[str, str], json_body: object
) -> HttpReply:
    return send_http_request(
        path,
        api_publish_port=api_publish_port,
        method=method,
        headers={**headers, "Content-Type": "application/json"},
        body=json.dumps(json_body).encode(),
    )
