"""Utility functions shared across ClassForge modules."""
from bson import ObjectId
from bson.errors import InvalidId
from typing import Any
from app.core.errors import ValidationError


def validate_object_id(id_str: Any, field_name: str = "id") -> ObjectId:
    """Validates and converts a string or ObjectId to a MongoDB ObjectId.
    
    Args:
        id_str: The string representation or ObjectId instance.
        field_name: Name of the field for error messages.
    
    Returns:
        A valid ObjectId instance.
    
    Raises:
        ValidationError if the value is not a valid ObjectId.
    """
    if isinstance(id_str, ObjectId):
        return id_str

    if not id_str or not isinstance(id_str, (str, bytes)):
        raise ValidationError(
            f"'{field_name}' con valor '{id_str}' no es un ID válido.",
            code="INVALID_OBJECT_ID"
        )

    try:
        if not ObjectId.is_valid(str(id_str)):
            raise ValidationError(
                f"'{field_name}' con valor '{id_str}' no es un ID válido.",
                code="INVALID_OBJECT_ID"
            )
        return ObjectId(str(id_str))
    except (InvalidId, TypeError, ValueError):
        raise ValidationError(
            f"'{field_name}' con valor '{id_str}' no es un ID válido.",
            code="INVALID_OBJECT_ID"
        )


def serialize_doc(doc: dict | None) -> dict | None:
    """Converts a MongoDB document's ObjectId fields to strings for JSON serialization.
    
    Recursively converts all ObjectId values (including nested dicts and lists).
    
    Args:
        doc: A MongoDB document dict (or None).
    
    Returns:
        The document with all ObjectId values converted to strings, or None.
    """
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(item) if isinstance(item, dict)
                else str(item) if isinstance(item, ObjectId)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result
