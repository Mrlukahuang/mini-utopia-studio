extends SceneTree

## No cloud credentials are needed to prove that the exported browser does
## not contact its own localhost. Native and Web rules are tested separately.

func _initialize() -> void:
    if MiniUtopiaBridgeEndpointPolicy.normalize("", true) != "":
        _fail("Web cannot fall back to localhost")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("http://127.0.0.1:8765", true) != "":
        _fail("Web must reject loopback HTTP")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("http://localhost:8765", true) != "":
        _fail("Web must reject localhost HTTP")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("http://family.example.com", true) != "":
        _fail("Web must reject unencrypted remote HTTP")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("https://family.example.com/", true) != "https://family.example.com":
        _fail("Web should accept an HTTPS family service")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("https://name:secret@family.example.com", true) != "":
        _fail("Credentials must not be embedded in the URL")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("https://family.example.com?token=secret", true) != "":
        _fail("Credentials in query strings must be rejected")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("https://family.example.com/#private", true) != "":
        _fail("Fragments are unsupported")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("", false) != MiniUtopiaBridgeEndpointPolicy.DESKTOP_LOOPBACK_URL:
        _fail("Desktop development still needs the local Bridge")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("http://127.0.0.1:8765/", false) != MiniUtopiaBridgeEndpointPolicy.DESKTOP_LOOPBACK_URL:
        _fail("Local desktop loopback should be supported")
        return
    if MiniUtopiaBridgeEndpointPolicy.normalize("http://192.168.1.50:8765", false) != "":
        _fail("Native client must reject insecure LAN HTTP")
        return

    print("bridge_endpoint_policy_smoke: PASS · safe Web/Desktop transports")
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_endpoint_policy_smoke: FAIL · " + message)
    quit(1)
