import pytest
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.zip_service import create_project_zip

def test_generate_spring_boot_project():
    graph_data = {
        "nodes": [
            {
                "id": "1",
                "type": "classNode",
                "data": {
                    "name": "User",
                    "attributes": [
                        {"name": "username", "type": "string"},
                        {"name": "email", "type": "string"},
                        {"name": "age", "type": "int"}
                    ]
                }
            },
            {
                "id": "2",
                "type": "classNode",
                "data": {
                    "name": "Profile",
                    "attributes": [
                        {"name": "bio", "type": "string"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "source": "1",
                "target": "2",
                "type": "composition",
                "label": "has_one"
            }
        ]
    }
    
    files = generate_spring_boot_project(graph_data, "com.test")
    
    # Assert Infrastructure
    assert "pom.xml" in files
    assert "spring-boot-starter-web" in files["pom.xml"]
    assert "springdoc-openapi-starter-webmvc-ui" in files["pom.xml"]
    assert "src/main/resources/application.yml" in files
    assert "src/main/java/com/test/MainApplication.java" in files
    assert "src/main/java/com/test/config/OpenApiConfig.java" in files
    assert "src/main/java/com/test/config/CorsConfig.java" in files
    assert "src/main/java/com/test/exceptions/GlobalExceptionHandler.java" in files
    assert "README.md" in files
    
    # Assert Entity files
    assert "src/main/java/com/test/entities/User.java" in files
    user_entity = files["src/main/java/com/test/entities/User.java"]
    assert "private String username;" in user_entity
    assert "private String email;" in user_entity
    assert "private Integer age;" in user_entity
    assert "@OneToMany" in user_entity
    assert "@CreationTimestamp" in user_entity
    
    assert "src/main/java/com/test/entities/Profile.java" in files
    profile_entity = files["src/main/java/com/test/entities/Profile.java"]
    assert "@ManyToOne" in profile_entity
    assert "private User user;" in profile_entity
    
    # Assert DTOs & Validation
    assert "src/main/java/com/test/dto/UserRequestDTO.java" in files
    user_dto = files["src/main/java/com/test/dto/UserRequestDTO.java"]
    assert "@Email" in user_dto
    assert "@NotBlank" in user_dto
    
    assert "src/main/java/com/test/dto/UserResponseDTO.java" in files
    
    # Assert Mapper (SRP)
    assert "src/main/java/com/test/mappers/UserMapper.java" in files
    user_mapper = files["src/main/java/com/test/mappers/UserMapper.java"]
    assert "toEntity" in user_mapper
    assert "toResponseDTO" in user_mapper
    
    # Assert Repositories
    assert "src/main/java/com/test/repositories/UserRepository.java" in files
    
    # Assert Services
    assert "src/main/java/com/test/services/UserService.java" in files
    assert "src/main/java/com/test/services/impl/UserServiceImpl.java" in files
    
    # Assert Controllers
    assert "src/main/java/com/test/controllers/UserController.java" in files
    user_controller = files["src/main/java/com/test/controllers/UserController.java"]
    assert "/api/v1/users" in user_controller
    assert "ResponseEntity" in user_controller
    assert "@Valid" in user_controller
    
    # Zip Creation
    zip_bytes = create_project_zip(files)
    assert len(zip_bytes) > 0
    
def test_inheritance_relations():
    graph_data = {
        "nodes": [
            {
                "id": "parent",
                "type": "classNode",
                "data": {"name": "Vehicle", "attributes": [{"name": "speed", "type": "int"}]}
            },
            {
                "id": "child",
                "type": "classNode",
                "data": {"name": "Car", "attributes": [{"name": "brand", "type": "string"}]}
            }
        ],
        "edges": [
            {
                "source": "child",
                "target": "parent",
                "type": "inheritance"
            }
        ]
    }
    files = generate_spring_boot_project(graph_data, "com.test")
    
    vehicle_entity = files["src/main/java/com/test/entities/Vehicle.java"]
    assert "@Inheritance(strategy = InheritanceType.JOINED)" in vehicle_entity
    
    car_entity = files["src/main/java/com/test/entities/Car.java"]
    assert "extends Vehicle" in car_entity

def test_classforge_native_x6_format():
    graph_data = {
        "nodes": [
            {
                "id": "node-1",
                "type": "class",
                "shape": "uml-class",
                "data": {
                    "name": "Order",
                    "attributes": [
                        "+ orderNumber: string",
                        {"name": "totalAmount", "type": "double"}
                    ],
                    "methods": [
                        "+ calculateTotal(): double"
                    ]
                }
            },
            {
                "id": "node-2",
                "type": "class",
                "shape": "uml-class",
                "data": {
                    "name": "OrderItem",
                    "attributes": [
                        "- quantity: int",
                        "- price: double"
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "edge-1",
                "type": "composition",
                "shape": "uml-composition",
                "source": {"cell": "node-1"},
                "target": {"cell": "node-2"}
            }
        ]
    }
    
    files = generate_spring_boot_project(graph_data, "com.classforge.demo")
    assert "pom.xml" in files
    assert "src/main/java/com/classforge/demo/entities/Order.java" in files
    assert "src/main/java/com/classforge/demo/entities/OrderItem.java" in files
    assert "src/main/java/com/classforge/demo/controllers/OrderController.java" in files
    
    order_entity = files["src/main/java/com/classforge/demo/entities/Order.java"]
    assert "private String orderNumber;" in order_entity
    assert "private Double totalAmount;" in order_entity
    assert "@OneToMany" in order_entity
    
    item_entity = files["src/main/java/com/classforge/demo/entities/OrderItem.java"]
    assert "private Integer quantity;" in item_entity
    assert "@ManyToOne" in item_entity
    assert "private Order order;" in item_entity


