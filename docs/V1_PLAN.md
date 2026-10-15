# Mini Utopia — V1 计划（唯一任务来源）

> 规则见 `AGENTS.md`，方向变更见 `AMEND.md`。
> **代理只能从本文件的"本周任务"中领取任务。**
> 状态：⬜ 未开始 · 🟡 进行中 · ✅ 完成 · ⏸ 暂停

---

## 1. 产品一句话

孩子在 iPad 上创造自己的角色，进入迷你世界玩耍，并当导演拍出带声音的短片。家长负责审核与导出。

---

## 2. 系统框架（当前，已锁定）

```text
┌──────────── iPad Safari / Mac 浏览器 ────────────┐
│  Godot 4.7.2 Web（儿童 UI + 实时 3D 渲染）        │
│  角色创建 · 衣柜 · 村子 · 导演台 · 我的电影        │
└───────────────┬──────────────────────────────────┘
                │ HTTPS（Caddy，同源）
┌───────────────▼──────────────────────────────────┐
│  Python Core（studio/）                           │
│  family_api · 角色/装备/道具/影片草稿 · SQLite    │
│  家长审核 · 渲染队列                              │
└───────────────┬──────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────┐
│  渲染 Worker：Godot（xvfb）逐帧 → FFmpeg → 私有 MP4 │
└──────────────────────────────────────────────────┘

离线素材管线（开发者使用，不在儿童闭环里）：
gpt-image-2 概念图 → 视觉框选 → Pixal3D → 静态 GLB（见 AMEND A-003）
CC0 套件：KayKit / Kenney / Quaternius
```

---

## 3. 阶段总览

| 阶段 | 名称 | 目标 | 状态 |
|---|---|---|---|
| Phase 0 | 治理与对齐 | AGENTS.md / AMEND.md / V1_PLAN.md 上线，停止跑偏 | 🟡 本 PR |
| **Phase 1** | **v1 冲刺（4 周）** | 两个孩子在真 iPad 上跑通完整闭环 | ⬜ |
| Phase 2 | 素材与模型升级 | 用更好的模型提升素材质量和产出速度 | ⏸ 等 v1 |
| Phase 3 | 玩法扩展 | 宠物/宝宝、稀有度、任务、更多世界（参考 Roadmap v2） | ⏸ |
| Phase 4 | 公开发布 | 短视频平台内容，需完成许可证清理（AMEND A-004） | ⏸ |

**进入下一阶段的条件：** 上一阶段的"完成标准"全部打勾，且人类在 AMEND.md 中批准。

---

## 4. 已完成的能力（截至 2026-10-15，勿重复开发）

- ✅ Godot 角色创建：物种/体型/颜色/眼睛/发型/动画预览（GODOT-CC01–05）
- ✅ 九槽位装备、衣柜、即时预览；孩子自制 3D 道具（GODOT-EQ01、CREATOR-01/02）
- ✅ 新手村可玩，iPad 触控移动与镜头（CLOUD-02、PLAY-01）
- ✅ 两个孩子独立档案、云端保存、30 分钟会话（FAMILY-01/02）
- ✅ 导演台：两个英雄同框、镜头/动作、15/30 秒剪辑、保存草稿（DIRECTOR-01/02）
- ✅ 字幕：预设安全字幕可用于预览和 MP4（DIRECTOR-03a）
- ✅ 私有 MP4 渲染、家长审核/发布/撤销、渲染队列（MOVIE-01–04）
- ✅ HTTPS 私有部署包、备份恢复（FAMILY-03/05）
- ❌ **成片没有任何声音**（没有音乐、音效、配音）
- ❌ **尚未在真 iPad 上让孩子完整试玩过**

---

## 5. Phase 1：v1 冲刺

### v1 完成标准（全部打勾才算 v1 完成）

- [ ] 孩子 A、孩子 B 各自在**真 iPad Safari** 上独立完成下面整条闭环，过程中不需要大人帮忙操作
- [ ] 建角色 → 换装 → 装备道具 → 保存
- [ ] 进村子：移动、跳、互动，退出后角色不丢
- [ ] 进导演台：选两个角色、选镜头和动作、加字幕，拍 15–30 秒
- [ ] 成片有**背景音乐 + 至少一句孩子的声音**
- [ ] 家长在 iPad 上审核并下载 MP4，MP4 在相册里能正常播放
- [ ] 重启服务器后，角色、衣服、影片都还在
- [ ] 孩子界面里看不到任何代码、localhost、技术提示

---

### W1：真机验收 + 修 bug（不加新功能）

**交付物：** 一份真机试玩记录 + 修掉阻断闭环的 bug

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| V1-W1-01 | 部署到家庭服务器，Mac + iPad 都能打开 | iPad Safari 通过 HTTPS 打开游戏，能登录孩子档案 | ⬜ |
| V1-W1-02 | 按 §6 清单完成第一次真机试玩，记录到 §7 | §7 至少 1 条完整记录 | ⬜ |
| V1-W1-03 | 修复试玩中**阻断闭环**的问题（每个问题一个 PR） | 闭环能从头走到尾 | 🟡 |
| V1-W1-04 | 重写 README：只保留项目介绍、当前架构、本地运行、文档地图，旧内容移到 `docs/archive/README_LEGACY.md` | README < 200 行，与 §2 一致 | ✅ 51 行 README + 历史归档，CI 已通过 |

**不做：** 任何新功能、性能优化、安全加固。

---

### W1.5：视觉与可玩性冲刺（AMEND A-010，方向锁定，优先于 W2–W4）

**交付物：** 孩子第一眼就觉得"好看、想玩"，并且能自己建角色进村子走走

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| V1-W15-01 | 展示村子：≥20 栋 KayKit 房子 + 15 个不同 KayKit NPC，NPC 有待机/闲逛动画，所有物体都有碰撞，不能穿模 | iPad 截图：俯视 + 第三人称两张；玩家撞房子、撞 NPC 都会被挡住 | ✅ |
| V1-W15-02 | UI 整体换风格：以 Logo 为基准的马卡龙方块玩具风，统一首页、角色库、Creator、村子 HUD、导演台；首页放 Logo | 每个界面一张 iPad 截图，风格统一，不再有灰色开发者界面 | ⬜ |
| V1-W15-03 | 建角色 → 进村：孩子自己建角色、命名、保存，直接进村子行走；孩子界面不出现任何技术文字，家长登录收进家长入口 | iPad 上 3 次点按以内从首页进到 Creator；保存后一次点按进村子 | ✅ Lane C CI 全绿＋1180×820 截图已生成；等三 Lane 集成后真 iPad 验收 |

**顺序：** 01 → 02 → 03，可以在不冲突的部分并行。
**不做：** 声音、录音、新玩法、战斗、任务系统、安全加固。

---

### W2：声音（⏸ 暂停，见 AMEND A-010）

**交付物：** 带音轨的 MP4

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| V1-W2-01 | 背景音乐：内置 3–5 首 CC0 音乐，导演台可选，混入 MP4 | ffprobe 检测到音轨；iPad 播放有音乐 | 🟡 #385 三首音乐、#388 AAC、#389 worker 已合并；选曲 UI #386 受 §9.2 阻断，iPad 待验收 |
| V1-W2-02 | 孩子录音：每个镜头可录一句话（≤10 秒），保存为私有音频，按时间线混入 MP4 | 成片里能听到孩子的声音，与对应镜头对齐 | 🟡 #391 元数据政策已合并；当前单镜头 9s Safari 录音 → owner 私有上传/FFprobe → 家长重新审核 → AAC MP4 开发中，真实 iPad 尚未验收 |
| V1-W2-03 | 预览时也能听到音乐和录音 | 导演台预览有声音 | 🟡 #390 点击播放 helper 已合并，Director 接线依赖 #386；录音预览尚未实现 |

**实现提示：** 优先评估 Godot Movie Maker（`--write-movie`，可同时输出音频）；如果不适合现有逐帧管线，就用 FFmpeg 在合成步骤混音（`-c:a aac`）。录音文件与 MP4 一样默认私有。
**不做：** TTS、声音克隆、音效编辑器、AI 配乐。

---

### W3：孩子反馈打磨

**交付物：** 第二次试玩记录 + 修掉前 5 个体验问题

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| V1-W3-01 | 第二次真机试玩，记录到 §7 | 有记录 | ⬜ |
| V1-W3-02 | 从 §7 选出"孩子卡住/觉得无聊"的前 5 个问题，逐个修复 | 每个问题一个小 PR | ⬜ |

---

### W4：内容扩充

**交付物：** 孩子有更多东西可以玩、可以拍

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| V1-W4-01 | 新增 1 个可拍片的世界场景（使用现有 CC0 套件） | 导演台可以选择这个场景 | ⬜ |
| V1-W4-02 | 新增 5 个导演动作/动画（Quaternius 等 CC0 动画库，重定向到 `humanoid_kaykit_v1`） | 导演台可选，成片中正确播放 | ⬜ |
| V1-W4-03 | 新增 5 件装备/衣服 | 衣柜里可以穿，游戏和成片里都显示 | ⬜ |
| V1-W4-04 | v1 验收：完成 §5 完成标准全部打勾 | 人类在 AMEND.md 记录"v1 完成" | ⬜ |

---

## 6. 真机试玩清单（每次试玩照着做）

```text
设备：iPad 型号 / iPadOS 版本 / Safari
孩子：A / B
1. 打开网址 → 进入孩子档案（是否顺利？）
2. 建一个新角色 → 换物种、颜色、发型（孩子能自己完成吗？）
3. 换衣服 + 装备一个道具 → 保存
4. 进村子 → 走、跳、互动 → 退出（角色还在吗？）
5. 导演台 → 选两个角色 → 选镜头和动作 → 加字幕 → 录音 → 保存
6. 家长审核 → 渲染 → 下载 MP4 → 在相册播放
7. 记录：卡住的地方、孩子主动想玩的地方、孩子说的原话
```

---

## 7. 孩子试玩记录

| 日期 | 孩子 | 设备 | 卡在哪 | 觉得好玩的地方 | 孩子原话 | 转成任务 |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 8. 本周任务（代理只从这里领任务）

```text
当前：W1.5 视觉与可玩性冲刺（AMEND A-010，方向锁定）
暂停：W2 全部（#386 不合并）
三个 Codex 并行，各自只做自己的通道（Lane），只改自己负责的文件
完成 W1.5 三项后：通知负责人用 iPad 复测，负责人认可后才能恢复 W2
```

### 8.1 并行通道与文件所有权（W1.5 期间生效）

| 通道 | 任务 | 只能改这些文件 |
|---|---|---|
| **Lane A 村子** | V1-W15-01 展示村子（#394 进行中） | `godot/scripts/village.gd`、`kaykit_village_npc.gd`、`camera_rig.gd`、`player.gd`、`touch_controls.gd`、`newbie_village*.gd`、`godot/scenes/newbie_village*.tscn`、`godot/scenes/player.tscn`、**`godot/assets/kaykit/**`（所有新 3D 素材统一由 Lane A 入库）**、`tools/` 下的素材准备脚本、`godot/tests/village_*`、`godot/tests/lane_a_*` |
| **Lane B UI 风格** | V1-W15-02 UI 换风格 | `godot/ui/theme/**`（新建：全局 Theme、StyleBox、配色）、`godot/assets/ui/**`（新建：Logo 副本、图标、按钮贴图）、`godot/assets/fonts/**`（标题字体）、`godot/project.godot` 里的 theme 配置、`godot/scenes/main.tscn`（首页）、`godot/scenes/director_stage.tscn`、`godot/scripts/director_stage.gd`（只改界面部分）、`godot/tests/lane_b_*` |
| **Lane C 建角色进村** | V1-W15-03 建角色 → 进村 | `godot/scenes/character_creator.tscn`、`godot/scenes/family_hero_library.tscn`、`godot/scripts/character_creator_shell.gd`、`creator_avatar_stage.gd`、`creator_avatar_catalog.gd`、`kaykit_avatar_v1.gd`、`family_hero_library.gd`、`bridge_client.gd`、`family_character_play_adapter.gd`、`hero_runtime_loader.gd`、`creator_play_runtime.gd`、`studio/family_api.py`（只在必要时）、`godot/tests/creator_*`、`godot/tests/lane_c_*` |

**共同规则：**
1. 不在自己通道里的文件**一律不改**。确实需要改别人的文件时，在 PR 描述里写"需要 Lane X 配合：___"，然后停下等对方处理，不要自己动手。
2. **Lane B 负责定义外观，Lane A 和 Lane C 负责使用。** Lane B 把风格做成 Godot 全局 Theme（`project.godot` 里的 theme），所有 Control 节点自动继承。Lane A 和 Lane C 不在自己的文件里写死颜色、字体或 StyleBox；已有的写死样式在各自文件里删掉，让全局 Theme 生效。
3. 村子 HUD（`village.gd` 里的界面）由 Lane A 改，等 Lane B 的 Theme 合并后，Lane A 只做"套用 Theme"的小改动。
4. 素材：Lane C 需要新角色或部件素材时，告诉 Lane A 入库，自己不直接往 `godot/assets/kaykit/` 放文件。
5. 共享文件：`docs/V1_PLAN.md` 只更新自己那一行的状态；`godot/THIRD_PARTY_NOTICES.md` 只追加、不改别人写的内容。合并前先 rebase 最新 main。
6. 谁都不改：`AGENTS.md`、`AMEND.md`、`tools/scope_guard.py`、`.github/workflows/`。需要改时交给负责人。
7. 每条通道每天各自最多合并 15 个 PR（互不占用，见 AMEND A-011）。全力推进，不需要保守。PR 标题用任务 ID 开头（V1-W15-01/02/03）。
8. 每个 PR 都要附上 1180×820 iPad 截图；自己通道完成后，在 PR 里通知负责人。

**W1 家长设备预检（非孩子试玩记录，不能替代 §7）：** Mac Safari 与 iPhone Safari/Chrome 已在家庭 HTTPS 下加载游戏，直接 POST Child B 的家庭 API 返回 HTTP 201；Godot 家长解锁页面显示 `Parent unlock could not start` / `Parent unlock denied`。项目负责人明确要求允许 8 位家长口令。记录为 V1-W1-03 的单项阻断修复；真 iPad 验收及粘贴体验后续独立记录。

---

## 9. Phase 2 及以后（现在不做，见 AMEND A-002）

| 项目 | 说明 |
|---|---|
| TRELLIS.2 替换 Pixal3D | MIT 许可、PBR 材质；同时解决 A-004 的许可证问题 |
| Nano Banana 2.1 图像 provider | 多参考图、多角色一致性，用于角色设定图和分镜 |
| 视觉模型换成 gpt-6-luna | 先验证是否支持图像输入 |
| Tripo P1 低多边形 / UniRig 自动绑骨 | 仅用于"会动的生物/宠物"，需新 AMEND |
| HY-Motion 等 text-to-motion | 扩充导演动作库 |
| Phantom Camera / Dialogic 2 插件 | 评估替换自写镜头和对白系统 |
| TTS | 角色配音（不克隆孩子声音） |
| AI 视频（Veo / Kling） | 只考虑做可选特效后期，儿童影像不得上传 |

---

## 10. 以后再说（代理发现的范围外问题写在这里）

| 日期 | 发现者 | 问题 | 建议 |
|---|---|---|---|
| | | | |
