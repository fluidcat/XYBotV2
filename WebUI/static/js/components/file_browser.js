(function () {
    // 检查全局工具函数是否已存在，不存在则初始化
    if (!window.FileBrowserUtils) {
        window.FileBrowserUtils = {
            getLoadingTemplate: () => `
                <div class="text-center p-3">
                    <i class="fas fa-spinner fa-spin"></i> 加载中...
                </div>
            `,

            handleResponse: async (response, successHandler) => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || `HTTP错误: ${response.status}`);
                }
                return successHandler(data);
            },

            handleError: (context, error) => {
                console.error(`${context}:`, error);
                alert(`${context}: ${error.message}`);
            },

            formatFileSize: (bytes) => {
                if (bytes === 0) return '0 B';
                const units = ['B', 'KB', 'MB', 'GB', 'TB'];
                const i = Math.floor(Math.log(bytes) / Math.log(1024));
                return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + units[i];
            },

            formatDateTime: (timestamp) => {
                const date = new Date(timestamp * 1000);
                return date.toLocaleString();
            },

            getFileIcon: (filename) => {
                const extension = filename.split('.').pop().toLowerCase();
                const iconMap = {
                    'txt': 'far fa-file-alt text-secondary',
                    'log': 'fas fa-file-alt text-info',
                    'py': 'fab fa-python text-primary',
                    'js': 'fab fa-js-square text-warning',
                    'html': 'fab fa-html5 text-danger',
                    'css': 'fab fa-css3-alt text-primary',
                    'json': 'fas fa-file-code text-secondary',
                    'md': 'fas fa-file-alt text-primary',
                    'jpg': 'far fa-file-image text-success',
                    'jpeg': 'far fa-file-image text-success',
                    'png': 'far fa-file-image text-success'
                };
                return iconMap[extension] || 'far fa-file text-secondary';
            },

            getParentPath: (path) => {
                if (!path) return '';
                const lastSlashIndex = path.lastIndexOf('/');
                return lastSlashIndex === -1 ? '' : path.substring(0, lastSlashIndex);
            }
        };
    }

    // 全局暴露文件浏览器初始化函数
    window.initFileBrowser = function (containerId, initialPath = '') {
        const container = document.getElementById(containerId);
        if (!container) return;

        // 状态管理对象
        const state = {
            currentPath: initialPath,
            viewMode: 'list'
        };

        // DOM元素引用
        const dom = {
            fileList: document.getElementById(`${containerId}-list`),
            breadcrumb: container.querySelector('.file-path-breadcrumb'),
            fullPath: document.getElementById(`${containerId}-full-path`),
            refreshBtn: document.getElementById(`${containerId}-refresh`),
            viewToggleBtn: document.getElementById(`${containerId}-view-toggle`)
        };

        // 初始化事件监听
        function initEventListeners() {
            // 面包屑导航
            if (dom.breadcrumb) {
                dom.breadcrumb.addEventListener('click', handleBreadcrumbClick);
            }

            // 刷新按钮
            if (dom.refreshBtn) {
                dom.refreshBtn.addEventListener('click', () => {
                    core.loadFileList(state.currentPath);
                });
            }

            // 视图切换
            if (dom.viewToggleBtn) {
                dom.viewToggleBtn.addEventListener('click', toggleViewMode);
            }
        }

        // 核心功能方法
        const core = {
            // 加载文件列表
            async loadFileList(path) {
                try {
                    const response = await fetch(`/file/api/list?path=${encodeURIComponent(path)}`);
                    await FileBrowserUtils.handleResponse(response, (data) => {

                        if (data.files && Array.isArray(data.files)) {
                            state.currentPath = data.path || path;
                            render.fileList(data.files);
                            updateBreadcrumb();
                        } else if (Array.isArray(data)) {
                            state.currentPath = path;
                            render.fileList(data);
                            updateBreadcrumb();
                        } else {
                            console.error('无效的API响应格式', data);
                            dom.fileList.innerHTML = `<div class="alert alert-danger m-3">无法加载文件列表：无效的数据格式</div>`;
                        }
                    });
                } catch (error) {
                    FileBrowserUtils.handleError('加载文件列表失败', error);
                    dom.fileList.innerHTML = `<div class="alert alert-danger m-3">加载失败: ${error.message}</div>`;
                }
            }
        };

        // 内部辅助函数
        function getFileListTemplate(files, isRoot) {
            return `
                <table class="table table-hover table-sm">
                    <thead>
                        <tr>
                            <th width="50%">名称</th>
                            <th width="20%">大小</th>
                            <th width="30%">修改时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${!isRoot ? `
                        <tr class="file-item" data-path="${FileBrowserUtils.getParentPath(state.currentPath)}" data-type="dir">
                            <td><i class="fas fa-level-up-alt"></i> 上级目录</td>
                            <td></td>
                            <td></td>
                        </tr>` : ''}
                        ${files.map(file => `
                        <tr class="file-item" data-path="${file.path}" data-type="${file.is_dir ? 'dir' : 'file'}">
                            <td>
                                <i class="${file.is_dir ? 'fas fa-folder text-warning' : FileBrowserUtils.getFileIcon(file.name)}"></i>
                                ${file.name}
                            </td>
                            <td>${file.is_dir ? '-' : FileBrowserUtils.formatFileSize(file.size)}</td>
                            <td>${FileBrowserUtils.formatDateTime(file.modified)}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            `;
        }

        function getFileGridTemplate(files, isRoot) {
            return `
                <div class="file-grid">
                    ${!isRoot ? `
                    <div class="file-grid-item" data-path="${FileBrowserUtils.getParentPath(state.currentPath)}" data-type="dir">
                        <div class="file-icon"><i class="fas fa-level-up-alt"></i></div>
                        <div class="file-grid-name">上级目录</div>
                    </div>` : ''}
                    ${files.map(file => `
                    <div class="file-grid-item" data-path="${file.path}" data-type="${file.is_dir ? 'dir' : 'file'}">
                        <div class="file-icon">
                            <i class="${file.is_dir ? 'fas fa-folder text-warning' : FileBrowserUtils.getFileIcon(file.name)}"></i>
                        </div>
                        <div class="file-grid-name">${file.name}</div>
                    </div>`).join('')}
                </div>
            `;
        }

        // 视图渲染方法
        const render = {
            fileList(files) {
                files = files.filter(file => {
                    return !file.permissions || (file.permissions & 0o400) !== 0;
                });

                const isRoot = !state.currentPath;
                const template = state.viewMode === 'list'
                    ? getFileListTemplate(files, isRoot)
                    : getFileGridTemplate(files, isRoot);

                dom.fileList.innerHTML = template;
                bindFileItemEvents();
            }
        };

        // 事件处理
        function handleBreadcrumbClick(e) {
            if (e.target.tagName === 'A') {
                e.preventDefault();
                const path = e.target.dataset.path || e.target.getAttribute('data-path');
                core.loadFileList(path);
            }
        }

        function toggleViewMode() {
            state.viewMode = state.viewMode === 'list' ? 'grid' : 'list';
            core.loadFileList(state.currentPath);
            updateViewToggleIcon();
        }

        function updateViewToggleIcon() {
            if (!dom.viewToggleBtn) return;

            const icon = dom.viewToggleBtn.querySelector('i');
            if (icon) {
                icon.className = state.viewMode === 'list' ? 'fas fa-th' : 'fas fa-th-list';
            }
        }

        function updateBreadcrumb() {
            if (dom.fullPath) {
                let displayPath = state.currentPath;
                if (!displayPath) {
                    displayPath = '/';
                } else if (!displayPath.startsWith('/')) {
                    displayPath = '/' + displayPath;
                }
                dom.fullPath.textContent = displayPath;
            }

            if (dom.breadcrumb) {
                dom.breadcrumb.innerHTML = '';

                if (!state.currentPath) {
                    dom.breadcrumb.innerHTML = '<li class="breadcrumb-item active">根目录</li>';
                    return;
                }

                const parts = state.currentPath.split('/');
                let currentPath = '';

                const rootLi = document.createElement('li');
                rootLi.className = 'breadcrumb-item';
                const rootLink = document.createElement('a');
                rootLink.href = '#';
                rootLink.dataset.path = '';
                rootLink.textContent = '根目录';
                rootLi.appendChild(rootLink);
                dom.breadcrumb.appendChild(rootLi);

                parts.forEach((part, index) => {
                    if (!part) return;

                    currentPath += (currentPath ? '/' : '') + part;

                    const li = document.createElement('li');
                    li.className = 'breadcrumb-item';

                    if (index === parts.length - 1) {
                        li.classList.add('active');
                        li.textContent = part;
                    } else {
                        const link = document.createElement('a');
                        link.href = '#';
                        link.dataset.path = currentPath;
                        link.textContent = part;
                        li.appendChild(link);
                    }

                    dom.breadcrumb.appendChild(li);
                });
            }
        }

        function bindFileItemEvents() {
            dom.fileList.querySelectorAll('.file-item, .file-grid-item').forEach(item => {
                item.addEventListener('click', () => {
                    const path = item.dataset.path;
                    const type = item.dataset.type;

                    if (type === 'dir') {
                        core.loadFileList(path);
                    } else {
                        openFileViewer(path);
                    }
                });
            });
        }

        function openFileViewer(path) {
            window.location.href = `/explorer/view/${encodeURIComponent(path)}`;
        }

        // 初始化执行
        function init() {
            initEventListeners();
            core.loadFileList(state.currentPath);
        }

        init();
    }
})(); 