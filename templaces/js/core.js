async function loadWorkspace(page) {
    const root = document.getElementById('workspace-root');
    if (!root) return;

    try {
        const res = await fetch(`/templaces/html/${page}`);
        if (!res.ok) return;
        const html = await res.text();
        root.innerHTML = html;
    } catch (err) {
        console.error('Không thể tải workspace:', err);
    }
}

async function loadOverlays() {
    const root = document.getElementById('overlays-root');
    if (!root) return;

    try {
        const res = await fetch('/templaces/html/overlays.html');
        if (!res.ok) return;
        const html = await res.text();
        root.innerHTML = html;
    } catch (err) {
        console.error('Không thể tải overlays:', err);
    }
}

function slugifyTabLabel(label) {
    const map = {
        'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
        'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
        'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
        'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
        'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
        'đ': 'd',
    };

    const normalized = String(label)
        .trim()
        .toLowerCase()
        .split('')
        .map(ch => map[ch] || ch)
        .join('');

    return normalized
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
}

function initTabBindings() {
    const tabs = document.querySelectorAll('.horizontal-tabs .tab-item');
    if (!tabs || tabs.length === 0) return;

    tabs.forEach(tab => {
        tab.onclick = async function () {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const label = (tab.textContent || '').trim();
            const slug = slugifyTabLabel(label);
            const page = `${slug}.html`;

            await loadWorkspace(page);
            await loadConfig();
            initWorkspaceBindings(slug);
        };
    });
}

function initWorkspaceBindings(slug) {
    const inits = window.PageInits || {};
    const initFn = inits[slug];
    if (typeof initFn === 'function') {
        initFn();
    }
}

async function saveToConfig(data) {
    try {
        await fetch('/save_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    } catch (err) {
        console.error('Lỗi lưu config:', err);
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/config/config.json');
        if (!response.ok) {
            throw new Error('Không thể tải file config.json');
        }

        const data = await response.json();

        const setSelectByValueOrText = (selectEl, desired) => {
            if (!selectEl) return;
            if (desired === undefined || desired === null) return;

            const desiredStr = String(desired);
            const desiredNum = Number(desiredStr);
            const hasNumeric = Number.isFinite(desiredNum) && desiredStr.trim() !== '';

            // 1) Match by option.value
            for (let i = 0; i < selectEl.options.length; i++) {
                if (String(selectEl.options[i].value) === desiredStr) {
                    selectEl.selectedIndex = i;
                    return;
                }
            }

            // 2) Match by option.textContent contains desired
            for (let i = 0; i < selectEl.options.length; i++) {
                const text = String(selectEl.options[i].textContent || '');
                if (text.toLowerCase().includes(desiredStr.toLowerCase())) {
                    selectEl.selectedIndex = i;
                    return;
                }
            }

            // 3) Backward-compat: if stored as index
            if (hasNumeric) {
                const idx = Math.max(0, Math.min(selectEl.options.length - 1, Math.floor(desiredNum)));
                selectEl.selectedIndex = idx;
            }
        };

        const versionElements = document.querySelectorAll('.app-version');
        versionElements.forEach(el => {
            el.innerText = `v${data.VERSION}`;
        });

        const userIdElement = document.getElementById('userId');
        if (userIdElement) {
            userIdElement.innerText = data.ACCOUNT_ID;
        }

        // Sidebar model select (UI text may not match MODEL_AI string, so only best-effort)
        const sidebarModelSelect = document.querySelector('#sidebar .group-box select');
        if (sidebarModelSelect) {
            setSelectByValueOrText(sidebarModelSelect, data.MODEL_AI);
        }

        // Model select with ID
        const modelSelect = document.getElementById('model-select');
        if (modelSelect) {
            setSelectByValueOrText(modelSelect, data.MODEL_AI);
        }

        const cloneVideoModelSelect = document.getElementById('cloneVideoModelSelect');
        setSelectByValueOrText(cloneVideoModelSelect, data.MODEL_AI);

        const cloneVideoApiKey = document.getElementById('cloneVideoApiKey');
        if (cloneVideoApiKey) {
            cloneVideoApiKey.value = data.API_CHAT || data.API_KEY || '';
        }

        window.configData = data;
    } catch (error) {
        console.error('Lỗi loading config:', error);
        const versionElements = document.querySelectorAll('.app-version');
        versionElements.forEach(el => el.innerText = 'Error');
    }
}

function copyId(event) {
    if (event) event.stopPropagation();
    const idEl = document.getElementById('userId');
    if (!idEl) return;
    const idText = idEl.innerText;
    navigator.clipboard.writeText(idText).then(() => {
        alert('Đã sao chép User ID thành công!');
    });
}

function enableEdit() {
    const userIdSpan = document.getElementById('userId');
    if (!userIdSpan) return;
    if (userIdSpan.contentEditable === 'true') return;

    userIdSpan.contentEditable = 'true';
    userIdSpan.focus();

    const btnCopy = document.getElementById('btn-copy');
    const btnSave = document.getElementById('btn-save');
    if (btnCopy) btnCopy.style.display = 'none';
    if (btnSave) btnSave.style.display = 'inline-block';
}

function saveUserId(event) {
    if (event) event.stopPropagation();
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function cancelEdit() {
    const userIdSpan = document.getElementById('userId');
    if (!userIdSpan) return;

    userIdSpan.contentEditable = 'false';
    const btnCopy = document.getElementById('btn-copy');
    const btnSave = document.getElementById('btn-save');
    if (btnCopy) btnCopy.style.display = 'inline-block';
    if (btnSave) btnSave.style.display = 'none';
}

function closeModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function initConfirmModalBindings() {
    const btn = document.getElementById('confirmSaveBtn');
    if (!btn) return;

    btn.onclick = function () {
        const userIdSpan = document.getElementById('userId');
        if (!userIdSpan) return;

        const newId = userIdSpan.innerText.trim();
        if (!newId) {
            const msg = document.getElementById('modalMessage');
            if (msg) msg.innerText = 'User ID không hợp lệ';
            return;
        }

        userIdSpan.contentEditable = 'false';

        const btnCopy = document.getElementById('btn-copy');
        const btnSave = document.getElementById('btn-save');
        if (btnCopy) btnCopy.style.display = 'inline-block';
        if (btnSave) btnSave.style.display = 'none';

        const modalMessage = document.getElementById('modalMessage');
        if (modalMessage) modalMessage.innerText = 'Lưu thành công ✔';

        const modalButtons = document.querySelector('.modal-buttons');
        if (modalButtons) modalButtons.style.display = 'none';

        setTimeout(() => {
            closeModal();
            if (modalMessage) modalMessage.innerText = 'Lưu ID mới?';
            if (modalButtons) modalButtons.style.display = 'flex';
        }, 1500);
    };
}

function showSuccessOverlay(message) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;

    const messageBox = document.createElement('div');
    messageBox.style.cssText = `
        background: var(--card-bg, rgba(255,255,255,0.1));
        border: 2px solid var(--accent-color, #4CAF50);
        border-radius: 12px;
        padding: 20px 40px;
        color: var(--text-primary, #fff);
        font-size: 18px;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
        animation: slideUp 0.3s ease;
    `;
    messageBox.textContent = message;

    overlay.appendChild(messageBox);
    document.body.appendChild(overlay);

    setTimeout(() => {
        overlay.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
        }, 300);
    }, 2000);

    overlay.addEventListener('click', () => {
        overlay.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
        }, 300);
    });
}

if (!document.getElementById('success-overlay-styles')) {
    const style = document.createElement('style');
    style.id = 'success-overlay-styles';
    style.textContent = `
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    `;
    document.head.appendChild(style);
}

function showProcessingOverlay(message) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;

    const messageBox = document.createElement('div');
    messageBox.style.cssText = `
        background: var(--card-bg, rgba(255,255,255,0.1));
        border: 2px solid var(--accent-color, #3498db);
        border-radius: 12px;
        padding: 20px 40px;
        color: var(--text-primary, #fff);
        font-size: 18px;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(52, 152, 219, 0.3);
        animation: slideUp 0.3s ease;
    `;
    messageBox.textContent = message;

    overlay.appendChild(messageBox);
    document.body.appendChild(overlay);
}

function closeProcessingOverlay() {
    const overlays = document.querySelectorAll('div[style*="position: fixed"]');
    overlays.forEach(overlay => {
        if (overlay.textContent.includes('Đang tạo kịch bản') || overlay.textContent.includes('Đang xử lý')) {
            overlay.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                if (document.body.contains(overlay)) {
                    document.body.removeChild(overlay);
                }
            }, 300);
        }
    });
}

let pendingDeleteMusic = null;

function deleteSelectedMusic() {
    const musicSelect = document.getElementById('musicSelect');
    if (!musicSelect) return;

    const idx = musicSelect.selectedIndex;
    if (idx <= 0) {
        return;
    }

    const opt = musicSelect.options[idx];
    const fileName = opt.textContent;

    pendingDeleteMusic = { index: idx, name: fileName };

    const msgEl = document.getElementById('deleteMusicMessage');
    const btnsEl = document.getElementById('deleteMusicButtons');
    if (msgEl) {
        msgEl.textContent = `Xóa file nhạc "${fileName}"?`;
    }
    if (btnsEl) {
        btnsEl.style.display = 'flex';
    }

    const modal = document.getElementById('deleteMusicModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeDeleteMusicModal() {
    const modal = document.getElementById('deleteMusicModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function confirmDeleteMusic() {
    const musicSelect = document.getElementById('musicSelect');
    if (!musicSelect || !pendingDeleteMusic) return;

    const { index, name } = pendingDeleteMusic;

    fetch('/deletemusic', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name }),
    })
        .then(res => res.json().then(body => ({ ok: res.ok, body })))
        .then(({ ok, body }) => {
            const msgEl = document.getElementById('deleteMusicMessage');
            const btnsEl = document.getElementById('deleteMusicButtons');

            if (!ok || !body.ok) {
                console.error('Xóa nhạc thất bại:', body.error);
                if (msgEl) {
                    msgEl.textContent = 'Xóa thất bại. Vui lòng thử lại.';
                }
                return;
            }

            if (index < musicSelect.options.length) {
                musicSelect.remove(index);
            }
            musicSelect.selectedIndex = 0;

            if (msgEl) {
                msgEl.textContent = 'Đã xóa file nhạc ✔';
            }
            if (btnsEl) {
                btnsEl.style.display = 'none';
            }

            pendingDeleteMusic = null;

            setTimeout(() => {
                closeDeleteMusicModal();
                if (msgEl) {
                    msgEl.textContent = 'Xóa file nhạc này?';
                }
                if (btnsEl) {
                    btnsEl.style.display = 'flex';
                }
            }, 1500);
        })
        .catch(err => {
            console.error('Lỗi gọi /deletemusic:', err);
        });
}

async function loadMusicList() {
    try {
        const res = await fetch('/listmusic');
        const list = await res.json().catch(() => []);
        const musicSelect = document.getElementById('musicSelect');
        if (!musicSelect) return;

        let first = musicSelect.options[0];
        if (!first) {
            first = document.createElement('option');
            first.textContent = 'None (Mặc định)';
            musicSelect.appendChild(first);
        }
        first.value = '';

        while (musicSelect.options.length > 1) {
            musicSelect.remove(1);
        }

        (Array.isArray(list) ? list : []).forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.url;
            opt.textContent = item.name;
            musicSelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Không load được danh sách nhạc:', err);
    }
}

function initMusicBindings() {
    // Preview music
    const previewBtn = document.querySelector('.btn-preview');
    if (previewBtn) {
        previewBtn.onclick = function () {
            const musicSelect = document.getElementById('musicSelect');
            if (!musicSelect) return;

            const opt = musicSelect.options[musicSelect.selectedIndex];
            if (!opt || !opt.value) return;

            openAudioOverlay(opt.value, opt.textContent);
        };
    }

    // Add music
    const addMusicBtn = document.getElementById('addMusicBtn');
    const addMusicInput = document.getElementById('addMusicInput');
    if (addMusicBtn && addMusicInput) {
        addMusicBtn.onclick = function () {
            addMusicInput.click();
        };

        addMusicInput.onchange = async function () {
            if (!this.files || !this.files[0]) return;

            const file = this.files[0];
            const desiredName = await askDesiredMusicName(file.name);
            if (!desiredName) {
                addMusicInput.value = '';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('desired_name', desiredName);

            fetch('/uploadmusic', {
                method: 'POST',
                body: formData,
            })
                .then(res => res.json().then(body => ({ ok: res.ok, body })))
                .then(({ ok, body }) => {
                    if (!ok || !body.ok) {
                        console.error('Thêm nhạc thất bại:', body.error);
                        return;
                    }

                    const musicSelect = document.getElementById('musicSelect');
                    if (!musicSelect) return;

                    const opt = document.createElement('option');
                    opt.value = body.url;
                    opt.textContent = body.name;
                    musicSelect.appendChild(opt);
                    musicSelect.value = body.url;

                    addMusicInput.value = '';
                })
                .catch(err => {
                    console.error('Lỗi gọi /uploadmusic:', err);
                });
        };
    }
}

function initResultFolderBindings() {
    const resultBtn = document.getElementById('resultFolderBtn');
    const resultInput = document.getElementById('resultFolderInput');
    const resultLabel = document.getElementById('resultFolderLabel');

    if (!resultBtn || !resultInput || !resultLabel) return;

    resultBtn.onclick = function () {
        resultInput.click();
    };

    resultInput.onchange = function () {
        if (!this.files || this.files.length === 0) return;

        const firstFile = this.files[0];
        let folderPath = '';

        if (firstFile.webkitRelativePath) {
            const parts = firstFile.webkitRelativePath.split('/');
            if (parts.length > 1) {
                folderPath = parts.slice(0, -1).join('/');
            } else {
                folderPath = parts[0];
            }
        }

        if (!folderPath) {
            folderPath = 'Đã chọn thư mục';
        }

        resultLabel.textContent = folderPath;
    };
}

function initSettingsAccountBindings() {
    const settingsBtn = document.getElementById('btn-settings-account');
    const modelSelect = document.getElementById('model-select');

    if (!settingsBtn || !modelSelect) return;

    settingsBtn.onclick = async function () {
        const selectedModel = modelSelect.options[modelSelect.selectedIndex].textContent;
        
        try {
            const response = await fetch('/setup_profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    model: selectedModel 
                })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                showSuccessOverlay('Thiết lập tài khoản thành công!');
            } else {
                showSuccessOverlay('Thiết lập tài khoản thất bại: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Lỗi thiết lập tài khoản:', error);
            showSuccessOverlay('Lỗi kết nối đến server');
        }
    };
}

window.onload = async function () {
    await loadOverlays();
    initConfirmModalBindings();
    initTabBindings();

    await loadWorkspace('home.html');

    const savedTheme = localStorage.getItem('selectedTheme');
    if (savedTheme) {
        document.body.classList.add(savedTheme);
    }

    await loadConfig();

    await loadMusicList();
    initMusicBindings();

    initResultFolderBindings();
    initSettingsAccountBindings();

    initWorkspaceBindings('home');

    document.addEventListener('keydown', function (e) {
        const userIdSpan = document.getElementById('userId');
        if (!userIdSpan) return;

        if (userIdSpan.contentEditable === 'true' && e.key === 'Enter') {
            e.preventDefault();
            saveUserId(e);
        }

        if (userIdSpan.contentEditable === 'true' && e.key === 'Escape') {
            cancelEdit();
        }
    });
};
