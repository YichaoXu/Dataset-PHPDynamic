#!/usr/bin/env python3
"""
Script to automatically translate Chinese comments and docstrings to English.
This script identifies and translates Chinese text in Python files.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]+')

# Common translation patterns for technical documentation
TRANSLATION_PATTERNS = {
    # Common verbs
    r'初始化([^，。\n]*)': r'Initialize\1',
    r'检测([^，。\n]*)': r'Detect\1',
    r'获取([^，。\n]*)': r'Get\1',
    r'设置([^，。\n]*)': r'Set\1',
    r'分析([^，。\n]*)': r'Analyze\1',
    r'搜索([^，。\n]*)': r'Search for\1',
    r'导出([^，。\n]*)': r'Export\1',
    r'创建([^，。\n]*)': r'Create\1',
    r'清理([^，。\n]*)': r'Clean up\1',
    r'构建([^，。\n]*)': r'Build\1',
    r'执行([^，。\n]*)': r'Execute\1',
    r'解析([^，。\n]*)': r'Parse\1',
    r'统计([^，。\n]*)': r'Count\1',
    r'缓存([^，。\n]*)': r'Cache\1',
    
    # Common nouns in technical context
    r'仓库': 'repository',
    r'文件': 'file',
    r'路径': 'path',
    r'内容': 'content',
    r'结果': 'result',
    r'列表': 'list',
    r'字符串': 'string',
    r'参数': 'parameter',
    r'错误': 'error',
    r'失败': 'failed',
    r'成功': 'success',
    
    # Common phrases
    r'本模块': 'This module',
    r'本方法': 'This method',
    r'本函数': 'This function',
    r'本类': 'This class',
    r'用于': 'for',
    r'如果': 'If',
    r'否则': 'Otherwise',
    r'返回': 'Returns',
    r'抛出': 'Raises',
    r'输入': 'Input',
    r'输出': 'Output',
}

# Structured translations for common docstring patterns
DOCSTRING_TRANSLATIONS = {
    # Module docstrings
    'PHP项目筛选系统核心模块': 'PHP Project Filtering System Core Module',
    '本模块包含用于从GitHub搜索和分析PHP项目的所有核心组件。': 
        'This module contains all core components for searching and filtering PHP projects from GitHub.',
    
    # Common class docstrings
    '管理API请求的缓存，避免重复查询': 'Manages caching of API requests to avoid duplicate queries',
    '处理GitHub API速率限制': 'Handles GitHub API rate limiting',
    'PHP代码分析器，检测安全风险特征': 'PHP code analyzer that detects security risk characteristics',
    '项目搜索器，协调所有组件完成项目搜索和筛选': 
        'Project searcher that coordinates all components to complete project search and filtering',
    'CSV导出器，将搜索结果导出为CSV文件': 'CSV exporter that exports search results to CSV files',
    '存储单个项目的搜索结果和分析数据': 'Stores search results and analysis data for a single project',
    '使用Semgrep进行PHP代码静态分析': 'Performs static analysis of PHP code using Semgrep',
    
    # Common method patterns
    '初始化': lambda m: 'Initialize',
    '检测': lambda m: 'Detect',
    '获取': lambda m: 'Get',
    '设置': lambda m: 'Set',
}

def translate_common_patterns(text: str) -> str:
    """Translate common Chinese patterns to English"""
    result = text
    
    # Apply structured translations first (exact matches)
    for chinese, english in DOCSTRING_TRANSLATIONS.items():
        if isinstance(english, str):
            result = result.replace(chinese, english)
    
    # Apply regex patterns
    for pattern, replacement in TRANSLATION_PATTERNS.items():
        result = re.sub(pattern, replacement, result)
    
    return result


def translate_docstring_content(content: str) -> str:
    """Translate docstring content from Chinese to English"""
    lines = content.split('\n')
    translated_lines = []
    
    for line in lines:
        # Skip if line doesn't contain Chinese
        if not CHINESE_PATTERN.search(line):
            translated_lines.append(line)
            continue
        
        # Translate common patterns
        translated_line = translate_common_patterns(line)
        
        # Handle specific docstring patterns
        if 'Args:' in translated_line or 'Arguments:' in translated_line:
            # Args section - translate parameter descriptions
            translated_line = re.sub(
                r'(\w+):\s*([^\n]+)',
                lambda m: f"{m.group(1)}: {translate_common_patterns(m.group(2))}",
                translated_line
            )
        elif 'Returns:' in translated_line or '返回:' in translated_line:
            translated_line = translated_line.replace('返回:', 'Returns:')
        elif 'Raises:' in translated_line or '抛出:' in translated_line:
            translated_line = translated_line.replace('抛出:', 'Raises:')
        
        translated_lines.append(translated_line)
    
    return '\n'.join(translated_lines)


def translate_file(file_path: Path, dry_run: bool = False) -> Tuple[int, List[str]]:
    """
    Translate Chinese text in a Python file
    
    Returns:
        Tuple of (number of changes, list of changed lines)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0, []
    
    original_content = content
    changed_lines = []
    
    # Split into lines for processing
    lines = content.split('\n')
    translated_lines = []
    
    in_docstring = False
    docstring_type = None
    
    for i, line in enumerate(lines, 1):
        original_line = line
        translated_line = line
        
        # Detect docstrings
        if '"""' in line or "'''" in line:
            quote_type = '"""' if '"""' in line else "'''"
            if line.count(quote_type) == 2:
                # Single-line docstring
                if CHINESE_PATTERN.search(line):
                    translated_line = translate_docstring_content(line)
            else:
                # Multi-line docstring
                in_docstring = not in_docstring
                docstring_type = quote_type if in_docstring else None
        
        # Translate docstring content
        if in_docstring and CHINESE_PATTERN.search(line):
            translated_line = translate_docstring_content(line)
        
        # Translate inline comments
        if '#' in line and CHINESE_PATTERN.search(line):
            comment_start = line.index('#')
            comment_part = line[comment_start:]
            code_part = line[:comment_start]
            translated_comment = translate_common_patterns(comment_part)
            translated_line = code_part + translated_comment
        
        if translated_line != original_line:
            changed_lines.append(f"Line {i}: {original_line[:60]}...")
        
        translated_lines.append(translated_line)
    
    translated_content = '\n'.join(translated_lines)
    
    # Only write if content changed and not dry run
    if translated_content != original_content and not dry_run:
        file_path.write_text(translated_content, encoding='utf-8')
    
    changes = len(changed_lines)
    return changes, changed_lines


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Translate Chinese comments and docstrings to English'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be translated without making changes'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Translate a specific file (relative to project root)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Translate all Python files in phpincludes/'
    )
    
    args = parser.parse_args()
    
    if args.file:
        files_to_translate = [Path(args.file)]
    elif args.all:
        phpincludes_dir = Path('phpincludes')
        files_to_translate = list(phpincludes_dir.rglob('*.py'))
    else:
        # Default: find all files with Chinese
        phpincludes_dir = Path('phpincludes')
        all_files = list(phpincludes_dir.rglob('*.py'))
        files_to_translate = []
        
        for py_file in all_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                if CHINESE_PATTERN.search(content):
                    files_to_translate.append(py_file)
            except Exception:
                pass
    
    if not files_to_translate:
        print("No files found to translate.")
        return
    
    print(f"Found {len(files_to_translate)} file(s) to translate\n")
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")
    
    total_changes = 0
    for py_file in sorted(files_to_translate):
        print(f"Processing {py_file}...")
        changes, changed_lines = translate_file(py_file, dry_run=args.dry_run)
        total_changes += changes
        
        if changes > 0:
            print(f"  ✓ {changes} line(s) would be translated")
            if args.dry_run and changed_lines:
                for line_info in changed_lines[:3]:
                    print(f"    {line_info}")
                if len(changed_lines) > 3:
                    print(f"    ... and {len(changed_lines) - 3} more")
        else:
            print(f"  - No changes needed")
        print()
    
    print(f"\nTotal: {total_changes} line(s) {'would be' if args.dry_run else ''}translated")
    
    if not args.dry_run and total_changes > 0:
        print("\n⚠️  Note: This is an automated translation. Please review the changes!")
        print("   Some translations may need manual adjustment for accuracy.")


if __name__ == '__main__':
    main()