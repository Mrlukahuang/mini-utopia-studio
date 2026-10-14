class_name MiniUtopiaBridgeEndpointPolicy
extends RefCounted

## One transport rule for both desktop and browser clients.
## Web builds MUST NOT talk to a child's local loopback server.
## Only a separately provisioned HTTPS family API may be used in Web.
## Authentication and family ownership are separate server-side concerns.

const DESKTOP_LOOPBACK_URL := "http://127.0.0.1:8765"


static func normalize(raw_url: String, web_mode: bool) -> String:
    var url := raw_url.strip_edges()
    if url.is_empty():
        return "" if web_mode else DESKTOP_LOOPBACK_URL

    while url.ends_with("/"):
        url = url.left(url.length() - 1)

    # No embedded credentials, query strings, fragments, whitespace or
    # insecure remote HTTP endpoints. Reject malformed URLs closed.
    var scheme_end := url.find("://")
    if scheme_end <= 0:
        return ""
    var scheme := url.substr(0, scheme_end).to_lower()
    if scheme != "https" and scheme != "http":
        return ""
    if web_mode and scheme != "https":
        return ""

    var rest := url.substr(scheme_end + 3)
    var authority := rest.get_slice("/", 0).to_lower()
    if authority.is_empty() or authority.contains("@"):
        return ""
    if authority.contains("?") or authority.contains("#"):
        return ""
    if url.contains("?") or url.contains("#") or url.contains(" "):
        return ""

    # Native HTTP is allowed ONLY for local development.
    if scheme == "http" and not (
        authority == "127.0.0.1"
        or authority == "localhost"
        or authority.begins_with("127.0.0.1:")
        or authority.begins_with("localhost:")
        or authority == "[::1]"
        or authority.begins_with("[::1]:")
    ):
        return ""

    return url


static func is_configured(url: String) -> bool:
    return not url.is_empty()
