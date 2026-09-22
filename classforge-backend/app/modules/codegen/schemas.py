from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class CodegenPreviewRequest(BaseModel):
    graph_data: Optional[Dict[str, Any]] = None

class CodegenPreviewResponseData(BaseModel):
    files: Dict[str, str]
    total_files: int

class CodegenPreviewResponse(BaseModel):
    success: bool
    data: CodegenPreviewResponseData

class FrontendPromptRequest(BaseModel):
    target_framework: str = "flutter"  # flutter, react-native, react, angular, vue, vanilla
    theme: str = "dark"  # dark, light
    graph_data: Optional[Dict[str, Any]] = None

class FrontendPromptResponseData(BaseModel):
    prompt: str
    character_count: int
    estimated_tokens: int
    target_framework: str
    theme: str

class FrontendPromptResponse(BaseModel):
    success: bool
    data: FrontendPromptResponseData
    message: str = "Frontend meta-prompt generated successfully"
