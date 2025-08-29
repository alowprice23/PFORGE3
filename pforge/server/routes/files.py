from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.responses import FileResponse
from pathlib import Path
import shutil
import tempfile
import uuid

from pforge.sandbox.fs_manager import onboard_repo
from pforge.sandbox.path_policy import is_path_safe

router = APIRouter()

# This should be configured, but we'll use a default for the slice.
_SANDBOX_WORKTREE = Path("pforge/workspace")

@router.post(
    "/onboard",
    summary="Onboard a new project from a ZIP archive",
    tags=["Files"]
)
async def onboard_project_from_zip(file: UploadFile = File(...)):
    """
    Accepts a ZIP file, extracts it to a temporary directory, and then
    onboards it into the pForge sandbox system.
    """
    if file.content_type != "application/zip":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a ZIP archive.")

    # Use a temporary directory to safely extract the archive
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip_path = Path(temp_dir) / f"{uuid.uuid4()}.zip"

        # Save the uploaded file to the temp path
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract the archive
        shutil.unpack_archive(temp_zip_path, temp_dir)

        # Now, onboard the extracted contents
        # We need to find the root directory within the extracted archive.
        # Often, a zip file contains a single root folder.
        extracted_items = list(Path(temp_dir).iterdir())
        # Filter out the zip file itself
        extracted_dirs = [item for item in extracted_items if item.is_dir()]

        if len(extracted_dirs) == 1:
            source_path = extracted_dirs[0]
        else:
            # If there are multiple dirs or no dirs, use the temp dir itself.
            source_path = Path(temp_dir)

        try:
            initial_commit_sha = onboard_repo(str(source_path))
            return {
                "status": "onboarding_successful",
                "initial_commit_sha": initial_commit_sha
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to onboard repository: {e}")


@router.get(
    "/download/{file_path:path}",
    summary="Download a file from the sandbox",
    tags=["Files"]
)
async def download_sandbox_file(file_path: str):
    """
    Provides secure, read-only access to files within the current sandbox
    worktree. Prevents path traversal attacks.
    """
    full_path = _SANDBOX_WORKTREE / file_path

    # Use the path policy to ensure the requested path is safe
    if not is_path_safe(full_path, _SANDBOX_WORKTREE):
        raise HTTPException(status_code=403, detail="Forbidden: Access to this path is not allowed.")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(full_path)
