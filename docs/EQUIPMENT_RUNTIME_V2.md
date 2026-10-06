# Mini Utopia Equipment Runtime v2

**Track:** PLAY-01C Equipment Slot Expansion + Proper Hand Attachments

## Canonical playable slots

1. `top` — upper-body clothing
2. `bottom` — pants / lower-body clothing
3. `shoes` — footwear
4. `headwear` — hats, crowns, helmets and future head accessories
5. `weapon_main` — right-hand weapon
6. `weapon_offhand` — left-hand shield / secondary weapon
7. `backpack`
8. `wings`
9. `accessory` — chest/body charm

The old `outfit` slot remains parseable only for v1 migration. Creator UI and new runtime payloads use the nine v2 slots.

## Migration

Existing owned items are not deleted.

- a v1 `outfit_item_id` pointer migrates to `top_item_id`
- legacy equipment definitions with `slot=outfit` normalize to `slot=top`
- the historic `starter_outfit` asset keeps its stable Asset ID and starter generation seed
- existing rolled stats remain on the owned instance

## Avatar attachment contract

Shared sockets:

- `Socket_Weapon_R`
- `Socket_Weapon_L`
- `Socket_Backpack`
- `Socket_Wings`
- `Socket_Accessory`
- `Socket_Headwear`

Browser Dressing Room behavior:

- main-hand weapon is parented to the right arm and points upward/outward about 45 degrees
- offhand shield is parented to the left arm
- both therefore follow arm animation in Idle / Walk / Run / Jump
- top, bottom and shoes recolor separate body parts
- headwear sits above the stable Q-style head
- accessory sits on the chest/body rather than the face

Godot retains the same slot/socket names. Full skeleton/bone attachment is completed when the Creator payload is wired into the Godot Player Runtime.

## Starter v2 collection

- Explorer Top
- Adventure Pants
- Cloud Sneakers
- Starwood Sword
- Wood Shield
- Cloud Backpack
- Tiny Star Wings
- Portal Charm
- Soft Cap
- Tiny Crown

## Persistence contract

`CreatorCollection` owns equipment instances. Each Character owns only its `CharacterLoadout` pointers. Dressing Room and My Stuff operate on the same persisted loadout.
