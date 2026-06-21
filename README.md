# 📈 CrawlFund — 天天基金排行榜爬虫

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![curl_cffi](https://img.shields.io/badge/TLS-curl__cffi_Chrome120-success)
![Pandas](https://img.shields.io/badge/Data-Pandas-orange)
![Pyecharts](https://img.shields.io/badge/Visualization-Pyecharts-yellow)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> 针对东方财富/天天基金网（`fund.eastmoney.com`）的生产级排行榜爬虫。  
> 通过 **curl_cffi Chrome120 TLS 指纹伪装**突破 JA3/JA4 检测，逆向解析私有 JSONP 接口，一键导出全量基金排名数据到 CSV。

---

## 🚀 核心特性

| 特性 | 实现方式 |
|------|---------|
| **TLS 指纹伪装** | `curl_cffi` 模拟 Chrome 120 JA3/JA4 握手，绕过服务端指纹检测 |
| **Referer & Cookie 反爬** | Session 预热：先 GET 主页取 `em_hq_fls`/`qgqp_b_id` Cookie，再带 Referer 请求 API |
| **URL Hash 逆向** | 完整解析 `#tall;c0;r;s1nzf;pn50;ddesc;qsd...` hash 参数，映射到 `rankhandler.aspx` Query String |
| **JS 对象解析** | API 返回非标准 JS 字面量（unquoted keys），通过 Regex 自动补引号后再 `json.loads` |
| **自动翻页** | 读取响应 `allRecords` 字段计算总页数，支持 `--pages` 限定上限 |
| **指数退避重试** | 单页最多 3 次重试，间隔 2ⁿ 秒，避免短时封禁 |
| **随机延迟** | 每页请求间隔 `delay × [0.8, 2.0]` 随机抖动，降低特征识别概率 |

---

## 🔬 接口逆向分析

### 目标 URL

```
https://fund.eastmoney.com/data/fundranking.html
#tall;c0;r;s1nzf;pn50;ddesc;qsd20250621;qed20260621;qdii;zq;gg;gzbd;gzfs;bbzt;sfbb
```

### Hash → API 参数映射

| Hash 片段 | API 参数 | 含义 |
|-----------|---------|------|
| `tall` | `ft=all` | 基金类型（全部） |
| `tgp/thh/tzq/tzs/tqdii/tlof` | `ft=gp/hh/zq/zs/qdii/lof` | 股票/混合/债券/指数/QDII/LOF |
| `s1nzf` | `sc=1nzf` | 排序字段：近1年增长率 |
| `ddesc/dasc` | `st=desc/asc` | 排序方向 |
| `pn50` | `pn=50` | 每页返回条数 |
| `qsd20250621` | `sd=2025-06-21` | 自定义区间开始日 |
| `qed20260621` | `ed=2026-06-21` | 自定义区间结束日 |

### 真实 API 端点

```
GET https://fund.eastmoney.com/data/rankhandler.aspx
    ?op=ph&dt=kf&ft=all&sc=1nzf&st=desc
    &sd=2025-06-21&ed=2026-06-21
    &pi=1&pn=50&dx=1&v=<随机浮点>
```

### 响应格式（JS 字面量，非 JSON）

```javascript
var rankData = {
  datas: [
    "014915,财通匠心优选一年持有混合A,CTJXYXYNCYHHA,2026-06-18,4.0954,4.0954,2.83,23.34,...",
    ...
  ],
  allRecords: 19747,
  pageIndex: 1,
  pageNum: 50,
  allPages: 395
};
```

> ⚠️ 响应的 `{}` 内 key 不加引号（非标准 JSON），需通过 Regex 转换后才能 `json.loads`。

### 字段映射（逗号分隔，共 24 位）

| 索引 | 字段名 | 含义 |
|------|-------|------|
| 0 | `fund_code` | 基金代码 |
| 1 | `fund_name` | 基金名称 |
| 2 | `fund_abbr` | 拼音缩写 |
| 3 | `date_nav` | 净值日期 |
| 4 | `nav` | 单位净值 |
| 5 | `acc_nav` | 累计净值 |
| 6 | `ret_1d` | 日增长率 % |
| 7 | `ret_1w` | 近1周 % |
| 8 | `ret_1m` | 近1月 % |
| 9 | `ret_3m` | 近3月 % |
| 10 | `ret_6m` | 近6月 % |
| 11 | `ret_1y` | 近1年 % |
| 12 | `ret_2y` | 近2年 % |
| 13 | `ret_3y` | 近3年 % |
| 14 | `ret_since` | 成立以来 % |
| 15 | `ret_custom` | 自定义区间 %（`sd`~`ed`） |
| 16 | `inception_date` | 成立日期 |
| 18 | `fund_size` | 基金规模（亿） |
| 19 | `fee_full` | 原始申购费率 |
| 20 | `fee_discount` | 折扣申购费率 |

---

## 💻 快速开始

### 环境要求

- Python 3.10+

### 安装

```bash
git clone https://github.com/yourname/CrawlFund.git
cd CrawlFund

# 推荐使用虚拟环境
python -m venv .venv && source .venv/bin/activate

pip install curl_cffi pandas
```

### 运行

```bash
cd tiantianfund

# 默认：全部基金，近1年排序，爬取全量（~395页）
python eastmoney_fund_crawler2026.py

# 常用参数示例
python eastmoney_fund_crawler2026.py \
  --ft qdii \          # 只爬 QDII 基金
  --sc 1nzf \          # 按近1年收益排序
  --sd 2025-01-01 \    # 自定义区间开始
  --ed 2026-01-01 \    # 自定义区间结束
  --pages 5 \          # 只爬前5页（250条）
  --output qdii.csv \  # 输出文件名
  --delay 1.5          # 请求基准间隔秒
```

### CLI 参数一览

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--ft` | `all` | 基金类型：`all/gp/hh/zq/zs/qdii/lof` |
| `--sc` | `1nzf` | 排序字段：`1nzf/3nzf/6yzf/1yzf/zzf/dwjz/ljjz` |
| `--st` | `desc` | 排序方向：`desc/asc` |
| `--sd` | 一年前今日 | 自定义区间开始日期 `YYYY-MM-DD` |
| `--ed` | 今日 | 自定义区间结束日期 `YYYY-MM-DD` |
| `--pages` | `0`（全量） | 最多爬取页数，`0` = 不限 |
| `--output` | `funds.csv` | 输出 CSV 文件名 |
| `--delay` | `1.0` | 请求间隔基准秒，实际随机 `×[0.8, 2.0]` |
| `--hash` | — | 直接传入 URL Hash 字符串覆盖所有参数 |

### 实际输出示例

```
━━━ 前10条预览 ━━━
fund_code      fund_name     nav  ret_1m  ret_3m  ret_6m   ret_1y  ret_custom
   014915  财通匠心优选一年持有混合A  4.0954   67.32  145.88  173.96   473.75      309.54
   017490  财通景气甄选一年持有期混合A  6.5682   65.68  143.70  170.39   472.89      556.82
   001480      财通成长优选混合A 10.0740   61.55  135.59  163.30   472.06      907.40
   ...

近1年收益率统计:
count    250.000000
mean     263.565720
std       59.938356
min      203.410000
max      473.750000
```

---

## 🛠️ 架构说明

```
tiantianfund/
├── eastmoney_fund_crawler2026.py   # 主爬虫（当前版本）
│   ├── CrawlConfig         # 参数配置（dataclass，支持 from_hash 解析）
│   ├── EastmoneySession    # curl_cffi Session 封装，处理 TLS/Cookie/Referer
│   ├── _js_obj_to_json()   # JS字面量 → JSON 转换（Regex补引号）
│   ├── parse_jsonp()       # JSONP 响应解析 + ErrCode 检测
│   ├── parse_fund_row()    # 逗号分隔字段 → dict
│   └── FundRankCrawler     # 翻页控制、数值清洗、DataFrame 输出
└── Visualization.py        # Pyecharts 可视化模块
```

### 反爬对抗要点

1. **TLS 指纹**：`curl_cffi` 内置 Chrome 120 的完整 ClientHello 扩展序列（JA3/JA4），与真实浏览器一致，绕过 Cloudflare/WAAP 的指纹检测。
2. **Cookie 热身**：每次启动先 GET 主页，让服务端写入 `em_hq_fls`、`qgqp_b_id` 等 Session Cookie，API 请求携带这些 Cookie 后才返回数据。
3. **Referer 校验**：API 强制校验 `Referer: https://fund.eastmoney.com/data/fundranking.html`，缺失则返回空数据。
4. **随机 `v` 参数**：每次请求追加随机浮点 `v=0.xxxx`，模拟前端 JS 的 `Math.random()` 行为，防止请求特征固化。

---

## 📦 依赖

```
curl_cffi>=0.15.0
pandas>=2.0
```

```bash
pip install curl_cffi pandas
```

---

## ⚠️ 免责声明

本项目仅供学习网络爬虫技术与 HTTP 协议分析使用。请遵守目标网站的 `robots.txt` 及服务条款，控制请求频率，勿用于商业目的。