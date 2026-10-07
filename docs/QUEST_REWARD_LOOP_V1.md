# GP-05 · Generic Quest Loot & Reward Loop

GP-05 makes Quest completion rewards durable Creator data instead of
hardcoded enemy loot.

## Trust boundary

Godot does **not** author item rarity or stats.

When a Quest completes, Godot writes only a completion receipt:

- completion_id
- quest_id
- session_id
- character_asset_id
- created_at

Creator reloads the persisted QuestDefinition and executes its rewards from the
canonical repository.

## Equipment reward data

An equipment QuestReward uses:

- `target_id` = stable Equipment Asset slug
- `metadata.rarity`
- `metadata.item_level`
- `amount`

The owned EquipmentInstance is created by the existing deterministic rarity /
power-budget system.

Generation seed:

`QUEST_REWARD::<claim_id>`

This keeps rolled HP / ATK / DEF reproducible.

## Idempotency

CreatorCollection adds the backward-compatible field:

`claimed_quest_reward_ids[]`

For a non-repeatable Quest, a reward claim is keyed by Quest + reward, so a
second PlaySession cannot farm it accidentally.

For a repeatable Quest, the completion receipt ID is part of the claim key, so
each legitimate completion may reward again.

Legacy `claimed_drop_ids` stays unchanged for PLAY-03 combat receipts.

## First reward proof

Story-generated playable Quests now include:

**🟣 Portal Medal / 传送门勋章**

- slot: Accessory
- rarity: Purple
- reward-only (not in the starter recipes)
- deterministic stats
- appears in My Stuff only after the Quest completion receipt is claimed

My Stuff claims Quest rewards on entry and shows a visible **Quest Reward /
任务奖励** banner.

## Reserved rewards

`baby_xp`, `baby_bond`, and `unlock` remain in the same Quest reward
contract. GP-05 deliberately leaves those receipts unconsumed. BB-02 will
execute Baby progression from the same completion receipt without inventing a
second Quest system.
