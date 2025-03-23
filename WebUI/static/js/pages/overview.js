let autoRefreshTimer = null;
let previousStatus = null; // 保存上一次的状态数据
let socket;
let logViewer; // 全局日志查看器元素
let notificationContainer; // 全局通知容器元素

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    // 初始化变量 - 获取DOM元素
    const refreshBtn = document.getElementById('refreshBtn');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const restartBtn = document.getElementById('restartBtn');

    // 全局元素
    logViewer = document.getElementById('logViewer');
    notificationContainer = document.getElementById('notificationContainer');

    // 防止日志滚动传播到页面
    if (logViewer) {
        logViewer.addEventListener('wheel', function (e) {
            if (e.deltaY !== 0) {
                e.stopPropagation();
            }
        });
    }

    // 绑定事件
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshAllData);
    }

    if (startBtn) {
        startBtn.addEventListener('click', handleBotStart);
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', handleBotStop);
    }

    if (restartBtn) {
        restartBtn.addEventListener('click', handleBotRestart);
    }

    // 加载所有数据
    refreshAllData();

    // 初始化WebSocket连接
    initWebSocket();

    // 启动自动刷新
    startAutoRefresh();

    // 页面关闭时清理
    window.addEventListener('beforeunload', function () {
        stopAutoRefresh();
        if (socket && socket.connected) {
            socket.disconnect();
        }
    });
});

// 初始化WebSocket连接
function initWebSocket() {
    try {
        // 确保logViewer已存在
        if (!logViewer) {
            logViewer = document.getElementById('logViewer');
            if (!logViewer) {
                return;
            }
        }

        // 显示连接中状态
        logViewer.innerHTML = '<div class="text-center p-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">连接中...</span></div><p class="mt-2 text-muted">正在连接到日志服务器...</p></div>';

        // 连接WebSocket，指定明确的选项
        const serverUrl = window.location.protocol + '//' + window.location.host;
        socket = io(serverUrl, {
            transports: ['websocket', 'polling'],
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            timeout: 5000
        });

        // 连接建立事件
        socket.on('connect', function () {
            // 移除加载中状态
            logViewer.innerHTML = '<div class="text-muted p-3">正在请求日志...</div>';

            // 连接后请求初始日志
            socket.emit('request_logs', {n: 100});
        });

        // 断开连接事件
        socket.on('disconnect', function () {
            if (logViewer) {
                logViewer.innerHTML = '<div class="text-danger p-3">与服务器的连接已断开</div>';
            }
        });

        // 接收日志响应
        socket.on('logs_response', function (data) {
            if (data && data.logs) {
                displayLogs(data.logs);
            } else {
                if (logViewer) {
                    logViewer.innerHTML = '<div class="text-warning p-3">收到的日志数据无效</div>';
                }
            }
        });

        // 新日志事件
        socket.on('new_logs', function (data) {
            if (data && data.logs) {
                appendLogs(data.logs);
            }
        });

        // 连接错误事件
        socket.on('connect_error', function (error) {
            if (logViewer) {
                logViewer.innerHTML = '<div class="text-danger p-3">连接服务器失败</div>';
            }
            showNotification('日志连接失败，将在稍后重试...', 'warning');
        });

    } catch (error) {
        if (logViewer) {
            logViewer.innerHTML = '<div class="text-danger p-3">初始化日志连接失败</div>';
        }
    }
}

// 显示初始日志
function displayLogs(logs) {
    if (!logViewer) {
        return;
    }

    try {
        // 清空现有内容
        logViewer.innerHTML = '';

        // 检查日志数据
        if (!logs || !Array.isArray(logs) || logs.length === 0) {
            logViewer.innerHTML = '<div class="text-muted p-3">暂无日志数据</div>';
            return;
        }

        // 创建文档片段，提高性能
        const fragment = document.createDocumentFragment();

        // 处理每行日志
        logs.forEach((log, index) => {
            // 创建日志行
            const logLine = document.createElement('div');
            logLine.className = 'log-line';
            logLine.textContent = log;

            // 应用样式
            applyLogLevelStyle(logLine, log);

            // 添加到文档片段
            fragment.appendChild(logLine);
        });

        // 一次性添加所有日志行到DOM
        logViewer.appendChild(fragment);

        // 滚动到底部
        logViewer.scrollTop = logViewer.scrollHeight;
    } catch (error) {
        logViewer.innerHTML = '<div class="text-danger p-3">显示日志时出错</div>';
    }
}

// 追加新日志
function appendLogs(logs) {
    if (!logViewer) {
        return;
    }

    if (!logs || !Array.isArray(logs) || logs.length === 0) {
        return;
    }

    try {
        // 在更新前检查是否在底部
        const isScrolledToBottom = logViewer.scrollHeight - logViewer.clientHeight <= logViewer.scrollTop + 5;

        // 创建文档片段
        const fragment = document.createDocumentFragment();

        logs.forEach(log => {
            // 创建日志行
            const logLine = document.createElement('div');
            logLine.className = 'log-line';
            logLine.textContent = log;

            // 应用样式
            applyLogLevelStyle(logLine, log);

            // 添加到文档片段
            fragment.appendChild(logLine);
        });

        // 添加到日志查看器
        logViewer.appendChild(fragment);

        // 只有当之前在底部时才滚动到底部
        if (isScrolledToBottom) {
            logViewer.scrollTop = logViewer.scrollHeight;
        }
    } catch (error) {
        // 出错时静默处理，不中断用户体验
    }
}

// 应用日志级别样式
function applyLogLevelStyle(logElement, logText) {
    if (!logElement || !logText) return;

    if (logText.includes('DEBUG')) {
        logElement.classList.add('log-debug');
    } else if (logText.includes('INFO')) {
        logElement.classList.add('log-info');
    } else if (logText.includes('SUCCESS')) {
        logElement.classList.add('log-success');
    } else if (logText.includes('WARNING')) {
        logElement.classList.add('log-warning');
    } else if (logText.includes('ERROR')) {
        logElement.classList.add('log-error');
    } else if (logText.includes('CRITICAL')) {
        logElement.classList.add('log-critical');
    } else if (logText.includes('WEBUI')) {
        logElement.classList.add('log-webui');
    }
}

// 刷新状态
function refreshStatus() {
    fetch('/overview/api/status')
        .then(response => response.json())
        .then(status => {
            // 检查数据是否有变化，如果没有变化则不更新
            if (previousStatus && JSON.stringify(previousStatus) === JSON.stringify(status)) {
                return;
            }

            // 保存当前数据用于下次比较
            previousStatus = JSON.parse(JSON.stringify(status));

            // 更新状态信息
            updateStatusDisplay(status);
            updateControlButtons(status);

            // 更新指标数据
            updateMetricsDisplay(status);
        })
        .catch(error => {
            // 出错时静默处理
        });
}

// 更新状态显示
function updateStatusDisplay(status) {
    const statusIndicator = document.querySelector('tbody tr:first-child td span');
    const pidCell = document.querySelector('tbody tr:nth-child(2) td');
    const startTimeCell = document.querySelector('tbody tr:nth-child(3) td');

    if (status.running) {
        statusIndicator.className = 'badge bg-success';
        statusIndicator.textContent = '运行中';
    } else {
        statusIndicator.className = 'badge bg-danger';
        statusIndicator.textContent = '已停止';
    }

    pidCell.textContent = status.pid || '无';
    startTimeCell.textContent = status.start_time || '未启动';
}

// 更新指标显示
function updateMetricsDisplay(status) {
    // 更新卡片上的指标数据
    document.querySelectorAll('.status-card-value').forEach(function (element) {
        const metricType = element.dataset.metric;
        if (metricType && status[metricType] !== undefined) {
            element.textContent = status[metricType];
        }
    });

    // 更新头像和账号信息
    const profilePicture = document.getElementById('profilePicture');
    const nicknameElement = document.getElementById('botNickname');
    const wxidElement = document.getElementById('botWxid');
    const aliasElement = document.getElementById('botAlias');

    if (profilePicture) profilePicture.innerHTML = status.avatar ? `<i><img src="${status.avatar}" alt="QRCode"></i>` : '<i class="fas fa-user-circle"></i>';
    if (nicknameElement) nicknameElement.textContent = status.nickname || '未登陆';
    if (wxidElement) wxidElement.textContent = status.wxid || '未登陆';
    if (aliasElement) aliasElement.textContent = status.alias || '未登陆';
}

// 更新控制按钮
function updateControlButtons(status) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const restartBtn = document.getElementById('restartBtn');

    if (startBtn) {
        startBtn.style.display = status.running ? 'none' : 'inline-block';
    }

    if (stopBtn) {
        stopBtn.style.display = status.running ? 'inline-block' : 'none';
    }

    if (restartBtn) {
        restartBtn.style.display = status.running ? 'inline-block' : 'none';
    }
}

// 处理机器人启动
function handleBotStart() {
    const btn = this;
    btn.disabled = true;

    fetch('/bot/api/start', {method: 'POST'})
        .then(response => response.json())
        .then(result => {
            btn.disabled = false;
            if (result.success) {
                showNotification(result.message, 'success');
                refreshAllData();
            } else {
                showNotification(result.message, 'danger');
            }
        })
        .catch(error => {
            btn.disabled = false;
            showNotification('启动机器人失败', 'danger');
        });
}

// 处理机器人停止
function handleBotStop() {
    const btn = this;
    btn.disabled = true;

    fetch('/bot/api/stop', {method: 'POST'})
        .then(response => response.json())
        .then(result => {
            btn.disabled = false;
            if (result.success) {
                showNotification(result.message, 'warning');
                refreshAllData();
            } else {
                showNotification(result.message, 'danger');
            }
        })
        .catch(error => {
            btn.disabled = false;
            showNotification('停止机器人失败', 'danger');
        });
}

// 处理机器人重启
function handleBotRestart() {
    const btn = this;
    btn.disabled = true;

    fetch('/bot/api/restart', {method: 'POST'})
        .then(response => response.json())
        .then(result => {
            btn.disabled = false;
            if (result.success) {
                showNotification(result.message, 'success');
                refreshAllData();
            } else {
                showNotification(result.message, 'danger');
            }
        })
        .catch(error => {
            btn.disabled = false;
            showNotification('重启机器人失败', 'danger');
        });
}

// 刷新所有数据
function refreshAllData() {
    refreshStatus();
}

// 启动自动刷新
function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(refreshAllData, 10000);
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 使用通知管理器
    if (window.NotificationManager) {
        NotificationManager.show(message, type);
        return;
    }

    // 以下是备用实现，当通知管理器不可用时使用
    let container = document.getElementById('notificationContainer');

    // 确保容器唯一性
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        document.body.appendChild(container);
    }

    // 类型映射 - 确保使用正确的CSS类
    let cssType = 'info';
    switch (type) {
        case 'success':
            cssType = 'success';
            break;
        case 'error':
        case 'danger':
            cssType = 'error';
            break;
        case 'warning':
            cssType = 'warning';
            break;
        default:
            cssType = 'info';
    }

    // 创建纯净通知元素
    const notification = document.createElement('div');
    notification.className = `pure-notification ${cssType}-notification`;

    // 使用文本节点避免HTML解析
    const textNode = document.createTextNode(message);
    notification.appendChild(textNode);

    container.appendChild(notification);

    // 强制布局刷新
    notification.offsetHeight;

    // 显示动画 - 添加show类并设置内联样式
    notification.classList.add('show');
    notification.style.opacity = '1';
    notification.style.transform = 'translateY(0)';

    // 自动移除
    setTimeout(() => {
        notification.classList.remove('show');
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            if (notification.parentNode) {
                container.removeChild(notification);
            }
        }, 300);
    }, 3000);
}