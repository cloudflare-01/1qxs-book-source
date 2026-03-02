#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多站点书源验证脚本
当前支持：一七小说(1qxs.com)、速读谷(sudugu.org)
"""

import json, time, os, sys, random
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    os.system("pip3 install requests beautifulsoup4 lxml -q")
    import requests
    from bs4 import BeautifulSoup

SOURCE_FILE = Path(__file__).parent / "sources" / "1qxs.json"
REPORT_FILE = Path(__file__).parent / "logs" / "validation_report.md"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

results = {}  # {站点名: {检查项: {ok, detail}}}


# ── 通用工具 ──────────────────────────────────────────────
def fetch(url, retries=3, delay=2.0, headers=None):
    h = {**HEADERS, **(headers or {})}
    for i in range(retries):
        try:
            resp = requests.get(url, headers=h, timeout=20)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e:
            print(f"    [重试{i+1}/{retries}] {url} → {e}")
            time.sleep(delay + random.uniform(0.5, 1.5))
    return None

def soup(html): return BeautifulSoup(html, "lxml")

def check(site, name, ok, detail=""):
    results.setdefault(site, {})[name] = {"ok": ok, "detail": detail}
    icon = "✅" if ok else "❌"
    print(f"    {icon} {name}" + (f" → {detail}" if detail else ""))
    return ok


# ── 一七小说验证 ──────────────────────────────────────────
SITE1 = "一七小说"
BASE1 = "https://www.1qxs.com"
TEST_BOOK1 = "/xs/14094"       # 赤心巡天

def validate_1qxs():
    print(f"\n{'='*50}")
    print(f"📖 验证：{SITE1}（{BASE1}）")
    print(f"{'='*50}")

    # 1. 首页
    html = fetch(BASE1 + "/")
    if not html:
        check(SITE1, "首页连通", False, "无法访问"); return
    s = soup(html)
    check(SITE1, "首页连通", "一七小说" in (s.title.string or ""),
          s.title.string.strip() if s.title else "无title")
    time.sleep(1)

    # 2. 书库列表
    html = fetch(BASE1 + "/all/0_0_0_0_0_1.html")
    if html:
        s = soup(html)
        for sel in [".book-list li", ".list-box li", "#bookList .item", ".item"]:
            items = s.select(sel)
            if items:
                check(SITE1, "书库列表", True, f"选择器={sel!r} 共{len(items)}本")
                break
        else:
            check(SITE1, "书库列表", False, "未匹配任何选择器")
    time.sleep(1)

    # 3. 书籍详情
    html = fetch(BASE1 + TEST_BOOK1)
    first_ch = None
    if html:
        s = soup(html)
        h1 = s.select_one("h1.book-name,h1")
        check(SITE1, "书名", bool(h1), h1.text.strip()[:20] if h1 else "未找到")

        toc = None
        for sel in ["#catalog li","#chapterList li",".catalog-list li",".chapter-list li"]:
            items = s.select(sel)
            if items:
                toc = items; break
        check(SITE1, "目录章节", bool(toc), f"共{len(toc)}章" if toc else "未找到")

        if toc:
            a = toc[0].select_one("a")
            if a and a.get("href"):
                first_ch = a["href"]
    time.sleep(1)

    # 4. 章节正文
    ch_url = (BASE1 + first_ch) if first_ch else BASE1 + "/xs/14094/1792.html"
    html = fetch(ch_url)
    if html:
        s = soup(html)
        for sel in ["#content","#chapterContent",".content","#chapterBody"]:
            el = s.select_one(sel)
            if el and len(el.get_text(strip=True)) > 100:
                check(SITE1, "章节正文", True, f"选择器={sel!r}")
                break
        else:
            check(SITE1, "章节正文", False, "正文选择器全部未匹配")


# ── 速读谷验证 ────────────────────────────────────────────
SITE2 = "速读谷"
BASE2 = "https://www.sudugu.org"

def validate_sudugu():
    print(f"\n{'='*50}")
    print(f"📖 验证：{SITE2}（{BASE2}）")
    print(f"{'='*50}")

    # 1. 首页
    html = fetch(BASE2 + "/")
    if not html:
        check(SITE2, "首页连通", False, "无法访问"); return
    s = soup(html)
    check(SITE2, "首页连通", "速读谷" in html,
          s.title.string.strip() if s.title else "无title")
    time.sleep(1)

    # 2. 最新更新页（书单）
    html = fetch(BASE2 + "/zuixin/")
    if html:
        s = soup(html)
        # 速读谷首页结构：每本书是 h3>a + 作者a + 章节a 的组合
        books = s.select("h3")
        if not books:
            books = s.select("article")
        check(SITE2, "书单列表", bool(books), f"找到{len(books)}个书名元素")

        # 取第一本书的链接
        first_book_url = None
        if books:
            a = books[0].select_one("a")
            if a and a.get("href"):
                href = a["href"]
                first_book_url = href if href.startswith("http") else BASE2 + href
                check(SITE2, "书籍链接", True, href)
    time.sleep(1)

    # 3. 书籍详情（用已知书 /51/ 捞尸人）
    html = fetch(BASE2 + "/51/")
    first_ch = None
    if html:
        s = soup(html)
        # 书名
        h1 = s.select_one("h1")
        check(SITE2, "书名", bool(h1), h1.text.strip()[:20] if h1 else "未找到")

        # 目录
        toc = None
        for sel in ["#chapterlist li","#catalog li",".chapterlist li","ul li"]:
            items = s.select(sel)
            # 过滤掉菜单导航项
            items = [i for i in items if i.select_one("a") and
                     i.select_one("a").get("href","").startswith("/51/")]
            if items:
                toc = items; break
        check(SITE2, "目录章节", bool(toc), f"共{len(toc)}章" if toc else "未找到")

        if toc:
            a = toc[0].select_one("a")
            if a and a.get("href"):
                first_ch = a["href"]
    time.sleep(1)

    # 4. 章节正文
    ch_url = (BASE2 + first_ch) if first_ch else BASE2 + "/51/3011773.html"
    html = fetch(ch_url, headers={"Referer": BASE2 + "/51/"})
    if html:
        s = soup(html)
        for sel in ["#nr","#content","#chaptercontent",".content"]:
            el = s.select_one(sel)
            if el and len(el.get_text(strip=True)) > 100:
                check(SITE2, "章节正文", True, f"选择器={sel!r}")
                break
        else:
            # fallback: 找最长div
            divs = sorted(s.find_all("div"), key=lambda d: len(d.get_text()), reverse=True)
            if divs and len(divs[0].get_text(strip=True)) > 200:
                check(SITE2, "章节正文", True, "fallback: 最长div")
            else:
                check(SITE2, "章节正文", False, "正文选择器全部未匹配")

    # 5. 搜索（POST）
    time.sleep(1)
    try:
        resp = requests.post(
            BASE2 + "/i/so.aspx",
            data={"searchkey": "捞尸人", "page": "1"},
            headers={**HEADERS, "Referer": BASE2 + "/i/so.aspx",
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=20
        )
        resp.encoding = resp.apparent_encoding
        ok = "捞尸人" in resp.text or resp.status_code == 200
        check(SITE2, "搜索POST", ok, f"状态码={resp.status_code}")
    except Exception as e:
        check(SITE2, "搜索POST", False, str(e))


# ── 更新时间戳 & 生成报告 ────────────────────────────────
def update_timestamp():
    if not SOURCE_FILE.exists(): return
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    now_ms = int(time.time() * 1000)
    for s in data:
        s["lastUpdateTime"] = now_ms
    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n📝 已更新 lastUpdateTime → {now_ms}")

def write_report():
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total = sum(len(v) for v in results.values())
    passed = sum(1 for v in results.values() for i in v.values() if i["ok"])

    lines = [
        "# 书源验证报告",
        "",
        f"> 验证时间：{now}  ",
        f"> 总通过率：**{passed}/{total}**",
        "",
    ]

    for site, checks in results.items():
        site_pass = sum(1 for i in checks.values() if i["ok"])
        lines += [f"## {site}（{site_pass}/{len(checks)}）", "",
                  "| 检查项 | 状态 | 详情 |",
                  "|--------|------|------|"]
        for name, info in checks.items():
            icon = "✅" if info["ok"] else "❌"
            lines.append(f"| {name} | {icon} | {info['detail']} |")
        lines.append("")

    lines += [
        "---", "",
        "## 书源订阅链接", "",
        "在 legado（阅读3.0）中导入：", "",
        "```",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/sources/1qxs.json",
        "```",
    ]

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📊 报告已写出：{REPORT_FILE}")


# ── 主入口 ────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("🚀 多站点书源验证开始")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    validate_1qxs()
    validate_sudugu()

    total  = sum(len(v) for v in results.values())
    passed = sum(1 for v in results.values() for i in v.values() if i["ok"])
    print(f"\n{'='*50}")
    print(f"✅ 验证完成：{passed}/{total} 项通过")

    update_timestamp()
    write_report()

    if passed < total * 0.5:
        print("❌ 通过率低于50%，请检查！")
        sys.exit(1)

if __name__ == "__main__":
    main()
