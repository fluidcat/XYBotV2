(function () {
    // 检查全局工具函数是否已存在，不存在则初始化
    if (!window.FileViewerUtils) {
        window.FileViewerUtils = {
            handleResponse: async (response, successHandler) => {
                if (!response.ok) {
                    const text = await response.text();
                    try {
                        const data = JSON.parse(text);
                        throw new Error(data.error || `HTTP错误: ${response.status}`);
                    } catch (e) {
                        throw new Error(`服务器错误(${response.status}): ${text.substring(0, 100)}`);
                    }
                }
                return successHandler(await response.json());
            },

            handleError: (context, error) => {
                console.error(`${context}:`, error);
                alert(`${context}: ${error.message}`);
            },

            formatFileSize: (bytes) => {
                if (bytes === 0) return '0 B';
                if (bytes === undefined || bytes === null || isNaN(bytes)) return '未知';
                try {
                    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
                    const i = Math.floor(Math.log(bytes) / Math.log(1024));
                    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + units[i];
                } catch (e) {
                    console.error('格式化文件大小出错:', e);
                    return '未知';
                }
            },

            formatDateTime: (timestamp) => {
                if (timestamp === undefined || timestamp === null || isNaN(timestamp)) return '未知';
                try {
                    const date = new Date(timestamp * 1000);
                    if (isNaN(date.getTime())) return '未知';
                    return date.toLocaleString();
                } catch (e) {
                    console.error('格式化时间出错:', e);
                    return '未知';
                }
            },

            getFileExtension: (filename) => {
                return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
            },

            guessLanguage: (filename) => {
                const ext = window.FileViewerUtils.getFileExtension(filename);

                const extensionMap = {
                    'js': 'javascript',
                    'ts': 'typescript',
                    'py': 'python',
                    'html': 'html',
                    'css': 'css',
                    'json': 'json',
                    'md': 'markdown',
                    'txt': 'plaintext',
                    'xml': 'xml',
                    'sh': 'shell',
                    'bash': 'shell',
                    'yml': 'yaml',
                    'yaml': 'yaml',
                    'toml': 'toml',
                    'java': 'java',
                    'c': 'c',
                    'cpp': 'cpp',
                    'cs': 'csharp',
                    'go': 'go',
                    'php': 'php',
                    'rb': 'ruby',
                    'rs': 'rust',
                    'sql': 'sql'
                };

                return extensionMap[ext] || 'plaintext';
            }
        };
    }

    // 全局暴露文件查看器初始化函数
    window.initFileViewer = function (containerId, filePath) {
        // 状态变量
        const state = {
            originalContent: '',
            editor: null
        };

        // DOM元素
        const dom = {
            monacoContainer: document.getElementById(`${containerId}-monaco-editor`),
            reloadBtn: document.getElementById(`${containerId}-reload`),
            saveBtn: document.getElementById(`${containerId}-save`),
            lineWrapCheck: document.getElementById(`${containerId}-line-wrap`),
            fileSizeEl: document.getElementById(`${containerId}-size`),
            fileModifiedEl: document.getElementById(`${containerId}-modified`),
            editorLanguageSelect: document.getElementById(`${containerId}-editor-language`),
            fontSizeSelect: document.getElementById(`${containerId}-font-size`)
        };

        // 初始化方法
        async function init() {
            loadFileData();
            initEventListeners();
        }

        // 核心功能方法
        async function loadFileData() {
            try {
                dom.monacoContainer.innerHTML = `
                    <div class="loading-container">
                        <i class="fas fa-file-alt"></i>
                        <p>正在加载文件内容...</p>
                    </div>
                `;

                const response = await fetch(`/file/api/content?path=${encodeURIComponent(filePath)}`);

                await FileViewerUtils.handleResponse(response, async data => {
                    updateFileInfo(data.info);

                    let fileContent = data.content;

                    if (data.info && data.info.total_lines && data.content.length < data.info.total_lines) {

                        dom.monacoContainer.innerHTML = `
                            <div class="loading-container">
                                <i class="fas fa-spinner fa-spin"></i>
                                <p>正在加载大文件，请稍候...</p>
                            </div>
                        `;

                        const totalLines = data.info.total_lines;
                        let completeContent = [...fileContent];

                        let currentLine = fileContent.length;

                        while (currentLine < totalLines) {

                            const nextResponse = await fetch(
                                `/file/api/content?path=${encodeURIComponent(filePath)}&start=${currentLine}`
                            );

                            const nextData = await nextResponse.json();
                            if (nextData.content && nextData.content.length > 0) {
                                completeContent = completeContent.concat(nextData.content);
                                currentLine += nextData.content.length;
                            } else {
                                break;
                            }
                        }

                        fileContent = completeContent;
                    }

                    initMonacoEditor(fileContent.join('\n'));
                });
            } catch (error) {
                FileViewerUtils.handleError('文件加载失败', error);
                dom.monacoContainer.innerHTML = `<div class="alert alert-danger m-3">加载失败: ${error.message}</div>`;
            }
        }

        async function saveFileContent() {
            try {
                const content = state.editor.getValue();

                dom.saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
                dom.saveBtn.disabled = true;

                const response = await fetch('/file/api/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        path: filePath,
                        content: content
                    })
                });

                await FileViewerUtils.handleResponse(response, data => {
                    if (data.success) {
                        alert('文件保存成功');
                        state.originalContent = content;
                    } else {
                        throw new Error(data.error || '保存失败');
                    }
                });
            } catch (error) {
                FileViewerUtils.handleError('保存文件失败', error);
            } finally {
                dom.saveBtn.innerHTML = '<i class="fas fa-save"></i> 保存';
                dom.saveBtn.disabled = false;
            }
        }

        // Monaco编辑器初始化
        function initMonacoEditor(content) {
            // 只有在全局没有配置过Monaco时才进行配置
            if (!window.monacoConfigured) {
                require.config({paths: {'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs'}});
                window.monacoConfigured = true;
            }

            // 如果Monaco已加载，直接创建编辑器
            if (window.monaco) {
                createEditor(content);
                return;
            }

            // 否则加载Monaco
            require(['vs/editor/editor.main'], function () {
                createEditor(content);
            });
        }

        // 创建编辑器
        function createEditor(content) {
            const language = FileViewerUtils.guessLanguage(filePath);

            if (dom.editorLanguageSelect) {
                if (dom.editorLanguageSelect.querySelector(`option[value="${language}"]`)) {
                    dom.editorLanguageSelect.value = language;
                }
            }

            const fontSize = dom.fontSizeSelect ? parseInt(dom.fontSizeSelect.value, 10) : 16;

            dom.monacoContainer.innerHTML = '';
            state.editor = monaco.editor.create(dom.monacoContainer, {
                value: content,
                language: language,
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: {enabled: true},
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                wordWrap: dom.lineWrapCheck && dom.lineWrapCheck.checked ? 'on' : 'off',
                fontSize: fontSize,
                tabSize: 4,
                insertSpaces: true,
                fontFamily: "'JetBrains Mono', 'Source Code Pro', 'Menlo', 'Ubuntu Mono', 'Fira Code', monospace",
                fontLigatures: true,
                letterSpacing: 0.5
            });

            state.originalContent = content;
        }

        // 事件处理
        function initEventListeners() {
            if (dom.reloadBtn) {
                dom.reloadBtn.addEventListener('click', function () {
                    if (state.editor && state.editor.getValue() !== state.originalContent) {
                        if (confirm('您有未保存的更改，确定要刷新吗？')) {
                            loadFileData();
                        }
                    } else {
                        loadFileData();
                    }
                });
            }

            if (dom.saveBtn) {
                dom.saveBtn.addEventListener('click', function () {
                    saveFileContent();
                });
            }

            if (dom.editorLanguageSelect) {
                dom.editorLanguageSelect.addEventListener('change', function () {
                    if (state.editor) {
                        monaco.editor.setModelLanguage(
                            state.editor.getModel(),
                            this.value
                        );
                    }
                });
            }

            if (dom.fontSizeSelect) {
                dom.fontSizeSelect.addEventListener('change', function () {
                    if (state.editor) {
                        const fontSize = parseInt(this.value, 10);
                        state.editor.updateOptions({fontSize: fontSize});
                    }
                });
            }

            if (dom.lineWrapCheck) {
                dom.lineWrapCheck.addEventListener('change', function () {
                    if (state.editor) {
                        state.editor.updateOptions({wordWrap: this.checked ? 'on' : 'off'});
                    }
                });
            }
        }

        // 更新文件信息
        function updateFileInfo(info) {
            if (!info || typeof info !== 'object') {
                console.warn('缺少文件信息数据');
                info = {size: null, modified: null};
            }

            if (dom.fileSizeEl) {
                dom.fileSizeEl.textContent = FileViewerUtils.formatFileSize(info.size);
            }

            if (dom.fileModifiedEl) {
                dom.fileModifiedEl.textContent = FileViewerUtils.formatDateTime(info.modified);
            }

            const filePathElements = document.querySelectorAll('.file-path');
            filePathElements.forEach(el => {
                if (el.textContent.trim() === '') {
                    el.textContent = filePath || '未知';
                }
            });
        }

        // 初始化执行
        init();
    }
})(); 