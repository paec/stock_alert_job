import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


ADD_MORE_API_URL = os.getenv("ADD_MORE_API_URL") or "https://example.invalid/api/add-more"


def _build_add_more_endpoint_url(symbol, base_url, path_suffix=None):
    parsed_url = urlsplit(base_url)
    path = parsed_url.path
    if path_suffix:
        path = f"{path.rstrip('/')}/{path_suffix}"

    query_params = parse_qsl(parsed_url.query, keep_blank_values=True)
    query_params.append(("symbol", symbol))
    query = urlencode(query_params)
    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            path,
            query,
            parsed_url.fragment,
        )
    )


def build_add_more_url(symbol, base_url=None):
    if base_url is None:
        base_url = ADD_MORE_API_URL
    return _build_add_more_endpoint_url(symbol, base_url)


def build_add_more_status_url(symbol, base_url=None):
    if base_url is None:
        base_url = ADD_MORE_API_URL
    return _build_add_more_endpoint_url(symbol, base_url, "status")


def check_add_more_status(symbol: str, base_url=None) -> bool:
    try:
        if base_url is None:
            status_url = build_add_more_status_url(symbol)
        else:
            status_url = build_add_more_status_url(symbol, base_url)
        response = requests.get(status_url, timeout=20)
        if not 200 <= response.status_code < 300:
            print(
                f"{symbol}: add-more status API error: "
                f"{response.status_code} {response.text}"
            )
            return False

        status = response.json()
        if not isinstance(status, bool):
            raise ValueError("response JSON must be a boolean")
        return status
    except Exception as exc:
        print(f"{symbol}: add-more status check failed: {exc}")
        return False
