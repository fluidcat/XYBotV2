async function loadInitialLogs(limit = 100) {
    try {
        const response = await fetch('/logs/api/recent?limit=' + limit);
        const logs = await response.json();
        displayLogs(logs);
    } catch (error) {
        console.error('加载日志失败:', error);
    }
}

// 定时获取新日志
function startLogUpdates(interval = 2000) {
    return setInterval(async () => {
        try {
            const response = await fetch('/logs/api/new');
            const newLogs = await response.json();
            if (newLogs && newLogs.length > 0) {
                appendLogs(newLogs);
            }
        } catch (error) {
            console.error('获取新日志失败:', error);
        }
    }, interval);
}

// 显示日志
function displayLogs(logs) {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    logContainer.innerHTML = '';
    logs.forEach(log => {
        appendLogLine(log);
    });
    scrollToBottom();
}

// 添加新日志
function appendLogs(logs) {
    logs.forEach(log => {
        appendLogLine(log);
    });
    scrollToBottom();
}

// 添加单行日志
function appendLogLine(log) {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    const logLine = document.createElement('div');
    logLine.className = 'log-line';
    logLine.textContent = log;
    logContainer.appendChild(logLine);

    // 尝试根据日志内容添加级别样式
    applyLogLevelStyle(logLine, log);
}

// 应用日志级别样式
function applyLogLevelStyle(logElement, logText) {
    if (!logElement || !logText) return;

    logText = logText.toLowerCase();
    if (logText.includes('debug')) {
        logElement.classList.add('log-debug');
    } else if (logText.includes('info')) {
        logElement.classList.add('log-info');
    } else if (logText.includes('warning') || logText.includes('warn')) {
        logElement.classList.add('log-warning');
    } else if (logText.includes('error')) {
        logElement.classList.add('log-error');
    } else if (logText.includes('critical') || logText.includes('fatal')) {
        logElement.classList.add('log-critical');
    }
}

// 滚动到底部
function scrollToBottom() {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    const autoScroll = document.getElementById('auto-scroll');
    if (!autoScroll || autoScroll.checked) {
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

// 页面加载完成时初始化实时日志
function initRealtimeLog() {
    // 检查当前页面是否包含实时日志容器
    const realtimeLogContainer = document.getElementById('realtime-log-container');
    if (realtimeLogContainer) {
        loadInitialLogs();
        const updateInterval = startLogUpdates();

        // 页面关闭时清除定时器
        window.addEventListener('beforeunload', () => {
            clearInterval(updateInterval);
        });
    }
}

// 阻止日志滚动事件传播
function preventScrollPropagation() {
    const logContainers = document.querySelectorAll('.log-container, .log-viewer');
    logContainers.forEach(container => {
        if (container) {
            container.addEventListener('wheel', function (e) {
                // 如果容器已滚动到底部或顶部，则不阻止传播
                const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 1;
                const isAtTop = container.scrollTop <= 0;

                if (e.deltaY > 0 && !isAtBottom) {
                    // 向下滚动且不在底部
                    e.stopPropagation();
                } else if (e.deltaY < 0 && !isAtTop) {
                    // 向上滚动且不在顶部
                    e.stopPropagation();
                }
            });
        }
    });
}

// 页面加载完成时初始化
document.addEventListener('DOMContentLoaded', () => {
    initRealtimeLog();
    preventScrollPropagation();

    // 检查是否需要为非实时页面的日志查看器添加样式
    const logViewers = document.querySelectorAll('.log-viewer');
    logViewers.forEach(viewer => {
        const logLines = viewer.querySelectorAll('pre');
        logLines.forEach(line => {
            // 为已存在的pre标签添加样式
            if (line.parentNode === viewer) {
                const lineContent = line.textContent;
                const lines = lineContent.split('\n');

                if (lines.length > 1) {
                    line.remove();
                    lines.forEach(text => {
                        if (text.trim() !== '') {
                            const logLine = document.createElement('div');
                            logLine.className = 'log-line';
                            logLine.textContent = text;
                            viewer.appendChild(logLine);
                            applyLogLevelStyle(logLine, text);
                        }
                    });
                }
            }
        });
    });
}); 