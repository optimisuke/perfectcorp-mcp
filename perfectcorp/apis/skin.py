from perfectcorp.client import PerfectCorpClient

TASK_ENDPOINT = "/s2s/v2.0/task/skin-analysis"


async def analyze_skin(client: PerfectCorpClient, image_path: str) -> dict:
    """Upload image and run Skin Analysis. Returns raw API response."""
    file_id = await client.upload_file(image_path)
    task_id = await client.create_task(TASK_ENDPOINT, {"file_id": file_id})
    return await client.poll_task(TASK_ENDPOINT, task_id)
