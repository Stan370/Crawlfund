# 📈 FundCrawler (天天基金数据采集与分析流水线)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Asyncio](https://img.shields.io/badge/Concurrency-Asyncio-success)
![Pandas](https://img.shields.io/badge/Data-Pandas-orange)
![Pyecharts](https://img.shields.io/badge/Visualization-Pyecharts-yellow)

FundCrawler 是一个面向东方财富/天天基金网的高性能、高并发爬虫与数据处理流水线。本项目突破了基础的接口防护，实现了全网 3000+ 基金元数据、历史净值、基金经理信息的自动化采集与持久化，并集成了基于 Pandas 与 Pyecharts 的可视化回测分析模块。

## 🚀 核心特性 (Key Features)

- **深度的接口逆向与伪装**：通过抓包分析 ASP/AJAX 动态渲染接口，破解 Query String 参数（`ft`, `sc`, `st`, `pi`, `pn`），绕过 Referer 检测与基础反爬策略。
- **高并发 I/O 调度**：实现了从“同步阻塞”到“多线程池”，再到“单线程异步协程 (`asyncio`)”的架构演进，IO 密集型任务性能提升 **100%+**。
- **全链路数据处理**：支持从网络请求 -> 数据清洗 -> Pandas 结构化 -> CSV/数据库持久化的完整 ETL 流程。
- **动态可视化生成**：基于 `pyecharts` 实现单支基金历史净值的动态交互式图表（折线图/柱状图），支持任意时间窗口的收益回测。

---

## 🛠️ 技术架构与演进 (Architecture & Evolution)

### 1. 协议分析与反爬对抗 (Protocol Analysis & Anti-Bot)
目标站点（天天基金）的排行数据采用客户端动态渲染，并通过特定的 API 端点返回 ASP 格式数据。
- **参数逆向**：精确定位排行接口（`rankhandler.aspx`），解析出核心控制参数（如 `pn` 控制返回数量，`sc` 控制排序字段）。
- **流量伪装**：发现并绕过其严格的 `Referer` 校验机制，构造合规的 HTTP Headers，模拟真实浏览器访问链路，避免被 WAF 拦截或返回 200 空白页。

### 2. 基金历史净值提取与分页 (Historical Data Extraction)
单支基金的详情页（如 `jjjz_162719.html`）历史数据极其庞大。
- 使用 Python 的 `yield` 生成器重构了分页抓取逻辑，实现内存友好的惰性求值（Lazy Evaluation），防止海量数据抓取时内存溢出。
- 自动化清洗 ASP 响应中的脏数据，提取核心字段（日期、单位净值、累计净值、日增长率等）。

### 3. 性能调优：并发架构的演进 (Concurrency Optimization)
为了在极短时间内完成全网 3000+ 基金及其二级页面（基金经理信息）的抓取，本项目经历了三次架构重构，深度探索了 IO 密集型场景的极限：

| 架构版本 | 技术栈 | 耗时 (抓取 300条并写入) | 性能瓶颈分析 |
| :--- | :--- | :--- | :--- |
| **V1.0 同步单线程** | `requests` | > 150 秒 | 遇到网络 I/O 阻塞时 CPU 处于闲置状态，效率极低。 |
| **V2.0 多线程池** | `ThreadPoolExecutor` | 133.6 秒 | 设置 32 核心线程池。虽有提升，但在海量并发下，**上下文切换开销**与**线程锁竞争**导致边际收益递减。 |
| **V3.0 异步协程** | `asyncio` + `aiohttp` | **55.25 秒** | **最终方案**。利用 Event Loop 和底层系统 API (epoll)，在单线程内实现无锁的高效 I/O 状态切换，性能飙升近一倍。 |

*(注：并发测试详细过程见 `/docs/performance_test.md`)*

### 4. 数据清洗与可视化 (Data Pipeline & Visualization)
- 引入 `pandas` 进行时间序列处理，支持自定义 `min_date` 计算历史任意时间节点投入资金（如 10,000 元本金）的绝对收益与年化收益。
- 接入 `pyecharts` 渲染前端交互式 HTML 报表，可结合 `snapshot_selenium` 直接输出高清静态分析图片。

*(由于 GitHub 不支持直接渲染动态 HTML，下图为静态截图展示)*
> **💡 图表展示**
> 
> ![Fund Chart Demo](./assets/echart_demo.png) *(请将你的效果图保存为 echart_demo.png 放到 assets 目录)*

---

## 💻 快速开始 (Setup & Usage)

### 环境依赖
- Python 3.8+
- Node.js (如需后续扩展 JS 逆向环境)

### 安装配置
```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/fund_crawler.git
cd fund_crawler

# 2. 安装 Python 依赖
pip install -r requirements.txt