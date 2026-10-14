extends MiniUtopiaBridgeClient

## No network: records which private, owner-scoped route must be rechecked.
var calls: Array[String] = []

func list_family_films() -> int:
    calls.append("films:list")
    return OK

func get_family_film(film_id: String) -> int:
    calls.append("films:get:" + film_id)
    return OK

func get_character(character_id: String) -> int:
    calls.append("character:get:" + character_id)
    return OK

func get_equipment(character_id: String) -> int:
    calls.append("equipment:get:" + character_id)
    return OK
