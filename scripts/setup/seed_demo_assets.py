import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

IMAGES_DIR = settings.DEMO_DIR / "images"
EXPECTED_DIR = settings.DEMO_DIR / "expected"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

def create_demo_assets():
    # 1. Compliant Shampoo (Cosmetics)
    img_shampoo = Image.new("RGB", (900, 1100), color=(248, 250, 252))
    draw = ImageDraw.Draw(img_shampoo)
    
    # Title & Branding header
    draw.rectangle([0, 0, 900, 140], fill=(16, 185, 129))
    draw.text((40, 35), "NATURE'S ESSENCE HERBAL SHAMPOO", fill=(255, 255, 255))
    draw.text((40, 85), "Deep Nourishment & Scalp Care | For All Hair Types", fill=(209, 250, 229))

    # Declarations Box
    draw.rectangle([40, 180, 860, 1020], outline=(203, 213, 225), width=2)
    
    lines_shampoo = [
        "Generic Name: Herbal Hair Shampoo",
        "Net Quantity: 200 ml",
        "M.R.P. : Rs. 249.00 (Incl. of all taxes)",
        "Month & Year of Mfg: 06/2026",
        "Best Before: 24 Months from Mfd Date",
        "Batch No.: BATCH-HERB-9842",
        "Manufactured by: Herbal Care India Pvt. Ltd.",
        "Address: Plot 42, Sector 5, Industrial Area, Haridwar, PIN 249403",
        "Country of Origin: India",
        "Consumer Care Details:",
        "Helpline: 1800-200-4567 | Email: customercare@herbalindia.com",
        "Postal Address: Consumer Care Cell, Herbal Care India, Haridwar, PIN 249403"
    ]
    
    y = 220
    for l in lines_shampoo:
        draw.text((80, y), l, fill=(15, 23, 42))
        y += 62

    img_shampoo.save(IMAGES_DIR / "compliant_shampoo.png", quality=95)

    # 2. Missing Consumer Care Biscuit (Food)
    img_biscuit = Image.new("RGB", (900, 1100), color=(255, 251, 235))
    draw = ImageDraw.Draw(img_biscuit)
    
    draw.rectangle([0, 0, 900, 140], fill=(217, 119, 6))
    draw.text((40, 35), "CRUNCHY GOLD BUTTER COOKIES", fill=(255, 255, 255))
    draw.text((40, 85), "Rich Butter Flavour Biscuits", fill=(254, 243, 199))

    draw.rectangle([40, 180, 860, 950], outline=(252, 211, 77), width=2)
    
    lines_biscuit = [
        "Generic Name: Butter Cookies Biscuits",
        "Net Weight: 100 g",
        "MRP: Rs. 30.00 (Inclusive of all taxes)",
        "Date of Manufacture: 05/2026",
        "Best Before: 6 Months from Packaging",
        "Manufactured by: Crunchy Bakes Foods Ltd.",
        "Factory Address: 12 Bakery Road, Food Park, Pune, Maharashtra - 411028",
        "Country of Origin: India"
    ]
    
    y = 220
    for l in lines_biscuit:
        draw.text((80, y), l, fill=(69, 26, 3))
        y += 75

    img_biscuit.save(IMAGES_DIR / "missing_consumer_care_biscuit.png", quality=95)

    # 3. Blurry Cooking Oil (Fail Quality)
    img_oil = Image.new("RGB", (800, 1000), color=(254, 240, 138))
    draw = ImageDraw.Draw(img_oil)
    draw.text((50, 50), "PURE GOLD SUNFLOWER OIL 1 L", fill=(113, 63, 18))
    draw.text((50, 150), "Net Quantity: 1 L", fill=(113, 63, 18))
    draw.text((50, 250), "MRP: Rs. 165.00", fill=(113, 63, 18))
    draw.text((50, 350), "Packed by: Gold Agro Industries", fill=(113, 63, 18))
    blurred_oil = img_oil.filter(ImageFilter.GaussianBlur(radius=14))
    blurred_oil.save(IMAGES_DIR / "blurry_label_oil.png", quality=80)

    # 4. Multipack Snack (Packaged Commodity)
    img_snack = Image.new("RGB", (900, 1100), color=(254, 242, 242))
    draw = ImageDraw.Draw(img_snack)
    draw.rectangle([0, 0, 900, 140], fill=(220, 38, 38))
    draw.text((40, 35), "SPICY CRUNCH POTATO CHIPS (DUO PACK)", fill=(255, 255, 255))
    draw.text((40, 85), "Twin Pack Value Offer", fill=(254, 202, 202))

    draw.rectangle([40, 180, 860, 1020], outline=(248, 113, 113), width=2)
    lines_snack = [
        "Generic Name: Potato Chips Snacks",
        "Net Quantity: 2 x 50 g (Total: 100 g)",
        "MRP: Rs. 40.00 (Incl. of all taxes)",
        "Month of Pkd: 04/2026",
        "Best Before: 4 Months from Pkd",
        "Manufactured & Packed by: SnackTime Foods Pvt Ltd",
        "Address: Plot 9, Express Highway, Noida, UP - 201301",
        "Country of Origin: India",
        "Consumer Care Helpline: 1800-444-1234",
        "Consumer Email: support@snacktimefoods.in"
    ]
    y = 220
    for l in lines_snack:
        draw.text((80, y), l, fill=(127, 29, 29))
        y += 70
    img_snack.save(IMAGES_DIR / "non_standard_qty_snack.png", quality=95)

    # 5. Electronics (USB-C Fast Charger)
    img_elec = Image.new("RGB", (900, 1100), color=(241, 245, 249))
    draw = ImageDraw.Draw(img_elec)
    draw.rectangle([0, 0, 900, 140], fill=(30, 41, 59))
    draw.text((40, 35), "VOLTX 65W GaN USB-C FAST CHARGER", fill=(255, 255, 255))
    draw.text((40, 85), "Universal Power Adapter with PD 3.0", fill=(148, 163, 184))

    draw.rectangle([40, 180, 860, 1020], outline=(148, 163, 184), width=2)
    lines_elec = [
        "Generic Name: Fast Power Adapter",
        "Net Quantity: 1 N",
        "MRP: Rs. 799.00 (Inclusive of all taxes)",
        "Month & Year of Import: 03/2026",
        "Imported & Marketed by: Apex Tech Solutions India Pvt Ltd",
        "Registered Office: 501 Cyber Towers, Hitec City, Hyderabad, PIN 500081",
        "Country of Origin: India",
        "Customer Support Toll-Free: 1800-111-9988",
        "Support Email: care@apextech.in"
    ]
    y = 220
    for l in lines_elec:
        draw.text((80, y), l, fill=(15, 23, 42))
        y += 75
    img_elec.save(IMAGES_DIR / "sample_electronics.png", quality=95)

    # Reference OCR expected annotations
    shampoo_expected = {
        "raw_ocr_lines": [
            {"text": "NATURE'S ESSENCE HERBAL SHAMPOO", "confidence": 0.98, "bbox": [40, 35, 750, 75]},
            {"text": "Generic Name: Herbal Hair Shampoo", "confidence": 0.96, "bbox": [80, 220, 520, 250]},
            {"text": "Net Quantity: 200 ml", "confidence": 0.95, "bbox": [80, 282, 340, 312]},
            {"text": "M.R.P. : Rs. 249.00 (Incl. of all taxes)", "confidence": 0.97, "bbox": [80, 344, 580, 374]},
            {"text": "Month & Year of Mfg: 06/2026", "confidence": 0.93, "bbox": [80, 406, 450, 436]},
            {"text": "Best Before: 24 Months from Mfd Date", "confidence": 0.92, "bbox": [80, 468, 520, 498]},
            {"text": "Manufactured by: Herbal Care India Pvt. Ltd.", "confidence": 0.94, "bbox": [80, 592, 600, 622]},
            {"text": "Address: Plot 42, Sector 5, Industrial Area, Haridwar, PIN 249403", "confidence": 0.91, "bbox": [80, 654, 780, 684]},
            {"text": "Country of Origin: India", "confidence": 0.96, "bbox": [80, 716, 380, 746]},
            {"text": "Helpline: 1800-200-4567 | Email: customercare@herbalindia.com", "confidence": 0.95, "bbox": [80, 840, 750, 870]}
        ]
    }
    
    biscuit_expected = {
        "raw_ocr_lines": [
            {"text": "CRUNCHY GOLD BUTTER COOKIES", "confidence": 0.97, "bbox": [40, 35, 680, 75]},
            {"text": "Generic Name: Butter Cookies Biscuits", "confidence": 0.95, "bbox": [80, 220, 550, 250]},
            {"text": "Net Weight: 100 g", "confidence": 0.96, "bbox": [80, 295, 320, 325]},
            {"text": "MRP: Rs. 30.00 (Inclusive of all taxes)", "confidence": 0.95, "bbox": [80, 370, 550, 400]},
            {"text": "Date of Manufacture: 05/2026", "confidence": 0.92, "bbox": [80, 445, 430, 475]},
            {"text": "Manufactured by: Crunchy Bakes Foods Ltd.", "confidence": 0.93, "bbox": [80, 595, 620, 625]},
            {"text": "Factory Address: 12 Bakery Road, Food Park, Pune, Maharashtra - 411028", "confidence": 0.90, "bbox": [80, 670, 820, 700]},
            {"text": "Country of Origin: India", "confidence": 0.95, "bbox": [80, 745, 380, 775]}
        ]
    }

    oil_expected = {"raw_ocr_lines": []}

    snack_expected = {
        "raw_ocr_lines": [
            {"text": "SPICY CRUNCH POTATO CHIPS (DUO PACK)", "confidence": 0.97, "bbox": [40, 35, 750, 75]},
            {"text": "Generic Name: Potato Chips Snacks", "confidence": 0.94, "bbox": [80, 220, 520, 250]},
            {"text": "Net Quantity: 2 x 50 g (Total: 100 g)", "confidence": 0.96, "bbox": [80, 290, 540, 320]},
            {"text": "MRP: Rs. 40.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": [80, 360, 500, 390]},
            {"text": "Month of Pkd: 04/2026", "confidence": 0.91, "bbox": [80, 430, 380, 460]},
            {"text": "Manufactured & Packed by: SnackTime Foods Pvt Ltd", "confidence": 0.93, "bbox": [80, 570, 700, 600]},
            {"text": "Country of Origin: India", "confidence": 0.96, "bbox": [80, 710, 380, 740]},
            {"text": "Consumer Care Helpline: 1800-444-1234", "confidence": 0.94, "bbox": [80, 780, 520, 810]},
            {"text": "Consumer Email: support@snacktimefoods.in", "confidence": 0.95, "bbox": [80, 850, 560, 880]}
        ]
    }

    elec_expected = {
        "raw_ocr_lines": [
            {"text": "VOLTX 65W GaN USB-C FAST CHARGER", "confidence": 0.98, "bbox": [40, 35, 720, 75]},
            {"text": "Generic Name: Fast Power Adapter", "confidence": 0.95, "bbox": [80, 220, 500, 250]},
            {"text": "Net Quantity: 1 N", "confidence": 0.96, "bbox": [80, 295, 300, 325]},
            {"text": "MRP: Rs. 799.00 (Inclusive of all taxes)", "confidence": 0.97, "bbox": [80, 370, 560, 400]},
            {"text": "Month & Year of Import: 03/2026", "confidence": 0.92, "bbox": [80, 445, 450, 475]},
            {"text": "Imported & Marketed by: Apex Tech Solutions India Pvt Ltd", "confidence": 0.94, "bbox": [80, 520, 750, 550]},
            {"text": "Country of Origin: India", "confidence": 0.96, "bbox": [80, 670, 380, 700]},
            {"text": "Customer Support Toll-Free: 1800-111-9988", "confidence": 0.95, "bbox": [80, 745, 560, 775]},
            {"text": "Support Email: care@apextech.in", "confidence": 0.96, "bbox": [80, 820, 460, 850]}
        ]
    }

    import json
    with open(EXPECTED_DIR / "compliant_shampoo.json", "w", encoding="utf-8") as f:
        json.dump(shampoo_expected, f, indent=2)
    with open(EXPECTED_DIR / "missing_consumer_care_biscuit.json", "w", encoding="utf-8") as f:
        json.dump(biscuit_expected, f, indent=2)
    with open(EXPECTED_DIR / "blurry_label_oil.json", "w", encoding="utf-8") as f:
        json.dump(oil_expected, f, indent=2)
    with open(EXPECTED_DIR / "non_standard_qty_snack.json", "w", encoding="utf-8") as f:
        json.dump(snack_expected, f, indent=2)
    with open(EXPECTED_DIR / "sample_electronics.json", "w", encoding="utf-8") as f:
        json.dump(elec_expected, f, indent=2)

    print("Demo assets written directly to settings.DEMO_DIR successfully.")

if __name__ == "__main__":
    create_demo_assets()
