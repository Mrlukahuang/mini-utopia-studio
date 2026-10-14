# AGENTS.md — Mini Utopia 开发总规则

> 本文件适用于所有 AI 编码代理：GPT / Codex / Claude Code / 其他工具。
> **每次开工前必须先读完本文件。** 本文件与其他任何文档冲突时，以本文件为准。

---

## 0. 开工必读顺序（不可跳过）

1. `AGENTS.md`（本文件）：规则
2. `docs/V1_PLAN.md`：当前阶段、里程碑、交付要求、本周任务
3. `AMEND.md`：所有已批准的方向变更。**最新条目优先于任何旧文档**
4. 只有在任务需要时，才读具体技术文档（见 §6 文档地图）

开工第一条回复必须用 3–5 行说明以下内容，**等人确认后再写代码**：

```text
任务 ID：
对应 V1_PLAN 里程碑：
将修改的文件：
验收标准（孩子在 iPad 上能看到/做到什么）：
明确不做的事：
```

---

## 1. 项目当前阶段

**Phase 1：v1 冲刺（Family Playable v1）**

v1 只有一个目标：两个孩子在**真 iPad Safari** 上完成完整闭环：

```text
建角色 → 换装/道具 → 进村子玩 → 导演 15–30 秒短片（有画面 + 字幕 + 声音）→ 家长审核并导出 MP4
```

不在这条闭环上的工作，都不是现在要做的事。

---

## 2. 禁止事项（除非任务或 AMEND.md 明确批准）

- ❌ 新增安全加固、权限、审计、撤销、队列、备份、预检类功能（现有实现已足够家庭使用）
- ❌ 把一个任务拆成 a/b/c/d/e 多个子 PR 连续推进
- ❌ 新建 `docs/*.md` 文档（只允许更新 `docs/V1_PLAN.md`、`AMEND.md` 和本文件；例外：把旧内容**移入** `docs/archive/` 做归档，见 AMEND A-005）
- ❌ 新增 AI provider、更换模型、引入新框架、换后端或数据库
- ❌ 重构不在本任务路径上的代码
- ❌ 为凑覆盖率写测试；为"以防万一"加防御代码
- ❌ 自己决定下一个任务。下一个任务只能来自 `docs/V1_PLAN.md` 的"本周任务"
- ❌ 改变 §5 中的锁定技术决策

发现范围外的问题时**不要顺手修**，写进 `docs/V1_PLAN.md` 的"以后再说"清单即可。

---

## 3. 每个任务的交付要求

- 1 个任务 = 1 个分支 = 1 个 PR
- 改动规模目标 < 500 行（不含资源文件）。超过 800 行的 PR 必须先拆分或在 AMEND.md 中说明理由
- 测试：只写 1–3 个关键 smoke test，证明功能可用
- PR 描述必须使用 `.github/pull_request_template.md`，并填写：
  - **孩子可见变化**：孩子在 iPad 上能看到或做到的变化是 ___
  - 如果答案是"没有"，这个任务就不应该做（纯文档、修 CI 除外）
- 完成后更新 `docs/V1_PLAN.md` 里对应任务的状态（⬜ → ✅）

---

## 4. 方向变更流程（防跑偏核心）

**任何**以下情况都不能直接写代码，必须先在 `AMEND.md` 新增一条 `PROPOSED` 条目，由项目负责人（人类）改为 `APPROVED` 后才能执行：

- 新增或删除里程碑、改变 v1 范围
- 更换模型、provider、引擎、后端、存储
- 新增顶层目录、新的子系统或服务
- 推翻 §5 中任何锁定决策
- 代理认为"计划有问题，应该换个做法"

代理**不得**自行把 AMEND 条目改为 APPROVED。

---

## 5. 锁定技术决策（改动需 AMEND）

| 领域 | 决策 |
|---|---|
| 引擎 | Godot 4.7.2；Web 导出；Compatibility 渲染；单线程 Web 模板 |
| 儿童 UI 与实时渲染 | 只在 Godot 中实现 |
| 数据真相源 | Python Core + SQLite（`studio/`），通过 family API 访问 |
| Streamlit | 只做家长/制作人查看，冻结编辑功能 |
| 角色 | 共享人形骨骼 `humanoid_kaykit_v1` + 模块化外观（见 `docs/AVATAR_CONTRACT_V1.md`） |
| AI 生成 3D | **只能作为静态道具、建筑、场景物件**，不能作为可动角色 |
| 成片 | Godot 渲染 + FFmpeg 合成 MP4。不使用 AI 视频模型生成主画面 |
| 隐私 | 儿童内容默认私有；不在客户端、CI、公开产物中出现儿童数据或 API key |
| 美术 | 优先使用 CC0 素材（KayKit / Kenney / Quaternius）；付费模型调用需事先批准 |
| AI provider | 必须通过 `studio/providers/` 抽象层接入，业务代码不得直接调用厂商 SDK |

---

## 6. 文档地图

| 需要了解 | 读这个 |
|---|---|
| 当前计划和任务 | `docs/V1_PLAN.md` |
| 方向变更记录 | `AMEND.md` |
| 角色骨骼/外观合同 | `docs/AVATAR_CONTRACT_V1.md` |
| 装备系统 | `docs/EQUIPMENT_RUNTIME_V2.md` |
| 家庭 API | `docs/FAMILY_PRIVATE_API_V1.md` |
| 村子基线 | `docs/WORLD_BASELINE_NEWBIE_VILLAGE_V1.md` |
| 美术风格 | `docs/MINI_UTOPIA_VISUAL_DNA_v1.md`、`docs/MINI_UTOPIA_BRAND_CANON_V1.md` |
| 长期产品愿景（**仅参考，不是当前任务来源**） | `docs/MINI_UTOPIA_MASTER_PRODUCT_ROADMAP_V2.md` |

`README.md` 的旧章节可能已过时，不得作为任务依据。

---

## 7. 常用命令

```bash
pip install -r requirements.txt
pytest -q                       # Python 测试
# Godot 测试与 Web 导出由 GitHub Actions 执行（.github/workflows/）
```

---

## 8. 代理自检（提交 PR 前逐条确认）

- [ ] 这个任务在 `docs/V1_PLAN.md` 的本周任务里吗？
- [ ] 我有没有做任务以外的事？
- [ ] 我有没有新建文档、新增 provider、改锁定决策？（有 → 撤回，或先写 AMEND）
- [ ] PR 里写了"孩子可见变化"吗？
- [ ] V1_PLAN 里的任务状态更新了吗？
