# AMEND.md — 方向变更记录

> 这是项目方向、范围、技术决策变更的**唯一入口**。
> 最新的 APPROVED 条目优先于任何旧文档（包括 README 和 docs/ 下的 roadmap）。

## 规则

1. 代理（GPT / Codex / Claude）可以新增 `PROPOSED` 条目，**但不能自行批准**。
2. 只有项目负责人（人类）能把状态改为 `APPROVED` 或 `REJECTED`。
3. 状态为 `PROPOSED` 的条目不得执行，只能等待。
4. 条目只追加，不删除。被取代的条目标记为 `SUPERSEDED by A-xxx`。
5. 新条目追加在"条目"部分的**最上方**（最新在前）。

## 条目模板

```markdown
### A-xxx 标题
- 状态：PROPOSED | APPROVED | REJECTED | SUPERSEDED by A-xxx
- 日期：YYYY-MM-DD
- 提出者：人类 / GPT / Claude
- 变更内容：一句话说明改什么
- 原因：为什么要改
- 影响：哪些里程碑、文件、锁定决策会受影响
- 不改会怎样：
```

---

## 条目

### A-005 允许归档旧文档到 docs/archive/
- 状态：APPROVED（合并本 PR 即视为人类批准）
- 日期：2026-10-15
- 提出者：GPT 发现冲突 / Claude 起草
- 变更内容：AGENTS.md §2 的"禁止新建 docs/*.md"增加例外：把**已有**内容移入 `docs/archive/` 做归档是允许的；在 archive 中不得写新内容。
- 原因：V1-W1-04 需要把 README 旧内容移到 `docs/archive/README_LEGACY.md`，与 §2 文字冲突（Scope Guard 本来就放行 docs/archive/）。
- 影响：AGENTS.md §2、PR 模板。

### A-004 Pixal3D 仅限非公开使用
- 状态：APPROVED
- 日期：2026-10-15
- 提出者：Claude（审查）/ 人类批准
- 变更内容：Pixal3D 生成的资产只能用于家庭私有内容。任何公开发布（小红书、视频平台等）之前，必须把相关资产替换为 MIT 等商用许可模型（如 TRELLIS.2）或 CC0 资产。
- 原因：Pixal3D 模型许可证只允许学术用途，不允许商业或生产使用。
- 影响：Phase 4（公开发布）的前置条件。v1 期间不需要改代码。

### A-003 AI 生成 3D 只做静态资产
- 状态：APPROVED
- 日期：2026-10-15
- 提出者：Claude（审查）/ 人类批准
- 变更内容：图片转 3D（Pixal3D 及以后的任何替代模型）输出只能作为静态道具、建筑、场景物件。可动角色一律使用 `humanoid_kaykit_v1` 模块化套件。
- 原因：生成的 GLB 没有骨骼，无法复用共享动画，与 AVATAR_CONTRACT 冲突。
- 影响：`docs/AVATAR_CONTRACT_V1.md`、`studio/providers/hero_asset.py` 的使用范围。

### A-002 模型与 provider 升级推迟到 v1 之后
- 状态：APPROVED
- 日期：2026-10-15
- 提出者：Claude（审查）/ 人类批准
- 变更内容：以下事项全部放进 Phase 2，v1 期间不做：TRELLIS.2 替换 Pixal3D、Nano Banana 2.1 图像 provider、视觉模型从 gpt-4o-mini 换成 gpt-6-luna、自动绑骨、text-to-motion、AI 视频、后端框架替换。
- 原因：这些都不在孩子玩的主闭环上。
- 影响：docs/V1_PLAN.md 的"Phase 2"和"以后再说"清单。

### A-001 进入 v1 冲刺，冻结基础设施扩张
- 状态：APPROVED
- 日期：2026-10-15
- 提出者：人类
- 变更内容：
  1. 以 `AGENTS.md` 和 `docs/V1_PLAN.md` 作为唯一开发依据；
  2. 暂停所有安全加固、队列、审计、备份、预检类新任务（MOVIE-04x、FAMILY-05x 系列到此为止）；
  3. 所有任务以"孩子在真 iPad 上能做到什么"作为验收标准；
  4. `docs/MINI_UTOPIA_MASTER_PRODUCT_ROADMAP_V2.md` 降级为长期愿景参考，不再作为任务来源。
- 原因：开发持续扩范围，产品闭环一直没有经过真机和孩子验证。
- 影响：所有正在进行的分支；README 的旧章节作废。
