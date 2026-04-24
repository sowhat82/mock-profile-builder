"""
Company/entity name anonymisation.
"""
import re

# Keywords → industry type mapping
INDUSTRY_KEYWORDS = [
    (["bank", "banking", "finance", "financial", "capital", "credit", "lending"], "Financial"),
    (["asset", "invest", "fund", "portfolio", "wealth", "equity", "securities", "ventures"], "Investment"),
    (["property", "real estate", "realty", "development", "developer", "construction"], "Real Estate"),
    (["tech", "technology", "digital", "software", "systems", "solutions", "data", "cyber"], "Technology"),
    (["healthcare", "health", "medical", "pharma", "biotech", "life sciences"], "Healthcare"),
    (["energy", "oil", "gas", "power", "renewable", "solar", "utilities"], "Energy"),
    (["retail", "consumer", "trading", "commerce", "goods", "products"], "Consumer"),
    (["logistics", "transport", "shipping", "freight", "supply chain"], "Logistics"),
    (["media", "entertainment", "publishing", "broadcast", "content"], "Media"),
    (["food", "beverage", "restaurant", "hospitality", "hotel", "tourism"], "Hospitality"),
    (["education", "learning", "academy", "institute", "university", "school"], "Education"),
    (["law", "legal", "consultancy", "consulting", "advisory", "partners"], "Advisory"),
    (["insurance", "assurance", "reinsurance"], "Insurance"),
    (["manufacturing", "industrial", "engineering", "machinery", "factory"], "Industrial"),
]


def detect_industry(entity_name: str) -> str:
    """Detect industry type from entity name."""
    name_lower = entity_name.lower()
    for keywords, industry in INDUSTRY_KEYWORDS:
        if any(kw in name_lower for kw in keywords):
            return industry
    return "Diversified"


def detect_jurisdiction(entity_name: str) -> str:
    """Detect the jurisdiction suffix to use."""
    name_lower = entity_name.lower()
    if any(x in name_lower for x in ["pte ltd", "pte. ltd", "private limited", "singapore"]):
        return "Pte Ltd"
    if any(x in name_lower for x in ["sdn bhd", "malaysia"]):
        return "Sdn Bhd"
    if any(x in name_lower for x in ["limited", "ltd", "plc", "llp"]):
        return "Ltd"
    if any(x in name_lower for x in ["llc", "inc", "corp", "incorporated"]):
        return "LLC"
    return "Pte Ltd"  # Default Singapore


def generate_fake_entity(original_name: str) -> str:
    """Generate a fake entity name based on detected industry and jurisdiction."""
    industry = detect_industry(original_name)
    jurisdiction = detect_jurisdiction(original_name)
    return f"{industry} Holdings Test-Data {jurisdiction}"
