"""
为 Dashboard SINOR 风格架构图生成 7 张缩略图
把 output/ 里的大图压缩到 480x300 保存到 app/resources/thumbs/
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
THUMB_DIR = os.path.join(ROOT, "app", "resources", "thumbs")

# (目标文件名, 源文件路径) — 对应 SINOR 7 模块
MAPPING = [
    ("01_dashboard.png",   os.path.join(OUTPUT_DIR, "全字段_1_NRMSE对比.png")),
    ("02_monitoring.png",  os.path.join(OUTPUT_DIR, "属性总览_2_独立子图.png")),
    ("03_alarms.png",      os.path.join(OUTPUT_DIR, "属性总览_4_异常事件放大.png")),
    ("04_forecast.png",    os.path.join(OUTPUT_DIR, "多属性_1_预测曲线.png")),
    ("05_root_cause.png",  os.path.join(OUTPUT_DIR, "属性总览_3_统计与相关性.png")),
    ("06_lifetime.png",    os.path.join(OUTPUT_DIR, "horizon_2_MAE曲线.png")),
    ("07_health.png",      os.path.join(OUTPUT_DIR, "全字段_2_判据象限.png")),
]

TARGET_W, TARGET_H = 480, 300


def main():
    os.makedirs(THUMB_DIR, exist_ok=True)
    for dst_name, src_path in MAPPING:
        if not os.path.exists(src_path):
            print(f"[SKIP] 源文件不存在: {src_path}")
            continue
        im = Image.open(src_path)
        # 按目标宽高比裁切
        src_w, src_h = im.size
        target_ratio = TARGET_W / TARGET_H
        src_ratio = src_w / src_h
        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            im = im.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            top = (src_h - new_h) // 2
            im = im.crop((0, top, src_w, top + new_h))
        im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        if im.mode != "RGB":
            im = im.convert("RGB")
        dst = os.path.join(THUMB_DIR, dst_name)
        im.save(dst, "JPEG", quality=85, optimize=True)
        size_kb = os.path.getsize(dst) / 1024
        print(f"[OK] {dst_name} ({size_kb:.1f} KB)")

    # 重命名为 .jpg 扩展更诚实
    for dst_name, _ in MAPPING:
        png_path = os.path.join(THUMB_DIR, dst_name)
        jpg_path = png_path.replace(".png", ".jpg")
        if os.path.exists(png_path) and png_path != jpg_path:
            os.rename(png_path, jpg_path)
    print(f"\n输出目录: {THUMB_DIR}")


if __name__ == "__main__":
    main()
