import asyncio
import pytest
from app.modules.codegen.gemini_generator import parse_diagram_semantics, generate_spring_boot_with_gemini
from app.core.config import settings

def test_parse_diagram_semantics():
    graph_data = {
        "cells": [
            {
                "id": "c1",
                "shape": "class-node",
                "data": {
                    "name": "Factura",
                    "attributes": [
                        {"name": "numero", "type": "String"},
                        {"name": "total", "type": "Double"}
                    ],
                    "methods": [
                        {"name": "calcularTotal", "return_type": "Double"}
                    ]
                }
            },
            {
                "id": "c2",
                "shape": "class-node",
                "data": {
                    "name": "Cliente",
                    "attributes": [
                        {"name": "nombre", "type": "String"},
                        {"name": "email", "type": "String"}
                    ]
                }
            },
            {
                "id": "e1",
                "shape": "edge",
                "source": {"cell": "c1"},
                "target": {"cell": "c2"},
                "data": {
                    "type": "association",
                    "sourceMultiplicity": "*",
                    "targetMultiplicity": "1"
                }
            }
        ]
    }
    
    semantics = parse_diagram_semantics(graph_data)
    assert len(semantics["classes"]) == 2
    assert semantics["classes"][0]["name"] == "Factura"
    assert semantics["classes"][1]["name"] == "Cliente"
    assert len(semantics["relations"]) == 1
    assert semantics["relations"][0]["source"] == "Factura"
    assert semantics["relations"][0]["target"] == "Cliente"

def test_gemini_live_generation():
    graph_data = {
        "cells": [
            {
                "id": "c1",
                "shape": "class-node",
                "data": {
                    "name": "Producto",
                    "attributes": [{"name": "nombre", "type": "String"}, {"name": "precio", "type": "Double"}]
                }
            }
        ]
    }
    result = asyncio.run(generate_spring_boot_with_gemini(graph_data, model="gemini-3.8-flash"))
    assert "files" in result
    assert result["total_files"] >= 10
    assert "pom.xml" in result["files"]
    assert ".vscode/launch.json" in result["files"]
    assert "run.bat" in result["files"]
    assert "engine_used" in result
    assert len(result["engine_used"]) > 0

