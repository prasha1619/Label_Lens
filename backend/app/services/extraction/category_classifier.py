"""
Category Classifier
===================
Keyword-based OCR text classifier that auto-detects the product category
from the raw label text when the user does not explicitly select one.

Categories supported (must match rule definition IDs):
    - electronics_and_appliances
    - food_and_beverages
    - pharmaceuticals
    - cosmetics_and_toiletries
    - packaged_commodity  (fallback / general)

The classifier scores each category against term lists and returns the
highest-confidence winner.  Confidence >= 0.40 triggers an override;
below that threshold the user-supplied category is kept unchanged.
"""
import re
from typing import Dict, Optional, Tuple
from app.core.logging import logger


# ---------------------------------------------------------------------------
# Keyword term banks - ordered from specific to generic to reduce false hits
# ---------------------------------------------------------------------------

_CATEGORY_TERMS: Dict[str, Dict[str, float]] = {
    "electronics_and_appliances": {
        "usb cable":          3.0,
        "usb-c":              2.5,
        "type-c cable":       2.5,
        "micro usb":          2.5,
        "charging cable":     2.5,
        "data cable":         2.5,
        "power bank":         3.0,
        "earphone":           2.5,
        "earbuds":            2.5,
        "headphone":          2.5,
        "bluetooth":          2.0,
        "wireless charger":   2.5,
        "fast charger":       2.5,
        "wall charger":       2.5,
        "led bulb":           2.5,
        "smart bulb":         2.5,
        "cfl":                2.0,
        "tube light":         2.0,
        "electric iron":      2.5,
        "hair dryer":         2.5,
        "hair straightener":  2.5,
        "electric kettle":    2.5,
        "mixer grinder":      2.5,
        "juicer":             2.0,
        "inverter":           2.5,
        "adapter":            2.0,
        "converter":          2.0,
        "voltage":            1.5,
        "wattage":            1.5,
        "ampere":             1.5,
        "input voltage":      2.0,
        "output voltage":     2.0,
        "rated power":        2.0,
        "rated voltage":      2.0,
        "electric":           1.0,
        "electronic":         1.5,
        "battery":            1.5,
        "charger":            1.5,
        "cable":              1.0,
        "wire":               0.8,
        "connector":          1.0,
        "hdmi":               2.5,
        "memory card":        2.5,
        "sd card":            2.5,
        "pen drive":          2.5,
        "flash drive":        2.5,
        "laptop":             2.5,
        "smartphone":         2.0,
        "smartwatch":         2.5,
        "router":             2.5,
        "modem":              2.5,
        "speaker":            2.0,
        "webcam":             2.5,
        "bis registration":   3.0,
        "bis no":             2.5,
        "bis cert":           2.5,
        "electronics":        1.5,
        "appliances":         1.5,
    },

    "food_and_beverages": {
        "fssai":                  3.5,
        "lic. no.":               2.0,
        "lic no":                 2.0,
        "nutritional information": 3.0,
        "nutrition facts":        3.0,
        "nutritional values":     3.0,
        "nutritional":            2.5,
        "energy (kcal":           3.0,
        "energy kcal":            3.0,
        "carbohydrate":           2.5,
        "dietary fiber":          2.5,
        "dietary fibre":          2.5,
        "added sugar":            2.5,
        "trans fat":              2.5,
        "saturated fat":          2.5,
        "serving size":           2.5,
        "per serve":              2.5,
        "per 100g":               2.5,
        "per 100ml":              2.5,
        "vegetarian":             2.5,
        "non-vegetarian":         2.5,
        "green dot":              2.0,
        "edible oil":             3.0,
        "cooking oil":            3.0,
        "mustard oil":            3.0,
        "sunflower oil":          3.0,
        "olive oil":              3.0,
        "biscuit":                2.5,
        "cookies":                2.5,
        "wafers":                 2.5,
        "chips":                  2.0,
        "snack":                  2.0,
        "namkeen":                2.5,
        "noodles":                2.5,
        "pasta":                  2.0,
        "instant noodles":        2.5,
        "tea":                    2.0,
        "coffee":                 2.0,
        "juice":                  2.0,
        "milk":                   2.0,
        "dairy":                  2.0,
        "paneer":                 2.5,
        "cheese":                 2.0,
        "butter":                 2.0,
        "chocolate":              2.0,
        "confectionery":          2.5,
        "candy":                  2.0,
        "rice":                   2.0,
        "atta":                   2.5,
        "wheat flour":            2.5,
        "maida":                  2.5,
        "besan":                  2.5,
        "pulses":                 2.0,
        "dal":                    2.0,
        "spices":                 2.5,
        "masala":                 2.0,
        "sauce":                  2.0,
        "ketchup":                2.5,
        "jam":                    2.0,
        "pickle":                 2.5,
        "cereal":                 2.5,
        "oats":                   2.5,
        "muesli":                 2.5,
        "cornflakes":             2.5,
        "soft drink":             2.5,
        "beverage":               2.0,
        "energy drink":           2.5,
    },

    "pharmaceuticals": {
        "drug":               2.5,
        "medicine":           2.5,
        "tablet":             2.5,
        "capsule":            2.5,
        "syrup":              2.5,
        "injection":          3.0,
        "ointment":           2.5,
        "dosage":             3.0,
        "dose":               2.5,
        "prescription":       3.0,
        "rx only":            3.0,
        "schedule h":         3.0,
        "schedule g":         3.0,
        "mfg lic":            2.0,
        "drug lic":           3.0,
        "active ingredient":  3.0,
        "antibiotic":         3.0,
        "analgesic":          2.5,
        "antipyretic":        2.5,
        "contraindication":   3.0,
        "side effect":        2.5,
        "pharmacist":         2.5,
    },

    "cosmetics_and_toiletries": {
        "shampoo":            3.0,
        "conditioner":        2.5,
        "hair oil":           2.5,
        "face wash":          2.5,
        "face cream":         2.5,
        "moisturizer":        2.5,
        "moisturiser":        2.5,
        "body lotion":        2.5,
        "lotion":             2.0,
        "serum":              2.0,
        "sunscreen":          3.0,
        "spf":                2.5,
        "foundation":         2.5,
        "lipstick":           2.5,
        "mascara":            2.5,
        "eyeliner":           2.5,
        "kajal":              2.5,
        "perfume":            3.0,
        "deodorant":          2.5,
        "deo":                2.5,
        "body spray":         2.5,
        "body mist":          3.0,
        "cologne":            3.0,
        "aftershave":         3.0,
        "eau de parfum":      3.0,
        "eau de toilette":    3.0,
        "soap":               2.0,
        "bath soap":          2.5,
        "toothpaste":         3.0,
        "mouthwash":          2.5,
        "hand wash":          2.5,
        "body wash":          2.5,
        "nail polish":        2.5,
        "hair dye":           2.5,
        "skin care":          2.5,
        "skincare":           2.5,
        "cosmetic":           2.5,
        "dermatologically":   2.5,
    },

    "packaged_commodity": {
        "room freshener":     3.5,
        "air freshener":      3.5,
        "roomfreshener":      3.5,
        "roomfresiener":      3.5,
        "freshener":          3.0,
        "home fragrance":     3.0,
        "car fragrance":      3.0,
        "fragrance diffuser": 3.0,
        "diffuser":           2.5,
        "room spray":         3.0,
        "incense stick":      3.0,
        "agarbatti":          3.0,
        "camphor":            3.0,
        "detergent":          3.0,
        "washing powder":     3.0,
        "dishwash":           3.0,
        "floor cleaner":      3.0,
        "surface cleaner":    3.0,
        "glass cleaner":      3.0,
        "toilet cleaner":     3.0,
        "disinfectant":       3.0,
        "fabric softener":    3.0,
        "liquid detergent":   3.0,
        "bleach":             3.0,
        "insecticide":        3.0,
        "mosquito repellent": 3.0,
        "repellent":          2.5,
        "cockroach spray":    3.0,
        "shoe polish":        2.5,
        "paint":              2.5,
        "varnish":            2.5,
        "cement":             2.5,
        "adhesive":           2.5,
        "fevicol":            3.0,
        "lubricant":          2.5,
        "motor oil":          2.5,
        "stationery":         2.5,
        "notebook":           2.5,
        "pencil":             2.5,
    },
}

_MIN_SCORE_THRESHOLD = 2.0
_MIN_MARGIN = 0.5


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def detect_category(ocr_text: str) -> Tuple[Optional[str], float]:
    """
    Analyse raw OCR text and return (category_id, confidence_score).
    Returns (None, 0.0) when no category exceeds the minimum threshold.
    """
    normalised = _normalise(ocr_text)

    scores: Dict[str, float] = {}
    for cat_id, terms in _CATEGORY_TERMS.items():
        total = 0.0
        for term, weight in terms.items():
            if term in normalised:
                total += weight
        scores[cat_id] = total

    if not scores:
        return None, 0.0

    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0.0

    logger.debug(
        f"[CategoryClassifier] scores={scores}, best={best_cat}({best_score:.1f}), "
        f"second={second_score:.1f}"
    )

    if best_score < _MIN_SCORE_THRESHOLD:
        return None, 0.0

    if (best_score - second_score) < _MIN_MARGIN:
        return None, 0.0

    confidence = min(1.0, round(best_score / 10.0, 3))
    return best_cat, confidence


def auto_detect_category(
    ocr_text: str,
    user_category: str = "packaged_commodity",
    override_always: bool = False,
) -> Tuple[str, bool, float]:
    """
    High-level helper called by the pipeline.

    Returns (final_category, was_overridden, confidence).
    """
    detected, confidence = detect_category(ocr_text)

    user_chose_default = (user_category == "packaged_commodity")

    if detected is None:
        return user_category, False, 0.0

    if detected == user_category:
        return user_category, False, confidence

    if user_chose_default or override_always:
        logger.info(
            f"[CategoryClassifier] Auto-detected '{detected}' (confidence={confidence:.2f}) "
            f"overriding default/user category '{user_category}'."
        )
        return detected, True, confidence

    logger.info(
        f"[CategoryClassifier] Detected '{detected}' but user explicitly chose "
        f"'{user_category}' - keeping user choice."
    )
    return user_category, False, confidence
