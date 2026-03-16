import asyncio
import requests


UPLOAD_INPUT = "input.hidden[type='file'][name='files'], input.hidden[type='file']"

PROMPT_EDITOR = """
textarea[aria-label='Create'],
textarea[placeholder*='imagine'],
div.tiptap.ProseMirror[contenteditable='true'],
div.ProseMirror[contenteditable='true'],
p[data-placeholder='Type to imagine'],
p[data-placeholder*='Imagine']
"""

SELECTOR_SUBMIT_SEND = """
button[type='submit'][aria-label='Send'],
button[type='submit']:has-text('Send')
"""

SELECTOR_CREATE_BUTTON = """
button:has-text('Create'),
button:has-text('Generate'),
button[aria-label='Create'],
button[aria-label='Generate']
"""

SELECTOR_CREATING_OVERLAY = """
div:has-text("Creating"),
div:has-text("Generating"),
div:has-text("Đang tạo")
"""

SELECTOR_RESULT_IMAGE = """
img#sd-image,
img[src*="/generated/"],
img[src^="blob:"],
img[src^="data:image"]
"""


async def create_image_grok(browser, image1, image2, prompt, out_path):

    context = browser.contexts[0]

    # mỗi task mở tab riêng
    page = await context.new_page()

    try:

        # =====================
        # open imagine page
        # =====================

        await page.goto("https://grok.com/imagine", timeout=60000)

        # =====================
        # upload images
        # =====================

        upload = page.locator(UPLOAD_INPUT).first
        await upload.wait_for(timeout=30000)

        await upload.set_input_files([image1, image2])

        await asyncio.sleep(2)

        # =====================
        # wait prompt editor
        # =====================

        editor = page.locator(PROMPT_EDITOR).first
        await editor.wait_for(timeout=60000)

        await editor.click()
        await editor.fill(prompt)

        # =====================
        # click SEND (priority)
        # =====================

        send_btn = page.locator(SELECTOR_SUBMIT_SEND)

        if await send_btn.count() > 0:
            await send_btn.first.click()

        else:

            create_btn = page.locator(SELECTOR_CREATE_BUTTON)
            await create_btn.first.click()

        # =====================
        # wait generating overlay
        # =====================

        try:
            overlay = page.locator(SELECTOR_CREATING_OVERLAY).first
            await overlay.wait_for(timeout=10000)
        except:
            pass

        # =====================
        # wait result image
        # =====================

        img = page.locator(SELECTOR_RESULT_IMAGE).first
        await img.wait_for(timeout=180000)

        url = await img.get_attribute("src")

        # =====================
        # download image
        # =====================

        r = requests.get(url, timeout=60)

        with open(out_path, "wb") as f:
            f.write(r.content)

        return out_path

    finally:

        await page.close()