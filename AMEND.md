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

### A-006 家庭 MacBook 无域名、仅局域网 HTTPS 部署（V1-W1-01）
- 状态：PROPOSED
- 日期：2026-10-15
- 提出者：GPT（根据项目负责人的 MacBook Air 15-inch M5／无域名／仅家庭 Wi-Fi 要求）
- 变更内容：提议把 V1-W1-01 的“公网域名 + Caddy 公网证书”部署方式，针对家庭试用改为 **方案 A：MacBook Air 上的 Caddy 内部 CA（`tls internal`）+ 固定私网 IPv4 地址 + iPad/Mac 显式信任该家庭 CA**。Godot Web、Python Core + SQLite、家长审核与 Godot/FFmpeg 成片技术栈不变。HTTPS 同源加载游戏和 API；不购买域名、不对公网开放、不设置路由器端口转发。只允许批准的家庭 LAN 接口提供访问，家长必须单独确认 LAN 端口开放、证书安装、密钥初始化及任何付费操作。
- 原因：当前家庭没有域名，只在家中同一 Wi-Fi 使用；计划 W2 的 iPad Safari 录音需要可信 HTTPS 安全上下文及麦克风许可，不能以普通 `http://192.168.x.x` 替代。
- 影响：V1-W1-01 的部署步骤；获批后预计仅调整现有 `deploy/family/Caddyfile`、`deploy/family/compose.yaml`、`deploy/family/.env.example`、`deploy/family/README.md` 及现有部署检查中强制公网域名的假设（具体文件修改仍要先提交对应任务计划并逐项授权）。需给 MacBook 在路由器分配固定私网地址，限制 Docker 端口仅绑定批准的家庭 LAN IP，建立并持久保存 Caddy CA，向家庭自有 iPad 和 Mac 安装**仅根证书公钥**并显式信任，验证 Safari 无证书警告、同源登录及 `isSecureContext` / 录音授权；真实私有电影和密钥仍不得进入 GitHub。MacBook 须插电、保持开机且不自动睡眠；真机渲染对 Apple Silicon M5 的兼容性需单独验收。
- 备选方案（尚未批准）：**方案 B：Tailscale Serve + 自动可信的 `*.ts.net` HTTPS**；不用购买个人域名，也不用在家用路由器做公网端口转发或在 iPad 安装自建根 CA，但需要 Tailscale 账户、Mac/iPad 安装客户端、MagicDNS、HTTPS 证书和授权；设备名可能公开在证书透明度日志中，并且 tailnet 连接有可能在外网使用，与“严格仅家庭 Wi-Fi”不是同一约束。方案 B **不得因本条获批而自动执行**；如改选 B，必须另外提出具体 AMEND、获人类批准后才可实施，且不得开启 Funnel。
- 不改会怎样：现有 `FAMILY_DOMAIN`、Caddy 公网 DNS/证书及离线预检都假设真实域名，现有 Compose 还默认映射主机所有接口的 80/443；直接按原部署说明无法满足无域名、仅家庭 LAN、iPad 可信 HTTPS 和后续浏览器录音要求。V1-W1-01 继续保持未完成，直到人类批准方案并在真 iPad 上验收。

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
