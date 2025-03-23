from pathlib import Path

from flask import Blueprint, render_template, jsonify, request
from loguru import logger
from werkzeug.exceptions import BadRequest

from WebUI.services.file_service import file_service, ROOT_DIR
from WebUI.utils.auth_utils import login_required

file_bp = Blueprint('file', __name__, url_prefix='/file')


def normalize_path(rel_path: str) -> Path:
    """安全路径标准化方法（增加日志目录例外）"""
    try:
        # 允许直接访问日志目录
        if rel_path.strip().lower() == 'logs':
            log_path = ROOT_DIR / 'logs'
            if log_path.exists():
                return log_path

        # 空路径处理
        if not rel_path.strip():
            return ROOT_DIR

        # 路径分解和清理
        components = []
        for part in rel_path.split('/'):
            part = part.strip()
            if not part or part == '.':
                continue
            if part == '..':
                if components:
                    components.pop()
                continue
            components.append(part)

        safe_path = ROOT_DIR.joinpath(*components)
        resolved_path = safe_path.resolve()

        # 最终安全性检查
        if not resolved_path.is_relative_to(ROOT_DIR.resolve()):
            raise BadRequest("非法路径访问")

        return resolved_path
    except Exception as e:
        logger.log('WEBUI', f"路径标准化错误: {str(e)}")
        raise BadRequest("路径处理错误")


@file_bp.route('/api/list')
@login_required
def api_list_files():
    """获取目录文件列表API"""
    try:
        raw_path = request.args.get('path', '')

        # 对于logs、plugins等特殊目录，提供额外处理
        if raw_path.startswith('plugins/') or raw_path == 'plugins':
            # 确保plugins目录存在
            plugins_dir = ROOT_DIR / 'plugins'
            if not plugins_dir.exists():
                return jsonify({'error': '插件目录不存在'}), 404

            # 如果是具体的插件目录
            if raw_path != 'plugins':
                plugin_path = ROOT_DIR / raw_path
                if not plugin_path.exists():
                    return jsonify({'error': '指定的插件不存在'}), 404

                if not plugin_path.is_dir():
                    return jsonify({'error': '不是目录'}), 400

            target_path = ROOT_DIR / raw_path

        elif raw_path == 'logs' or raw_path.startswith('logs/'):
            # 日志目录特殊处理
            logs_dir = ROOT_DIR / 'logs'
            if not logs_dir.exists():
                return jsonify({'error': '日志目录不存在'}), 404

            target_path = ROOT_DIR / raw_path

        else:
            # 常规路径处理
            target_path = normalize_path(raw_path)

        if not target_path.exists():
            return jsonify({
                'path': raw_path,
                'files': [],
                'error': '路径不存在'
            }), 200  # 返回200但提供错误消息

        if not target_path.is_dir():
            return jsonify({
                'path': raw_path,
                'files': [],
                'error': '不是目录'
            }), 200

        files = file_service.list_directory(str(target_path.relative_to(ROOT_DIR)))

        return jsonify({
            'path': raw_path,
            'files': files
        })

    except Exception as e:
        logger.log('WEBUI', f"文件列表API错误: {str(e)}")
        return jsonify({
            'path': raw_path or '',
            'files': [],
            'error': str(e)
        }), 200  # 返回200但提供错误消息


def is_safe_path(path: str) -> bool:
    """检查路径是否安全，不包含危险组件"""
    return '../' not in path and not path.startswith('/')


@file_bp.route('/api/content')
@login_required
def api_file_content():
    """获取文件内容API"""
    try:
        # 获取请求参数
        rel_path = request.args.get('path', '')
        start_line = int(request.args.get('start', 0))
        max_lines = int(request.args.get('max', 1000))

        # 使用normalize_path而不是is_safe_path
        try:
            # 特殊处理日志文件
            if rel_path.startswith('logs/'):
                file_path = ROOT_DIR / rel_path
            else:
                # 使用normalize_path而不是is_safe_path
                file_path = normalize_path(rel_path)

            if not file_path.exists():
                return jsonify({
                    'content': [],
                    'info': {
                        'error': '文件不存在',
                        'size': 0,
                        'start_line': start_line,
                        'total_lines': 0
                    }
                })

            # 获取文件内容
            content, info = file_service.get_file_content(
                str(file_path.relative_to(ROOT_DIR)),
                start_line,
                max_lines
            )
            return jsonify({
                'content': content,
                'info': info
            })
        except Exception as e:
            logger.log('WEBUI', f"读取文件失败: {str(e)}")
            return jsonify({
                'content': [],
                'info': {
                    'error': f'读取文件失败: {str(e)}',
                    'path': rel_path,
                    'size': 0,
                    'start_line': start_line,
                    'total_lines': 0
                }
            })
    except Exception as e:
        logger.log('WEBUI', f"处理文件内容请求失败: {str(e)}")
        return jsonify({
            'content': [],
            'info': {
                'error': f'处理请求失败: {str(e)}'
            }
        })


@file_bp.route('/api/search')
@login_required
def api_search_in_file():
    """在文件中搜索内容API"""
    try:
        path = request.args.get('path', '')
        query = request.args.get('query', '')

        if not path or not query:
            return jsonify({'error': '路径和查询参数不能为空'}), 400

        results = file_service.search_in_file(path, query)
        return jsonify(results)
    except BadRequest as e:
        logger.log('WEBUI', f"搜索文件参数错误: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.log('WEBUI', f"搜索文件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@file_bp.route('/api/save', methods=['POST'])
@login_required
def api_save_file():
    """保存文件内容API"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        path = data.get('path', '')
        content = data.get('content', '')

        if not path:
            return jsonify({'error': '文件路径不能为空'}), 400

        # 检查路径安全性
        if not is_safe_path(path):
            logger.log('WEBUI', f"尝试访问不安全路径: {path}")
            return jsonify({'error': '路径不安全'}), 403

        result = file_service.save_file_content(path, content)

        if result:
            logger.log('WEBUI', f"文件保存成功: {path}")
            return jsonify({'success': True, 'message': '文件保存成功'})
        else:
            logger.log('WEBUI', f"文件保存失败: {path}")
            return jsonify({'success': False, 'error': '文件保存失败'}), 500
    except BadRequest as e:
        logger.log('WEBUI', f"保存文件请求错误: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.log('WEBUI', f"保存文件异常: {str(e)}")
        return jsonify({'error': str(e)}), 500


@file_bp.route('/view/<path:file_path>')
@login_required
def view_file(file_path):
    """通用文件查看页面"""
    logger.log('WEBUI', f"访问文件查看页面: {file_path}")
    context = {
        'page_title': '文件查看',
        'file_path': file_path
    }
    return render_template('file/view.html', **context)
