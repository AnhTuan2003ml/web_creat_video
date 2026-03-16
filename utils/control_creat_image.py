import asyncio
from utils.grok.creat_image import create_image_grok


async def run_tasks(context, provider, tasks, max_tabs: int = 5):

    jobs = []

    try:
        max_tabs = int(max_tabs)
    except Exception:
        max_tabs = 5
    if max_tabs < 1:
        max_tabs = 1

    sem = asyncio.Semaphore(max_tabs)

    # kiểm tra provider 1 lần
    provider_check = provider.lower()

    if provider_check in ["grok", "grok (x-ai)"]:

        for task in tasks:

            async def _run_one(t=task):
                async with sem:
                    return await create_image_grok(
                        context=context,
                        image1=t["image1"],
                        image2=t["image2"],
                        prompt=t["prompt"],
                        out_path=t["out"]
                    )

            jobs.append(_run_one())

    else:
        raise ValueError(f"Provider not supported: {provider}")

    await asyncio.gather(*jobs)