import json
import random
import ee


# ============================================================
# STEP 1: อ่าน GeoJSON -> แปลงเป็น bounding box ภูมิศาสตร์ (lat/lon)
# ============================================================

def geojson_to_geo_bboxes(geojson_path):
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    class_map = {
        "ruins": 0,
        "archaeological_site": 0,
        "city_gate": 0,
        "fort": 0,
        "castle_wall": 0,
        "ruins;archaeological_site": 0,
    }

    results = []
    for feature in data["features"]:
        geom = feature["geometry"]
        props = feature["properties"]

        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
        elif geom["type"] == "LineString":
            coords = geom["coordinates"]
        else:
            continue

        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]

        results.append({
            "name": props.get("name", "unknown"),
            "class_id": class_map.get(props.get("historic"), 0),
            "min_lon": min(lons), "max_lon": max(lons),
            "min_lat": min(lats), "max_lat": max(lats),
        })

    return results


# ============================================================
# STEP 2: สร้างจุด Negative sample (พื้นที่ที่ไม่มีโบราณสถาน)
# ============================================================

def generate_negative_points(positive_bboxes, n_negatives, min_distance_deg=0.01):
    all_lons = [b["min_lon"] for b in positive_bboxes] + [b["max_lon"] for b in positive_bboxes]
    all_lats = [b["min_lat"] for b in positive_bboxes] + [b["max_lat"] for b in positive_bboxes]
    lon_range = (min(all_lons), max(all_lons))
    lat_range = (min(all_lats), max(all_lats))

    negatives = []
    attempts = 0
    while len(negatives) < n_negatives and attempts < n_negatives * 50:
        attempts += 1
        lon = random.uniform(*lon_range)
        lat = random.uniform(*lat_range)

        too_close = any(
            b["min_lon"] - min_distance_deg <= lon <= b["max_lon"] + min_distance_deg and
            b["min_lat"] - min_distance_deg <= lat <= b["max_lat"] + min_distance_deg
            for b in positive_bboxes
        )
        if not too_close:
            size = 0.001
            negatives.append({
                "name": f"negative_{len(negatives)}",
                "class_id": None,
                "min_lon": lon - size, "max_lon": lon + size,
                "min_lat": lat - size, "max_lat": lat + size,
            })

    print(f"สร้าง negative sample ได้ {len(negatives)} จุด (พยายาม {attempts} ครั้ง)")
    return negatives


# ============================================================
# STEP 3: ดึงภาพดาวเทียมจาก Google Earth Engine
# ============================================================

GEE_PROJECT_ID = "ayutthaya-archaeology"


def init_gee():
    ee.Authenticate()
    ee.Initialize(project=GEE_PROJECT_ID)
    print("เชื่อมต่อ Google Earth Engine สำเร็จ")

def download_tile(min_lon, min_lat, max_lon, max_lat, name,
                   buffer_deg=0.002, jitter_ratio=0.5):
    # จุดศูนย์กลางจริงของ site
    site_center_lon = (min_lon + max_lon) / 2
    site_center_lat = (min_lat + max_lat) / 2

    # สุ่มระยะเยื้องจุดศูนย์กลาง tile ออกจาก site (ไม่ให้ site อยู่กลางภาพเสมอ)
    max_jitter = buffer_deg * jitter_ratio
    jitter_lon = random.uniform(-max_jitter, max_jitter)
    jitter_lat = random.uniform(-max_jitter, max_jitter)

    tile_center_lon = site_center_lon + jitter_lon
    tile_center_lat = site_center_lat + jitter_lat

    half_width = (max_lon - min_lon) / 2 + buffer_deg
    half_height = (max_lat - min_lat) / 2 + buffer_deg

    region = ee.Geometry.Rectangle([
        tile_center_lon - half_width, tile_center_lat - half_height,
        tile_center_lon + half_width, tile_center_lat + half_height
    ])

    collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterBounds(region)
                  .filterDate("2023-01-01", "2024-12-31")
                  .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
                  .sort("CLOUDY_PIXEL_PERCENTAGE"))

    image = collection.first().select(["B4", "B3", "B2"])

    task = ee.batch.Export.image.toDrive(
        image=image,
        description=f"tile_{name}",
        folder="satellite_tiles",
        region=region,
        scale=10,
        fileFormat="GeoTIFF"
    )
    task.start()
    return task


def download_all_tiles(all_bboxes, limit=None, prefix="site"):
    items = all_bboxes[:limit] if limit else all_bboxes
    tasks = []
    tile_registry = []

    for idx, item in enumerate(items):
        safe_id = f"{prefix}_{idx:04d}"
        task = download_tile(
            item["min_lon"], item["min_lat"],
            item["max_lon"], item["max_lat"],
            name=safe_id
        )
        tasks.append(task)
        tile_registry.append({
            "id": safe_id,
            "min_lon": item["min_lon"], "min_lat": item["min_lat"],
            "max_lon": item["max_lon"], "max_lat": item["max_lat"],
            "class_id": item["class_id"],
            "original_name": item["name"]
        })
        print(f"send: {safe_id} ({item['name']})")

    registry_path = f"tile_registry_{prefix}.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(tile_registry, f, ensure_ascii=False, indent=2)

    print(f"total tasks sent: {len(tasks)}")
    print(f"saved registry to {registry_path}")
    return tasks
# ============================================================
# STEP 4: แปลง geo bbox -> YOLO format (ใช้ภาพ .tif จริงที่มีแล้ว)
# ============================================================

import rasterio
import os
import shutil
import random


def geo_bbox_to_yolo_line(min_lon, min_lat, max_lon, max_lat, raster_path, class_id):
    if class_id is None:
        return None  # negative sample = ไม่มีวัตถุ ไม่มีบรรทัด label

    with rasterio.open(raster_path) as src:
        # แปลงพิกัด lon/lat (WGS84) -> ระบบพิกัดของภาพ (เช่น UTM) ก่อนคำนวณตำแหน่งพิกเซล
        from rasterio.warp import transform as warp_transform

        xs, ys = warp_transform("EPSG:4326", src.crs, [min_lon, max_lon], [min_lat, max_lat])
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        row_min, col_min = src.index(min_x, max_y)
        row_max, col_max = src.index(max_x, min_y)
        img_width, img_height = src.width, src.height

        x_center = ((col_min + col_max) / 2) / img_width
        y_center = ((row_min + row_max) / 2) / img_height
        box_width = abs(col_max - col_min) / img_width
        box_height = abs(row_max - row_min) / img_height

        MIN_BOX_SIZE = 0.05
        box_width = max(box_width, MIN_BOX_SIZE)
        box_height = max(box_height, MIN_BOX_SIZE)

        # กันค่าหลุดขอบ (clip ให้อยู่ในช่วง 0-1 เสมอ)
        x_center = min(max(x_center, 0), 1)
        y_center = min(max(y_center, 0), 1)
        box_width = min(max(box_width, 0), 1)
        box_height = min(max(box_height, 0), 1)

        return f"{class_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"

def build_tile_records(tiles_dir="tiles"):
    records = []
    for prefix in ["site", "neg"]:
        registry_path = f"tile_registry_{prefix}.json"
        if not os.path.exists(registry_path):
            print(f"ไม่พบ {registry_path} ข้าม prefix นี้")
            continue

        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        for item in registry:
            tif_path = os.path.join(tiles_dir, f"tile_{item['id']}.tif")
            if os.path.exists(tif_path):
                records.append({**item, "tif_path": tif_path})
            else:
                print(f"ไม่พบไฟล์: {tif_path} ข้ามไป")

    print(f"จับคู่ได้ทั้งหมด {len(records)} tile (ตรงกับพิกัดจริง 100%)")
    return records

# ============================================================
# STEP 5: จัดโครงสร้างไฟล์สำหรับ YOLO (train/val split)
# ============================================================

def prepare_yolo_dataset(records, output_dir="yolo_dataset", split_ratio=0.8):
    import numpy as np
    from PIL import Image

    for split in ["train", "val"]:
        os.makedirs(f"{output_dir}/images/{split}", exist_ok=True)
        os.makedirs(f"{output_dir}/labels/{split}", exist_ok=True)

    random.shuffle(records)
    split_idx = max(1, int(len(records) * split_ratio))
    train_data, val_data = records[:split_idx], records[split_idx:]

    for split, items in [("train", train_data), ("val", val_data)]:
        for item in items:
            tif_path = item["tif_path"]
            base_name = os.path.basename(tif_path).replace(".tif", "")
            jpg_name = f"{base_name}.jpg"
            img_dst = f"{output_dir}/images/{split}/{jpg_name}"

            # แปลง .tif -> .jpg (YOLOv8 อ่าน .tif ไม่ได้โดยตรง)
            with rasterio.open(tif_path) as src:
                arr = src.read([1, 2, 3])  # อ่าน 3 band แรก (R, G, B)
                arr = np.transpose(arr, (1, 2, 0))  # (band, h, w) -> (h, w, band)

                # normalize ค่าพิกเซลให้อยู่ในช่วง 0-255 (ภาพดาวเทียมมักมีค่าสูงกว่า 255)
                arr = arr.astype(np.float32)
                p2, p98 = np.percentile(arr, (2, 98))  # ตัด outlier ทำให้ภาพคมชัดขึ้น
                arr = np.clip((arr - p2) / (p98 - p2 + 1e-6) * 255, 0, 255).astype(np.uint8)

                Image.fromarray(arr).save(img_dst, quality=95)

            yolo_line = geo_bbox_to_yolo_line(
                item["min_lon"], item["min_lat"], item["max_lon"], item["max_lat"],
                tif_path, item["class_id"]
            )
            label_path = f"{output_dir}/labels/{split}/{base_name}.txt"
            with open(label_path, "w") as f:
                if yolo_line:
                    f.write(yolo_line + "\n")

    yaml_content = f"""path: {os.path.abspath(output_dir)}
train: images/train
val: images/val
names:
  0: ancient_site
"""
    with open(f"{output_dir}/data.yaml", "w") as f:
        f.write(yaml_content)

    print(f"Train: {len(train_data)} | Val: {len(val_data)}")
    print(f"Dataset พร้อมใช้ที่: {os.path.abspath(output_dir)}")
# ============================================================
# STEP 6: เทรนโมเดล YOLOv8
# ============================================================

def train_model(data_yaml_path="yolo_dataset/data.yaml", epochs=50):
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")  # เริ่มจาก pretrained weight ขนาดเล็กสุด

    results = model.train(
        data=data_yaml_path,
        epochs=epochs,
        imgsz=640,
        batch=16,
        patience=20,
        project="ancient_site_detection",
        name="run3_gpu",
        augment=True,
        device=0,
    )
    return model, results

def evaluate_model(model_path="runs/detect/ancient_site_detection/run3_gpu/weights/best.pt"):
    from ultralytics import YOLO
    model = YOLO(model_path)
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50}")
    print(f"mAP50-95: {metrics.box.map}")
    return metrics

if __name__ == "__main__":
    GEOJSON_PATH = "ayutthaya_ancient_sites_filtered.geojson"

    positive_bboxes = geojson_to_geo_bboxes(GEOJSON_PATH)
    print(f"Positive samples: {len(positive_bboxes)}")

    negative_bboxes = generate_negative_points(positive_bboxes, n_negatives=len(positive_bboxes))

    # ดึงภาพใหม่พร้อม registry (ต้องรันใหม่เพราะของเดิมไม่มี registry)
    #init_gee()
    #download_all_tiles(positive_bboxes, limit=500, prefix="site")
    #download_all_tiles(negative_bboxes, limit=500, prefix="neg")

    # STEP 4-6 — comment ไว้ก่อน จนกว่าจะดาวน์โหลดภาพใหม่ครบจาก Google Drive
    records = build_tile_records(tiles_dir="tiles")
    prepare_yolo_dataset(records)
    model, results = train_model(epochs=50)
    evaluate_model()