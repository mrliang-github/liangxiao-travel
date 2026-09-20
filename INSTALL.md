# 安装与首次使用

目标宿主：**WorkBuddy**。本包不包含 Key，也不包含同程连接器或腾讯地图助手本体。完整流程需要分别配置它们。

## 1. 安装本 skill

### macOS：Git 安装

需要已安装 Git，且目标目录尚不存在：

```bash
mkdir -p "$HOME/.workbuddy/skills"
git clone https://github.com/mrliang-github/liangxiao-travel.git "$HOME/.workbuddy/skills/liangxiao-travel"
```

### macOS：ZIP 安装

从 [Releases](https://github.com/mrliang-github/liangxiao-travel/releases/latest) 下载 **`liangxiao-travel-1.1.4.zip`**，终端切换到下载目录后运行：

```bash
mkdir -p "$HOME/.workbuddy/skills"
ditto -x -k liangxiao-travel-1.1.4.zip "$HOME/.workbuddy/skills/"
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
Expand-Archive -Path .\liangxiao-travel-1.1.4.zip -DestinationPath "$env:USERPROFILE\.workbuddy\skills"
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
3. 对话里说「申请腾讯地图体验 Key」，按官方引导由本人完成手机号验证。该助手自己的依赖按其安装说明配置。
4. Key 保存在 `~/.tencentmap/tempkey.json`（Windows：`%USERPROFILE%\.tencentmap\tempkey.json`）。不要复制进本仓库或发到聊天中。

检查脚本会检查本地 Key 的状态和有效日期，但不会向腾讯地图发请求验证服务端鉴权；额度和实际可用性以服务端为准。

## 4. 检查并开始规划

macOS 可手动检查：

```bash
python3 "$HOME/.workbuddy/skills/liangxiao-travel/scripts/check_deps.py"
```

Windows：

```powershell
py -3 "$env:USERPROFILE\.workbuddy\skills\liangxiao-travel\scripts\check_deps.py"
```

退出码 `0` 表示本地检查通过；退出码 `1` 会显示缺项和操作步骤。配置完成后，在 WorkBuddy 回复「继续」重新检查。

规划时请给出：**出发地、目的地、未来的出行日期、人数**。预算、住宿偏好、想玩的内容也可以一起说。输出文件应位于当前任务的 `outputs/` 目录，详细数据格式见 [references/schema.md](references/schema.md)。

## 常见问题

- **其他 Agent 能用吗？** 可读取指令或单独运行解析脚本，但完整查价流程依赖 WorkBuddy 的同程授权，未验证其他宿主的完整兼容性。
- **为什么缺依赖就停？** 避免在没有真实查询能力时编造票价和地点信息。按提示补齐后继续即可。
- **日期不一致或没解析到表格？** 不要使用这份数据；核对请求日期、同程结果格式和是否已开放查询。酒店／景区没有日期列时会单独标明无法校验日期。
- **地图空白？** 检查网络、Key 有效期及腾讯地图助手的配置；本地检查通过不保证 Key 在服务端仍可用。
- **可以把页面放到 GitHub Pages 吗？** 生成的 HTML 会内嵌 Key，请先按[官方代理说明](https://lbs.qq.com/webApi/javascriptGL/glGuide/glKeyDelegate)保护凭据。本仓库适合公开，个人生成页面默认只用于本地或受信任内网。
- **升级后有问题？** 在 [Releases](https://github.com/mrliang-github/liangxiao-travel/releases) 下载对应版本，先备份本地修改，再按相同目录结构安装。反馈时只提供脱敏日志。
