import zipfile
import io
from typing import Dict

def create_project_zip(files: Dict[str, str]) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path, content in files.items():
            # Add root directory to the zip archive as requested: classforge-backend/
            zip_file.writestr(f"classforge-backend/{file_path}", content)
            
    return zip_buffer.getvalue()
