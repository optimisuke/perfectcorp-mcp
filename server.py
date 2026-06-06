import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path regardless of how the server is launched
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

from perfectcorp.apis.skin_v21 import HD_ACTIONS, SD_ACTIONS, analyze_skin_v21
from perfectcorp.client import PerfectCorpClient

_IMAGESNAP = shutil.which("imagesnap") or "/opt/homebrew/bin/imagesnap"

mcp = FastMCP(
    "perfectcorp-ai",
    instructions=(
        "Tools for Perfect Corp AI analysis APIs. "
        "Returns raw API responses — interpret results after receiving them."
    ),
)

_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@mcp.tool()
async def analyze_skin_image(
    image_path: str,
    dst_actions: list[str] | None = None,
    format: str = "json",
) -> str:
    """Analyze skin condition from a facial photograph using Perfect Corp AI Skin Analysis API v2.1.

    Uploads the image, submits an async task, polls until done, and returns the raw JSON response.
    The caller is responsible for interpreting the scores and detected conditions.

    Args:
        image_path: Absolute or ~ path to a jpg/png image (max 10 MB, long side <= 4096 px).
        dst_actions: Analysis features to run. Must all be HD or all be SD — cannot mix tiers.
            HD features (high-definition):
              hd_redness, hd_oiliness, hd_age_spot, hd_radiance, hd_moisture,
              hd_dark_circle, hd_eye_bag, hd_droopy_upper_eyelid, hd_droopy_lower_eyelid,
              hd_firmness, hd_texture, hd_acne, hd_pore, hd_wrinkle,
              hd_tear_trough, hd_skin_type
            SD features (standard-definition):
              wrinkle, droopy_upper_eyelid, droopy_lower_eyelid, firmness, acne,
              moisture, eye_bag, dark_circle_v2, age_spot, radiance, redness,
              oiliness, pore, texture, tear_trough, skin_type
            Defaults to all 16 HD features when omitted.
        format: "json" (default) returns scores inline in the response.
                "zip" returns a download URL for a ZIP archive with JSON + images.

    Returns:
        Raw API response as a JSON string.
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")
    if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{path.suffix}'. Supported: jpg, jpeg, png."
        )
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Image file exceeds 10 MB limit.")
    if format not in {"json", "zip"}:
        raise ValueError("format must be 'json' or 'zip'.")

    client = PerfectCorpClient()
    result = await analyze_skin_v21(
        client,
        str(path),
        dst_actions=dst_actions,
        format=format,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def capture_and_analyze_skin(
    dst_actions: list[str] | None = None,
    warmup_seconds: float = 2.0,
    save_path: str | None = None,
) -> str:
    """Capture a photo from the Mac's FaceTime camera and analyze skin condition in one step.

    Takes a photo using imagesnap, sends it to Perfect Corp AI Skin Analysis API v2.1,
    and returns the raw JSON response. The caller is responsible for interpreting the results.

    Args:
        dst_actions: Analysis features to run (HD or SD tier, cannot mix).
                     Defaults to all 16 HD features when omitted.
        warmup_seconds: Seconds to wait for the camera to warm up before capturing.
                        Default 2.0. Increase if the image comes out dark.
        save_path: Optional path to save the captured photo (e.g. ~/Desktop/skin.jpg).
                   If omitted the photo is stored in a temp file and deleted after analysis.

    Returns:
        Raw API response as a JSON string.
    """
    if not Path(_IMAGESNAP).exists():
        raise FileNotFoundError(
            "imagesnap not found. Install it with: brew install imagesnap"
        )

    if save_path:
        photo_path = Path(save_path).expanduser().resolve()
        photo_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = None
    else:
        tmp_dir = tempfile.mkdtemp()
        photo_path = Path(tmp_dir) / "capture.jpg"

    try:
        proc = await asyncio.create_subprocess_exec(
            _IMAGESNAP, "-w", str(warmup_seconds), str(photo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=warmup_seconds + 15)

        if proc.returncode != 0:
            raise RuntimeError(f"imagesnap failed: {stderr.decode().strip()}")
        if not photo_path.exists() or photo_path.stat().st_size == 0:
            raise RuntimeError("imagesnap ran but produced no output file.")

        client = PerfectCorpClient()
        result = await analyze_skin_v21(
            client,
            str(photo_path),
            dst_actions=dst_actions,
        )

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    out = {"captured_photo": save_path or "(temp, deleted)", **result}
    return json.dumps(out, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
