extends MiniUtopiaBridgeClient

## Fake network: no parent secret ever leaves this private synthetic UI test.
var calls: Array[Dictionary] = []

func get_family_film(film_id: String) -> int:
    calls.append({"kind": "films:get", "film_id": film_id})
    return OK


func parent_review_film(
    _parent_token: String, profile_id: String,
    film_id: String, revision: String, decision: String
) -> int:
    calls.append({
        "kind": "family:film-review", "profile_id": profile_id,
        "film_id": film_id, "revision": revision, "decision": decision,
    })
    return OK
