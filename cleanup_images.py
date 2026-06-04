#!/usr/bin/env python3
"""每月清理 3 个月前的论文图片"""
import os, shutil, time
from pathlib import Path

IMAGES_DIR = Path("D:/Obsidian/20_Research/Papers/images")
if not IMAGES_DIR.exists():
    print("Images dir not found, nothing to clean.")
    exit(0)

cutoff = time.time() - 90 * 24 * 3600  # 90 days
cleaned = 0
for subdir in IMAGES_DIR.iterdir():
    if subdir.is_dir():
        mtime = os.path.getmtime(subdir)
        if mtime < cutoff:
            shutil.rmtree(subdir)
            cleaned += 1
            print(f"Cleaned: {subdir.name}")

print(f"Done. Cleaned {cleaned} old image folders.")
