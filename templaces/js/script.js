// ===============================
// COPY USER ID
// ===============================
function copyId(event) {

    if (event) event.stopPropagation();

    const idText = document.getElementById('userId').innerText;

    navigator.clipboard.writeText(idText).then(() => {
        alert('Đã sao chép User ID thành công!');
    });

}



// ===============================
// THEME LIST + CHANGE THEME
// ===============================
// Danh sách theme sẽ được load từ API /listthemes
let THEMES = [];

function changeTheme(themeName) {

    document.body.classList.remove(
        'theme-default',
        'theme-hacker',
        'theme-tech',
        'theme-princess'
    );

    document.body.classList.add(themeName);

    localStorage.setItem('selectedTheme', themeName);

    // Đồng bộ radio trong grid
    const inputs = document.querySelectorAll('input[name="theme"]');
    inputs.forEach(input => {
        input.checked = (input.value === themeName);
    });

}

function renderThemes() {

    const grid = document.getElementById('themeGrid');
    if (!grid) return;

    grid.innerHTML = '';

    THEMES.forEach(theme => {

        const label = document.createElement('label');
        label.style.cursor = 'pointer';
        label.style.textAlign = 'center';

        const img = document.createElement('img');
        // dùng url do backend trả về nếu có
        img.src = theme.url || `/templaces/img/${theme.file}`;
        img.style.width = '100px';
        img.style.display = 'block';
        img.style.borderRadius = '6px';
        img.style.border = '2px solid transparent';

        // Click vào ảnh để mở xem lớn trong overlay
        img.style.cursor = 'zoom-in';
        img.addEventListener('click', function (e) {
            e.stopPropagation();
            openImageOverlay(this.src);
        });

        const input = document.createElement('input');
        input.type = 'radio';
        input.name = 'theme';
        input.value = theme.className || theme.name || theme.file;
        input.style.marginTop = '8px';

        const labelText = theme.label || theme.name || theme.file;
        const text = document.createTextNode(' ' + labelText);

        input.addEventListener('change', function () {
            if (this.checked) {
                changeTheme(input.value);
            }
        });

        label.appendChild(img);
        label.appendChild(input);
        label.appendChild(text);

        grid.appendChild(label);

    });

}


// ===============================
// IMAGE OVERLAY
// ===============================
function openImageOverlay(src) {
    const overlay = document.getElementById('imageOverlay');
    const img = document.getElementById('overlayImage');
    if (!overlay || !img) return;
    img.src = src;
    overlay.style.display = 'flex';
}

function closeImageOverlay() {
    const overlay = document.getElementById('imageOverlay');
    if (!overlay) return;
    overlay.style.display = 'none';
}


// ===============================
// AUDIO OVERLAY (NGHE THỬ NHẠC)
// ===============================
function openAudioOverlay(src, title) {
    const overlay = document.getElementById('audioOverlay');
    const audio = document.getElementById('audioPlayer');
    const titleEl = document.getElementById('audioTitle');
    if (!overlay || !audio) return;

    audio.src = src;
    audio.currentTime = 0;
    audio.play().catch(() => {});

    if (titleEl && title) {
        titleEl.textContent = title;
    }

    overlay.style.display = 'flex';
}

function closeAudioOverlay() {
    const overlay = document.getElementById('audioOverlay');
    const audio = document.getElementById('audioPlayer');
    if (audio) {
        audio.pause();
        audio.currentTime = 0;
    }
    if (overlay) {
        overlay.style.display = 'none';
    }
}



function openVideoOverlay(src, title, mime) {
    const overlay = document.getElementById('videoOverlay');
    const video = document.getElementById('videoPlayer');
    const titleEl = document.getElementById('videoTitle');
    const unsupportedMsg = document.getElementById('videoUnsupportedMsg');
    const openVlcBtn = document.getElementById('openVlcBtn');
    if (!overlay || !video || !unsupportedMsg || !openVlcBtn) return;

    // Reset trạng thái
    video.style.display = 'block';
    unsupportedMsg.style.display = 'none';

    const canPlay = mime ? video.canPlayType(mime) : '';

    if (!canPlay) {
        // Video không hỗ trợ, ẩn video, hiện message và nút VLC
        video.style.display = 'none';
        unsupportedMsg.style.display = 'block';

        // Gán event cho nút VLC
        openVlcBtn.onclick = async () => {
            // Lấy file từ state
            const file = window.__cloneVideoState?.file;
            if (!file) return;
            try {
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch('/open_video', { method: 'POST', body: formData });
                const body = await res.json().catch(() => ({}));
                if (!res.ok || !body.ok) {
                    console.error('Không mở được video bằng VLC:', body.error);
                }
            } catch (err) {
                console.error('Lỗi gọi /open_video:', err);
            }
        };
    } else {
        // Hỗ trợ, set src và autoplay
        video.src = src;
        video.currentTime = 0;
        if (titleEl && title) {
            titleEl.textContent = title;
        }
        overlay.style.display = 'flex';
        video.play().catch(() => {});
    }

    // Luôn hiện overlay
    overlay.style.display = 'flex';
}

function closeVideoOverlay() {
    const overlay = document.getElementById('videoOverlay');
    const video = document.getElementById('videoPlayer');
    if (video) {
        video.pause();
        video.currentTime = 0;
        video.removeAttribute('src');
        video.load();
    }
    if (overlay) {
        overlay.style.display = 'none';
    }
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
            initWorkspaceBindings();
        };
    });
}

function askUninstallConfirm() {
    return new Promise((resolve) => {
        const modal = document.getElementById('uninstallConfirmModal');
        const btnOk = document.getElementById('uninstallConfirmBtn');
        const btnCancel = document.getElementById('uninstallCancelBtn');

        if (!modal || !btnOk || !btnCancel) {
            resolve(false);
            return;
        }

        let settled = false;

        const cleanup = () => {
            btnOk.onclick = null;
            btnCancel.onclick = null;
            document.onkeydown = null;
        };

        const close = () => {
            modal.style.display = 'none';
            cleanup();
        };

        const confirm = () => {
            if (settled) return;
            settled = true;
            close();
            resolve(true);
        };

        const cancel = () => {
            if (settled) return;
            settled = true;
            close();
            resolve(false);
        };

        modal.style.display = 'flex';

        btnOk.onclick = confirm;
        btnCancel.onclick = cancel;

        document.onkeydown = function (e) {
            if (e.key === 'Escape') {
                e.preventDefault();
                cancel();
            }
            if (e.key === 'Enter') {
                e.preventDefault();
                confirm();
            }
        };
    });
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

function initConfirmModalBindings() {
    const btn = document.getElementById('confirmSaveBtn');
    if (!btn) return;

    btn.onclick = function(){

        const userIdSpan = document.getElementById("userId");

        const newId = userIdSpan.innerText.trim();

        if(!newId){

        document.getElementById("modalMessage").innerText="User ID không hợp lệ";

        return;

        }


        // LƯU

        userIdSpan.contentEditable = "false";

        document.getElementById("btn-copy").style.display="inline-block";

        document.getElementById("btn-save").style.display="none";


        // ĐỔI NỘI DUNG MODAL

        document.getElementById("modalMessage").innerText="Lưu thành công ✔";


        // ẨN BUTTON

        const modalButtons = document.querySelector(".modal-buttons");
        if (modalButtons) {
            modalButtons.style.display="none";
        }


        // TỰ ĐÓNG

        setTimeout(()=>{

        closeModal();

        document.getElementById("modalMessage").innerText="Lưu ID mới?";
        if (modalButtons) {
            modalButtons.style.display="flex";
        }

        },1500);

        }
}

function askDesiredMusicName(defaultName) {
    return new Promise((resolve) => {
        const modal = document.getElementById('saveMusicNameModal');
        const input = document.getElementById('saveMusicNameInput');
        const btnOk = document.getElementById('saveMusicNameConfirmBtn');
        const btnCancel = document.getElementById('saveMusicNameCancelBtn');

        if (!modal || !input || !btnOk || !btnCancel) {
            resolve(null);
            return;
        }

        let settled = false;

        const cleanup = () => {
            btnOk.onclick = null;
            btnCancel.onclick = null;
            input.onkeydown = null;
        };

        const close = () => {
            modal.style.display = 'none';
            cleanup();
        };

        const confirm = () => {
            if (settled) return;
            settled = true;
            const name = String(input.value || '').trim();
            close();
            resolve(name || null);
        };

        const cancel = () => {
            if (settled) return;
            settled = true;
            close();
            resolve(null);
        };

        input.value = defaultName || '';
        modal.style.display = 'flex';
        input.focus();
        input.select();

        btnOk.onclick = confirm;
        btnCancel.onclick = cancel;
        input.onkeydown = function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                confirm();
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                cancel();
            }
        };
    });
}


// ===============================
// XÓA FILE NHẠC ĐANG CHỌN (CÓ XÁC NHẬN)
// ===============================
let pendingDeleteMusic = null;

function deleteSelectedMusic() {
    const musicSelect = document.getElementById('musicSelect');
    if (!musicSelect) return;

    const idx = musicSelect.selectedIndex;
    if (idx <= 0) {
        // 0 là "None (Mặc định)" hoặc chưa chọn
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

            // Xóa option khỏi select
            if (index < musicSelect.options.length) {
                musicSelect.remove(index);
            }
            musicSelect.selectedIndex = 0;

            // Hiển thị "đã xóa" ngay trong overlay
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



// ===============================
// LOAD CONFIG JSON
// ===============================
async function loadConfig() {

    try {

        const response = await fetch('../../config/config.json');

        if (!response.ok) {
            throw new Error('Không thể tải file config.json');
        }

        const data = await response.json();


        // VERSION
        const versionElements = document.querySelectorAll('.app-version');

        versionElements.forEach(el => {
            el.innerText = `v${data.VERSION}`;
        });


        // USER ID
        const userIdElement = document.getElementById('userId');

        if (userIdElement) {
            userIdElement.innerText = data.ACCOUNT_ID;
        }


        // MODEL AI
        const modelSelect = document.querySelector('#sidebar .group-box select');

        if (modelSelect && data.MODEL_AI !== undefined && data.MODEL_AI !== null) {
            modelSelect.selectedIndex = Math.max(0, Number(data.MODEL_AI) - 1);
        }

        const cloneVideoModelSelect = document.getElementById('cloneVideoModelSelect');
        if (cloneVideoModelSelect && data.MODEL_AI !== undefined && data.MODEL_AI !== null) {
            cloneVideoModelSelect.selectedIndex = Math.max(0, Number(data.MODEL_AI));
        }

        const cloneVideoApiKey = document.getElementById('cloneVideoApiKey');
        if (cloneVideoApiKey && data.API_CHAT) {
            cloneVideoApiKey.value = data.API_CHAT;
        }


        console.log("System Ready. Project:", data.PROJECT);

        window.configData = data;

    }

    catch (error) {

        console.error("Lỗi loading config:", error);

        const versionElements = document.querySelectorAll('.app-version');

        versionElements.forEach(el => el.innerText = "Error");

    }

}



// ===============================
// ENABLE EDIT USER ID
// ===============================
function enableEdit() {

    const userIdSpan = document.getElementById('userId');

    if (userIdSpan.contentEditable === "true") return;

    userIdSpan.contentEditable = "true";

    userIdSpan.focus();


    document.getElementById('btn-copy').style.display = 'none';
    document.getElementById('btn-save').style.display = 'inline-block';

}



// ===============================
// SAVE USER ID
// ===============================
function saveUserId(event){

    if(event) event.stopPropagation();
    
    const modal = document.getElementById("confirmModal");
    
    if (modal) {
        modal.style.display = "flex";
    }
    
    }

    function closeModal(){

        document.getElementById("confirmModal").style.display = "none";
        
        }
// ===============================
// CANCEL EDIT
// ===============================
function cancelEdit() {

    const userIdSpan = document.getElementById('userId');

    userIdSpan.contentEditable = "false";

    document.getElementById('btn-copy').style.display = 'inline-block';
    document.getElementById('btn-save').style.display = 'none';

}



// ===============================
// KEYBOARD CONTROL
// ===============================
document.addEventListener("keydown", function(e) {

    const userIdSpan = document.getElementById("userId");

    if (!userIdSpan) return;


    // ENTER = SAVE
    if (userIdSpan.contentEditable === "true" && e.key === "Enter") {

        e.preventDefault();

        saveUserId(e);

    }


    // ESC = CANCEL
    if (userIdSpan.contentEditable === "true" && e.key === "Escape") {

        cancelEdit();

    }

});



// ===============================
// PAGE LOAD
// ===============================
window.onload = async function() {

    await loadOverlays();
    initConfirmModalBindings();

    initTabBindings();

    await loadWorkspace('home.html');

    // LOAD THEME
    const savedTheme = localStorage.getItem('selectedTheme');

    if (savedTheme) {
        document.body.classList.add(savedTheme);
    }

    initWorkspaceBindings();
};

function initWorkspaceBindings() {

    const cloneVideoChooseBtn = document.getElementById('cloneVideoChooseBtn');
    const cloneVideoFileInput = document.getElementById('cloneVideoFileInput');
    const cloneVideoPathInput = document.getElementById('cloneVideoPathInput');
    const cloneVideoPreview = document.getElementById('cloneVideoPreview');
    const cloneVideoPreviewThumb = document.getElementById('cloneVideoPreviewThumb');
    const cloneVideoPreviewVideo = document.getElementById('cloneVideoPreviewVideo');
    const cloneVideoPlayIcon = document.getElementById('cloneVideoPlayIcon');

    if (!window.__cloneVideoState) {
        window.__cloneVideoState = { objectUrl: '', lastFileSig: '', file: null };
    }

    const setCloneVideoObjectUrl = (url) => {
        if (window.__cloneVideoState.objectUrl && window.__cloneVideoState.objectUrl !== url) {
            try { URL.revokeObjectURL(window.__cloneVideoState.objectUrl); } catch (_) {}
        }
        window.__cloneVideoState.objectUrl = url;
    };

    const guessMimeTypeFromName = (name) => {
        const lower = String(name || '').toLowerCase();
        if (lower.endsWith('.mp4')) return 'video/mp4';
        if (lower.endsWith('.webm')) return 'video/webm';
        if (lower.endsWith('.ogv') || lower.endsWith('.ogg')) return 'video/ogg';
        if (lower.endsWith('.mov')) return 'video/quicktime';
        return '';
    };

    const openVideoInOsPlayer = async (file) => {
        if (!file) return;
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch('/open_video', { method: 'POST', body: formData });
            const body = await res.json().catch(() => ({}));
            if (!res.ok || !body.ok) {
                console.error('Không mở được video bằng hệ điều hành:', body.error);
            }
        } catch (err) {
            console.error('Lỗi gọi /open_video:', err);
        }
    };

    const tryExtractCloneVideoFrame = async (file) => {
        if (!file) return null;

        // tránh gọi lại nếu cùng 1 file (tên + size + lastModified)
        const sig = `${file.name}:${file.size}:${file.lastModified}`;
        if (window.__cloneVideoState.lastFileSig === sig && cloneVideoPreviewThumb && cloneVideoPreviewThumb.src) {
            return cloneVideoPreviewThumb.src;
        }
        window.__cloneVideoState.lastFileSig = sig;

        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch('/extract_frame', {
                method: 'POST',
                body: formData,
            });
            const body = await res.json().catch(() => ({}));
            if (!res.ok || !body.ok || !body.data_url) {
                return null;
            }
            return body.data_url;
        } catch (err) {
            console.error('Lỗi gọi /extract_frame:', err);
            return null;
        }
    };

    if (cloneVideoChooseBtn && cloneVideoFileInput) {
        cloneVideoChooseBtn.onclick = function () {
            cloneVideoFileInput.click();
        };

        cloneVideoFileInput.onchange = async function () {
            if (!this.files || !this.files[0]) return;
            const file = this.files[0];
            window.__cloneVideoState.file = file;
            const url = URL.createObjectURL(file);
            setCloneVideoObjectUrl(url);

            if (cloneVideoPathInput) {
                cloneVideoPathInput.value = file.name;
            }

            // Thumbnail bằng ffmpeg (backend). Nếu có thumb thì ưu tiên hiển thị ảnh để tránh lỗi codec trên browser
            const thumbUrl = await tryExtractCloneVideoFrame(file);
            if (thumbUrl && cloneVideoPreviewThumb) {
                cloneVideoPreviewThumb.src = thumbUrl;
                cloneVideoPreviewThumb.style.display = 'block';
                if (cloneVideoPreviewVideo) {
                    cloneVideoPreviewVideo.style.display = 'none';
                    cloneVideoPreviewVideo.removeAttribute('src');
                    cloneVideoPreviewVideo.load();
                }
            } else {
                if (cloneVideoPreviewThumb) {
                    cloneVideoPreviewThumb.removeAttribute('src');
                    cloneVideoPreviewThumb.style.display = 'none';
                }

                // Chỉ preview bằng <video> nếu browser hỗ trợ, tránh lỗi "No video with supported format..."
                if (cloneVideoPreviewVideo) {
                    const mime = file.type || guessMimeTypeFromName(file.name);
                    const playable = mime ? cloneVideoPreviewVideo.canPlayType(mime) : '';

                    if (playable) {
                        cloneVideoPreviewVideo.style.display = 'block';
                        cloneVideoPreviewVideo.src = url;
                        cloneVideoPreviewVideo.load();
                    } else {
                        cloneVideoPreviewVideo.style.display = 'none';
                        cloneVideoPreviewVideo.removeAttribute('src');
                        cloneVideoPreviewVideo.load();
                    }
                }
            }

            if (cloneVideoPlayIcon) {
                cloneVideoPlayIcon.style.display = 'flex';
            }
        };
    }

    if (cloneVideoPreview) {
        cloneVideoPreview.onclick = function () {
            const url = window.__cloneVideoState?.objectUrl;
            if (!url) return;
            const title = (cloneVideoPathInput && cloneVideoPathInput.value) ? cloneVideoPathInput.value : 'Xem video';

            const file = window.__cloneVideoState?.file;
            const mime = file?.type || guessMimeTypeFromName(file?.name);
            const probeEl = document.getElementById('videoPlayer');
            const canPlay = (probeEl && mime) ? probeEl.canPlayType(mime) : '';

            // Nếu browser không play được thì mở bằng app mặc định của hệ điều hành
            if (!canPlay && file) {
                openVideoInOsPlayer(file);
                return;
            }

            openVideoOverlay(url, title);
        };
    }

    // RENDER THEME GRID (đọc từ danh sách file)
    // tạm thời render (có thể rỗng) rồi sẽ cập nhật sau khi fetch list
    renderThemes();

    // LOAD THEME LIST từ API local /listthemes
    fetch('/listthemes')
        .then(res => res.json())
        .then(list => {
            // map danh sách ảnh thành THEMES
            THEMES = list.map(item => ({
                className: item.theme || 'theme-default',
                name: item.name,
                file: item.file,
                url: item.url,
                label: item.name,
            }));
            renderThemes();
        })
        .catch(err => {
            console.error('Không load được danh sách theme:', err);
        });

    // Đồng bộ radio với theme đang áp dụng
    const currentThemeClass = Array.from(document.body.classList)
        .find(cls => ['theme-default', 'theme-hacker', 'theme-tech', 'theme-princess'].includes(cls)) || 'theme-default';
    const themeInputs = document.querySelectorAll('input[name="theme"]');
    themeInputs.forEach(input => {
        if (input.value === currentThemeClass) input.checked = true;
    });

    // GÁN SỰ KIỆN CHỌN THƯ MỤC KẾT QUẢ
    const resultBtn = document.getElementById('resultFolderBtn');
    const resultInput = document.getElementById('resultFolderInput');
    const resultLabel = document.getElementById('resultFolderLabel');

    if (resultBtn && resultInput && resultLabel) {
        resultBtn.onclick = function () {
            resultInput.click();
        };

        resultInput.onchange = function () {
            if (!this.files || this.files.length === 0) return;

            // Lấy "đường dẫn" thư mục tương đối từ file đầu tiên
            const firstFile = this.files[0];
            let folderPath = '';

            if (firstFile.webkitRelativePath) {
                const parts = firstFile.webkitRelativePath.split('/');
                // Bỏ tên file, chỉ giữ lại phần thư mục
                if (parts.length > 1) {
                    folderPath = parts.slice(0, -1).join('/');
                } else {
                    folderPath = parts[0];
                }
            }

            if (!folderPath) {
                folderPath = 'Đã chọn thư mục';
            }

            // Hiển thị lại "đường dẫn" thư mục lên nút
            resultLabel.textContent = folderPath;
        };
    }

    const uninstallBtn = document.getElementById('uninstallBtn');
    if (uninstallBtn) {
        uninstallBtn.onclick = async function () {
            const ok = await askUninstallConfirm();
            if (!ok) return;

            fetch('/uninstall', {
                method: 'POST',
            })
                .then(res => res.json().then(body => ({ ok: res.ok, body })))
                .then(({ ok, body }) => {
                    if (!ok || !body.ok) {
                        console.error('Gỡ cài đặt thất bại:', body.error);
                        return;
                    }
                })
                .catch(err => {
                    console.error('Lỗi gọi /uninstall:', err);
                });
        };
    }

    // LOAD CONFIG (thông tin từ config.json)
    loadConfig();

    // LOAD MUSIC LIST từ API local /listmusic
    fetch('/listmusic')
        .then(res => res.json())
        .then(list => {
            const musicSelect = document.getElementById('musicSelect');
            if (!musicSelect) return;

            // đảm bảo option đầu tiên là None
            let first = musicSelect.options[0];
            if (!first) {
                first = document.createElement('option');
                first.textContent = 'None (Mặc định)';
                musicSelect.appendChild(first);
            }
            first.value = '';

            // xóa các option nhạc cũ
            while (musicSelect.options.length > 1) {
                musicSelect.remove(1);
            }

            list.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.url;      // URL để phát nhạc
                opt.textContent = item.name;
                musicSelect.appendChild(opt);
            });
        })
        .catch(err => {
            console.error('Không load được danh sách nhạc:', err);
        });

    // GÁN SỰ KIỆN "NGHE THỬ"
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

    // GÁN SỰ KIỆN "THÊM ÂM THANH"
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

                    // reset input để có thể chọn lại cùng file nếu cần
                    addMusicInput.value = '';
                })
                .catch(err => {
                    console.error('Lỗi gọi /uploadmusic:', err);
                });
        };
    }
}