let currentPluginId = null;
let jsonEditor = null;
let botActive = false;
let allPlugins = []; // 存储所有插件数据用于搜索

// 页面加载完成后执行
$(document).ready(function () {
    // 初始化检查
    initializePluginManager();

    // 绑定事件
    bindEvents();
});

// 初始化插件管理器
function initializePluginManager() {
    checkBotStatus()
        .done((res) => {
            botActive = res?.running || false;
            if (!botActive) {
                $('.plugin-action-btn, .reload-btn')
                    .tooltip('dispose')
                    .attr('title', '请先启动机器人')
                    .tooltip({trigger: 'hover'});
            }
        })
        .fail(() => {
            botActive = false;
            showNotification('机器人状态检查失败，部分功能受限', 'warning');
        })
        .always(loadPlugins);
}

// 绑定事件
function bindEvents() {
    // 刷新按钮点击事件
    $('#refreshPlugins').click(loadPlugins);

    // 插件列表容器事件委托
    $('#pluginListContainer')
        .on('click', '.plugin-action-btn', handlePluginActionClick)
        .on('click', '.reload-btn:not(:disabled)', handlePluginReloadClick)
        .on('click', '.config-btn', handleConfigButtonClick);

    // 模态框按钮事件
    $('#enableDisablePlugin').click(handleEnableDisableClick);
    $('#reloadPlugin').click(handleReloadClick);
    $('#savePluginConfig').click(handleSaveConfigClick);

    // 搜索框输入事件
    $('#pluginSearch').on('input', handlePluginSearch);
}

// 检查机器人状态
function checkBotStatus() {
    return $.ajax({
        url: '/bot/api/status',
        type: 'GET'
    });
}

// 加载插件列表
function loadPlugins() {
    $('#pluginListContainer').html('<div class="text-center p-4"><i class="fas fa-spinner fa-spin me-2"></i>正在加载插件列表...</div>');

    return $.ajax({
        url: '/plugin/api/list',
        type: 'GET',
        success: function (response) {
            if (response.code === 0) {
                allPlugins = response.data || [];
                renderPluginList(allPlugins);
            } else {
                showLoadError(response.msg);
            }
        },
        error: function (xhr, status, error) {
            showLoadError(error);
        }
    });
}

// 显示加载错误
function showLoadError(error) {
    $('#pluginListContainer').html(`
        <div class="alert alert-danger m-4">
            <i class="fas fa-exclamation-triangle me-2"></i>
            加载失败: ${error}
            <button class="btn btn-outline-danger btn-sm float-end" onclick="loadPlugins()">
                <i class="fas fa-redo"></i> 重试
            </button>
        </div>
    `);
}

// 渲染插件列表
function renderPluginList(plugins) {
    const container = $('#pluginListContainer');
    container.empty();

    if (!plugins || plugins.length === 0) {
        container.html('<div class="text-center p-4 text-gray-500">没有可用的插件</div>');
        return;
    }

    plugins.forEach(plugin => {
        plugin.id = plugin.id || plugin.name;
        const isEnabled = plugin.enabled;

        const card = $(`
            <div class="card plugin-card shadow-sm">
                <div class="card-body d-flex justify-content-between align-items-center p-4">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center gap-3 mb-2">
                            <h5 class="plugin-title mb-0">${plugin.name}</h5>
                            <span class="badge bg-blue-100 text-blue-800 text-sm px-2 py-1 rounded-full">v${plugin.version || '未知'}</span>
                        </div>
                        
                        <div class="plugin-meta">
                            <i class="fas fa-folder-open mr-1"></i>${plugin.directory || '未知'}
                            <span class="mx-2 text-gray-300">|</span>
                            <i class="fas fa-user mr-1"></i>${plugin.author || '未知'} 
                            <span class="mx-2 text-gray-300">|</span>
                            <i class="fas fa-circle text-xs ${isEnabled ? 'text-emerald-500' : 'text-gray-400'}"></i>
                            ${isEnabled ? '已加载' : '已卸载'}
                        </div>
                        
                        <p class="plugin-description mb-0">${plugin.description || '无描述信息'}</p>
                    </div>

                    <div class="d-flex align-items-center gap-3 me-3">
                        <button class="btn btn-sm ${isEnabled ? 'btn-danger' : 'btn-success'} plugin-action-btn"
                                data-id="${plugin.id}"
                                data-action="${isEnabled ? 'unload' : 'load'}"
                                ${!botActive ? 'disabled title="机器人未启动"' : ''}>
                            <i class="fas ${isEnabled ? 'fa-power-off' : 'fa-plug'} me-1"></i>
                            ${isEnabled ? '卸载' : '加载'}
                        </button>

                        <button class="btn btn-sm btn-outline-warning reload-btn"
                                data-id="${plugin.id}"
                                ${!botActive || !isEnabled ? 'disabled' : ''}
                                title="${!botActive ? '机器人未启动' : '重新加载插件'}">
                            <i class="fas fa-redo"></i>
                        </button>

                        <button class="btn btn-sm btn-outline-primary config-btn"
                                data-id="${plugin.id}"
                                data-directory="${plugin.directory}" 
                                title="打开文件目录">
                            <i class="fas fa-folder-open"></i>
                        </button>
                    </div>
                </div>
            </div>
        `);

        container.append(card);
    });
}

// 处理插件操作按钮点击
function handlePluginActionClick() {
    const pluginId = $(this).data('id');
    const action = $(this).data('action');
    handlePluginAction(pluginId, action);
}

// 处理插件重载按钮点击
function handlePluginReloadClick() {
    const pluginId = $(this).data('id');
    reloadPlugin(pluginId);
}

// 处理配置按钮点击
function handleConfigButtonClick() {
    const directory = $(this).data('directory');
    window.location.href = `/explorer/?path=${encodeURIComponent(directory)}`;
}

// 处理启用/禁用按钮点击
function handleEnableDisableClick() {
    if (!currentPluginId) return;

    const action = $(this).text();
    try {
        if (action === '加载') {
            enablePlugin(currentPluginId);
        } else {
            disablePlugin(currentPluginId);
        }
        $('#pluginDetailModal').modal('hide');
    } catch (e) {
        showNotification('处理失败: ' + e.message, 'error');
    }
}

// 处理重载按钮点击
function handleReloadClick() {
    if (!currentPluginId) return;
    reloadPlugin(currentPluginId);
}

// 处理保存配置按钮点击
function handleSaveConfigClick() {
    if (!currentPluginId || !jsonEditor) return;

    try {
        const config = jsonEditor.get();
        savePluginConfig(currentPluginId, config);
    } catch (e) {
        showNotification('配置格式错误: ' + e.message, 'error');
    }
}

// 处理插件搜索
function handlePluginSearch() {
    const keyword = $(this).val().toLowerCase();
    const filtered = allPlugins.filter(plugin => {
        return (
            plugin.name.toLowerCase().includes(keyword) ||
            (plugin.author && plugin.author.toLowerCase().includes(keyword)) ||
            (plugin.description && plugin.description.toLowerCase().includes(keyword))
        );
    });
    renderPluginList(filtered);
}

// 处理插件操作
function handlePluginAction(pluginId, action) {
    const btn = $(`.plugin-action-btn[data-id="${pluginId}"]`);
    const apiUrl = `/plugin/api/${action === 'load' ? 'enable' : 'disable'}/${pluginId}`;

    btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>处理中...');

    $.ajax({
        url: apiUrl,
        type: 'POST',
        success: (res) => {
            if (res.code === 0) {
                showNotification(`插件${action === 'load' ? '加载' : '卸载'}成功`, 'success');
                loadPlugins();
            } else {
                showNotification(res.msg, 'error');
            }
        },
        error: (xhr) => {
            showNotification(`操作失败: ${xhr.statusText}`, 'error');
        },
        complete: () => btn.prop('disabled', false)
    });
}

// 启用插件
function enablePlugin(pluginId) {
    return $.ajax({
        url: `/plugin/api/enable/${pluginId}`,
        type: 'POST'
    });
}

// 禁用插件
function disablePlugin(pluginId) {
    return $.ajax({
        url: `/plugin/api/disable/${pluginId}`,
        type: 'POST'
    });
}

// 重新加载插件
function reloadPlugin(pluginId) {
    return $.ajax({
        url: `/plugin/api/reload/${pluginId}`,
        type: 'POST'
    });
}

// 保存插件配置
function savePluginConfig(pluginId, config) {
    return $.ajax({
        url: `/plugin/api/config/${pluginId}`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(config)
    });
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