import os
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple

from loguru import logger

from WebUI.utils.singleton import Singleton

# 项目根目录路径
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# 日志目录
LOGS_DIR = ROOT_DIR / 'logs'


class SecurityError(Exception):
    """安全性验证错误，当路径访问超出允许范围时抛出"""
    pass


class PathValidationError(Exception):
    """路径验证错误，当路径处理过程中出现问题时抛出"""
    pass


class FileService(metaclass=Singleton):
    """文件服务类，提供文件系统操作功能
    
    负责处理文件系统相关操作，包括读取目录内容、获取文件内容、
    在文件中搜索和保存文件。所有路径操作都经过安全性验证，
    以防止目录遍历攻击。
    """

    def __init__(self):
        """初始化文件服务
        
        确保必要的目录结构存在，如日志目录。
        """
        # 确保日志目录存在
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logger.log('WEBUI', f"文件服务初始化完成，根目录: {ROOT_DIR}")

    def _validate_path(self, rel_path: str) -> Path:
        """验证并返回安全的文件路径
        
        对输入的相对路径进行安全验证，确保访问不超出根目录范围，
        防止目录遍历攻击和恶意访问。
        
        Args:
            rel_path: 相对于根目录的文件路径
            
        Returns:
            Path: 验证后的安全绝对路径
            
        Raises:
            SecurityError: 当路径尝试访问根目录之外的位置时
            PathValidationError: 当路径处理过程中出现其他错误时
        """
        try:
            # 规范化路径处理
            clean_path = rel_path.strip('/')  # 去除首尾斜杠
            if not clean_path:  # 处理根目录情况
                return ROOT_DIR

            # 分解路径组件并过滤危险字符
            path_components = [p for p in clean_path.split('/') if p not in ('', '.', '..')]

            # 重建安全路径
            safe_path = ROOT_DIR.joinpath(*path_components)
            resolved_path = safe_path.resolve()

            # 二次验证路径安全性
            if not resolved_path.is_relative_to(ROOT_DIR):
                logger.log('WEBUI', f"安全警告：路径越界访问尝试: {rel_path} -> {resolved_path}")
                raise SecurityError("路径越界访问尝试")

            return resolved_path
        except SecurityError:
            # 直接重新抛出安全错误
            raise
        except Exception as e:
            logger.log('WEBUI', f"路径验证失败: {rel_path}, 错误: {str(e)}")
            raise PathValidationError(f"路径验证失败: {str(e)}")

    def list_directory(self, rel_path: str = '') -> List[Dict[str, Any]]:
        """列出指定目录中的内容
        
        获取指定目录中的文件和子目录列表，并返回其元数据信息。
        结果按照目录优先、名称字母顺序排序。
        
        Args:
            rel_path: 相对于根目录的目录路径，默认为根目录
            
        Returns:
            List[Dict[str, Any]]: 目录内容列表，每项包含名称、路径、类型等信息
        """
        try:
            target_dir = self._validate_path(rel_path)

            if not target_dir.exists():
                logger.log('WEBUI', f"目录不存在: {target_dir}")
                raise FileNotFoundError(f"目录不存在: {target_dir}")
            if not target_dir.is_dir():
                logger.log('WEBUI', f"路径不是目录: {target_dir}")
                raise NotADirectoryError(f"路径不是目录: {target_dir}")

            items = []
            for path in target_dir.iterdir():
                try:
                    # 过滤隐藏文件（以.开头）
                    if path.name.startswith('.'):
                        continue

                    stat = path.stat()
                    items.append({
                        'name': path.name,
                        'path': str(path.relative_to(ROOT_DIR)),
                        'is_dir': path.is_dir(),
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'created': stat.st_ctime,
                        'permissions': stat.st_mode
                    })
                except Exception as e:
                    logger.log('WEBUI', f"处理目录项时出错: {path.name}, 错误: {str(e)}")
                    continue  # 跳过处理失败的项

            # 排序：目录在前，按名称排序
            sorted_items = sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
            return sorted_items

        except (SecurityError, PathValidationError, FileNotFoundError, NotADirectoryError) as e:
            # 这些是预期的异常，记录后返回空列表
            logger.log('WEBUI', f"目录列表错误: {str(e)}")
            return []
        except Exception as e:
            # 未预期的异常，记录详细信息
            logger.log('WEBUI', f"目录列表未知错误: {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return []

    def get_file_content(self, rel_path: str = '',
                         start_line: int = 0, max_lines: int = 1000) -> Tuple[List[str], Dict[str, Any]]:
        """获取文件内容
        
        读取指定文件的内容，支持指定起始行和最大行数，适用于分页读取大文件。
        
        Args:
            rel_path: 相对于根目录的文件路径
            start_line: 起始行号（从0开始）
            max_lines: 最大行数
            
        Returns:
            Tuple[List[str], Dict[str, Any]]: (文件内容行列表, 文件信息字典)
        """
        try:
            file_path = self._validate_path(rel_path)

            if not file_path.exists() or not file_path.is_file():
                logger.log('WEBUI', f"文件不存在或不是常规文件: {rel_path}")
                return [], {'error': '文件不存在'}

            file_info = {
                'name': file_path.name,
                'path': str(file_path.relative_to(ROOT_DIR)),
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime,
                'created': file_path.stat().st_ctime,
                'total_lines': 0,
                'start_line': start_line,
                'end_line': 0
            }

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # 如果起始行为0，直接读取指定行数
                if start_line == 0:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n'))

                    file_info['total_lines'] = i + 1 if i < max_lines else i + 1 + 1  # +1表示还有更多行
                    file_info['end_line'] = min(start_line + len(lines) - 1, file_info['total_lines'] - 1)

                    logger.log('WEBUI', f"读取文件 {rel_path} 内容, 从第 {start_line} 行起，共 {len(lines)} 行")
                    return lines, file_info

                # 否则，先跳过前面的行
                for i, _ in enumerate(f):
                    if i >= start_line - 1:
                        break

                if i < start_line - 1:
                    # 起始行超出文件行数
                    file_info['total_lines'] = i + 1
                    file_info['end_line'] = i
                    logger.log('WEBUI', f"请求的起始行 {start_line} 超出文件 {rel_path} 的行数 {i + 1}")
                    return [], file_info

                # 然后读取指定行数
                lines = []
                for j in range(max_lines):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip('\n'))

                # 继续读取剩余行数，计算总行数
                remaining_count = 0
                while f.readline():
                    remaining_count += 1
                    if remaining_count > 1000:  # 设置一个合理的限制，避免处理过大的文件
                        break

                file_info['total_lines'] = start_line + len(lines) + remaining_count
                file_info['end_line'] = min(start_line + len(lines) - 1, file_info['total_lines'] - 1)

                logger.log('WEBUI',
                           f"读取文件 {rel_path} 内容, 从第 {start_line} 行起，共 {len(lines)} 行，总行数约 {file_info['total_lines']}")
                return lines, file_info

        except (SecurityError, PathValidationError) as e:
            # 安全相关错误
            logger.log('WEBUI', f"读取文件内容安全错误: {str(e)}")
            return [], {'error': f'安全错误: {str(e)}'}
        except UnicodeDecodeError as e:
            # 编码错误，可能是二进制文件
            logger.log('WEBUI', f"文件编码错误: {rel_path}, {str(e)}")
            return [], {'error': f'文件编码错误, 可能是二进制文件'}
        except Exception as e:
            # 其他未预期的错误
            logger.log('WEBUI', f"读取文件内容出错: {rel_path}, {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return [], {'error': f'读取文件出错: {str(e)}'}

    def search_in_file(self, rel_path: str = '',
                       query: str = '', max_results: int = 100) -> List[Dict[str, Any]]:
        """在文件中搜索指定内容
        
        在指定文件中搜索字符串，返回匹配的行信息，包括行号、内容和匹配位置。
        
        Args:
            rel_path: 相对于根目录的文件路径
            query: 要搜索的字符串
            max_results: 最大结果数
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表，每项包含行号、内容和匹配位置
        """
        if not query:
            logger.log('WEBUI', "搜索查询为空，返回空结果")
            return []

        try:
            file_path = self._validate_path(rel_path)

            if not file_path.exists() or not file_path.is_file():
                logger.log('WEBUI', f"搜索的文件不存在或不是常规文件: {rel_path}")
                return []

            results = []

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for i, line in enumerate(f):
                    if query.lower() in line.lower():
                        results.append({
                            'line_number': i + 1,  # 从1开始的行号
                            'content': line.rstrip('\n'),
                            'match_position': line.lower().find(query.lower())
                        })

                        if len(results) >= max_results:
                            logger.log('WEBUI', f"搜索结果达到上限 {max_results}，停止搜索")
                            break

            logger.log('WEBUI', f"在文件 {rel_path} 中搜索 '{query}'，找到 {len(results)} 条匹配")
            return results
        except (SecurityError, PathValidationError) as e:
            logger.log('WEBUI', f"搜索文件安全错误: {str(e)}")
            return []
        except UnicodeDecodeError as e:
            logger.log('WEBUI', f"搜索文件编码错误: {rel_path}, {str(e)}")
            return []
        except Exception as e:
            logger.log('WEBUI', f"搜索文件内容出错: {rel_path}, {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return []

    def save_file_content(self, rel_path: str, content: str) -> bool:
        """保存文件内容
        
        将内容写入指定文件，如果文件不存在则创建。
        
        Args:
            rel_path: 相对于根目录的文件路径
            content: 要保存的文件内容
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 验证路径
            file_path = self._validate_path(rel_path)

            # 确保目标是文件而不是目录
            if file_path.is_dir():
                logger.log('WEBUI', f"保存失败: 目标是目录，不能保存内容: {rel_path}")
                raise ValueError("目标是目录，不能保存内容")

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.log('WEBUI', f"文件内容保存成功: {rel_path}, 大小: {len(content)} 字符")
            return True
        except (SecurityError, PathValidationError) as e:
            logger.log('WEBUI', f"保存文件安全错误: {str(e)}")
            return False
        except Exception as e:
            logger.log('WEBUI', f"保存文件异常: {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return False


# 创建文件服务实例
file_service = FileService()
