import pytest
from app.modules.ai.service import process_prompt
from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.schemas import UMLCommandResponse

def test_parse_heuristic_create_class():
    prompt = "crear clase Usuario con atributos nombre, edad"
    res = parse_heuristic(prompt)
    assert res is not None
    assert res.action == "create_class"
    assert len(res.classes) == 1
    assert res.classes[0].name == "Usuario"
    assert len(res.classes[0].attributes) == 2
    assert res.classes[0].attributes[0].name == "nombre"
    assert res.classes[0].attributes[1].name == "edad"

def test_parse_heuristic_add_attribute():
    prompt = "agregar atributo fecha datetime a la clase Factura"
    res = parse_heuristic(prompt)
    assert res is not None
    assert res.action == "add_attribute"
    assert res.classes[0].name == "Factura"
    assert res.classes[0].attributes[0].name == "fecha"
    assert res.classes[0].attributes[0].type == "datetime"

def test_parse_heuristic_create_relation():
    prompt = "relacionar Factura con Cliente (composicion)"
    res = parse_heuristic(prompt)
    assert res is not None
    assert res.action == "create_relation"
    assert res.relations[0].source == "Factura"
    assert res.relations[0].target == "Cliente"
    assert res.relations[0].type == "composition"

@pytest.mark.asyncio
async def test_process_prompt_fallback():
    # Prompt that won't match heuristic, and assuming Ollama is down/mocked out, it should use fallback
    prompt = "sistema de biblioteca"
    # To reliably test fallback without actually calling Ollama, we could patch call_ollama, 
    # but here since Ollama likely isn't running in CI, it will naturally fallback.
    res = await process_prompt(prompt)
    assert res.action == "generate_system"
    assert len(res.classes) > 0
    assert res.source == "nlu_heuristic"
