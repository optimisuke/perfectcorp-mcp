import asyncio
import mimetypes
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_URL = "https://yce-api-01.perfectcorp.com"
DEFAULT_POLL_INTERVAL = 2.0
MAX_POLL_RETRIES = 60  # 2 min max at default interval


class PerfectCorpClient:
    """Async HTTP client for Perfect Corp AI APIs."""

    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("PERFECTCORP_API_KEY")
        if not api_key:
            raise ValueError("PERFECTCORP_API_KEY is not set in environment")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def upload_file(self, image_path: str) -> str:
        """Upload a local image file to the v2.0 File API and return its file_id.

        API: POST /s2s/v2.0/file
        """
        path = Path(image_path)
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        async with httpx.AsyncClient(base_url=BASE_URL, headers=self._headers, timeout=60.0) as client:
            with path.open("rb") as f:
                response = await client.post(
                    "/s2s/v2.0/file",
                    files={"file": (path.name, f, mime_type)},
                )
            _raise_for_status(response)
            return response.json()["file_id"]

    async def upload_file_v21(self, image_path: str, file_endpoint: str) -> str:
        """Two-step presigned URL upload for v2.1 APIs.

        Step 1: POST file metadata to file_endpoint → receive presigned URL + file_id.
        Step 2: PUT the binary to the presigned URL (no auth headers needed).

        Args:
            image_path: Local path to the image file.
            file_endpoint: Feature-specific file endpoint, e.g. /s2s/v2.1/file/skin-analysis.

        Returns:
            file_id to pass to the task creation endpoint.
        """
        path = Path(image_path)
        file_size = path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Step 1: request a presigned upload URL
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self._headers, timeout=30.0) as client:
            response = await client.post(
                file_endpoint,
                json={
                    "files": [
                        {
                            "content_type": mime_type,
                            "file_name": path.name,
                            "file_size": file_size,
                        }
                    ]
                },
            )
            _raise_for_status(response)
            file_info = response.json()["data"]["files"][0]

        file_id: str = file_info["file_id"]
        upload_req: dict = file_info["requests"][0]

        # Step 2: PUT the file binary to the presigned URL (no Authorization header)
        async with httpx.AsyncClient(timeout=120.0) as client:
            with path.open("rb") as f:
                data = f.read()
            response = await client.request(
                method=upload_req["method"],
                url=upload_req["url"],
                content=data,
                headers=upload_req["headers"],
            )
            _raise_for_status(response)

        return file_id

    async def create_task(self, endpoint: str, payload: dict) -> str:
        """Submit a task and return the task_id."""
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self._headers, timeout=30.0) as client:
            response = await client.post(endpoint, json=payload)
        _raise_for_status(response)
        return response.json()["data"]["task_id"]

    async def poll_task(self, endpoint: str, task_id: str) -> dict:
        """Poll until task_status is 'success' or 'error', then return the full response.

        Respects polling_interval from the response when provided (v2.1+).
        Handles both v2.0 (error_code) and v2.1 (error / error_message) response shapes.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self._headers, timeout=30.0) as client:
            for _ in range(MAX_POLL_RETRIES):
                response = await client.get(f"{endpoint}/{task_id}")
                _raise_for_status(response)
                body = response.json()
                data = body.get("data", body)  # v2.1 wraps payload under "data"
                status = data.get("task_status")

                if status == "success":
                    return data

                if status == "error":
                    code = data.get("error") or data.get("error_code") or "unknown_internal_error"
                    msg = data.get("error_message", "")
                    detail = f": {msg}" if msg else ""
                    raise RuntimeError(f"Task {task_id} failed with {code}{detail}")

                interval = float(data.get("polling_interval", DEFAULT_POLL_INTERVAL))
                await asyncio.sleep(interval)

        raise TimeoutError(
            f"Task {task_id} did not complete after {MAX_POLL_RETRIES} polls"
        )


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a descriptive error for non-2xx responses without logging auth headers."""
    if response.is_success:
        return
    try:
        body = response.json()
    except Exception:
        body = response.text
    raise httpx.HTTPStatusError(
        f"HTTP {response.status_code} from {response.url}: {body}",
        request=response.request,
        response=response,
    )
