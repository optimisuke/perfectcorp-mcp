from collections.abc import Sequence

from perfectcorp.client import PerfectCorpClient

FILE_ENDPOINT = "/s2s/v2.1/file/skin-analysis"
TASK_ENDPOINT = "/s2s/v2.1/task/skin-analysis"

HD_ACTIONS: list[str] = [
    "hd_redness",
    "hd_oiliness",
    "hd_age_spot",
    "hd_radiance",
    "hd_moisture",
    "hd_dark_circle",
    "hd_eye_bag",
    "hd_droopy_upper_eyelid",
    "hd_droopy_lower_eyelid",
    "hd_firmness",
    "hd_texture",
    "hd_acne",
    "hd_pore",
    "hd_wrinkle",
    "hd_tear_trough",
    "hd_skin_type",
]

SD_ACTIONS: list[str] = [
    "wrinkle",
    "droopy_upper_eyelid",
    "droopy_lower_eyelid",
    "firmness",
    "acne",
    "moisture",
    "eye_bag",
    "dark_circle_v2",
    "age_spot",
    "radiance",
    "redness",
    "oiliness",
    "pore",
    "texture",
    "tear_trough",
    "skin_type",
]

_ALL_VALID = set(HD_ACTIONS) | set(SD_ACTIONS)


def _validate_dst_actions(dst_actions: Sequence[str]) -> None:
    unknown = set(dst_actions) - _ALL_VALID
    if unknown:
        raise ValueError(f"Unknown dst_actions: {sorted(unknown)}")
    hd = [a for a in dst_actions if a in set(HD_ACTIONS)]
    sd = [a for a in dst_actions if a in set(SD_ACTIONS)]
    if hd and sd:
        raise ValueError("HD and SD dst_actions cannot be mixed. Choose one tier.")


async def analyze_skin_v21(
    client: PerfectCorpClient,
    image_path: str,
    dst_actions: Sequence[str] | None = None,
    format: str = "json",
) -> dict:
    """Run Skin Analysis v2.1. Returns raw API response.

    Args:
        client: Authenticated PerfectCorpClient instance.
        image_path: Local path to the image file.
        dst_actions: List of analysis features to run. Defaults to all HD features.
                     All items must belong to the same tier (HD or SD).
        format: "json" returns scores inline; "zip" returns a download URL. Default "json".
    """
    if dst_actions is None:
        dst_actions = HD_ACTIONS

    _validate_dst_actions(dst_actions)

    file_id = await client.upload_file_v21(image_path, FILE_ENDPOINT)
    task_id = await client.create_task(
        TASK_ENDPOINT,
        {
            "file_id": file_id,
            "dst_actions": list(dst_actions),
            "format": format,
        },
    )
    return await client.poll_task(TASK_ENDPOINT, task_id)
