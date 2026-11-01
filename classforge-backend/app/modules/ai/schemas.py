import base64
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Any

ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

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
    source: str = "gemini_ai" # "gemini_ai" | "offline_nlu" | "backend_ai" | "local" | "heuristic"

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    diagram_context: Optional[dict] = None
    api_key: Optional[str] = Field(default=None, repr=False)
    model: Optional[str] = None
    preferred_provider: Optional[str] = None  # "auto" | "gemini" | "local"
    local_only: Optional[bool] = False

    @field_validator("preferred_provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip().lower()
        if clean not in ("auto", "gemini", "local", "ollama", "heuristic", "fake"):
            raise ValueError(f"preferred_provider no permitido: '{v}'")
        return clean

    @model_validator(mode="before")
    @classmethod
    def block_client_ollama_url(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for forbidden_key in ("ollama_url", "local_url", "base_url", "endpoint"):
                if forbidden_key in data:
                    raise ValueError(
                        f"El parámetro '{forbidden_key}' no está permitido desde el cliente por protección contra SSRF. "
                        "El endpoint local se configura exclusivamente en las variables de entorno del servidor."
                    )
        return data

class ImagePromptRequest(BaseModel):
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    diagram_id: Optional[str] = None
    api_key: Optional[str] = Field(default=None, repr=False)
    model: Optional[str] = None

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: Optional[str]) -> str:
        clean = (v or "image/jpeg").strip().lower()
        if clean not in ALLOWED_IMAGE_MIMES:
            raise ValueError(f"MIME type no permitido: '{v}'. Permitidos: {', '.join(sorted(ALLOWED_IMAGE_MIMES))}")
        return clean

    @field_validator("image_base64")
    @classmethod
    def validate_image_payload(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_base64 es requerido")
        raw = v.strip()
        if "," in raw:
            raw = raw.split(",", 1)[1]
        try:
            decoded = base64.b64decode(raw, validate=True)
        except Exception:
            raise ValueError("image_base64 no contiene datos base64 válidos")
        if len(decoded) > MAX_IMAGE_BYTES:
            raise ValueError("El tamaño de la imagen decodificada excede el límite de 8 MB")
        return raw




class FeedbackCorrectionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    corrected_command: UMLCommandResponse
    project_id: Optional[str] = None
    allow_feedback: bool = Field(default=False, description="Must be explicitly True for consent")
    comment: Optional[str] = None
