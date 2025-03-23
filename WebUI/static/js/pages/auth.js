document.addEventListener('DOMContentLoaded', function () {
    // 添加登录页面专用类
    document.body.classList.add('login-page');

    // 处理表单验证
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }

    // 处理记住我复选框
    const rememberMe = document.querySelector('#remember_me');
    if (rememberMe) {
        // 从localStorage读取之前的选择
        const remembered = localStorage.getItem('remember_me') === 'true';
        rememberMe.checked = remembered;

        // 保存选择到localStorage
        rememberMe.addEventListener('change', function () {
            localStorage.setItem('remember_me', this.checked);
        });
    }

    // 处理用户名自动填充
    const usernameInput = document.querySelector('#username');
    if (usernameInput) {
        const savedUsername = localStorage.getItem('last_username');
        if (savedUsername) {
            usernameInput.value = savedUsername;
        }

        // 保存用户名到localStorage
        form.addEventListener('submit', function () {
            if (rememberMe && rememberMe.checked) {
                localStorage.setItem('last_username', usernameInput.value);
            } else {
                localStorage.removeItem('last_username');
            }
        });
    }

    // 处理闪现消息
    const messages = document.querySelectorAll('.flash-message');
    messages.forEach(message => {
        const type = message.dataset.type || 'info';
        const text = message.textContent;
        showNotification(text, type);
        message.remove();
    });
}); 