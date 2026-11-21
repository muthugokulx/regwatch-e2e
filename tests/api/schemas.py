"""JSON Schema = the contract: what shape every API response MUST have."""

UPDATE_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "jurisdiction", "category", "published_date", "summary", "created_at"],
    "properties": {
        "id": {"type": "integer"},
        "title": {"type": "string", "minLength": 3},
        "jurisdiction": {"type": "string", "enum": ["UK", "US", "EU", "IN", "SG", "AU", "HK"]},
        "category": {"type": "string", "enum": ["Rule change", "Consultation", "Guidance", "Enforcement"]},
        "published_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "summary": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
    },
}

UPDATE_LIST_SCHEMA = {"type": "array", "items": UPDATE_SCHEMA}