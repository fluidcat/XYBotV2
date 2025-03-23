const NotificationManager = {
    /**
     * 显示通知
     * @param {string} message - 通知消息
     * @param {string} type - 通知类型: 'info', 'success', 'warning', 'error'
     * @param {number} duration - 通知显示持续时间(毫秒)
     */
    show: function (message, type = 'info', duration = 3000) {
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
        }, duration);
    }
};

// 导出到全局作用域
window.NotificationManager = NotificationManager; 