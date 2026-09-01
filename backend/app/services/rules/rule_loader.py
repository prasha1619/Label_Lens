import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.schemas.rule import ProductCategorySchema, RuleRequirementSchema

class RuleLoader:
    """
    Loads and caches declarative Legal Metrology compliance rule sets.
    Decouples all legal logic from application code.
    """

    _categories_cache: Dict[str, ProductCategorySchema] = {}

    @classmethod
    def load_all_rules(cls) -> Dict[str, ProductCategorySchema]:
        if cls._categories_cache:
            return cls._categories_cache

        rules_dir = settings.RULES_DIR
        if not rules_dir.exists():
            logger.warning(f"Rules directory not found at {rules_dir}")
            return {}

        categories: Dict[str, ProductCategorySchema] = {}

        for json_file in rules_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cat_id = data.get("category_id")
                    if not cat_id:
                        continue

                    reqs = [
                        RuleRequirementSchema(
                            rule_id=r["rule_id"],
                            field_name=r["field_name"],
                            title=r["title"],
                            legal_reference=r["legal_reference"],
                            description=r["description"],
                            is_mandatory=r.get("is_mandatory", True),
                            min_confidence_pass=r.get("min_confidence_pass", 70),
                            min_confidence_warning=r.get("min_confidence_warning", 50),
                            validation_regex=r.get("validation_regex"),
                            severity_if_missing=r.get("severity_if_missing", "HIGH"),
                            recommendation_template=r.get("recommendation_template", "Verify declaration manually.")
                        )
                        for r in data.get("requirements", [])
                    ]

                    categories[cat_id] = ProductCategorySchema(
                        category_id=cat_id,
                        display_name=data.get("display_name", cat_id),
                        description=data.get("description", ""),
                        rules=reqs
                    )
            except Exception as e:
                logger.error(f"Failed to parse rule file {json_file}: {e}")

        cls._categories_cache = categories
        logger.info(f"Loaded {len(categories)} Legal Metrology rule categories.")
        return categories

    @classmethod
    def get_category_rules(cls, category_id: str) -> Optional[ProductCategorySchema]:
        all_rules = cls.load_all_rules()
        # Fallback to packaged_commodity if specific category is not found
        return all_rules.get(category_id) or all_rules.get("packaged_commodity")

    @classmethod
    def list_categories(cls) -> List[Dict[str, str]]:
        all_rules = cls.load_all_rules()
        return [
            {
                "category_id": cat_id,
                "display_name": cat.display_name,
                "description": cat.description,
                "rule_count": len(cat.rules)
            }
            for cat_id, cat in all_rules.items()
        ]
