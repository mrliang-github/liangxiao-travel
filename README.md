# 良逍旅行规划 · liangxiao-travel

给 WorkBuddy 一段旅行需求，拿到 **行程方案、结构化数据和手机行程页**。交通与住宿价格通过同程旅行查询，地点、路线和美食信息通过腾讯地图查询；查不到的内容明确标注，不编造价格或坐标。

当前版本：**1.1.4** · [下载安装包](https://github.com/mrliang-github/liangxiao-travel/releases/latest) · [详细安装说明](INSTALL.md) · [更新记录](CHANGELOG.md)

## 能做什么

- 比较出行日期、航班或车次，给出一个主方案及取舍。
- 整理逐日行程、酒店、门票、美食、拍摄建议和两档预算。
- 生成 `travel-data.json`，让方案与页面使用同一份数据。
- 生成适合手机查看的 `index.html`，包含交通、路线地图、行程、门票、吃和 Todo 六个标签页。
- 校验查询日期，把估算、未查到和攻略类参考信息标清楚。

## 使用条件

| 条件 | 用途 |
| --- | --- |
| WorkBuddy | 本 skill 的目标宿主；完整流程依赖它的同程连接器 |
| 同程旅行／同程程心连接器授权 | 查询交通、酒店和门票信息 |
| [腾讯地图助手](https://github.com/TencentLBS/tencentmap-map-assistant)及有效 Key | 查询地点与路线，加载页面地图 |
| Python 3.9 或更新版本 | 运行本仓库的三个脚本，仅使用标准库 |

同程连接器还需要其自带的 Node.js 运行环境，腾讯地图助手有自己的安装要求。**“本仓库脚本无额外 Python 依赖”不代表无需安装外部工具。** 本次发布验证在 macOS 完成，Windows 安装步骤尚未实机验证。其他 Agent 可以阅读这些指令，但仅安装本包不会获得 WorkBuddy 的同程授权。

## 快速开始

安装 Git 后，在 macOS 终端运行（目标目录需尚不存在）：

```bash
mkdir -p "$HOME/.workbuddy/skills"
git clone https://github.com/mrliang-github/liangxiao-travel.git "$HOME/.workbuddy/skills/liangxiao-travel"
```

不使用 Git，或使用 Windows，见 [INSTALL.md](INSTALL.md)。下载 Release 中的 `liangxiao-travel-1.1.4.zip` 即可安装，解压后应有 `liangxiao-travel/SKILL.md` 这一层。

在 WorkBuddy 中启用本 skill，完成同程连接器授权及腾讯地图助手的 Key 申请，然后说：

> 用良逍旅行规划，帮我安排 2027 年 5 月 1 日到 5 月 4 日从武汉去成都的旅行，2 人，总预算 3000 元，经济型酒店，主要想吃当地美食和拍照。请查询当前能查到的信息，未开放的远期票价标为估算并说明重查时间。

请替换为自己的出发地、目的地、未来日期和人数。缺依赖时，Agent 会显示配置步骤；完成后回复「继续」，重新检查通过后开始规划。

## 交付物与预览

生成文件放在**当前任务的输出目录**，不要放进 skill 源码目录：

```text
outputs/my-trip/
├── travel-data.json
└── index.html
```

在电脑浏览器中打开 HTML 即可看行程。手机可使用 WorkBuddy 提供的预览入口（若当前版本支持），或在受信任的内网打开该文件；地图需要联网及有效的腾讯地图 Key。

仓库中的 [示例数据](examples/travel-data.example.json)全部是演示内容，不是实际查询结果，不能用于订票或出行。

## 数据与 Key

**源码和安装包不包含 Key、token 或真实行程。生成的 HTML 会内嵌本机腾讯地图 Key，不能直接上传公开 GitHub 仓库或 GitHub Pages。** 同程 token 不应粘贴到聊天中；证件、联系方式和订单信息不应写入行程文件。

如需公开分享生成页面，先按[腾讯地图官方 Key 代理说明](https://lbs.qq.com/webApi/javascriptGL/glGuide/glKeyDelegate)配置凭据保护和访问限制。本仓库的 `.gitignore` 排除了常见输出、HTML 和凭据文件，但不能替代发布前检查。

价格、班次和营业信息以实际查询及服务提供方的最终展示为准；本 skill 负责规划，不会代为下单或付款。

## 仓库结构与验证

```text
SKILL.md                         Agent 执行入口
INSTALL.md                       安装与常见问题
references/schema.md             行程数据字段
scripts/check_deps.py             检查连接器和地图 Key
scripts/parse_chengxin.py         解析同程返回结果并校验日期
scripts/build_html.py             从 JSON 生成手机页面
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
