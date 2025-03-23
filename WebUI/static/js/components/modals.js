class BaseModal {
    constructor(options = {}) {
        this.options = {
            id: options.id || 'modal',
            title: options.title || '',
            size: options.size || 'md',
            backdrop: options.backdrop !== undefined ? options.backdrop : true,
            keyboard: options.keyboard !== undefined ? options.keyboard : true
        };
        this.modal = null;
    }

    createModal() {
        const modalHtml = `
            <div class="modal fade" id="${this.options.id}" tabindex="-1" aria-labelledby="${this.options.id}Label" aria-hidden="true">
                <div class="modal-dialog modal-${this.options.size}">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="${this.options.id}Label">${this.options.title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                        </div>
                        <div class="modal-body">
                            ${this.getModalBody()}
                        </div>
                        ${this.getModalFooter()}
                    </div>
                </div>
            </div>
        `;

        const modalElement = document.createElement('div');
        modalElement.innerHTML = modalHtml;
        document.body.appendChild(modalElement.firstElementChild);
        this.modal = new bootstrap.Modal(document.getElementById(this.options.id), {
            backdrop: this.options.backdrop,
            keyboard: this.options.keyboard
        });
    }

    getModalBody() {
        return '';
    }

    getModalFooter() {
        return '';
    }

    show() {
        if (!this.modal) {
            this.createModal();
        }
        this.modal.show();
    }

    hide() {
        if (this.modal) {
            this.modal.hide();
        }
    }

    dispose() {
        if (this.modal) {
            this.modal.dispose();
            document.getElementById(this.options.id).remove();
            this.modal = null;
        }
    }
}

class ConfirmModal extends BaseModal {
    constructor(options = {}) {
        super(options);
        this.options.message = options.message || '您确定要执行此操作吗？';
        this.options.confirmText = options.confirmText || '确认';
        this.options.cancelText = options.cancelText || '取消';
        this.options.onConfirm = options.onConfirm || (() => {
        });
        this.options.onCancel = options.onCancel || (() => {
        });
    }

    getModalBody() {
        return `<p>${this.options.message}</p>`;
    }

    getModalFooter() {
        return `
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${this.options.cancelText}</button>
                <button type="button" class="btn btn-primary" id="${this.options.id}-confirm">${this.options.confirmText}</button>
            </div>
        `;
    }

    createModal() {
        super.createModal();
        document.getElementById(`${this.options.id}-confirm`).addEventListener('click', () => {
            this.options.onConfirm();
            this.hide();
        });
    }
}

class FormModal extends BaseModal {
    constructor(options = {}) {
        super(options);
        this.options.saveText = options.saveText || '保存';
        this.options.cancelText = options.cancelText || '取消';
        this.options.onSave = options.onSave || (() => {
        });
        this.options.formContent = options.formContent || '';
    }

    getModalBody() {
        return `
            <form id="${this.options.id}-form" class="modal-form">
                ${this.options.formContent}
            </form>
        `;
    }

    getModalFooter() {
        return `
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${this.options.cancelText}</button>
                <button type="button" class="btn btn-primary" id="${this.options.id}-save">${this.options.saveText}</button>
            </div>
        `;
    }

    createModal() {
        super.createModal();
        document.getElementById(`${this.options.id}-save`).addEventListener('click', () => {
            const form = document.getElementById(`${this.options.id}-form`);
            if (form.checkValidity()) {
                this.options.onSave(new FormData(form));
                this.hide();
            } else {
                form.reportValidity();
            }
        });
    }
}

class AjaxModal extends BaseModal {
    constructor(options = {}) {
        super(options);
        this.options.url = options.url || '';
        this.options.method = options.method || 'GET';
        this.options.data = options.data || null;
    }

    async loadContent() {
        try {
            const response = await fetch(this.options.url, {
                method: this.options.method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: this.options.data ? JSON.stringify(this.options.data) : null
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const content = await response.text();
            document.querySelector(`#${this.options.id} .modal-body`).innerHTML = content;
        } catch (error) {
            document.querySelector(`#${this.options.id} .modal-body`).innerHTML = `
                <div class="alert alert-danger">
                    加载失败: ${error.message}
                </div>
            `;
        }
    }

    getModalBody() {
        return `
            <div class="modal-loading">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <p>正在加载内容，请稍候...</p>
            </div>
        `;
    }

    show() {
        super.show();
        this.loadContent();
    }
}

// 导出模态框类
window.BaseModal = BaseModal;
window.ConfirmModal = ConfirmModal;
window.FormModal = FormModal;
window.AjaxModal = AjaxModal; 