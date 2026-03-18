import asyncio
import base64
import json
import os
import tempfile
import shutil
from typing import Any, Dict, List, Optional

from utils.grok.creat_video import VideoJob, create_video_grok
from utils.control_script import update_task_status
from utils.control_ffmpeg import merge_video_clips, TRANSCODE_DIR, apply_background_music


_CANCELLED_VIDEO_TASKS = set()


def cancel_video_task(task_id: str) -> bool:
    tid = str(task_id or '').strip()
    if not tid:
        return False
    _CANCELLED_VIDEO_TASKS.add(tid)
    return True


def is_video_task_cancelled(task_id: str) -> bool:
    tid = str(task_id or '').strip()
    if not tid:
        return False
    return tid in _CANCELLED_VIDEO_TASKS


def clear_video_task_cancel(task_id: str) -> None:
    tid = str(task_id or '').strip()
    if not tid:
        return
    try:
        _CANCELLED_VIDEO_TASKS.discard(tid)
    except Exception:
        pass
    # Fix 6: Prevent memory leak in _CANCELLED_VIDEO_TASKS
    if len(_CANCELLED_VIDEO_TASKS) > 1000:
        _CANCELLED_VIDEO_TASKS.clear()


def _get_scenes_dir(out_clips: List[str]) -> str:
    try:
        clips = [str(p) for p in (out_clips or []) if p]
        if not clips:
            return ''
        parents = {os.path.abspath(os.path.dirname(p)) for p in clips}
        if len(parents) != 1:
            return ''
        return list(parents)[0]
    except Exception:
        return ''


def _decode_data_url_to_temp_file(data_url: str, suffix: str = ".png") -> str:
    if not data_url or not str(data_url).startswith("data:image"):
        raise ValueError("Only data:image/* base64 is supported")
    header, b64 = str(data_url).split(",", 1)
    content = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
    except Exception:
        try:
            os.remove(path)
        except Exception:
            pass
        raise
    return path


async def _run_one_video_task(
    context,
    task: Dict[str, Any],
    sem: asyncio.Semaphore,
    cancel_event: Optional[asyncio.Event] = None
):
    task_id = str(task.get("task_id") or "").strip()
    scenes = task.get("scenes")
    out_clips = task.get("out_clips")
    effect_key = str(task.get("effect_key") or "").strip()
    merged_out = task.get("merged_out") or ""
    music_path = str(task.get("music_path") or "").strip()

    if not task_id:
        return None
    if not isinstance(scenes, list) or len(scenes) == 0:
        update_task_status(task_id, "failed", error="No scenes")
        return None
    if not isinstance(out_clips, list) or len(out_clips) != len(scenes):
        update_task_status(task_id, "failed", error="Invalid out_clips")
        return None
    if not merged_out:
        update_task_status(task_id, "failed", error="Missing merged_out")
        return None

    tmp_files: List[str] = []
    try:
        for idx, scene in enumerate(scenes):
            # Check cancellation
            if is_video_task_cancelled(task_id) or (cancel_event and cancel_event.is_set()):
                update_task_status(task_id, "cancelled", error="Đã hủy")
                raise asyncio.CancelledError()

            prompt = str(scene.get("prompt") or "").strip()
            img_data = str(scene.get("image") or "")
            if not prompt or not img_data:
                update_task_status(task_id, "failed", error=f"Thiếu prompt/ảnh ở cảnh {idx+1}")
                return None

            img_path = _decode_data_url_to_temp_file(img_data, suffix=".png")
            tmp_files.append(img_path)

            update_task_status(
                task_id,
                "processing",
                scene_index=idx + 1,
                total_scenes=len(scenes),
                progress_percent=int((idx / max(1, len(scenes))) * 100),
            )

            # Fix 4: Use Semaphore per scene for better tab utilization
            async with sem:
                clip_dir = str(out_clips[idx])
                job = VideoJob(image_path=img_path, prompt=prompt, out_path=clip_dir, task_id=task_id)

                real_clip_path = await create_video_grok(context, job, cancel_event)
                
                # Fix 2 & 3: Check real_clip_path and verify file size
                if not real_clip_path or not os.path.exists(real_clip_path):
                    update_task_status(task_id, "failed", error=f"Download fail scene {idx+1}")
                    return None
                
                if os.path.getsize(real_clip_path) < 200_000:
                    update_task_status(task_id, "failed", error=f"Video scene {idx+1} quá nhỏ hoặc lỗi")
                    return None

                # Fix 5: Handle duplicate filenames by renaming
                unique_name = f"scene_{idx+1}_{os.path.basename(real_clip_path)}"
                new_path = os.path.join(os.path.dirname(real_clip_path), unique_name)
                try:
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(real_clip_path, new_path)
                    real_clip_path = new_path
                except Exception:
                    pass

                out_clips[idx] = str(real_clip_path)

            update_task_status(
                task_id,
                "processing",
                scene_index=idx + 1,
                total_scenes=len(scenes),
                progress_percent=int(((idx + 1) / max(1, len(scenes))) * 100),
            )

        # Fix 7: Persist scene map once at the end
        try:
            scenes_dir = _get_scenes_dir(out_clips)
            if scenes_dir and os.path.isdir(scenes_dir):
                map_path = os.path.join(scenes_dir, 'scene_map.json')
                scene_data = {str(i + 1): os.path.basename(out_clips[i]) for i in range(len(out_clips))}
                with open(map_path, 'w', encoding='utf-8') as f:
                    json.dump(scene_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Final checks before merging
        if is_video_task_cancelled(task_id) or (cancel_event and cancel_event.is_set()):
            update_task_status(task_id, "cancelled", error="Đã hủy")
            raise asyncio.CancelledError()

        # Fix 8: Verify all clips exist before FFmpeg merge
        for p in out_clips:
            if not os.path.exists(p):
                update_task_status(task_id, "failed", error=f"Missing clip: {p}")
                return None

        update_task_status(
            task_id,
            "processing",
            scene_index=len(scenes),
            total_scenes=len(scenes),
            progress_percent=100,
            phase="merging",
        )

        merged_path = merge_video_clips(out_clips, merged_out, effect_key=effect_key)

        # Apply background music
        if music_path and os.path.exists(music_path):
            try:
                tmp_music_out = os.path.join(TRANSCODE_DIR, f"music_{task_id.replace('-', '')[:12]}_{os.path.basename(merged_out)}")
                applied = apply_background_music(merged_path, music_path, tmp_music_out)
                shutil.copy2(applied, merged_out)
                merged_path = merged_out
                if os.path.exists(tmp_music_out):
                    os.remove(tmp_music_out)
            except Exception:
                pass

        # Prepare for playback
        out_name = os.path.basename(merged_path)
        trans_name = f"{task_id.replace('-', '')[:12]}__{out_name}"
        trans_path = os.path.join(TRANSCODE_DIR, trans_name)
        try:
            if os.path.abspath(os.path.dirname(merged_path)) != os.path.abspath(TRANSCODE_DIR):
                shutil.copy2(merged_path, trans_path)
            else:
                trans_name = os.path.basename(merged_path)
        except Exception:
            trans_name = os.path.basename(merged_path)

        update_task_status(
            task_id,
            "completed",
            result_file=merged_path,
            result_url=f"/transcoded/{trans_name}",
            effect_key=effect_key,
            out_clips=list(out_clips),
            merged_out=str(merged_out),
            scenes_dir=_get_scenes_dir(out_clips),
        )
        return True

    except asyncio.CancelledError:
        raise
    except Exception as e:
        update_task_status(task_id, "failed", error=str(e))
        return None
    finally:
        clear_video_task_cancel(task_id)
        for p in tmp_files:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


async def run_video_tasks(
    context,
    provider: str,
    tasks: List[Dict[str, Any]],
    max_tabs: int = 5,
    cancel_event=None,
):
    try:
        max_tabs = int(max_tabs)
    except Exception:
        max_tabs = 5
    if max_tabs < 1:
        max_tabs = 1

    sem = asyncio.Semaphore(max_tabs)
    jobs = [
        _run_one_video_task(context, task, sem, cancel_event)
        for task in tasks
    ]

    gathered = await asyncio.gather(*jobs, return_exceptions=True)

    if cancel_event is not None and getattr(cancel_event, "is_set", None) and cancel_event.is_set():
        raise asyncio.CancelledError()

    return gathered
