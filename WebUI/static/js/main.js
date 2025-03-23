document.addEventListener('DOMContentLoaded', function () {
    // 激活当前页面的侧边栏菜单
    const path = window.location.pathname;
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href !== '/' && path.includes(href)) {
            link.classList.add('active');
        } else if (href === '/' && path === '/') {
            link.classList.add('active');
        }
    });

    // 禁用侧边栏的鼠标滚轮事件
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.addEventListener('wheel', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });
    }

    // 添加退出登录确认
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            confirmAction('确定要退出登录吗？', function () {
                window.location.href = '/auth/logout';
            });
        });
    }

    // 初始化Bootstrap工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化Bootstrap下拉菜单
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl);
    });

    // 在这里添加其他全局JavaScript功能
});

// 显示通知
function showNotification(message, type = 'info') {
    // 使用通知管理器
    if (window.NotificationManager) {
        NotificationManager.show(message, type);
        return;
    }

    // 如果通知管理器不可用，使用备用实现
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

// 格式化日期时间
function formatDateTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 显示确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function () {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// 节流函数
function throttle(func, wait) {
    let lastExec = 0;
    return function () {
        const context = this;
        const args = arguments;
        const now = Date.now();
        if (now - lastExec >= wait) {
            func.apply(context, args);
            lastExec = now;
        }
    };
}

// 导出全局函数
window.showNotification = showNotification;
window.formatDateTime = formatDateTime;
window.confirmAction = confirmAction;
window.debounce = debounce;
window.throttle = throttle; 