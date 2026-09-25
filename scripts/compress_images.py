#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压缩 src/ 下的老师照片：统一转 JPEG、按最长边缩放，并同步更新 teachers.json 与 .md 引用。

用法:
  python compress_images.py                 # 默认最长边 1000px, 质量 82
  python compress_images.py --max 800 --quality 78
"""

import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(BASE_DIR, "src")
JSON_PATH = os.path.join(SRC_DIR, "teachers.json")

EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def compress_one(path, max_side, quality):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)

    base = os.path.splitext(path)[0]
    target = base + ".jpg"
    img.save(target, "JPEG", quality=quality, optimize=True, progressive=True)

    if os.path.normcase(target) != os.path.normcase(path):
        os.remove(path)
    return path, target


def main():
    p = argparse.ArgumentParser(description="压缩老师照片")
    p.add_argument("--max", type=int, default=1000, help="最长边像素，默认 1000")
    p.add_argument("--quality", type=int, default=82, help="JPEG 质量，默认 82")
    args = p.parse_args()

    files = []
    for root, _dirs, names in os.walk(SRC_DIR):
        for n in names:
            if n.lower().endswith(EXTS):
                files.append(os.path.join(root, n))

    before = sum(os.path.getsize(f) for f in files)
    mapping = {}  # old_rel(posix) -> new_rel(posix)
    done = failed = 0
    for f in files:
        try:
            old_path = f
            _, new_path = compress_one(f, args.max, args.quality)
            old_rel = os.path.relpath(old_path, SRC_DIR).replace("\\", "/")
            new_rel = os.path.relpath(new_path, SRC_DIR).replace("\\", "/")
            mapping[old_rel] = new_rel
            done += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  [跳过] {f}: {e}")

    # 更新 teachers.json
    if os.path.exists(JSON_PATH):
        data = json.load(open(JSON_PATH, encoding="utf-8"))
        for r in data:
            r["images"] = [mapping.get(p, p) for p in r.get("images", [])]
        json.dump(data, open(JSON_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 更新 .md 里的图片引用（basename 替换即可覆盖两种写法）
    changed_md = 0
    for md in glob.glob(os.path.join(SRC_DIR, "**", "*.md"), recursive=True):
        text = open(md, encoding="utf-8").read()
        new = text
        for old_rel, new_rel in mapping.items():
            ob = os.path.basename(old_rel)
            nb = os.path.basename(new_rel)
            if ob != nb:
                new = new.replace(ob, nb)
        if new != text:
            open(md, "w", encoding="utf-8").write(new)
            changed_md += 1

    after = sum(os.path.getsize(os.path.join(SRC_DIR, r)) for r in mapping.values())
    print(f"[完成] 压缩 {done} 张（失败 {failed}），最长边 {args.max}, 质量 {args.quality}")
    print(f"       {before/1048576:.1f} MB -> {after/1048576:.1f} MB "
          f"(省 {(1 - after/before)*100:.0f}%)")
    print(f"       重命名 {sum(1 for a, b in mapping.items() if a != b)} 张，更新 md {changed_md} 个")
    print("       接着运行: python build_html.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
