# 安装与首次使用

目标宿主：**WorkBuddy**。名称「松鼠旅行官」，技术标识 `liangxiao-travel`。本包不包含 Key，也不包含同程连接器或腾讯地图助手本体；增强查询需要本人授权，基础攻略可以暂时跳过。

## 1. 安装本 skill

### 推荐：在 WorkBuddy 中导入

1. 从正式发布页下载 **1.2.0 或更新版** `liangxiao-travel-1.2.0.zip`（候选版使用本次交付的 ZIP）。
2. 打开 WorkBuddy → 技能 → 添加技能 → 上传技能，选择 ZIP，按客户端确认导入。
3. 确认「松鼠旅行官」已经启用。旧版显示名可能是「良逍旅行规划」；先备份自己的修改再升级，不重复安装两个目录。
4. 新建任务发送：**使用松鼠旅行官，带我完成首次配置，每次只引导当前一步，完成后继续规划。**

后面的配置由同一个任务逐步引导，不用一次做完下列文档中的所有步骤。缺什么处理什么，做完回复「继续」。普通用户无需运行终端命令；以下为手动安装备选。

### macOS：Git 安装

需要已安装 Git，且目标目录尚不存在：

```bash
mkdir -p "$HOME/.workbuddy/skills"
git clone https://github.com/mrliang-github/liangxiao-travel.git "$HOME/.workbuddy/skills/liangxiao-travel"
```

### macOS：ZIP 安装

从 [Releases](https://github.com/mrliang-github/liangxiao-travel/releases) 下载对应版本，终端切换到下载目录后运行：

```bash
mkdir -p "$HOME/.workbuddy/skills"
ditto -x -k liangxiao-travel-1.2.0.zip "$HOME/.workbuddy/skills/"
```

本发布 ZIP 自带 `liangxiao-travel/` 外层目录。GitHub 自动生成的 “Source code (zip)” 外层名称不同，若下载的是它，请手动把解压目录改名为 `liangxiao-travel` 后移动到 skills 目录。

### Windows：PowerShell

下面是对应安装方式，尚未在 Windows 实机验证。Git 安装：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.workbuddy\skills" | Out-Null
git clone https://github.com/mrliang-github/liangxiao-travel.git "$env:USERPROFILE\.workbuddy\skills\liangxiao-travel"
```

或在下载目录解压 Release 安装包：

```powershell
Expand-Archive -Path .\liangxiao-travel-1.2.0.zip -DestinationPath "$env:USERPROFILE\.workbuddy\skills"
```

**若已有同名安装目录，先备份自己的修改，不要直接覆盖或再次 clone。** Git 安装且没有本地修改时，可以更新：

```bash
git -C "$HOME/.workbuddy/skills/liangxiao-travel" pull --ff-only
```

### 确认目录

```text
~/.workbuddy/skills/liangxiao-travel/
├── SKILL.md
├── scripts/
│   ├── check_deps.py
│   ├── parse_chengxin.py
│   └── build_html.py
└── references/schema.md
```

Windows 中 `~` 对应当前用户目录。不要让文件散落成 `skills/SKILL.md`，也不要多套一层 `liangxiao-travel/liangxiao-travel/`。安装后在 WorkBuddy 的技能列表检查是否显示并启用；若未刷新，重启 WorkBuddy 后再查看。

本仓库脚本需要 Python 3.9+。macOS 使用 `python3`；Windows 使用 `py -3` 或 `python`。

## 2. 连接同程旅行

在 WorkBuddy 的连接器／「连应用」入口中，连接「同程旅行」或「同程程心」，由本人完成授权；入口文字可能随客户端版本变化。

Agent 会通过 `tc-chengxin token` 检查授权，输出只在脚本进程中使用。**不要把 token 发给 Agent 或写进仓库。** 同程查询脚本及其 Node.js 环境由同程连接器提供，本仓库不打包它们。

## 3. 安装腾讯地图助手并申请 Key

1. 在 WorkBuddy 技能市场安装「腾讯地图助手」，或按[腾讯位置服务官方仓库](https://github.com/TencentLBS/tencentmap-map-assistant)的说明安装。
2. 安装目录可为 `~/.workbuddy/skills/腾讯地图助手/`、`tencentmap-map-assistant/` 或 `tencentmap-map-assistant__skillhub/`，目录内应包含 `SKILL.md`。
3. 松鼠旅行官检测到此步骤后接上官方助手的申请流程：先阅读并同意协议，再由本人完成手机验证，自动创建/取得并保存 Key。不用去控制台寻找 Key。该助手自己的依赖按其安装说明配置。
4. Key 保存在 `~/.tencentmap/tempkey.json`（Windows：`%USERPROFILE%\.tencentmap\tempkey.json`）。不要复制进本仓库或发到聊天中。

检查脚本会检查本地 Key 的状态和有效日期，但不会向腾讯地图发请求验证服务端鉴权；额度和实际可用性以服务端为准。

## 4. 检查并开始规划

macOS 可手动检查：

```bash
python3 "$HOME/.workbuddy/skills/liangxiao-travel/scripts/check_deps.py" --state outputs/my-trip/onboarding-state.json --json
```

Windows：

```powershell
py -3 "$env:USERPROFILE\.workbuddy\skills\liangxiao-travel\scripts\check_deps.py" --state outputs/my-trip/onboarding-state.json --json
```

退出码 `0` 表示可开始所选模式的规划；`1` 只显示当前配置步骤；`2` 表示状态文件错误，保留原文件并处理。完成后回复「继续」重查，已有配置会跳过。已保存的进度不替代实际检查。

明确说「先做基础攻略」后，Skill 使用 `--mode basic` 保存选择，跳过增强查询。以后要实际票价和地图时切回 `--mode guided`。需求保留在当前任务，不能把个人进度文件上传公开网页。

规划时请给出：**出发地、目的地、未来的出行日期、人数**。预算、住宿偏好、想玩的内容也可以一起说。输出文件应位于当前任务的 `outputs/` 目录，详细数据格式见 [references/schema.md](references/schema.md)。

## 常见问题

- **其他 Agent 能用吗？** 可读取指令或单独运行解析脚本，但完整查价流程依赖 WorkBuddy 的同程授权，未验证其他宿主的完整兼容性。
- **没有 Key 能用吗？** 可看完整公开示例，也可选择基础攻略。在增强配置未完成时不会冒充已经查到票价或坐标。
- **日期不一致或没解析到表格？** 不要使用这份数据；核对请求日期、同程结果格式和是否已开放查询。酒店／景区没有日期列时会单独标明无法校验日期。
- **地图空白？** 检查网络、Key 有效期及腾讯地图助手的配置；本地检查通过不保证 Key 在服务端仍可用。
- **可以公开页面吗？** 1.2.0 默认生成无 Key 版，检查个人内容后可发布。显式 `--local-map` 版仍含 Key，不可公开；旧版 1.1.x 生成的 HTML 也需重新生成。
- **下载按钮等于存进 ima 了吗？** 不等于。下载的是同源 Markdown；分享页若限制下载，点击「复制行程文档」，按提示手动复制后让 WorkBuddy 保存为 `行程.md`。然后在 WorkBuddy 中选中文档 → 上传到云端 → ima 知识库，完成官方授权和上传后再在手机查询。
- **升级后有问题？** 在 [Releases](https://github.com/mrliang-github/liangxiao-travel/releases) 下载对应版本，先备份本地修改，再按相同目录结构安装。反馈时只提供脱敏日志。
