#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爬取广州商学院信息技术与工程学院「学院队伍」教师简介与照片。

用法:
  python crawl_teachers.py                # 只爬「教学名师」栏目
  python crawl_teachers.py --all          # 爬取学院队伍下所有栏目（推荐，选导师用）
  python crawl_teachers.py --url URL      # 指定栏目首页地址
  python crawl_teachers.py --out mydir    # 指定输出目录

依赖: requests, pyquery (项目 requirements.txt 已含)
"""

import argparse
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from pyquery import PyQuery as pq

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_URL = "https://site.gcc.edu.cn/xydw/jxms/index.htm"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BAD_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def safe_name(text):
    text = BAD_CHARS.sub("_", (text or "").strip())
    return text.strip(". ") or "未命名"


def fetch(session, url, timeout=30, retries=3):
    last = None
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = "utf-8"
            return r.text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.8 * (i + 1))
    raise RuntimeError(f"请求失败 {url}: {last}")


def last_page_index(doc):
    end = doc("a.gp-page-end")
    if not end:
        return 0
    href = end.attr("href") or end.attr("nohref") or "index.htm"
    m = re.search(r"index(\d+)\.htm", href)
    return int(m.group(1)) if m else 0


def discover_sections(entry_url, html):
    doc = pq(html)
    seen, sections = set(), []
    for a in doc("ul.gpColumnTitle a").items():
        name = a.text().strip()
        href = a.attr("href")
        if not name or not href:
            continue
        url = urljoin(entry_url, href)
        if url in seen:
            continue
        seen.add(url)
        sections.append((name, url))
    return sections


def collect_items(session, section_name, index_url, delay, timeout):
    section_dir = index_url.rsplit("/", 1)[0] + "/"
    items, last = [], None
    for page in range(0, 200):
        page_url = urljoin(
            section_dir, "index.htm" if page == 0 else f"index{page}.htm"
        )
        doc = pq(fetch(session, page_url, timeout))
        links = doc("a.gpArticleTitle")
        if links.length == 0:
            break
        if last is None:
            last = last_page_index(doc)
        for a in links.items():
            name = a.text().strip()
            href = a.attr("href")
            if not name or not href:
                continue
            items.append((name, urljoin(page_url, href)))
        if page >= last:
            break
        time.sleep(delay)
    return items


def download_image(session, url, dest_noext, timeout):
    try:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            ctype = r.headers.get("Content-Type", "").split(";")[0].strip()
            ext = {
                "image/png": ".png",
                "image/gif": ".gif",
                "image/webp": ".webp",
                "image/bmp": ".bmp",
            }.get(ctype, ".jpg")
        path = dest_noext + ext
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception as e:  # noqa: BLE001
        print(f"    [图片失败] {url} -> {e}")
        return None


def crawl_detail(session, section, name, detail_url, out_root, delay, timeout):
    html = fetch(session, detail_url, timeout)
    doc = pq(html)

    title = (doc("h3#shareTitle").text() or name).strip() or name
    date = ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", doc("span.date").text() or "")
    if m:
        date = m.group(0)

    article = doc("div.gp-article1")
    if article.length == 0:
        article = doc("div.gp-article")

    paras = article("p")
    if paras.length:
        text = "\n\n".join(
            p.text().strip() for p in paras.items() if p.text().strip()
        )
    else:
        text = article.text().strip()

    img_urls = []
    for img in article("img").items():
        src = img.attr("src")
        if src:
            img_urls.append(urljoin(detail_url, src))
    meta_img = doc('meta[name="Image"]').attr("content")
    if meta_img and meta_img not in ("null", ""):
        u = urljoin(detail_url, meta_img)
        if u not in img_urls:
            img_urls.append(u)

    sec_dir = os.path.join(out_root, safe_name(section))
    os.makedirs(sec_dir, exist_ok=True)
    base = safe_name(title)

    saved_imgs = []
    for i, url in enumerate(img_urls):
        dest = os.path.join(sec_dir, base if i == 0 else f"{base}_{i + 1}")
        p = download_image(session, url, dest, timeout)
        if p:
            saved_imgs.append(p)
        time.sleep(delay)

    md_path = os.path.join(sec_dir, base + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"- 栏目：{section}\n")
        if date:
            f.write(f"- 日期：{date}\n")
        f.write(f"- 原文：{detail_url}\n")
        if saved_imgs:
            f.write("- 照片：\n")
            for p in saved_imgs:
                f.write(f"  - {os.path.relpath(p, out_root)}\n")
        f.write("\n")
        if saved_imgs:
            f.write(f"![{title}]({os.path.relpath(saved_imgs[0], sec_dir)})\n\n")
        f.write(text or "（无简介正文）")
        f.write("\n")

    print(f"    OK {title} ({len(saved_imgs)} 图, {len(text)} 字)")
    return {
        "section": section,
        "name": title,
        "date": date,
        "url": detail_url,
        "text": text,
        "images": [os.path.relpath(p, out_root).replace("\\", "/") for p in saved_imgs],
    }


def main():
    p = argparse.ArgumentParser(description="爬取学院队伍教师简介与照片")
    p.add_argument("--url", default=DEFAULT_URL, help="栏目首页（默认教学名师）")
    p.add_argument("--all", action="store_true", help="爬取学院队伍下所有栏目")
    p.add_argument("--out", default=os.path.join(BASE_DIR, "src"), help="输出目录")
    p.add_argument("--delay", type=float, default=0.4, help="请求间隔秒")
    p.add_argument("--timeout", type=float, default=30, help="请求超时秒")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    entry_html = fetch(session, args.url, args.timeout)
    if args.all:
        sections = discover_sections(args.url, entry_html)
        print(f"[全量] 共发现 {len(sections)} 个栏目")
    else:
        col = pq(entry_html)('meta[name="ColumnName"]').attr("content") or "教学名师"
        sections = [(col.strip(), args.url)]

    records = []
    all_items = []
    seen_detail = set()
    for section, url in sections:
        print(f"[栏目] {section} -> {url}")
        items = collect_items(session, section, url, args.delay, args.timeout)
        print(f"  共 {len(items)} 人")
        for name, detail_url in items:
            if detail_url in seen_detail:
                continue
            seen_detail.add(detail_url)
            all_items.append((section, name, detail_url))

    print(f"\n[抓取] 共 {len(all_items)} 条简介\n")
    for i, (section, name, detail_url) in enumerate(all_items, 1):
        print(f"  ({i}/{len(all_items)}) {section} · {name}")
        try:
            records.append(
                crawl_detail(
                    session, section, name, detail_url, args.out,
                    args.delay, args.timeout,
                )
            )
        except Exception as e:  # noqa: BLE001
            print(f"    [失败] {e}")
        time.sleep(args.delay)

    import json

    with open(os.path.join(args.out, "teachers.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(os.path.join(args.out, "index.md"), "w", encoding="utf-8") as f:
        f.write("# 学院队伍 教师名录\n\n")
        f.write(f"共 {len(records)} 人\n\n")
        f.write(f"| 栏目 | 姓名 | 日期 | 照片 | 简介 |\n|---|---|---|---|---|\n")
        for r in sorted(records, key=lambda x: (x["section"], x["name"])):
            photo = r["images"][0] if r["images"] else ""
            f.write(
                f"| {r['section']} | [{r['name']}]({r['section']}/{safe_name(r['name'])}.md)"
                f" | {r['date']} | {photo} | [原文]({r['url']}) |\n"
            )

    print(f"\n[完成] {len(records)} 人 -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
