from pydantic import BaseModel, Field
from typing import List, Optional

class UMLAttribute(BaseModel):
    name: str
    type: str = "String"
    visibility: str = "+"

class UMLMethod(BaseModel):
    name: str
    params: str = ""
    return_type: str = "void"
    visibility: str = "+"

class UMLClassCommand(BaseModel):
    name: str
    attributes: List[UMLAttribute] = Field(default_factory=list)
    methods: List[UMLMethod] = Field(default_factory=list)
    stereotype: Optional[str] = None

class UMLRelationCommand(BaseModel):
    source: str
    target: str
    type: str # inheritance | composition | aggregation | association | dependency | realization
    label: Optional[str] = None
    source_multiplicity: Optional[str] = None
    target_multiplicity: Optional[str] = None

class UMLCommandResponse(BaseModel):
    action: str
    classes: List[UMLClassCommand] = Field(default_factory=list)
    relations: List[UMLRelationCommand] = Field(default_factory=list)
    deleted_elements: List[str] = Field(default_factory=list)
    explanation: str
    source: str # "nlu_heuristic" | "ollama_tinyllama"

class PromptRequest(BaseModel):
    prompt: str
    diagram_context: Optional[dict] = None
