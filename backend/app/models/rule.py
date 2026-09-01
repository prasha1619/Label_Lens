from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer
from app.database.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class ProductCategoryModel(Base):
    __tablename__ = "product_categories"

    id = Column(String(50), primary_key=True)  # e.g., packaged_commodity, food_and_beverages
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    rule_set_version = Column(String(50), default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

class RuleDefinitionModel(Base):
    __tablename__ = "rule_definitions"

    id = Column(String(100), primary_key=True)  # e.g., LM_PC_RULE_MRP_01
    category_id = Column(String(50), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    legal_reference = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    min_confidence_pass = Column(Integer, default=70)
    min_confidence_warning = Column(Integer, default=50)
    validation_regex = Column(String(500), nullable=True)
    validation_logic = Column(JSON, default=dict)
    severity_if_missing = Column(String(50), default="HIGH")
    recommendation_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
