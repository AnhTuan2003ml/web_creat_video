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
// CHANGE THEME
// ===============================
function changeTheme(themeName) {

    document.body.classList.remove(
        'theme-default',
        'theme-light',
        'theme-hacker',
        'theme-purple'
    );

    document.body.classList.add(themeName);

    localStorage.setItem('selectedTheme', themeName);

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

        const selector = document.getElementById('themeSelector');

        if (selector) selector.value = savedTheme;

    }


    // LOAD CONFIG
    loadConfig();

};