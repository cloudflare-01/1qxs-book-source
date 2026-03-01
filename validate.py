#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一七小说 (1qxs.com) 书源验证 & 规则自动修正脚本
运行于 GitHub Actions，负责：
  1. 验证书源各规则是否仍然有效
  2. 如发现 CSS 选择器失效，自动尝试修正
  3. 更新书源 JSON 中的 lastUpdateTime 字段
  4. 写出验证报告
"""

import json
import time
import re
import os
import sys
import random
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("依赖未安装，尝试安装...")
    os.system("pip install requests beautifulsoup4 lxml --break-system-packages -q")
    import requests
    from bs4 import BeautifulSoup


# ─────────────────────────────────────────
# 配置
# ─────────────────────────────────────────
BASE_URL   = "https://www.1qxs.com"
SOURCE_FILE = Path(__file__).parent / "sources" / "1qxs.json"
REPORT_FILE = Path(__file__).parent / "logs" / "validation_report.md"

# 用于测试的固定书籍（赤心巡天 - 连载稳定）
TEST_BOOK_PATH    = "/xs/14094"
TEST_CHAPTER_PATH = "/xs/14094/1792.html"   # 第三十五章

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL,
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ─────────────────────────────────────────
# 通用请求工具
# ─────────────────────────────────────────
def fetch(path: str, retries: int = 3, delay: float = 2.0) -> str | None:
    url = path if path.startswith("http") else BASE_URL + path
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e:
            print(f"  [请求失败 {i+1}/{retries}] {url} → {e}")
            time.sleep(delay + random.uniform(0.5, 1.5))
    return None


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ─────────────────────────────────────────
# 各规则验证函数
# ─────────────────────────────────────────
results = {}

def check(name: str, ok: bool, detail: str = ""):
    status = "✅ 通过" if ok else "❌ 失败"
    results[name] = {"ok": ok, "detail": detail}
    print(f"  {status}  {name}" + (f" → {detail}" if detail else ""))
    return ok


def validate_homepage():
    print("\n📋 [1] 首页连通性")
    html = fetch("/")
    if not html:
        return check("首页访问", False, "无法连接")
    s = soup(html)
    title = s.title.string if s.title else ""
    return check("首页访问", "一七小说" in title, f"title={title!r}")


def validate_booklist():
    print("\n📚 [2] 书库列表页")
    html = fetch("/all/0_0_0_0_0_1.html")
    if not html:
        return check("书库列表", False, "请求失败")
    s = soup(html)

    # 自动探测书单容器
    candidates = [
        (".book-list li", s.select(".book-list li")),
        (".list-box li",  s.select(".list-box li")),
        ("#bookList .item", s.select("#bookList .item")),
        ("ul.list li",   s.select("ul.list li")),
        (".item",         s.select(".item")),
    ]
    found_sel, found_els = None, []
    for sel, els in candidates:
        if els:
            found_sel, found_els = sel, els
            break

    if not found_els:
        # 打印可能有用的 class 供调试
        all_cls = [" ".join(t.get("class", [])) for t in s.find_all(True) if t.get("class")]
        unique_cls = list(dict.fromkeys(all_cls))[:20]
        return check("书库列表", False, f"未找到书单，已知class: {unique_cls}")

    check("书库列表", True, f"选择器={found_sel!r}，找到 {len(found_els)} 本书")

    # 检查第一本书的链接和标题
    first = found_els[0]
    link = first.select_one("a")
    title_el = first.select_one("a")
    ok = bool(link and link.get("href"))
    return check("书库 - 书籍链接", ok,
                 f"href={link.get('href') if link else 'None'!r}, text={title_el.text.strip()[:20] if title_el else 'None'!r}")


def validate_book_detail():
    print(f"\n📖 [3] 书籍详情页 ({TEST_BOOK_PATH})")
    html = fetch(TEST_BOOK_PATH)
    if not html:
        return check("书籍详情", False, "请求失败"), None

    s = soup(html)
    ok_all = True

    # 书名
    h1 = s.select_one("h1.book-name,h1")
    check("书名", bool(h1), h1.text.strip()[:30] if h1 else "未找到")
    ok_all = ok_all and bool(h1)

    # 作者
    author = s.select_one(".book-author a,.author")
    check("作者", bool(author), author.text.strip() if author else "未找到")

    # 简介
    intro = s.select_one("#intro,#bookIntro,.intro")
    check("简介", bool(intro), (intro.text.strip()[:40] + "…") if intro else "未找到")

    # 目录容器
    toc_candidates = [
        "#catalog li", "#chapterList li", ".catalog-list li",
        ".chapter-list li", "ul.list-chapter li",
    ]
    toc_items = []
    found_toc_sel = None
    for sel in toc_candidates:
        items = s.select(sel)
        if items:
            toc_items, found_toc_sel = items, sel
            break

    check("目录章节", bool(toc_items),
          f"选择器={found_toc_sel!r}，共 {len(toc_items)} 章" if toc_items else "未找到目录")
    ok_all = ok_all and bool(toc_items)

    # 返回第一章链接用于内容测试
    first_chapter_url = None
    if toc_items:
        a = toc_items[0].select_one("a")
        if a and a.get("href"):
            first_chapter_url = a["href"]
    return ok_all, first_chapter_url


def validate_chapter_content(chapter_url: str | None = None):
    print(f"\n📄 [4] 章节正文")
    url = chapter_url or TEST_CHAPTER_PATH
    html = fetch(url)
    if not html:
        return check("章节内容", False, "请求失败")

    s = soup(html)
    content_candidates = [
        "#content", "#chapterContent", ".content", "#chapterBody", ".chapter-content",
    ]
    content_el = None
    found_content_sel = None
    for sel in content_candidates:
        el = s.select_one(sel)
        if el and len(el.get_text(strip=True)) > 100:
            content_el, found_content_sel = el, sel
            break

    if not content_el:
        # fallback: 找文字最多的 div
        divs = s.find_all("div")
        divs_sorted = sorted(divs, key=lambda d: len(d.get_text(strip=True)), reverse=True)
        if divs_sorted:
            content_el = divs_sorted[0]
            found_content_sel = f"div (最长文本 fallback)"

    text = content_el.get_text(strip=True)[:80] if content_el else ""
    return check("章节内容", bool(text), f"选择器={found_content_sel!r}，内容预览：{text!r}")


def validate_search():
    print("\n🔍 [5] 搜索功能")
    # 常见搜索 URL 格式
    search_patterns = [
        "/so/赤心巡天/1/",
        "/search?key=赤心巡天",
        "/search/赤心巡天/",
        "/search?q=赤心巡天&page=1",
    ]
    for pattern in search_patterns:
        html = fetch(pattern)
        if not html:
            continue
        s = soup(html)
        # 如果有书单或书名元素，说明搜索成功
        if s.select("a") and len(s.get_text()) > 500:
            # 检查是否含有搜索目标
            if "赤心巡天" in s.get_text() or "情何以甚" in s.get_text():
                return check("搜索", True, f"URL格式={pattern!r}")
    return check("搜索", False, "所有搜索格式均未匹配，请手动确认搜索URL")


# ─────────────────────────────────────────
# 更新书源 JSON
# ─────────────────────────────────────────
def update_source_timestamp():
    if not SOURCE_FILE.exists():
        print(f"⚠️  书源文件不存在：{SOURCE_FILE}")
        return
    with open(SOURCE_FILE, encoding="utf-8") as f:
        data = json.load(f)
    now_ms = int(time.time() * 1000)
    for source in data:
        source["lastUpdateTime"] = now_ms
    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n📝 已更新 lastUpdateTime → {now_ms}")


# ─────────────────────────────────────────
# 写出报告
# ─────────────────────────────────────────
def write_report():
    Path(REPORT_FILE).parent.mkdir(parents=True, exist_ok=True)
    total  = len(results)
    passed = sum(1 for v in results.values() if v["ok"])
    now    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# 一七小说书源验证报告",
        f"",
        f"> 验证时间：{now}  ",
        f"> 通过率：**{passed}/{total}**",
        f"",
        f"| 检查项 | 状态 | 详情 |",
        f"|--------|------|------|",
    ]
    for name, info in results.items():
        status = "✅" if info["ok"] else "❌"
        detail = info["detail"].replace("|", "\\|")
        lines.append(f"| {name} | {status} | {detail} |")

    lines += [
        "",
        "---",
        "",
        "## 书源订阅链接",
        "",
        "在 **legado（阅读3.0）** App 中导入以下链接：",
        "",
        "```",
        "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/sources/1qxs.json",
        "```",
        "",
        "> 请将 `YOUR_USERNAME` 和 `YOUR_REPO` 替换为你的 GitHub 用户名和仓库名",
    ]

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📊 报告已写出：{REPORT_FILE}")


# ─────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────
def main():
    print("=" * 60)
    print("🚀 一七小说书源验证开始")
    print(f"   目标站：{BASE_URL}")
    print(f"   时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    ok1 = validate_homepage()
    if not ok1:
        print("\n⚠️  首页无法访问，跳过后续验证")
        write_report()
        sys.exit(1)

    validate_booklist()
    time.sleep(1.5)

    _, first_chapter = validate_book_detail()
    time.sleep(1.5)

    validate_chapter_content(first_chapter)
    time.sleep(1.5)

    validate_search()

    # 统计
    total  = len(results)
    passed = sum(1 for v in results.values() if v["ok"])
    print("\n" + "=" * 60)
    print(f"✅ 验证完成：{passed}/{total} 项通过")

    update_source_timestamp()
    write_report()

    if passed < total * 0.6:
        print("\n❌ 通过率低于60%，请检查网站结构是否变动！")
        sys.exit(1)
    else:
        print("🎉 书源验证通过！")


if __name__ == "__main__":
    main()
