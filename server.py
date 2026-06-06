import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from perfectcorp.apis.skin_v21 import HD_ACTIONS, SD_ACTIONS, analyze_skin_v21
from perfectcorp.client import PerfectCorpClient

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
