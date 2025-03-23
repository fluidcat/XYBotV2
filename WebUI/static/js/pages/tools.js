$(document).ready(function () {
    // 加载工具列表
    loadTools();
});

// 加载工具列表
function loadTools() {
    $.ajax({
        url: '/tools/api/list',
        type: 'GET',
        dataType: 'json',
        success: function (response) {
            if (response.code === 0) {
                renderTools(response.data);
            } else {
                showNotification('加载工具列表失败: ' + response.msg, 'danger');
                $('#toolsContainer').html('<div class="col-12"><div class="alert alert-danger">加载工具列表失败</div></div>');
            }
        },
        error: function (xhr, status, error) {
            showNotification('加载工具列表失败: ' + error, 'danger');
            $('#toolsContainer').html('<div class="col-12"><div class="alert alert-danger">加载工具列表失败</div></div>');
        }
    });
}

// 渲染工具列表
function renderTools(tools) {
    const toolsContainer = $('#toolsContainer');

    if (!tools || tools.length === 0) {
        toolsContainer.html('<div class="col-12"><div class="alert alert-warning">暂无可用工具</div></div>');
        return;
    }

    let html = '';

    tools.forEach(function (tool) {
        html += `
            <div class="col-md-4 mb-4">
                <div class="tool-card">
                    <div class="tool-header">
                        <div class="tool-icon">
                            <i class="fas fa-${tool.icon}"></i>
                        </div>
                        <h5 class="tool-title">${tool.title}</h5>
                    </div>
                    <div class="tool-body">
                        <p class="tool-description">${tool.description}</p>
                        <div class="execution-status" id="status-${tool.id}">
                            <span class="status-text"></span>
                        </div>
                    </div>
                    <div class="tool-footer">
                        <button type="button" class="btn btn-primary execute-tool" data-tool-id="${tool.id}">
                            <i class="fas fa-play mr-1"></i>执行
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    toolsContainer.html(html);

    // 绑定执行按钮事件
    $('.execute-tool').click(function () {
        const toolId = $(this).data('tool-id');
        const toolTitle = $(this).closest('.tool-card').find('.tool-title').text();

        // 显示确认对话框
        showConfirmModal('确认执行', `确定要执行"${toolTitle}"吗？`, function () {
            executeTool(toolId);
        });
    });
}

// 执行工具
function executeTool(toolId) {
    // 显示加载状态
    const statusElement = $(`#status-${toolId}`);
    statusElement.removeClass('success error').addClass('loading');
    statusElement.find('.status-text').text('正在执行中...');
    statusElement.show();

    $.ajax({
        url: `/tools/api/execute/${toolId}`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({}),
        dataType: 'json',
        success: function (response) {
            if (response.code === 0) {
                // 更新状态为成功
                statusElement.removeClass('loading error').addClass('success');
                statusElement.find('.status-text').text(response.data.message || '执行成功');

                // 显示执行详情
                showExecutionDetail(true, response.data);
            } else {
                // 更新状态为失败
                statusElement.removeClass('loading success').addClass('error');
                statusElement.find('.status-text').text(response.msg);

                // 显示执行详情
                showExecutionDetail(false, response.data);
            }
        },
        error: function (xhr, status, error) {
            // 更新状态为失败
            statusElement.removeClass('loading success').addClass('error');
            statusElement.find('.status-text').text('执行失败: ' + error);

            // 显示执行详情
            showExecutionDetail(false, {error: error});
        }
    });
}

// 显示执行详情
function showExecutionDetail(success, data) {
    const detailStatus = $('#detailExecutionStatus');
    const detailStatusText = $('#detailStatusText');
    const executionLog = $('#executionLog');

    if (success) {
        detailStatus.removeClass('error loading').addClass('success');
        detailStatusText.text(data.message || '执行成功');
    } else {
        detailStatus.removeClass('success loading').addClass('error');
        detailStatusText.text(data.error || '执行失败');
    }

    // 显示执行日志
    let logText = '';

    if (data.stack) {
        logText += data.stack;
    } else if (typeof data === 'object') {
        logText = JSON.stringify(data, null, 2);
    } else {
        logText = String(data);
    }

    executionLog.text(logText);

    // 显示模态框
    $('#executeDetailModal').modal('show');
}

// 显示确认对话框
function showConfirmModal(title, message, callback) {
    $('#confirmModalLabel').text(title);
    $('#confirmModalBody').text(message);

    $('#confirmModalConfirm').off('click').on('click', function () {
        $('#confirmModal').modal('hide');
        callback();
    });

    $('#confirmModal').modal('show');
} 