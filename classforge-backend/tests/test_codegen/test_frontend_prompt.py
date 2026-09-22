import pytest
from app.modules.codegen.frontend_prompt_generator import generate_frontend_meta_prompt

def test_generate_frontend_meta_prompt():
    graph_data = {
        "nodes": [
            {
                "id": "node-1",
                "type": "class",
                "shape": "uml-class",
                "data": {
                    "name": "Customer",
                    "attributes": [
                        "+ fullName: string",
                        "+ email: string",
                        "- active: bool"
                    ]
                }
            },
            {
                "id": "node-2",
                "type": "class",
                "shape": "uml-class",
                "data": {
                    "name": "Order",
                    "attributes": [
                        {"name": "orderCode", "type": "string"},
                        {"name": "total", "type": "double"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "rel-1",
                "type": "composition",
                "source": "node-1",
                "target": "node-2"
            }
        ]
    }
    
    # Test Flutter + Dark Mode
    prompt_flutter = generate_frontend_meta_prompt(graph_data, target_framework="flutter", theme="dark")
    assert "Flutter 3.x" in prompt_flutter
    assert "flutter_riverpod" in prompt_flutter
    assert "dio" in prompt_flutter
    assert "10.0.2.2:8080/api/v1" in prompt_flutter
    assert "/api/v1/customers" in prompt_flutter
    assert "Customer" in prompt_flutter
    
    # Test React Native
    prompt_rn = generate_frontend_meta_prompt(graph_data, target_framework="react-native", theme="dark")
    assert "React Native" in prompt_rn
    assert "TanStack" in prompt_rn
    assert "Expo" in prompt_rn
    assert "10.0.2.2:8080/api/v1" in prompt_rn
    
    # Test React + Dark Mode
    prompt_react = generate_frontend_meta_prompt(graph_data, target_framework="react", theme="dark")
    assert "React 18+" in prompt_react
    assert "http://localhost:8080/api/v1/customers" in prompt_react
    assert "fullName" in prompt_react
    assert "orderCode" in prompt_react
    assert "@OneToMany" in prompt_react
    assert "@ManyToOne" in prompt_react
    assert "GET /api/v1/customers" in prompt_react
    assert "POST /api/v1/customers" in prompt_react
    assert "DELETE /api/v1/customers/{id}" in prompt_react
    
    # Test Angular + Light Mode
    prompt_angular = generate_frontend_meta_prompt(graph_data, target_framework="angular", theme="light")
    assert "Angular 17+" in prompt_angular
    assert "ReactiveFormsModule" in prompt_angular
    
    # Test Vue
    prompt_vue = generate_frontend_meta_prompt(graph_data, target_framework="vue", theme="dark")
    assert "Vue 3" in prompt_vue
    assert "Pinia" in prompt_vue

