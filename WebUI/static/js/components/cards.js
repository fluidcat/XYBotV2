class StatusCard {
    constructor(element) {
        this.element = element;
        this.title = element.querySelector('.card-title');
        this.icon = element.querySelector('.status-icon i');
        this.value = element.querySelector('.card-value');
    }

    update(value) {
        if (this.value) {
            this.value.textContent = value;
        }
    }

    setIcon(iconClass) {
        if (this.icon) {
            this.icon.className = iconClass;
        }
    }
}

class ControlCard {
    constructor(element, options = {}) {
        this.element = element;
        this.startBtn = element.querySelector('[data-action="start"]');
        this.stopBtn = element.querySelector('[data-action="stop"]');
        this.statusIndicator = element.querySelector('.status-indicator');
        this.options = options;

        this.init();
    }

    init() {
        if (this.startBtn) {
            this.startBtn.addEventListener('click', () => this.start());
        }
        if (this.stopBtn) {
            this.stopBtn.addEventListener('click', () => this.stop());
        }
    }

    start() {
        if (this.options.onStart) {
            this.options.onStart();
        }
    }

    stop() {
        if (this.options.onStop) {
            this.options.onStop();
        }
    }

    setStatus(isRunning) {
        if (this.startBtn) {
            this.startBtn.style.display = isRunning ? 'none' : 'inline-block';
        }
        if (this.stopBtn) {
            this.stopBtn.style.display = isRunning ? 'inline-block' : 'none';
        }
        if (this.statusIndicator) {
            this.statusIndicator.className = `status-indicator ${isRunning ? 'status-online' : 'status-offline'}`;
        }
    }
}

class LogCard {
    constructor(element, options = {}) {
        this.element = element;
        this.logViewer = element.querySelector('.log-viewer');
        this.refreshBtn = element.querySelector('[data-action="refresh"]');
        this.clearBtn = element.querySelector('[data-action="clear"]');
        this.options = options;

        this.init();
    }

    init() {
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.refresh());
        }
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clear());
        }
    }

    refresh() {
        if (this.options.onRefresh) {
            this.options.onRefresh();
        }
    }

    clear() {
        if (this.logViewer) {
            this.logViewer.innerHTML = '';
        }
        if (this.options.onClear) {
            this.options.onClear();
        }
    }

    appendLog(logText, level = 'info') {
        if (!this.logViewer) return;

        const logLine = document.createElement('div');
        logLine.className = `log-line log-${level}`;
        logLine.textContent = logText;
        this.logViewer.appendChild(logLine);
        this.scrollToBottom();
    }

    scrollToBottom() {
        if (this.logViewer) {
            this.logViewer.scrollTop = this.logViewer.scrollHeight;
        }
    }
}

// 导出组件类
window.StatusCard = StatusCard;
window.ControlCard = ControlCard;
window.LogCard = LogCard; 