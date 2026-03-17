import asyncio
import base64
import os
import tempfile
from utils.grok.creat_image import create_image_grok
from utils.control_script import create_image_task, update_task_status

async def run_tasks(context, provider, tasks, max_tabs: int = 5, aspect_ratio: str = "9:16", cancel_event=None):
    jobs = []

    try:
        max_tabs = int(max_tabs)
    except Exception:
        max_tabs = 5
    if max_tabs < 1:
        max_tabs = 1

    sem = asyncio.Semaphore(max_tabs)
    provider_check = provider.lower()

    if provider_check in ["grok", "grok (x-ai)"]:
        for task in tasks:
            async def _run_one(t=task):
                if cancel_event is not None and getattr(cancel_event, "is_set", None) and cancel_event.is_set():
                    raise asyncio.CancelledError()

                task_id = str((t or {}).get("task_id") or "").strip()
                if not task_id:
                    task_name = f"Tạo ảnh: {os.path.basename(t['out'])}"
                    task_id = create_image_task(task_name, provider)
                
                # Tạo file tạm từ base64 data trong memory
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1, \
                     tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
                    
                    try:
                        # Decode base64 và ghi vào file tạm
                        if 'image1_data' in t and t['image1_data'].startswith('data:image'):
                            img1_content = base64.b64decode(t['image1_data'].split(',', 1)[1])
                            tmp1.write(img1_content)
                        tmp1.close()

                        if 'image2_data' in t and t['image2_data'].startswith('data:image'):
                            img2_content = base64.b64decode(t['image2_data'].split(',', 1)[1])
                            tmp2.write(img2_content)
                        tmp2.close()

                        async with sem:
                            try:
                                if cancel_event is not None and getattr(cancel_event, "is_set", None) and cancel_event.is_set():
                                    raise asyncio.CancelledError()

                                result = await create_image_grok(
                                    context=context,
                                    image1=tmp1.name,
                                    image2=tmp2.name,
                                    prompt=t["prompt"],
                                    out_path=t["out"],
                                    ratio=t.get("ratio", "9:16"),
                                    cancel_event=cancel_event,
                                )
                                update_task_status(task_id, "completed", result_file=t["out"])
                                return result
                            except asyncio.CancelledError:
                                update_task_status(task_id, "cancelled", error="Đã hủy")
                                raise
                            except Exception as e:
                                update_task_status(task_id, "failed", error=str(e))
                                raise e
                    finally:
                        # Luôn dọn dẹp file tạm
                        if os.path.exists(tmp1.name): os.remove(tmp1.name)
                        if os.path.exists(tmp2.name): os.remove(tmp2.name)

            jobs.append(_run_one())
    else:
        raise ValueError(f"Provider not supported: {provider}")

    gathered = await asyncio.gather(*jobs, return_exceptions=True)

    if cancel_event is not None and getattr(cancel_event, "is_set", None) and cancel_event.is_set():
        for r in gathered:
            if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                continue
        raise asyncio.CancelledError()

    return gathered