import asyncio
import base64
import requests


UPLOAD_INPUT = """
input.hidden[type='file'][name='files'],
input.hidden[type='file']
"""


PROMPT_EDITOR = """
textarea[aria-label='Create'],
textarea[aria-label='Tạo'],
textarea[placeholder*='imagine'],
textarea[placeholder*='tưởng tượng'],
textarea[placeholder*='Nhập'],
div.tiptap.ProseMirror[contenteditable='true'][tabindex='0'],
div.ProseMirror[contenteditable='true'][tabindex='0'],
div.tiptap.ProseMirror[contenteditable='true'],
div.ProseMirror[contenteditable='true'],
p[data-placeholder='Type to imagine'],
p[data-placeholder='Nhập để tưởng tượng'],
p[data-placeholder*='imagine'],
p[data-placeholder*='Imagine'],
p[data-placeholder*='tưởng tượng']
"""


SELECTOR_SUBMIT_SEND = """
button[type='submit'][aria-label='Send'],
button[type='submit'][aria-label='Gửi'],
button[type='submit']:has-text('Send'),
button[type='submit']:has-text('Gửi')
"""


SELECTOR_CREATE_BUTTON = """
button:has-text('Create'),
button:has-text('Generate'),
button:has-text('Tạo'),
button:has-text('Tạo ảnh'),
button:has-text('Tạo video'),
button:has-text('Create image'),
button:has-text('Generate image'),
button[aria-label='Create'],
button[aria-label='Generate'],
button[aria-label='Tạo']
"""


SELECTOR_CREATING_OVERLAY = """
div:has-text("Creating"),
div:has-text("Generating"),
div:has-text("Đang tạo"),
div:has-text("Đang tạo ảnh"),
div:has-text("Đang tạo video")
"""


SELECTOR_RESULT_IMAGE = """
img#sd-image,
img[src*="/generated/"],
img[src*="grok"],
img[src^="blob:"],
img[src^="data:image"]
"""


async def create_image_grok(context, image1, image2, prompt, out_path):

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

        content = None
        if url and url.startswith('data:image'):
            try:
                header, b64 = url.split(',', 1)
                content = base64.b64decode(b64)
            except Exception:
                content = None

        if content is None:
            r = requests.get(url, timeout=60)
            content = r.content

        with open(out_path, "wb") as f:
            f.write(content)

        return out_path

    finally:

        await page.close()