let imageFormCounter = 0;

function _createImageForm({ characterSrc, characterName }) {
    const formId = `img-form-${imageFormCounter++}`;

    const root = document.createElement('div');
    root.className = 'workspace-container';
    root.dataset.formId = formId;
    root.style.flex = '0 0 100%';

    const charBtnId = `${formId}-btn-select-character`;
    const prodBtnId = `${formId}-btn-select-product`;
    const resetBtnId = `${formId}-btn-reset-form`;
    const genBtnId = `${formId}-btn-generate-video`;

    const charBoxId = `${formId}-display-character`;
    const prodBoxId = `${formId}-display-product`;
    const descBoxId = `${formId}-display-description`;
    const resultBoxId = `${formId}-display-result`;

    root.innerHTML = `
        <div class="column">
            <button class="col-header-btn" type="button" id="${charBtnId}">Chọn Nhân Vật</button>
            <div class="content-area media-box" id="${charBoxId}"></div>
        </div>

        <div class="column">
            <button class="col-header-btn" type="button" id="${prodBtnId}">Chọn Sản Phẩm</button>
            <div class="content-area media-box placeholder" id="${prodBoxId}">Chưa có sản phẩm</div>
        </div>

        <div class="column">
            <div class="col-header-text">Nhập Mô Tả</div>
            <div class="content-area" id="${descBoxId}" style="padding: 8px;">
                <textarea></textarea>
            </div>
        </div>

        <div class="column">
            <div class="col-header-text">Kết Quả</div>
            <div class="content-area" id="${resultBoxId}"></div>
        </div>

        <div class="action-column">
            <button class="btn-small" type="button" id="${resetBtnId}">Xóa Form</button>
            <button class="btn-small" type="button" id="${genBtnId}" style="padding: 15px 5px;">Tạo</button>
        </div>
    `;

    const charBox = root.querySelector(`#${CSS.escape(charBoxId)}`);
    if (charBox && characterSrc) {
        const img = document.createElement('img');
        img.src = characterSrc;
        img.alt = characterName || 'character';
        charBox.appendChild(img);
    }

    const chooseCharBtn = root.querySelector(`#${CSS.escape(charBtnId)}`);
    if (chooseCharBtn) {
        chooseCharBtn.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = (e) => {
                const file = e.target.files && e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    const box = root.querySelector(`#${CSS.escape(charBoxId)}`);
                    if (!box) return;
                    box.innerHTML = '';
                    const img = document.createElement('img');
                    img.src = String(ev.target && ev.target.result ? ev.target.result : '');
                    img.alt = file.name;
                    box.appendChild(img);
                };
                reader.readAsDataURL(file);
            };
            input.click();
        });
    }

    const chooseProdBtn = root.querySelector(`#${CSS.escape(prodBtnId)}`);
    if (chooseProdBtn) {
        chooseProdBtn.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = (e) => {
                const file = e.target.files && e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    const box = root.querySelector(`#${CSS.escape(prodBoxId)}`);
                    if (!box) return;
                    box.innerHTML = '';
                    box.classList.remove('placeholder');
                    const img = document.createElement('img');
                    img.src = String(ev.target && ev.target.result ? ev.target.result : '');
                    img.alt = file.name;
                    box.appendChild(img);
                };
                reader.readAsDataURL(file);
            };
            input.click();
        });
    }

    const resetBtn = root.querySelector(`#${CSS.escape(resetBtnId)}`);
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            root.remove();
        });
    }

    const genBtn = root.querySelector(`#${CSS.escape(genBtnId)}`);
    if (genBtn) {
        genBtn.addEventListener('click', () => {
            const box = root.querySelector(`#${CSS.escape(resultBoxId)}`);
            if (!box) return;
            box.innerHTML = '';
            const note = document.createElement('div');
            note.style.cssText = 'padding: 10px; color: #aaa; font-size: 12px;';
            note.textContent = 'Chưa implement tạo ảnh.';
            box.appendChild(note);
        });
    }

    return root;
}

function _createPromptOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'prompt-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    const modal = document.createElement('div');
    modal.style.cssText = `
        background: #1a1a1a;
        border: 2px solid #555;
        border-radius: 12px;
        padding: 25px;
        width: 550px;
        max-width: 90%;
        box-shadow: 0 10px 30px rgba(0,0,0,0.8);
    `;

    const title = document.createElement('h3');
    title.textContent = 'Nhập mô tả cho tất cả ảnh';
    title.style.cssText = `
        margin: 0 0 20px 0;
        color: white;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    `;

    const textarea = document.createElement('textarea');
    textarea.id = 'prompt-textarea-all';
    textarea.placeholder = 'Nhập mô tả chung cho tất cả ảnh...';
    textarea.style.cssText = `
        width: 100%;
        height: 150px;
        background: #111;
        color: white;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 15px;
        font-size: 16px;
        font-weight: 500;
        resize: none;
        box-sizing: border-box;
        line-height: 1.5;
    `;

    const buttonsContainer = document.createElement('div');
    buttonsContainer.style.cssText = `
        display: flex;
        gap: 10px;
        justify-content: flex-end;
        margin-top: 15px;
    `;

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Hủy';
    cancelBtn.style.cssText = `
        background: #666;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        transition: background 0.3s;
    `;

    const confirmBtn = document.createElement('button');
    confirmBtn.textContent = 'Xác nhận';
    confirmBtn.style.cssText = `
        background: #e74c3c;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        transition: background 0.3s;
    `;

    buttonsContainer.appendChild(cancelBtn);
    buttonsContainer.appendChild(confirmBtn);
    modal.appendChild(title);
    modal.appendChild(textarea);
    modal.appendChild(buttonsContainer);
    overlay.appendChild(modal);

    cancelBtn.onclick = () => {
        document.body.removeChild(overlay);
    };

    confirmBtn.onclick = () => {
        const promptText = textarea.value.trim();
        if (promptText) {
            const descriptionTextareas = document.querySelectorAll('[id$="-display-description"] textarea');
            descriptionTextareas.forEach(textarea => {
                textarea.value = promptText;
            });
        }
        document.body.removeChild(overlay);
    };

    overlay.onclick = (e) => {
        if (e.target === overlay) {
            document.body.removeChild(overlay);
        }
    };

    return overlay;
}

function _showErrorOverlay(message) {
    const overlay = document.createElement('div');
    overlay.id = 'error-modal-overlay';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.85); display: flex; align-items: center;
        justify-content: center; z-index: 10000; color: white; font-family: sans-serif;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: #222; padding: 30px; border-radius: 12px;
        max-width: 500px; width: 90%; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #444;
    `;
    
    const title = document.createElement('h2');
    title.innerText = '⚠️ CẦN THIẾT LẬP TRÌNH DUYỆT';
    title.style.color = '#ff4d4d';
    title.style.marginBottom = '20px';
    
    const msg = document.createElement('p');
    msg.innerText = message;
    msg.style.lineHeight = '1.6';
    msg.style.fontSize = '16px';
    msg.style.marginBottom = '25px';
    
    const btn = document.createElement('button');
    btn.innerText = 'ĐÃ HIỂU';
    btn.style.cssText = `
        background: #007bff; color: white; border: none;
        padding: 12px 30px; border-radius: 6px; cursor: pointer;
        font-weight: bold; transition: background 0.2s;
    `;
    btn.onclick = () => document.body.removeChild(overlay);
    
    content.appendChild(title);
    content.appendChild(msg);
    content.appendChild(btn);
    overlay.appendChild(content);
    document.body.appendChild(overlay);
}

function initTaoAnhPage() {
    const addImagesBtn = document.getElementById('btn-add-images');
    if (addImagesBtn) {
        addImagesBtn.onclick = () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.multiple = true;
            input.onchange = (e) => {
                const files = Array.from(e.target.files);
                const displayArea = document.getElementById('image-display-area');
                if (!displayArea) return;
                files.forEach(file => {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        const src = String(event.target && event.target.result ? event.target.result : '');
                        const formEl = _createImageForm({ characterSrc: src, characterName: file.name });
                        displayArea.appendChild(formEl);
                    };
                    reader.readAsDataURL(file);
                });
            };
            input.click();
        };
    }

    const promptAllBtn = document.getElementById('btn-input-prompt-image-all');
    if (promptAllBtn) {
        promptAllBtn.onclick = () => {
            const overlay = _createPromptOverlay();
            document.body.appendChild(overlay);
        };
    }

    const generateAllBtn = document.getElementById('btn-generate-all-images');
    if (generateAllBtn) {
        generateAllBtn.onclick = async () => {
            const displayArea = document.getElementById('image-display-area');
            if (!displayArea) return;

            const forms = Array.from(displayArea.querySelectorAll('.workspace-container'));
            if (forms.length === 0) {
                if (typeof window.showSuccessOverlay === 'function') {
                    window.showSuccessOverlay('Chưa có thông tin để tạo');
                } else {
                    _showErrorOverlay('Chưa có thông tin để tạo');
                }
                return;
            }

            const tasks = forms.map(formEl => {
                const formId = formEl.dataset.formId || '';
                const charImg = formEl.querySelector(`[id$="-display-character"] img`);
                const prodImg = formEl.querySelector(`[id$="-display-product"] img`);
                const promptEl = formEl.querySelector(`[id$="-display-description"] textarea`);

                return {
                    form_id: formId,
                    image1: charImg ? String(charImg.getAttribute('src') || '') : '',
                    image2: prodImg ? String(prodImg.getAttribute('src') || '') : '',
                    prompt: promptEl ? String(promptEl.value || '') : ''
                };
            });

            const modelSelect = document.getElementById('model-select');
            const provider = modelSelect ? String(modelSelect.options[modelSelect.selectedIndex].textContent || '') : '';

            const aspectSelect = document.getElementById('aspect_ratio');
            const ratio = aspectSelect ? String(aspectSelect.value || '9:16').trim() : '9:16';

            const resultFolderLabel = document.getElementById('resultFolderLabel');
            const out_dir_label = resultFolderLabel ? String(resultFolderLabel.textContent || '').trim() : '';

            const maxTabsInput = document.getElementById('max-tabs-input');
            let max_tabs = 5;
            if (maxTabsInput) {
                const n = parseInt(String(maxTabsInput.value || '').trim(), 10);
                if (Number.isFinite(n) && n > 0) {
                    max_tabs = n;
                }
            }

            try {
                const res = await fetch('/create_images_batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ provider, out_dir_label, max_tabs, ratio, tasks })
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok || !data || data.ok !== true) {
                    const msg = (data && (data.error || data.message)) ? (data.error || data.message) : 'Tạo ảnh thất bại';
                    if (typeof window.showSuccessOverlay === 'function') {
                        window.showSuccessOverlay(msg);
                    } else {
                        _showErrorOverlay(msg);
                    }
                    return;
                }

            const results = Array.isArray(data.results) ? data.results : [];
            results.forEach(item => {
                const formId = item.form_id;
                const url = item.url;
                const error = item.error;
                if (!formId) return;

                const formEl = forms.find(f => (f.dataset.formId || '') === formId);
                if (!formEl) return;

                const resultBox = formEl.querySelector(`[id$="-display-result"]`);
                if (!resultBox) return;

                resultBox.innerHTML = '';
                if (url) {
                    const img = document.createElement('img');
                    img.src = url;
                    img.alt = 'result';
                    img.style.maxWidth = '100%';
                    img.style.maxHeight = '100%';
                    resultBox.appendChild(img);
                    
                    // Thêm nút mở thư mục nếu là custom dir (tùy chọn)
                    resultBox.title = "Click để xem ảnh";
                    resultBox.onclick = () => window.open(url, '_blank');
                } else {
                    const note = document.createElement('div');
                    note.style.cssText = 'padding: 10px; color: #ff4d4d; font-size: 12px;';
                    note.textContent = error || 'Tạo ảnh thất bại';
                    resultBox.appendChild(note);
                }
            });
            } catch (err) {
                console.error('Lỗi gọi /create_images_batch:', err);
                if (typeof window.showSuccessOverlay === 'function') {
                    window.showSuccessOverlay('Lỗi kết nối đến server');
                } else {
                    alert('Lỗi kết nối đến server');
                }
            }
        };
    }
}

window.PageInits = window.PageInits || {};
window.PageInits['tao-anh'] = initTaoAnhPage;
