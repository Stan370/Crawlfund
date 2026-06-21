"""
天天基金排行榜爬虫 - fund.eastmoney.com/data/fundranking.html
目标URL hash逆向:
  #tall;c0;r;s1nzf;pn50;ddesc;qsd20250621;qed20260621;qdii;zq;gg;gzbd;gzfs;bbzt;sfbb

真实API: rankhandler.aspx (JSONP格式)
反爬策略: Referer校验 + Cookie + UA检测 + 随机延迟
"""

import re
import json
import time
import random
import logging
import argparse
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

import pandas as pd

# curl_cffi 模拟真实浏览器TLS指纹，绕过JA3检测
try:
    from curl_cffi import requests as cffi_requests
    USE_CURL_CFFI = True
except ImportError:
    import requests as cffi_requests
    USE_CURL_CFFI = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 常量 & 参数映射表（从hash逆向得出）
# ─────────────────────────────────────────────
BASE_URL = "https://fund.eastmoney.com/data/rankhandler.aspx"

# ft: 基金类型 (hash前缀 t)
FT_MAP = {
    "tall":  "all",   # 全部
    "tgp":   "gp",    # 股票型
    "thh":   "hh",    # 混合型
    "tzq":   "zq",    # 债券型
    "tzs":   "zs",    # 指数型
    "tqdii": "qdii",  # QDII
    "tlof":  "lof",   # LOF
    "tbb":   "bb",    # 保本型
}

# sc: 排序字段 (hash前缀 s)
SC_MAP = {
    "s1nzf":  "1nzf",   # 近1年增长率
    "s3nzf":  "3nzf",   # 近3年增长率
    "s6yzf":  "6yzf",   # 近6月增长率
    "s1yzf":  "1yzf",   # 近1月增长率
    "szzf":   "zzf",    # 近3月增长率
    "sdwjz":  "dwjz",   # 单位净值
    "sljjz":  "ljjz",   # 累计净值
}

# 列名映射（API返回的逗号分隔字段顺序）
# 实际响应示例: 014915,财通匠心优选一年持有混合A,CTJXYXYNCYHHA,2026-06-18,4.0954,...
FIELD_NAMES = [
    "fund_code",       # 0   基金代码
    "fund_name",       # 1   基金名称
    "fund_abbr",       # 2   拼音缩写
    "date_nav",        # 3   净值日期
    "nav",             # 4   单位净值
    "acc_nav",         # 5   累计净值
    "ret_1d",          # 6   日增长率%
    "ret_1w",          # 7   近1周%
    "ret_1m",          # 8   近1月%
    "ret_3m",          # 9   近3月%
    "ret_6m",          # 10  近6月%
    "ret_1y",          # 11  近1年%
    "ret_2y",          # 12  近2年%
    "ret_3y",          # 13  近3年%
    "ret_since",       # 14  成立以来%
    "ret_custom",      # 15  自定义区间% (qsd~qed)
    "inception_date",  # 16  成立日期
    "unknown_17",      # 17  (标记位)
    "fund_size",       # 18  基金规模(亿)
    "fee_full",        # 19  原始费率
    "fee_discount",    # 20  折扣费率
    "unknown_21",      # 21
    "unknown_22",      # 22
    "unknown_23",      # 23
]

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
@dataclass
class CrawlConfig:
    # 来自URL hash的参数
    ft: str = "all"           # 基金类型 (tall→all)
    sc: str = "1nzf"          # 排序字段 (s1nzf→1nzf)
    st: str = "desc"          # 排序方向 (ddesc→desc)
    sd: str = "2025-06-21"    # 开始日期
    ed: str = "2026-06-21"    # 结束日期
    qdii: str = ""            # QDII子分类筛选
    tab_subtype: str = ",,,,,"  # tabSubtype (zq;gg;gzbd;gzfs;bbzt;sfbb → 逗号join)
    pn: int = 50              # 每页条数
    # 爬取控制
    max_pages: int = 0        # 0=自动翻页直到结束
    delay_min: float = 0.8    # 请求间隔最小秒
    delay_max: float = 2.0    # 请求间隔最大秒
    output: str = "funds.csv"

    @classmethod
    def from_hash(cls, hash_str: str) -> "CrawlConfig":
        """从URL hash字符串解析配置，如: tall;c0;r;s1nzf;pn50;ddesc;..."""
        cfg = cls()
        parts = hash_str.lstrip("#").split(";")
        tab_parts = []
        for p in parts:
            if p in FT_MAP:
                cfg.ft = FT_MAP[p]
            elif p in SC_MAP:
                cfg.sc = SC_MAP[p]
            elif p == "dasc":
                cfg.st = "asc"
            elif p == "ddesc":
                cfg.st = "desc"
            elif p.startswith("pn"):
                cfg.pn = int(p[2:])
            elif p.startswith("qsd"):
                d = p[3:]
                cfg.sd = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            elif p.startswith("qed"):
                d = p[3:]
                cfg.ed = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            elif p in ("qdii", "zq", "gg", "gzbd", "gzfs", "bbzt", "sfbb"):
                tab_parts.append(p)
        if tab_parts:
            # tabSubtype逗号分隔，位置对应固定槽位
            cfg.tab_subtype = ",".join(tab_parts[:6]).ljust(5, ",")
        return cfg


# ─────────────────────────────────────────────
# 核心请求器
# ─────────────────────────────────────────────
class EastmoneySession:
    """
    使用 curl_cffi 模拟 Chrome TLS 指纹（JA3/JA4）
    + Referer / Cookie 反爬处理
    """
    def __init__(self):
        if USE_CURL_CFFI:
            self.session = cffi_requests.Session(impersonate="chrome120")
            log.info("使用 curl_cffi Chrome120 TLS指纹")
        else:
            import requests
            self.session = requests.Session()
            log.warning("curl_cffi不可用，降级为普通requests（可能被TLS指纹识别）")

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://fund.eastmoney.com/data/fundranking.html",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        # 先访问主页拿Cookie (em_hq_fls, qgqp_b_id 等)
        self._init_cookies()

    def _init_cookies(self):
        """访问主页初始化Session Cookie，模拟真实用户行为"""
        try:
            self.session.get(
                "https://fund.eastmoney.com/data/fundranking.html",
                timeout=10
            )
            log.info("Cookie初始化完成")
        except Exception as e:
            log.warning(f"Cookie初始化失败（继续）: {e}")

    def get_jsonp(self, url: str, params: dict, retries: int = 3) -> Optional[str]:
        """请求JSONP接口，返回原始文本"""
        for attempt in range(1, retries + 1):
            try:
                # v参数是随机浮点数，模拟JS行为
                params["v"] = str(random.random())
                resp = self.session.get(url, params=params, timeout=15)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                log.warning(f"  第{attempt}次请求失败: {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)
        return None


# ─────────────────────────────────────────────
# JSONP 解析
# ─────────────────────────────────────────────
def _js_obj_to_json(js_str: str) -> str:
    """
    将JS对象字面量转为合法JSON:
      {datas:[...], allNum:9527}  →  {"datas":[...], "allNum":9527}
    给未加引号的属性名加上双引号
    """
    # 匹配 JS 对象中未被引号包裹的 key（在 { 或 , 后面的 word）
    return re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r' "\1":', js_str)


def parse_jsonp(raw: str) -> dict:
    """
    响应格式: var rankData = {datas:["...",..], allNum:9527, ...}
    API返回JS对象字面量（key未加引号），非标准JSON
    """
    # 匹配 var rankData = {...}
    m = re.search(r'var\s+rankData\s*=\s*(\{.*\})', raw, re.DOTALL)
    if not m:
        raise ValueError(f"JSONP解析失败，原始内容: {raw[:300]}")

    js_obj = m.group(1).rstrip(';').strip()
    json_str = _js_obj_to_json(js_obj)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"{e}")

    # 检查API级错误
    if data.get("ErrCode"):
        raise ValueError(f"API返回错误: ErrCode={data['ErrCode']}, Data={data.get('Data', '')}")

    return data


def parse_fund_row(pipe_str: str) -> dict:
    """
    解析单条基金数据（逗号分隔字符串）
    示例: "014915,财通匠心优选一年持有混合A,CTJXYXYNCYHHA,2026-06-18,4.0954,..."
    """
    cols = pipe_str.split(",")
    record = {}
    for i, name in enumerate(FIELD_NAMES):
        record[name] = cols[i] if i < len(cols) else ""
    # 附加原始字段数（方便调试新字段）
    record["_total_fields"] = len(cols)
    return record


# ─────────────────────────────────────────────
# 主爬取逻辑
# ─────────────────────────────────────────────
class FundRankCrawler:
    def __init__(self, cfg: CrawlConfig):
        self.cfg = cfg
        self.session = EastmoneySession()

    def _build_params(self, page: int) -> dict:
        """构建rankhandler.aspx请求参数"""
        return {
            "op":          "ph",
            "dt":          "kf",        # 开放式基金
            "ft":          self.cfg.ft,
            "rs":          "",
            "gs":          "0",
            "sc":          self.cfg.sc,
            "st":          self.cfg.st,
            "sd":          self.cfg.sd,
            "ed":          self.cfg.ed,
            "qdii":        self.cfg.qdii,
            "tabSubtype":  self.cfg.tab_subtype,
            "pi":          str(page),
            "pn":          str(self.cfg.pn),
            "dx":          "1",         # dx=1: 包含增长率数据
        }

    def fetch_page(self, page: int) -> tuple[list[dict], int]:
        """拉取单页，返回 (记录列表, 总记录数)"""
        params = self._build_params(page)
        log.info(f"  拉取第{page}页 | ft={self.cfg.ft} sc={self.cfg.sc} st={self.cfg.st}")

        raw = self.session.get_jsonp(BASE_URL, params)
        if not raw:
            return [], 0

        try:
            data = parse_jsonp(raw)
        except ValueError as e:
            log.error(f"  解析失败: {e}")
            return [], 0

        total = int(data.get("allRecords", data.get("allNum", 0)))
        datas = data.get("datas", [])
        records = [parse_fund_row(row) for row in datas if row]
        log.info(f"  第{page}页: {len(records)}条 | 总计: {total}条")
        return records, total

    def crawl_all(self) -> pd.DataFrame:
        cfg = self.cfg
        all_records = []

        # 先拉第1页确定总数
        page1, total = self.fetch_page(1)
        if not page1:
            log.error("第1页无数据，退出")
            return pd.DataFrame()
        all_records.extend(page1)

        if total == 0:
            log.warning("total=0，可能参数有误或被限流")
            return pd.DataFrame(all_records)

        import math
        total_pages = math.ceil(total / cfg.pn)
        if cfg.max_pages > 0:
            total_pages = min(total_pages, cfg.max_pages)

        log.info(f"总记录: {total} | 每页: {cfg.pn} | 总页数: {total_pages}")

        for page in range(2, total_pages + 1):
            delay = random.uniform(cfg.delay_min, cfg.delay_max)
            time.sleep(delay)
            records, _ = self.fetch_page(page)
            if not records:
                log.warning(f"第{page}页返回空，停止")
                break
            all_records.extend(records)

        df = pd.DataFrame(all_records)

        # 清理: 数值列转float
        numeric_cols = [
            "nav", "acc_nav",
            "ret_1d", "ret_1w", "ret_1m", "ret_3m",
            "ret_6m", "ret_1y", "ret_2y", "ret_3y",
            "ret_since", "ret_custom"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        log.info(f"爬取完成: {len(df)}条记录")
        return df


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="天天基金排行爬虫")
    parser.add_argument(
        "--hash",
        default="tall;c0;r;s1nzf;pn50;ddesc;qsd20250621;qed20260621;qdii;zq;gg;gzbd;gzfs;bbzt;sfbb",
        help="URL hash参数字符串"
    )
    parser.add_argument("--ft",     default=None, help="基金类型: all/gp/hh/zq/zs/qdii/lof")
    parser.add_argument("--sc",     default=None, help="排序字段: 1nzf/3nzf/6yzf/1yzf/dwjz")
    parser.add_argument("--st",     default=None, help="排序方向: desc/asc")
    parser.add_argument("--sd",     default=None, help="开始日期: YYYY-MM-DD")
    parser.add_argument("--ed",     default=None, help="结束日期: YYYY-MM-DD")
    parser.add_argument("--pages",  type=int, default=0, help="最多爬几页 (0=全部)")
    parser.add_argument("--output", default="funds.csv", help="输出文件名")
    parser.add_argument("--delay",  type=float, default=1.0, help="请求间隔基准秒数")
    args = parser.parse_args()

    # 从hash解析基础配置
    cfg = CrawlConfig.from_hash(args.hash)

    # CLI参数覆盖
    if args.ft:     cfg.ft = args.ft
    if args.sc:     cfg.sc = args.sc
    if args.st:     cfg.st = args.st
    if args.sd:     cfg.sd = args.sd
    if args.ed:     cfg.ed = args.ed
    if args.pages:  cfg.max_pages = args.pages
    cfg.output = args.output
    cfg.delay_min = args.delay * 0.8
    cfg.delay_max = args.delay * 2.0

    log.info("=" * 50)
    log.info(f"配置: ft={cfg.ft} sc={cfg.sc} st={cfg.st}")
    log.info(f"日期: {cfg.sd} → {cfg.ed}")
    log.info(f"输出: {cfg.output}")
    log.info("=" * 50)

    crawler = FundRankCrawler(cfg)
    df = crawler.crawl_all()

    if df.empty:
        log.error("无数据，请检查参数或网络")
        return

    # 保存
    df.to_csv(cfg.output, index=False, encoding="utf-8-sig")
    log.info(f"已保存: {cfg.output} ({len(df)}行)")

    # 预览
    preview_cols = [
        "fund_code", "fund_name",
        "nav", "ret_1m", "ret_3m", "ret_6m", "ret_1y", "ret_custom"
    ]
    avail = [c for c in preview_cols if c in df.columns]
    print("\n━━━ 前10条预览 ━━━")
    print(df[avail].head(10).to_string(index=False))

    # 统计摘要
    if "ret_1y" in df.columns:
        print(f"\n近1年收益率统计:")
        print(df["ret_1y"].describe().to_string())


if __name__ == "__main__":
    main()
