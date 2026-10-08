extends SceneTree

const CHARACTER_ID := "CHAR_EQUIPMENT_SMOKE"
const BASE_URL := "http://127.0.0.1:8766"
const EXPECTED_SLOTS := [
    "top",
    "bottom",
    "shoes",
    "headwear",
    "weapon_main",
    "weapon_offhand",
    "backpack",
    "wings",
    "accessory",
]

var _request: HTTPRequest
var _sword_item_id := ""
var _phase := "get"


func _initialize() -> void:
    call_deferred("_start")


func _start() -> void:
    _request = HTTPRequest.new()
    _request.timeout = 5.0
    root.add_child(_request)
    _request.request_completed.connect(_on_request_completed)
    _get_state()


func _get_state() -> void:
    _phase = "get"
    var error := _request.request(
        BASE_URL + "/characters/%s/equipment" % CHARACTER_ID
    )
    if error != OK:
        _fail("GET equipment request could not start")


func _put_slot(item_instance_id: Variant) -> void:
    _phase = "equip" if item_instance_id != null else "unequip"
    var headers := PackedStringArray(["Content-Type: application/json"])
    var body := JSON.stringify({"item_instance_id": item_instance_id})
    var error := _request.request(
        BASE_URL + "/characters/%s/equipment/weapon_main" % CHARACTER_ID,
        headers,
        HTTPClient.METHOD_PUT,
        body
    )
    if error != OK:
        _fail("PUT equipment request could not start")


func _on_request_completed(
    result: int,
    response_code: int,
    _headers: PackedStringArray,
    body: PackedByteArray
) -> void:
    if result != HTTPRequest.RESULT_SUCCESS:
        _fail("HTTP request failed: %s" % result)
        return
    if response_code != 200:
        _fail("unexpected HTTP status: %s" % response_code)
        return

    var parsed = JSON.parse_string(body.get_string_from_utf8())
    if typeof(parsed) != TYPE_DICTIONARY:
        _fail("Equipment Bridge response is not a JSON object")
        return
    var payload: Dictionary = parsed

    if payload.get("character_id") != CHARACTER_ID:
        _fail("stable Character ID was not preserved")
        return
    if payload.get("schema_version") != "2.0":
        _fail("Equipment Bridge schema mismatch")
        return

    if _phase == "get":
        var slots: Array = payload.get("slots", [])
        if slots.size() != EXPECTED_SLOTS.size():
            _fail("nine-slot contract missing")
            return
        for slot in EXPECTED_SLOTS:
            if not slots.has(slot):
                _fail("missing equipment slot: %s" % slot)
                return

        var items: Array = payload.get("items", [])
        for raw_item in items:
            if typeof(raw_item) != TYPE_DICTIONARY:
                continue
            var item: Dictionary = raw_item
            if item.get("slot") == "weapon_main":
                _sword_item_id = String(item.get("item_instance_id", ""))
                break
        if _sword_item_id.is_empty():
            _fail("starter main-hand item missing")
            return

        var stats: Dictionary = payload.get("final_stats", {})
        if int(stats.get("hp", 0)) < 100:
            _fail("Python Core final stats missing")
            return

        _put_slot(_sword_item_id)
        return

    var loadout: Dictionary = payload.get("loadout", {})
    var runtime: Dictionary = payload.get("runtime", {})
    var equipped: Dictionary = runtime.get("equipped", {})

    if _phase == "equip":
        if loadout.get("weapon_main_item_id") != _sword_item_id:
            _fail("canonical loadout did not equip selected item")
            return
        var main_hand: Dictionary = equipped.get("weapon_main", {})
        if main_hand.get("item_instance_id") != _sword_item_id:
            _fail("runtime spec did not reflect equipped item")
            return
        _put_slot(null)
        return

    if loadout.get("weapon_main_item_id") != null:
        _fail("canonical loadout did not unequip main hand")
        return
    if equipped.has("weapon_main"):
        _fail("runtime spec kept stale unequipped main hand")
        return

    print(
        "bridge_equipment_roundtrip_smoke: PASS · "
        + "nine slots equip/unequip through Python Core"
    )
    quit(0)


func _fail(message: String) -> void:
    push_error("bridge_equipment_roundtrip_smoke: FAIL · %s" % message)
    quit(1)
