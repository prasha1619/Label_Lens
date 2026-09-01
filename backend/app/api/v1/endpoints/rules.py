from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from app.services.rules.rule_loader import RuleLoader
from app.schemas.rule import ProductCategorySchema

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
def get_rule_categories():
    """
    Returns list of all available Legal Metrology commodity categories and rule summary counts.
    """
    return RuleLoader.list_categories()

@router.get("/{category_id}", response_model=ProductCategorySchema)
def get_category_rules(category_id: str):
    """
    Returns the complete declarative rule definitions and legal citations for a specific category.
    """
    rules = RuleLoader.get_category_rules(category_id)
    if not rules:
        raise HTTPException(status_code=404, detail=f"Category '{category_id}' not found.")
    return rules
