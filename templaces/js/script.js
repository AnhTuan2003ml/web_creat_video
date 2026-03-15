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
        const modelSelect = document.querySelector('.group-box select');

        if (modelSelect && data.MODEL_AI) {
            modelSelect.selectedIndex = data.MODEL_AI - 1;
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
    
    modal.style.display = "flex";
    
    }

    function closeModal(){

        document.getElementById("confirmModal").style.display = "none";
        
        }
        
        
        
        document.getElementById("confirmSaveBtn").onclick = function(){
        
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
        
        document.querySelector(".modal-buttons").style.display="none";
        
        
        // TỰ ĐÓNG
        
        setTimeout(()=>{
        
        closeModal();
        
        document.getElementById("modalMessage").innerText="Lưu ID mới?";
        document.querySelector(".modal-buttons").style.display="flex";
        
        },1500);
        
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
window.onload = function() {

    // LOAD THEME
    const savedTheme = localStorage.getItem('selectedTheme');

    if (savedTheme) {
        document.body.classList.add(savedTheme);
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
        resultBtn.addEventListener('click', function () {
            resultInput.click();
        });

        resultInput.addEventListener('change', function () {
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
        });
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
        previewBtn.addEventListener('click', function () {
            const musicSelect = document.getElementById('musicSelect');
            if (!musicSelect) return;

            const opt = musicSelect.options[musicSelect.selectedIndex];
            if (!opt || !opt.value) return;

            openAudioOverlay(opt.value, opt.textContent);
        });
    }

    // GÁN SỰ KIỆN "THÊM ÂM THANH"
    const addMusicBtn = document.getElementById('addMusicBtn');
    const addMusicInput = document.getElementById('addMusicInput');
    if (addMusicBtn && addMusicInput) {
        addMusicBtn.addEventListener('click', function () {
            addMusicInput.click();
        });

        addMusicInput.addEventListener('change', function () {
            if (!this.files || !this.files[0]) return;

            const file = this.files[0];
            const formData = new FormData();
            formData.append('file', file);

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
        });
    }

};