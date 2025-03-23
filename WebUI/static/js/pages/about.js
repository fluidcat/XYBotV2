document.addEventListener('DOMContentLoaded', function () {
    // 检查最新版本
    checkLatestVersion();

    // 添加平滑滚动效果
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// 检查最新版本
function checkLatestVersion() {
    const currentVersion = document.getElementById('currentVersion');
    const latestVersion = document.getElementById('latestVersion');
    const versionStatus = document.getElementById('versionStatus');

    if (!currentVersion || !latestVersion || !versionStatus) return;

    fetch('/about/api/version')
        .then(response => response.json())
        .then(data => {
            if (data.latest_version) {
                latestVersion.textContent = data.latest_version;

                // 比较版本
                if (data.latest_version === currentVersion.textContent) {
                    versionStatus.className = 'badge bg-success';
                    versionStatus.textContent = '已是最新版本';
                } else {
                    versionStatus.className = 'badge bg-warning';
                    versionStatus.textContent = '有新版本可用';
                }
            }
        })
        .catch(error => {
            console.error('检查版本出错:', error);
            versionStatus.className = 'badge bg-secondary';
            versionStatus.textContent = '版本检查失败';
        });
}

// 复制文本到剪贴板
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();

    try {
        document.execCommand('copy');
        showToast('复制成功！');
    } catch (err) {
        console.error('复制失败:', err);
        showToast('复制失败，请手动复制');
    }

    document.body.removeChild(textarea);
}

// 显示提示消息
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.appendChild(toast);
    document.body.appendChild(container);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(container);
    });
} 