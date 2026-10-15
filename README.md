# Mini Utopia · Family Playable v1

**阶段：Phase 1 — Family Playable v1（W1 真机验收与阻断修复）。**
孩子在真实 iPad Safari 中完成：创建角色 → 换装与装备 → 进入村子 → 拍摄 15–30 秒短片（字幕、声音）→ 家长审核并导出私人 MP4。**真机验收和声音仍有未完成项；CI 通过不等于 v1 已完成。**

开发代理请依序阅读 [AGENTS.md](AGENTS.md) → [docs/V1_PLAN.md](docs/V1_PLAN.md) → [AMEND.md](AMEND.md)。此三份文件是当前任务和变更规则依据；较早的产品规划和旧 README 不能代替它们。

## 当前架构

| 层 | 作用 |
| --- | --- |
| **Godot 4.7.2 Web** | iPad Safari 儿童界面、3D 角色、衣柜、新手村、导演台和影片列表（Compatibility / 单线程 Web） |
| **Python Core + SQLite** | `studio/`、家庭私有 API、角色/装备/电影草稿、家长审核与队列 |
| **渲染 Worker + FFmpeg** | Godot 逐帧渲染和私有 MP4 合成；音乐/录音属于 W2 任务 |
| **家庭局域网 HTTPS** | `deploy/family/` 使用 Caddy 内部 CA；仅家中 Wi-Fi，非公开服务 |
| **素材** | 授权 CC0 KayKit / Kenney / Quaternius 等，角色共用 `humanoid_kaykit_v1` 合同 |

本仓库不是公开在线游戏托管。勿上传家庭密钥、真实儿童内容或私有 MP4。现有家长审核与私有存储不能被 Web 客户端绕过。

## 本地开发与测试

依赖见 `requirements.txt`，推荐 Python 3.12/3.14，Godot 版本锁定 **4.7.2**。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Godot 项目位于 `godot/`；打开 `godot/project.godot` 可运行项目。Godot 解析、smoke tests、Web 导出和 Playwright iPad 分辨率截图由 GitHub Actions 验证；本地 Godot 和 CI 不能代替真 iPad Safari 试玩。

**家庭 Mac 部署：** 严格按 [LAN HTTPS 部署说明](deploy/family/README.md) 由家长操作。配置文件与证书私钥只存在本机，不能公开映射或提交到 GitHub。

## 文档地图

| 文件 | 用途 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 开发禁区、单任务单 PR、CI、合并与自主工作规则 |
| [docs/V1_PLAN.md](docs/V1_PLAN.md) | 唯一的任务来源、每周完成标准与真机验收清单 |
| [AMEND.md](AMEND.md) | 经负责人批准的方向变更与例外 |
| [docs/AVATAR_CONTRACT_V1.md](docs/AVATAR_CONTRACT_V1.md) | 共享人物骨骼、装备挂点和动画名称 |
| [docs/EQUIPMENT_RUNTIME_V2.md](docs/EQUIPMENT_RUNTIME_V2.md) | 装备运行时与私有库存 |
| [docs/FAMILY_PRIVATE_API_V1.md](docs/FAMILY_PRIVATE_API_V1.md) | 家庭私有 API |
| [docs/WORLD_BASELINE_NEWBIE_VILLAGE_V1.md](docs/WORLD_BASELINE_NEWBIE_VILLAGE_V1.md) | 新手村 |
| [docs/MINI_UTOPIA_VISUAL_DNA_v1.md](docs/MINI_UTOPIA_VISUAL_DNA_v1.md) | 画面风格 |
| [docs/MINI_UTOPIA_BRAND_CANON_V1.md](docs/MINI_UTOPIA_BRAND_CANON_V1.md) | 品牌设定 |
| [docs/archive/README_LEGACY.md](docs/archive/README_LEGACY.md) | 归档的完整旧 README（仅历史参考，不作为任务依据） |

**当前退出条件：** 参见 `docs/V1_PLAN.md` §5：两个孩子在真实 iPad Safari 完成角色创建、游戏、导演台、配音音乐、家长审核的闭环；重启后数据保持私有可用。
