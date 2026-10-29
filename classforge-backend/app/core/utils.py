"""Utility functions shared across ClassForge modules."""
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from typing import Any


def validate_object_id(id_str: str, field_name: str = "id") -> ObjectId:
    """Validates and converts a string to a MongoDB ObjectId.
    
    Args:
        id_str: The string representation of the ObjectId.
        field_name: Name of the field for error messages.
    
    Returns:
        A valid ObjectId instance.
    
    Raises:
        HTTPException 400 if the string is not a valid ObjectId.
    """
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{field_name}' con valor '{id_str}' no es un ID válido."
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
