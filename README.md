# 松鼠旅行官 · liangxiao-travel

**替你做攻略的 J 人小松鼠。** 给 WorkBuddy 一段需求，拿到行程方案、手机行程页和可存入腾讯 ima 的文档。第一次使用有逐步配置引导，以后沿用已有配置。也可先选择基础攻略，未知票价和坐标留空。

版本：**1.2.0** · [正式发布记录](https://github.com/mrliang-github/liangxiao-travel/releases) · [安装与首次启用](INSTALL.md) · [更新记录](CHANGELOG.md)

原名称「良逍旅行规划」；保留 `liangxiao-travel` 目录与技术标识，避免重复安装。功能分支中的 1.2.0 不等于正式 Release 已发布，请核对下载版本。

## 能做什么

- 比较出行日期、航班或车次，给出一个主方案及取舍。
- 整理逐日行程、酒店、门票、美食、拍摄建议和两档预算。
- 生成 `travel-data.json`，让方案与页面使用同一份数据。
- 生成适合手机查看的 `index.html`，包含交通、路线、行程、门票、美食和待办六个标签页。
- 校验查询日期，把估算、未查到和攻略类参考信息标清楚。
- 每日行程默认首屏，住宿随日期展示；待办按行程隔离保存在浏览器。
- 默认公开页不带地图 Key，没有 Key 也可查看完整行程和顺序示意。
- 从同一份 JSON 生成 HTML 与 Markdown，按官方流程保存至 ima。

## 使用条件

| 条件 | 用途 |
| --- | --- |
| WorkBuddy | 本 skill 的目标宿主；完整流程依赖它的同程连接器 |
| 同程旅行／同程程心连接器授权（增强模式） | 查询交通、酒店和门票；本人在「连应用」授权，不手填 Key |
| [腾讯地图助手](https://github.com/TencentLBS/tencentmap-map-assistant)及有效 Key（增强模式） | 查询地点与路线；官方助手引导手机验证并保存配置 |
| Python 3.9 或更新版本 | 运行本仓库脚本，仅使用标准库 |

同程连接器还需要其自带的 Node.js 运行环境，腾讯地图助手有自己的安装要求。**“本仓库脚本无额外 Python 依赖”不代表无需安装外部工具。** 本版本脚本测试在 macOS 完成，Windows 安装步骤尚未实机验证。其他 Agent 可以阅读这些指令，但仅安装本包不会获得 WorkBuddy 的同程授权。

## 快速开始

普通用户：从正式发布页下载 **1.2.0 或更新版** ZIP，在 WorkBuddy「技能 → 添加技能 → 上传技能」导入并启用。首次发送：

> 使用松鼠旅行官，先带我完成首次配置，已经配置的跳过，每次只引导当前一步。完成后继续帮我规划旅行。

Skill 会逐步引导安装腾讯地图助手、官方手机验证、同程授权。每步完成回复「继续」，需求与进度保存到当前任务，重新检查后续接。若暂不想配置，明确说「先做基础攻略」。

以下 Git 安装作为备选方式：

安装 Git 后，在 macOS 终端运行（目标目录需尚不存在）：

```bash
mkdir -p "$HOME/.workbuddy/skills"
git clone https://github.com/mrliang-github/liangxiao-travel.git "$HOME/.workbuddy/skills/liangxiao-travel"
```

不使用 Git，或使用 Windows，见 [INSTALL.md](INSTALL.md)。手动解压后应有 `liangxiao-travel/SKILL.md` 这一层。

已有配置的用户直接说：

> 用松鼠旅行官，帮我安排 2027 年 5 月 1 日到 5 月 4 日从武汉去成都的旅行，2 人，总预算 3000 元，经济型酒店，主要想吃当地美食和拍照。请查询当前能查到的信息，未开放的远期票价说明限制和重查时间。

请替换为自己的出发地、目的地、未来日期和人数。缺依赖时，Agent 会显示配置步骤；完成后回复「继续」，重新检查通过后开始规划。

## 交付物与预览

生成文件放在**当前任务的输出目录**，不要放进 skill 源码目录：

```text
outputs/my-trip/
├── travel-data.json
├── index.html                 # 默认公开无 Key 页
├── index.md                   # ima 可阅读文档
└── onboarding-state.json      # 私有任务进度，不公开上传
```

浏览器直接打开 HTML；需要分享时，在 WorkBuddy 中按官方「轻量发布」流程发布为网站。默认页面不读取地图 Key，顺序示意也不依赖外部网络。实际底图仅在显式本地模式下加载。已在 Chrome 的 WorkBuddy 公开页验证首次引导、复制回退、路线示意与待办保存；手机真机尚未验收。

在 WorkBuddy 选中 `index.md` → 上传到云端 → ima 知识库。分享页可能限制下载和自动复制；可点击「复制行程文档」，按提示手动复制选中的文字，再让 WorkBuddy 保存为 `行程.md`。复制或下载不代表上传成功；待办勾选不会同步到 ima，资料也不会自动更新。

仓库中的 [示例数据](examples/travel-data.example.json)全部是演示内容，不是实际查询结果，不能用于订票或出行。

## 数据与 Key

**源码、安装包、默认生成的 HTML 与 Markdown 不包含 Key 或 token。** 增强查询的授权留在用户本机，网页不提供 Key、手机号或验证码输入框。个人生成资料仍需检查内容隐私后再公开。

确需本地底图时运行 `python3 scripts/build_html.py travel-data.json index-local.html --local-map`。该显式模式含本机 Key，禁止公开上传；公开分享重新运行默认命令。也可另按[官方代理说明](https://lbs.qq.com/webApi/javascriptGL/glGuide/glKeyDelegate)设计服务端访问保护，但本项目不假装已提供代理。

价格、班次和营业信息以实际查询及服务提供方的最终展示为准；本 skill 负责规划，不会代为下单或付款。

## 仓库结构与验证

```text
SKILL.md                         Agent 执行入口
INSTALL.md                       安装与常见问题
references/schema.md             行程数据字段
scripts/check_deps.py             检查连接器和地图 Key
scripts/parse_chengxin.py         解析同程返回结果并校验日期
scripts/build_html.py             从 JSON 生成手机页面
scripts/trip_document.py          从同份 JSON 生成 ima 文档
references/onboarding.md          首次启用与恢复流程
examples/travel-data.example.json 离线演示数据
tests/test_scripts.py            脚本回归测试
```

在仓库目录运行：

```bash
python3 -m unittest discover -s tests -v
```

测试使用模拟数据和测试 Key，不读取本机凭据、不查询票价，也不产生订单。真实同程查询、腾讯地图鉴权仍需要在配置完成的 WorkBuddy 中验证。

## 许可证与反馈

本项目沿用原 skill 声明的 [MIT License](LICENSE)，可以使用、修改和分发；同程、腾讯地图及 WorkBuddy 的服务规则分别适用。本项目不附带这些服务的授权。

使用问题或改进建议可以提交 [Issue](https://github.com/mrliang-github/liangxiao-travel/issues)。请提供脱敏后的错误信息，勿上传含 Key 的 HTML、token 或真实个人行程。
