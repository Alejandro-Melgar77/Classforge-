# -*- coding: utf-8 -*-
import pytest
from app.modules.codegen.fastapi_generator import generate_fastapi_project

def test_generate_fastapi_project():
    graph_data = {
        "nodes": [
            {
                "id": "node-1",
                "type": "class",
                "data": {
                    "name": "Producto",
                    "attributes": [
                        {"name": "codigo", "type": "string"},
                        {"name": "nombre", "type": "string"},
                        {"name": "precio", "type": "double"},
                        {"name": "stock", "type": "int"}
                    ]
                }
            },
            {
                "id": "node-2",
                "type": "class",
                "data": {
                    "name": "Venta",
                    "attributes": [
                        {"name": "numeroFactura", "type": "string"},
                        {"name": "total", "type": "double"}
                    ]
                }
            }
        ],
        "edges": []
    }
    
    files = generate_fastapi_project(graph_data)
    
    # Assert core FastAPI files exist
    assert "app/main.py" in files
    assert "app/config.py" in files
    assert "app/database.py" in files
    assert "app/routers/cloud_sync.py" in files
    assert "requirements.txt" in files
    assert "Dockerfile" in files
    assert "render.yaml" in files
    assert "run.bat" in files
    assert "run.sh" in files
    assert "README.md" in files
    
    # Assert models, schemas and routers generated
    assert "app/models/producto.py" in files
    assert "app/schemas/producto.py" in files
    assert "app/routers/producto.py" in files
    assert "app/models/venta.py" in files
    assert "app/schemas/venta.py" in files
    assert "app/routers/venta.py" in files
    
    # Assert contents
    assert "fastapi" in files["requirements.txt"].lower()
    assert "class Producto(Base):" in files["app/models/producto.py"]
    assert "class ProductoResponse(ProductoBase):" in files["app/schemas/producto.py"]
    assert 'prefix="/api/v1/productos"' in files["app/routers/producto.py"]
    assert "CLASSFORGE_CLOUD_URL" in files["app/config.py"]
    assert "render.yaml" in files
