# Ayutthaya HeritageScan

**Feasibility Study: Detecting Archaeological Sites in Ayutthaya from Sentinel-2 Imagery with YOLOv8**

## 1. Project Overview

Ayutthaya HeritageScan is a geospatial AI feasibility study that tests whether publicly available data are sufficient to train an object detection model for archaeological sites in the Ayutthaya area. Ayutthaya is the historical context of the proposed high-speed rail corridor, where infrastructure development raises questions about heritage identification and preservation.

The project combines archaeological reference data from OpenStreetMap (OSM), Sentinel-2 satellite imagery, and the YOLOv8 object detection model.

**Key finding:** publicly available labeled data are insufficient to train a reliable detection model (see Sections 6 and 7).

## 2. Objectives

- Build an object detection dataset from geographic coordinates and bounding boxes.
- Train YOLOv8 on Sentinel-2 RGB imagery to detect archaeological features.
- Evaluate model performance and identify the limits of publicly available archaeological data.

## 3. Study Area

The Ayutthaya area, Thailand. The study area is defined by the spatial extent of the OSM archaeological features used as reference data. The high-speed rail route geometry was not used in sampling or analysis.

## 4. Data Sources

| Data | Source | Description |
|---|---|---|
| Archaeological reference data | OpenStreetMap (OSM) | Locations and classes from the `historic` and `name` tags |
| Satellite imagery | Sentinel-2 via Google Earth Engine | `COPERNICUS/S2_SR_HARMONIZED`, 2023-01-01 to 2024-12-31 |
| Negative samples | Generated programmatically | Random locations at least 0.01 degrees from known reference sites |
| Pretrained model | Ultralytics YOLOv8n | `yolov8n.pt` |

### 4.1 Archaeological Reference Data

Collected from OSM and filtered to these `historic` values: `ruins`, `archaeological_site`, `city_gate`, `fort`, `castle_wall`. Stored as `ayutthaya_ancient_sites_filtered.geojson`. All classes are merged into a single class (`ancient_site`). Data © OpenStreetMap contributors (see References).

### 4.2 Satellite Imagery

- **Dataset:** `COPERNICUS/S2_SR_HARMONIZED`
- **Period:** 2023-01-01 to 2024-12-31
- **Cloud cover:** at most 10%
- **Bands:** B4, B3, B2 (RGB), 10 m resolution
- **Export:** GeoTIFF, converted to JPG with 2-98 percentile contrast stretch for training

### 4.3 Negative Samples

Random points sampled inside the bounding rectangle of all positive sites, at least 0.01 degrees from any known site. One negative sample is generated per positive sample.

### 4.4 Pretrained Model

YOLOv8n (Ultralytics), used as the starting weights for training.

## 5. Methodology

1. **Geospatial preparation:** filter OSM features and extract geographic bounding boxes from polygons and lines.
2. **Image acquisition:** filter Sentinel-2 by date and cloud cover, then export RGB tiles via Google Earth Engine.
3. **Dataset preparation:** pair tiles with labels, convert geographic bounding boxes to YOLO format, and split randomly 80/20 into train and validation sets.
4. **Training:** fine-tune YOLOv8n (50 epochs, image size 640, batch 16, early-stopping patience 20).
5. **Evaluation:** Precision, Recall, mAP@50, mAP@50-95.

## 6. Results

| Metric | Value |
|---|---|
| Precision | [from results.csv] |
| Recall | [from results.csv] |
| mAP@50 | [from results.csv] |
| mAP@50-95 | [from results.csv] |

Training curves, confusion matrix, and PR/F1 curves are included in this repository.

**Interpretation:** [1-2 sentences, e.g. the model does not generalize reliably, and the likely causes are the limits listed in Section 7.]

Detections are model predictions, not confirmed discoveries, and require independent field verification.

## 7. Limitations

- **Limited reference data:** OSM does not cover all archaeological locations, and its completeness varies by area.
- **Incomplete ground truth:** places with no recorded site are not confirmed to be free of remains, so negative samples may contain unrecorded sites.
- **Spatial resolution:** 10 m Sentinel-2 pixels cannot resolve small or subtle features.
- **Approximate annotations:** boxes come from OSM geometry with a minimum size of 5% of the image, and tiles are randomly offset from site centers, so labels are not exact site extents.
- **Evaluation design:** the train/val split is random at tile level, so spatially adjacent tiles may fall in both sets.
- **Single class:** all feature types are merged into one class.

This project is a feasibility study, not a validated system for discovering unknown archaeological sites.

## 8. Technology Stack

| Category | Tools |
|---|---|
| Language | Python |
| Satellite data | Sentinel-2, Google Earth Engine (`earthengine-api`) |
| Geospatial processing | GeoJSON, `rasterio` |
| Deep learning | YOLOv8, Ultralytics |
| Image processing | NumPy, Pillow |
| Evaluation | Precision, Recall, mAP |

## 9. References

- OpenStreetMap: https://www.openstreetmap.org/
- OpenStreetMap copyright and attribution: https://www.openstreetmap.org/copyright
- Sentinel-2 SR Harmonized (Google Earth Engine): https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
- Ultralytics YOLOv8: https://docs.ultralytics.com/models/yolov8/



# Ayutthaya HeritageScan

**การศึกษาความเป็นไปได้ในการตรวจจับแหล่งโบราณคดีในอยุธยาจากภาพดาวเทียม Sentinel-2 ด้วย YOLOv8**

## 1. ภาพรวมโครงการ

โครงการนี้ทดสอบว่าข้อมูลสาธารณะเพียงพอหรือไม่ที่จะฝึกโมเดล object detection ให้ตรวจจับแหล่งโบราณคดีในพื้นที่อยุธยา ซึ่งเป็นบริบทของแนวรถไฟความเร็วสูง โดยใช้ข้อมูลโบราณสถานจาก OpenStreetMap (OSM), ภาพดาวเทียม Sentinel-2 และโมเดล YOLOv8

**ข้อค้นพบหลัก:** ข้อมูล label ที่เปิดเผยต่อสาธารณะไม่เพียงพอสำหรับฝึกโมเดลที่เชื่อถือได้ (ดูหัวข้อที่ 5 และ 6)

## 2. พื้นที่ศึกษา

พื้นที่อยุธยา โดยกำหนดขอบเขตจากการกระจายตัวของโบราณสถานใน OSM ที่ใช้เป็นข้อมูลอ้างอิง ไม่ได้ใช้แนวเส้นทางรถไฟความเร็วสูงในการสุ่มตัวอย่างหรือวิเคราะห์

## 3. แหล่งข้อมูล

| ข้อมูล | แหล่งที่มา | รายละเอียด |
|---|---|---|
| ข้อมูลโบราณสถาน | OpenStreetMap (OSM) | tag `historic`: `ruins`, `archaeological_site`, `city_gate`, `fort`, `castle_wall` จัดเป็นคลาสเดียว (`ancient_site`) เก็บในไฟล์ `ayutthaya_ancient_sites_filtered.geojson` |
| ภาพดาวเทียม | Sentinel-2 ผ่าน Google Earth Engine | `COPERNICUS/S2_SR_HARMONIZED` ช่วง 2023-01-01 ถึง 2024-12-31 เมฆไม่เกิน 10% band B4/B3/B2 ความละเอียด 10 เมตร |
| ตัวอย่างเชิงลบ (negative samples) | สร้างด้วยโค้ด | สุ่มจุดในกรอบพื้นที่ของโบราณสถาน ห่างจากโบราณสถานที่รู้จักอย่างน้อย 0.01 องศา จำนวนเท่ากับตัวอย่างเชิงบวก |
| โมเดลตั้งต้น | Ultralytics YOLOv8n | `yolov8n.pt` |

ข้อมูลโบราณสถาน © OpenStreetMap contributors

## 4. วิธีการ

1. กรองข้อมูล OSM และแปลงเป็น bounding box เชิงพิกัด
2. ดึงภาพ RGB จาก Sentinel-2 ผ่าน Google Earth Engine
3. แปลง bounding box เป็นรูปแบบ YOLO และแบ่ง train/val แบบสุ่ม 80/20
4. ฝึก YOLOv8n 50 epochs, ขนาดภาพ 640, batch 16
5. ประเมินด้วย Precision, Recall, mAP@50, mAP@50-95

## 5. ผลลัพธ์

| ตัวชี้วัด | ค่า |
|---|---|
| Precision | [จาก results.csv] |
| Recall | [จาก results.csv] |
| mAP@50 | [จาก results.csv] |
| mAP@50-95 | [จาก results.csv] |

**สรุปผล:** [1-2 ประโยค เช่น โมเดลไม่สามารถ generalize ได้อย่างน่าเชื่อถือ สาเหตุน่าจะมาจากข้อจำกัดในหัวข้อที่ 6]

ผลการตรวจจับเป็นเพียงการทำนายของโมเดล ไม่ใช่การค้นพบที่ยืนยันแล้ว และต้องตรวจสอบภาคสนามเพิ่มเติม

## 6. ข้อจำกัด

- **ข้อมูลอ้างอิงมีจำกัด:** OSM ไม่ครอบคลุมโบราณสถานทุกแห่ง และความครบถ้วนต่างกันตามพื้นที่
- **ground truth ไม่สมบูรณ์:** พื้นที่ที่ไม่มีบันทึกไม่ได้แปลว่าไม่มีโบราณสถาน ตัวอย่างเชิงลบจึงอาจปนกับแหล่งที่ยังไม่ถูกบันทึก
- **ความละเอียดภาพ:** Sentinel-2 ที่ 10 เมตร ไม่เห็นโครงสร้างขนาดเล็กหรือไม่ชัดเจน
- **annotation เป็นค่าประมาณ:** กล่องมีขนาดขั้นต่ำ 5% ของภาพ และ tile ถูกสุ่มเลื่อนจากจุดศูนย์กลางของแหล่ง
- **การแบ่งข้อมูล:** แบ่ง train/val แบบสุ่มระดับ tile tile ที่อยู่ติดกันอาจตกอยู่ทั้งสองชุด
- **คลาสเดียว:** รวมโบราณสถานทุกประเภทเป็นคลาสเดียว

โครงการนี้เป็นการศึกษาความเป็นไปได้ ไม่ใช่ระบบที่ผ่านการตรวจสอบเพื่อค้นหาแหล่งโบราณคดีใหม่

## 7. เทคโนโลยีที่ใช้

Python, Google Earth Engine (`earthengine-api`), `rasterio`, GeoJSON, YOLOv8 (Ultralytics), NumPy, Pillow
