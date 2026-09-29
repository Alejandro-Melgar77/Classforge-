from pydantic import BaseModel, Field
from typing import List, Optional, Any

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
    sourceMultiplicity: Optional[str] = None
    targetMultiplicity: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.source_multiplicity and not self.sourceMultiplicity:
            self.sourceMultiplicity = self.source_multiplicity
        elif self.sourceMultiplicity and not self.source_multiplicity:
            self.source_multiplicity = self.sourceMultiplicity
            
        if self.target_multiplicity and not self.targetMultiplicity:
            self.targetMultiplicity = self.target_multiplicity
        elif self.targetMultiplicity and not self.target_multiplicity:
            self.target_multiplicity = self.targetMultiplicity

class UMLCommandResponse(BaseModel):
    action: str
    classes: List[UMLClassCommand] = Field(default_factory=list)
    relations: List[UMLRelationCommand] = Field(default_factory=list)
    deleted_elements: List[str] = Field(default_factory=list)
    explanation: str
    source: str # "gemini_ai" | "offline_nlu" | "backend_ai"

class PromptRequest(BaseModel):
    prompt: str
    diagram_context: Optional[dict] = None
    api_key: Optional[str] = None
    model: Optional[str] = None

class ImagePromptRequest(BaseModel):
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    diagram_id: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


