"""
dedupe_tiles.py
----------------
ใช้จัดการไฟล์ tile ที่ถูกดาวน์โหลดซ้ำจาก Google Drive จนมีชื่อแบบ
    tile_neg_0002.tif
    tile_neg_0002(1).tif
    tile_neg_0002(2).tif

วิธีทำงาน:
1. สแกนทุกไฟล์ .tif ในโฟลเดอร์ tiles/
2. group ไฟล์ที่ "ชื่อฐาน" เดียวกัน (ตัดส่วน (1) (2) ออก)
3. เทียบเนื้อไฟล์ด้วย hash (MD5)
   - ถ้าเนื้อเหมือนกันหมดในกลุ่ม -> เก็บไว้ไฟล์เดียว (ตัวไม่มีวงเล็บก่อน) ลบที่เหลือ
   - ถ้าเนื้อไม่เหมือนกัน -> ไม่ลบ ปริ้นเตือนไว้ให้ไปเช็คเอง (เผื่อเป็นคนละรอบ export จริง ๆ)
4. สรุปผลตอนท้าย: ลบไปกี่ไฟล์, เหลือกี่ไฟล์, มีกลุ่มไหนที่เนื้อไม่ตรงกันบ้าง

วิธีใช้:
    python dedupe_tiles.py "C:\\Users\\minky\\Downloads\\project ayutthaya\\tiles"

ถ้าไม่ใส่ path จะใช้โฟลเดอร์ "tiles" ในตำแหน่งที่รันสคริปต์แทน
ค่าเริ่มต้นคือ "dry run" (แค่แสดงผลไม่ลบจริง) ต้องใส่ --apply ถึงจะลบจริง
"""

import sys
import os
import re
import hashlib
from collections import defaultdict

def get_base_name(filename):
    """
    tile_neg_0002(1).tif -> tile_neg_0002.tif
    tile_neg_0002.tif    -> tile_neg_0002.tif
    """
    name, ext = os.path.splitext(filename)
    base = re.sub(r"\(\d+\)$", "", name)
    return base + ext

def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    apply_changes = "--apply" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--apply"]
    folder = args[0] if args else "tiles"

    if not os.path.isdir(folder):
        print(f"ไม่พบโฟลเดอร์: {folder}")
        return

    files = [f for f in os.listdir(folder) if f.lower().endswith((".tif", ".tiff"))]
    print(f"พบไฟล์ .tif ทั้งหมด {len(files)} ไฟล์ ในโฟลเดอร์ {folder}\n")

    groups = defaultdict(list)
    for f in files:
        base = get_base_name(f)
        groups[base].append(f)

    dup_groups = {b: fs for b, fs in groups.items() if len(fs) > 1}
    print(f"พบชื่อที่ซ้ำกัน (มีมากกว่า 1 ไฟล์ต่อชื่อฐาน): {len(dup_groups)} กลุ่ม\n")

    to_delete = []
    mismatched = []

    for base, fs in dup_groups.items():
        # เรียงให้ไฟล์ไม่มีวงเล็บอยู่แรกสุด (ตัวที่จะเก็บไว้)
        fs_sorted = sorted(fs, key=lambda x: (x != base, x))
        hashes = {f: file_hash(os.path.join(folder, f)) for f in fs_sorted}
        unique_hashes = set(hashes.values())

        if len(unique_hashes) == 1:
            # เนื้อเหมือนกันหมด -> เก็บตัวแรก ลบที่เหลือ
            keep = fs_sorted[0]
            remove = fs_sorted[1:]
            to_delete.extend(remove)
        else:
            # เนื้อไม่ตรงกัน -> ไม่ลบ เตือนไว้
            mismatched.append((base, fs_sorted, hashes))

    print(f"ไฟล์ที่ระบุว่าเป็นซ้ำจริง (เนื้อเหมือนกัน) และจะลบ: {len(to_delete)} ไฟล์")
    if mismatched:
        print(f"\n⚠ พบ {len(mismatched)} กลุ่มที่เนื้อไฟล์ไม่ตรงกัน (อาจเป็นคนละรอบ export จริง) — จะไม่ลบ ต้องเช็คเอง:")
        for base, fs_sorted, hashes in mismatched:
            print(f"  - {base}: {fs_sorted}")

    if not apply_changes:
        print("\n(นี่คือ dry run — ยังไม่ลบไฟล์จริง)")
        print("ถ้าตรวจสอบผลด้านบนแล้วโอเค ให้รันคำสั่งนี้อีกครั้งพร้อม --apply เพื่อลบจริง:")
        print(f'    python dedupe_tiles.py "{folder}" --apply')
    else:
        for f in to_delete:
            os.remove(os.path.join(folder, f))
        print(f"\nลบไฟล์ซ้ำเรียบร้อยแล้ว {len(to_delete)} ไฟล์")

    remaining = len(files) - len(to_delete)
    print(f"\nสรุป: ไฟล์คงเหลือหลังลบซ้ำ (โดยประมาณ) = {remaining} ไฟล์")

if __name__ == "__main__":
    main()
