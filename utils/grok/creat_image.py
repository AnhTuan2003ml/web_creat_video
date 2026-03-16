import asyncio

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
div.tiptap.ProseMirror[contenteditable='true'],
div.ProseMirror[contenteditable='true'],
p[data-placeholder*='imagine'],
p[data-placeholder*='tưởng tượng']
"""

SELECTOR_SUBMIT_SEND = """
button[type='submit'][aria-label='Submit'],
button[type='submit'][aria-label='Gửi'],
button[aria-label='Submit'],
button[aria-label='Gửi'],
button[type='submit']:has-text('Send'),
button[type='submit']:has-text('Gửi')
"""

SELECTOR_CREATE_BUTTON = """
button:has-text('Create'),
button:has-text('Generate'),
button:has-text('Tạo'),
button:has-text('Tạo ảnh'),
button:has-text('Create image'),
button:has-text('Generate image')
"""

SELECTOR_CREATING_OVERLAY = """
div:has-text("Creating"),
div:has-text("Generating"),
div:has-text("Đang tạo"),
div:has-text("Đang tạo ảnh")
"""

SELECTOR_THUMBNAILS = """
img[alt^="Thumbnail"]
"""

SELECTOR_RESULT_IMAGE = """
img[src*="imagine-public"],
img[src*="generated"],
img[src^="blob:"],
img[src^="data:image"]
"""

SELECTOR_ASPECT_BUTTON = """
button[aria-label="Aspect Ratio"]
"""


async def create_image_grok(context, image1, image2, prompt, out_path, ratio="9:16"):

    page = await context.new_page()

    try:

        # =====================
        # open imagine page
        # =====================

        await page.goto("https://grok.com/imagine", timeout=60000)

        # =====================
        # set aspect ratio
        # =====================

        try:

            ratio_btn = page.locator(SELECTOR_ASPECT_BUTTON).first
            await ratio_btn.wait_for(timeout=10000)

            await ratio_btn.click()

            await page.wait_for_timeout(500)

            ratio_option = page.locator(f'role=menuitem >> text="{ratio}"').first

            await ratio_option.wait_for(timeout=10000)
            await ratio_option.click()

            await page.wait_for_timeout(500)

        except:
            print("Aspect ratio menu not found or already set")

        # =====================
        # upload images
        # =====================

        upload = page.locator(UPLOAD_INPUT).first
        await upload.wait_for(state="attached", timeout=30000)

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
        # click CREATE
        # =====================

        send_btn = page.locator(SELECTOR_SUBMIT_SEND)

        if await send_btn.count() > 0:
            await send_btn.first.click()
        else:
            create_btn = page.locator(SELECTOR_CREATE_BUTTON)
            await create_btn.first.click()
            
        await page.wait_for_timeout(2000)

        # =====================
        # click FIRST thumbnail
        # =====================

        thumbs = page.locator(SELECTOR_THUMBNAILS)

        await thumbs.first.wait_for(state="visible", timeout=30000)
        await thumbs.first.click()

        await page.wait_for_timeout(1500)
        # =====================
        # wait overlay
        # =====================

        overlay = page.locator(SELECTOR_CREATING_OVERLAY)

        try:
            await overlay.first.wait_for(state="visible", timeout=20000)

            await page.wait_for_selector(
                SELECTOR_CREATING_OVERLAY,
                state="hidden",
                timeout=180000
            )
        except:
            pass


        

        # =====================
        # wait big image
        # =====================

        img = page.locator(SELECTOR_RESULT_IMAGE).last
        await img.wait_for(state="visible", timeout=30000)

        await img.hover()

        await page.wait_for_timeout(800)

        # =====================
        # JS click DOWNLOAD
        # =====================

        async with page.expect_download() as download_info:

            await page.evaluate("""
                () => {

                    const buttons = [...document.querySelectorAll("button")];

                    const btn = buttons.find(b => {
                        const label = b.getAttribute("aria-label") || "";
                        return label.includes("Download") || label.includes("Tải");
                    });

                    if(!btn){
                        throw new Error("Download button not found");
                    }

                    btn.click();

                }
            """)

        download = await download_info.value

        await download.save_as(out_path)

        return out_path

    finally:

        await page.close()