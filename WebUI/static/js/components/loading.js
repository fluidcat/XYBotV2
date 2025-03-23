class LoadingSpinner {
    constructor(options = {}) {
        this.options = {
            size: options.size || 'md',
            color: options.color || 'primary',
            text: options.text || '加载中...'
        };
    }

    render() {
        const sizes = {
            "sm": "spinner-border-sm",
            "md": "",
            "lg": "spinner-border spinner-border-lg"
        };

        return `
            <div class="d-flex justify-content-center align-items-center loading-container">
                <div class="spinner-border text-${this.options.color} ${sizes[this.options.size]}" role="status">
                    <span class="visually-hidden">${this.options.text}</span>
                </div>
                ${this.options.text ? `<span class="ms-2">${this.options.text}</span>` : ''}
            </div>
        `;
    }
}

class ProgressBar {
    constructor(options = {}) {
        this.options = {
            value: options.value || 0,
            color: options.color || 'primary',
            striped: options.striped !== undefined ? options.striped : true,
            animated: options.animated !== undefined ? options.animated : true,
            label: options.label !== undefined ? options.label : true
        };
    }

    render() {
        return `
            <div class="progress" style="height: 20px;">
                <div class="progress-bar bg-${this.options.color} 
                    ${this.options.striped ? 'progress-bar-striped' : ''} 
                    ${this.options.animated ? 'progress-bar-animated' : ''}"
                    role="progressbar" 
                    style="width: ${this.options.value}%"
                    aria-valuenow="${this.options.value}" 
                    aria-valuemin="0" 
                    aria-valuemax="100">
                    ${this.options.label ? `${this.options.value}%` : ''}
                </div>
            </div>
        `;
    }

    update(value) {
        this.options.value = value;
        return this.render();
    }
}

class FullPageLoader {
    constructor(options = {}) {
        this.options = {
            message: options.message || '页面加载中...',
            id: options.id || 'fullPageLoader'
        };
        this.element = null;
    }

    show() {
        if (!this.element) {
            this.element = document.createElement('div');
            this.element.id = this.options.id;
            this.element.className = 'full-page-loader';
            this.element.innerHTML = `
                <div class="loader-content">
                    <div class="spinner-grow text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    ${this.options.message ? `<p class="mt-3">${this.options.message}</p>` : ''}
                </div>
            `;
            document.body.appendChild(this.element);
        }
        this.element.style.display = 'flex';
    }

    hide() {
        if (this.element) {
            this.element.style.display = 'none';
        }
    }

    setMessage(message) {
        this.options.message = message;
        if (this.element) {
            const messageElement = this.element.querySelector('p');
            if (messageElement) {
                messageElement.textContent = message;
            }
        }
    }
}

class ContentLoader {
    constructor(options = {}) {
        this.options = {
            size: options.size || 'md',
            containerClass: options.containerClass || ''
        };
    }

    render() {
        let skeletonLines = '';
        switch (this.options.size) {
            case 'sm':
                skeletonLines = `
                    <div class="skeleton-line" style="width: 30%; height: 15px;"></div>
                    <div class="skeleton-line" style="width: 80%; height: 15px;"></div>
                `;
                break;
            case 'lg':
                skeletonLines = `
                    <div class="skeleton-line" style="width: 40%; height: 25px;"></div>
                    <div class="skeleton-line" style="width: 90%; height: 15px;"></div>
                    <div class="skeleton-line" style="width: 60%; height: 15px;"></div>
                    <div class="skeleton-line" style="width: 75%; height: 15px;"></div>
                `;
                break;
            default:
                skeletonLines = `
                    <div class="skeleton-line" style="width: 40%; height: 20px;"></div>
                    <div class="skeleton-line" style="width: 90%; height: 15px;"></div>
                    <div class="skeleton-line" style="width: 60%; height: 15px;"></div>
                `;
        }

        return `
            <div class="content-loader ${this.options.containerClass}">
                <div class="loader-skeleton">
                    ${skeletonLines}
                </div>
            </div>
        `;
    }
}

// 导出组件类
window.LoadingSpinner = LoadingSpinner;
window.ProgressBar = ProgressBar;
window.FullPageLoader = FullPageLoader;
window.ContentLoader = ContentLoader; 