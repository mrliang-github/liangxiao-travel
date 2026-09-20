---
name: liangxiao-travel
description: "口述一段旅行需求 → 一次交付可执行方案 + travel-data.json + 移动端单页（含腾讯地图 / 出片攻略 / 美食）。价格走同程连接器，坐标与美食走腾讯地图。首次运行先检查同程授权和腾讯地图 Key，缺什么只提示什么，不把 Key 写进包。"
description_zh: "口述旅行需求，一次交付行程方案、数据 JSON 和手机行程页。同程查票房价，腾讯地图查坐标美食。缺连接器或 Key 时先引导补齐。"
description_en: "Turn a spoken trip brief into an executable itinerary, travel-data.json, and a mobile page with Tencent Map. Flights/hotels via Tongcheng connector; POIs via Tencent Map. Missing auth is prompted at runtime."
version: "1.1.4"
license: MIT
display_name: "良逍旅行规划"
display_name_en: "liangxiao-travel"
visibility: "public"
---

# liangxiao-travel

口述一段需求，一次交付：可执行方案 + `travel-data.json` + 移动端单页。

**目标宿主：WorkBuddy。** 完整流程依赖其同程连接器授权，仅在其他 Agent 中安装本包不会获得该授权。

本包**不携带任何 Key**。运行时先检查依赖；缺什么，把检查脚本的 stdout **原样展示给用户，然后停**，等用户回「继续」。

## 开始或恢复规划前

在查票、写方案、生成页面之前，先跑：

```bash
python3 "<本 SKILL.md 所在目录>/scripts/check_deps.py"
```

路径按实际安装位置替换（`SKILL.md` 自己就在包根目录，脚本在同级 `scripts/`）。脚本内部用 `os.path.dirname(__file__)` 定位，不依赖绝对路径。

解释器：macOS / Linux 用 `python3`；Windows 用 `py -3`，没有的话试 `python`。脚本只用标准库，无需额外安装。

| 退出码 | 动作 |
|---|---|
| 0 | 继续规划 |
| 1 | **把 stdout 原样发给用户，停止规划。** 不要自己改写引导、不要编造下一步、不要问 A/B 来绕过授权 |

缺的是两件不同的事，不要都叫 Key：

1. **同程旅行连接器** = WorkBuddy「连应用」授权。探测命令是 `tc-chengxin token`。**禁止让用户粘贴 token / API Key。**
2. **腾讯地图 Key** = 先装官方「腾讯地图助手」，再按它的引导申请体验 Key，写入 `~/.tencentmap/tempkey.json`。**禁止把 Key 写进本包、禁止让用户把 Key 发到对话里。**

这两样都需要用户本人在客户端操作，Agent 只能引导、不能代办。装依赖、申请 Key、点授权，都按脚本给出的步骤走。

两样都过了，按用户已给出的规划需求继续；不需要让用户重复需求。

## 必须先向用户确认的输入

下面这几项**不能默认、不能编**，缺就一次问完（最多三个问题），问完再动手：

- 出发地
- 目的地（或想去哪几个城市）
- **出行日期区间**（哪天走、哪天回）
- 人数

除此之外的缺项一律用默认并在结果里标「（默认）」，不要为了这些停下来问。

**如果当前环境无法向用户提问**（自动化任务、批量处理、无交互会话里提问工具不可用）：不要反复重试提问把自己卡死。改为——

- 能默认的按默认走，在结果里逐条标「（默认）」
- **出发地 / 目的地 / 日期 / 人数**缺任何一项，**中止并输出一份说明**：写清缺什么、为什么不能编、需要用户补什么。不要自行补造必填项
- 中止时不要产出 `travel-data.json` 或页面，避免用户误以为是完整结果

## 触发词

规划行程、旅行攻略、帮我排行程、/travel、出去玩 X 天、liangxiao-travel

## 默认（仅当用户没说）

- 住宿：经济型连锁，不限品牌，2 人拼房
- 未说请假 = 不把「请假错峰」定成主方案；错峰明显更便宜时，主方案仍按用户能走的日期，错峰只作为备选一行
- 缺项用默认并在结果里标「（默认）」

## 硬纪律

1. 价格/班次：同程旅行连接器。查到标查询日期；远月未开放标「估」+ 重查时间；失败写「未查到」，禁止编造
2. 坐标/路程/营业/人均：腾讯地图助手。查不到留空或写「未查到」，不许猜
3. 工具报错或未授权：在对应字段标明原因，其余能做的继续；**唯一例外是首次 `check_deps.py` 失败——必须停**
4. 隐私：护照、证件号、手机、邮箱、订单号、商户电话，一律不进 JSON、不进页面
5. 页面禁止：超宽大表、连接器/MCP/模型名、下单按钮、优惠券、登录、3D 图
6. 方案、JSON、页面三者同源
7. 数据自查：工具返回必须对得上目的地。关键词错配（「延吉」混进长白山酒店、「二道白河镇」解析到行政区中心点）必须标出来，不能当有效数据
8. 事实 vs 经验：车次票价、坐标、营业、人均＝事实；机位、最佳时段、必吃菜＝经验，标「参考」+ 来源 + 检索日期
9. 页面上**不要标「实」**。默认就是实查数字；只标「估」「未查到」「参考」
10. **禁止**使用 WorkBuddy 地图 Key 代理（`_TMapSecurityConfig` + `__WB_HTTP_PORT__`）。实测鉴权 -303，页面会白屏。JSAPI 用用户本机 `tempkey.json` 里的 Key，明文写入生成页
11. **日期双校验（强制，不可省）**：此前查询遇到过越界日期被静默替换的情况，不能假定请求日期就是返回日期。
    - **查之前**：日期早于今天就先拒绝，让用户重说一句，不要往下跑。`parse_chengxin.py --guard-date YYYY-MM-DD`，退出码 1 表示已过去
    - **查之后**：`parse_chengxin.py <输出文件> --expect-date YYYY-MM-DD` 反查月日。交通结果只有 `dateCheck.status = "ok"` 才能使用；其他状态必须说明原因并重查。酒店／景区的 `no_date_column` 仅表示无法验证日期，须保留这一限制，不能当作日期已核实
    - 返回的表格**只带月日、不带年份**，年份一律以用户说的为准，不采信接口
12. **最低价 ≠ 可比价**：酒店"最低价"可能是青旅床位或单人间（实测昆明站附近有 ¥23 的床位，而连锁酒店标准间 ¥173 起）；机票最低价常是红眼航班。下"性价比最优"结论时要按**同类房型、同时段**比，别把不可比的数字并排当结论
13. **结果条数少 = 如实说明，别下"只有这一班"的结论**：同程按航线返回，冷门直飞可能只有 1-2 条。实测同期对比——「武汉→曼谷」1 条、「武汉→张掖」1 条，而「上海→曼谷」33 条、「武汉→新加坡」46 条、「武汉→东京」46 条、**「武汉→成都」46 条**。差异来自**出发地**，不是接口对境外的覆盖差，别把出发地问题误判成工具缺陷。
    - 结果 ≤2 条时：方案里标「该航线可选班次少，建议另行核对航司官网」，并说明这是**查询结果**、不等于航线全貌
    - 「实查 ≥3 组比选」在结果不足时无法满足，**说明原因即可，不要为了凑数去编，也不要因此改线路**

## 一次输出（不要中途停下来问 A/B）

一、理解表：出发地 / 目的地 / 日期天数 / 人数 / 预算 / 请假 / 偏好 / 用了哪些默认

二、交通比选：实查 ≥3 组「日期 × 进出港 / 车次」。自己定 1 个主方案并写一句理由，按主方案继续

三、完整方案：总览、时间线、逐日（交通/酒店/游玩/出片/吃/取舍）、预算两档、行前 Todo

四、`travel-data.json`：字段见 `references/schema.md`。没查到填「未查到」或空

生成文件放在当前任务的输出目录（如 `outputs/my-trip/`），不要写进 skill 源码目录或 Git 仓库。

五、旅行页：用本包脚本生成，不要让模型现场重写地图页

```bash
python3 "<本包目录>/scripts/build_html.py" <travel-data.json> <index.html>
```

六、交付清单：文件列表 / 手机怎么预览 / 哪些字段是估或未查到

生成 HTML 后若源码含 `gljs?...&key=`，在回复里**原样**输出下面这段（把路径换成实际文件）：

> ⚠️ **HTML Key 安全提示**：检测到 `<HTML_FILE>` 中包含明文 Key（形如 `gljs?...&key=...`），任何人可通过查看源码或抓包获取，存在盗用风险；当前形式仅限本地/内网使用，若需公网发布请参考官方代理方案：https://lbs.qq.com/webApi/javascriptGL/glGuide/glKeyDelegate 。

## 同程怎么查

先注入令牌（不要手填）：

```bash
export CHENGXIN_WORKBUDDY_OUTPUT_DIR="$PWD/outputs"
export CHENGXIN_API_KEY="$(tc-chengxin token)"
export CHENGXIN_OUTPUT_GUARD=display_contract
```

脚本在已安装的同程 skill 的 `skills/scripts/` 下，例如：

- `flight-query.js` / `train-query.js` / `hotel-query.js` / `scenery-query.js` / `traffic-query.js`

定位办法：`tc-chengxin` 是连接器 CLI，同程 skill 通常在 `~/.workbuddy/skills/tc-chengxin/skills/scripts/`；找不到就在 `~/.workbuddy/skills/` 下搜 `flight-query.js`。用 `node <脚本> --departure X --destination Y --extra "..."` 调用。

**查完必须用本包脚本解析，不要自己现写正则抠表。**

```bash
python3 "<本包目录>/scripts/parse_chengxin.py" <同程输出文件> --expect-date YYYY-MM-DD
```

理由：同程只返回一整篇 markdown，**没有结构化价格数组**；抠表逻辑放在包里才能保证每次结果一致。脚本自动适配 5 套表头（机票 / 火车 / 汽车 / 酒店 / 景区，列位置各不相同），输出结构化 JSON。

- 退出码 0：数据可用，`items[]` 里有 `name / date / time / price / rating / booking`
- 退出码 1：日期校验没过（日期不符、混入其他日期、交通日期缺失、无效日期或过去日期）→ **丢弃，确认日期后重查**
- 退出码 2：文件读不到、没有有效 JSON 块或没有可用表格数据
- 火车/汽车价格取多席别里的最低价，全部席别在 `priceVariants`
- 酒店/景区表没有日期列，`dateCheck.status = no_date_column` 属正常

关键词错配要重查（酒店目的地用「延吉市」而不是「延吉」）。

## 腾讯地图怎么查

加载「腾讯地图助手」skill，用 `TmapClient`：`poi_search` / `geocoder` / `direction` / `distance_matrix`。

跨镇路线不要只传地名：geocoder 可能解析到行政区划中心点（二道白河镇实测偏 27 km）。用 `poi_search` 拿到的坐标再算距离。

## 内置地图（生成脚本已处理，不要改回代理模式）

- 位置：「路线」Tab 顶部
- 切 Tab 后约 80ms 再 `ensureMap()` 注入 `https://map.qq.com/api/gljs?v=1&key=...`
- `InfoWindow` 必须带初始 `position`，否则 SDK 抛 `Cannot read properties of null (reading 'x')`
- Tab 图标用内联 SVG，不用 emoji（日历 emoji 会显示成当天日期数字）
- 城市节点从 `days[].mapPoints` 推导，不要写死某条线路

## 出片 / 美食

- 出片：联网检索，每条机位写位置 / 最佳时段 / 拍摄要点 / 到达。标「参考」。冲突并列，禁止空话
- 美食：腾讯地图 POI，不要用同程景点接口冒充。丢弃 `tel`。菜名标「参考」

## 不要做

- 不要把任何 Key / token 写进本包、JSON、git
- 不要静默安装同程或腾讯地图助手
- 不要在 `check_deps.py` 失败后继续编行程
- 不要把本包当同程 CLI 或腾讯地图 API 的再封装
