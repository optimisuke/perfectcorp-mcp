# Face Analysis API — endpoint TBD, add when available
# from perfectcorp.client import PerfectCorpClient
#
# TASK_ENDPOINT = "/s2s/v2.0/task/face-analysis"
#
# async def analyze_face(client: PerfectCorpClient, image_path: str) -> dict:
#     file_id = await client.upload_file(image_path)
#     task_id = await client.create_task(TASK_ENDPOINT, {"file_id": file_id})
#     return await client.poll_task(TASK_ENDPOINT, task_id)
