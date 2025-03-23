document.addEventListener('DOMContentLoaded', function () {
    // 初始化文件浏览器
    initFileBrowser('file-explorer', window.initialPath || '');

    // 处理视图切换
    const viewToggleBtn = document.getElementById('view-toggle');
    if (viewToggleBtn) {
        viewToggleBtn.addEventListener('click', function () {
            const currentView = localStorage.getItem('explorer-view') || 'list';
            const newView = currentView === 'list' ? 'grid' : 'list';

            // 保存视图选择
            localStorage.setItem('explorer-view', newView);

            // 更新视图
            updateExplorerView(newView);
        });

        // 初始化视图
        const savedView = localStorage.getItem('explorer-view') || 'list';
        updateExplorerView(savedView);
    }

    // 更新视图显示
    function updateExplorerView(view) {
        const container = document.querySelector('.file-browser-container');
        if (!container) return;

        if (view === 'grid') {
            container.classList.add('view-grid');
            container.classList.remove('view-list');
            viewToggleBtn.innerHTML = '<i class="fas fa-list"></i>';
        } else {
            container.classList.add('view-list');
            container.classList.remove('view-grid');
            viewToggleBtn.innerHTML = '<i class="fas fa-th"></i>';
        }
    }

    // 处理文件操作
    function handleFileOperation(operation, path) {
        switch (operation) {
            case 'open':
                if (isImageFile(path)) {
                    previewImage(path);
                } else if (isTextFile(path)) {
                    openFileViewer(path);
                } else {
                    downloadFile(path);
                }
                break;
            case 'download':
                downloadFile(path);
                break;
            case 'delete':
                deleteFile(path);
                break;
        }
    }

    // 检查文件类型
    function isImageFile(path) {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
        return imageExtensions.some(ext => path.toLowerCase().endsWith(ext));
    }

    function isTextFile(path) {
        const textExtensions = ['.txt', '.log', '.md', '.json', '.yml', '.yaml', '.toml', '.ini', '.conf'];
        return textExtensions.some(ext => path.toLowerCase().endsWith(ext));
    }

    // 预览图片
    function previewImage(path) {
        const modal = new ImagePreviewModal({
            title: '图片预览',
            imagePath: path
        });
        modal.show();
    }

    // 打开文件查看器
    function openFileViewer(path) {
        window.location.href = `/explorer/view/${encodeURIComponent(path)}`;
    }

    // 下载文件
    function downloadFile(path) {
        window.location.href = `/file/download?path=${encodeURIComponent(path)}`;
    }

    // 删除文件
    function deleteFile(path) {
        const modal = new ConfirmModal({
            title: '确认删除',
            message: `确定要删除 ${path} 吗？此操作不可恢复。`,
            confirmText: '删除',
            cancelText: '取消',
            onConfirm: async () => {
                try {
                    const response = await fetch('/file/api/delete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({path})
                    });

                    const result = await response.json();
                    if (result.success) {
                        showNotification('文件删除成功', 'success');
                        // 重新加载文件列表
                        const refreshBtn = document.getElementById('file-explorer-refresh');
                        if (refreshBtn) {
                            refreshBtn.click();
                        }
                    } else {
                        showNotification(result.message || '删除失败', 'error');
                    }
                } catch (error) {
                    console.error('删除文件失败:', error);
                    showNotification('删除文件失败', 'error');
                }
            }
        });
        modal.show();
    }
});

// 图片预览模态框类
class ImagePreviewModal extends BaseModal {
    constructor(options = {}) {
        super({
            ...options,
            size: 'lg'
        });
        this.imagePath = options.imagePath;
    }

    getModalBody() {
        return `
            <div class="text-center">
                <img src="/file/preview?path=${encodeURIComponent(this.imagePath)}" 
                     class="img-fluid" 
                     alt="图片预览"
                     style="max-height: 80vh;">
            </div>
        `;
    }

    getModalFooter() {
        return `
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                <a href="/file/download?path=${encodeURIComponent(this.imagePath)}" 
                   class="btn btn-primary">
                    <i class="fas fa-download"></i> 下载
                </a>
            </div>
        `;
    }
} 