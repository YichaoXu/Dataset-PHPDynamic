"""
CSV导出器

本模块负责将搜索结果导出为CSV格式文件。
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .search_result import SearchResult


class CSVExporter:
    """CSV导出器，将搜索结果导出为CSV文件"""

    def __init__(self, output_dir: str = "data/output") -> None:
        """
        初始化CSV导出器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_results(
        self,
        results: List[SearchResult],
        filename: Optional[str] = None,
        include_unqualified: bool = False,
    ) -> str:
        """
        导出搜索结果到CSV文件

        Args:
            results: 搜索结果列表
            filename: 输出文件名，None则自动生成
            include_unqualified: 是否包含不符合条件的项目

        Returns:
            输出文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_{timestamp}.csv"

        output_path = self.output_dir / filename

        # 检查输出路径是否是目录（不应该发生，但如果存在同名目录会阻止文件创建）
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # 过滤结果
        filtered_results = self._filter_results(results, include_unqualified)

        # 写入CSV文件
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self._get_fieldnames())
            writer.writeheader()

            for result in filtered_results:
                writer.writerow(self._format_result_row(result))

        return str(output_path)

    def export_summary(
        self,
        results: List[SearchResult],
        filename: Optional[str] = None,
    ) -> str:
        """
        导出分析摘要到CSV文件

        Args:
            results: 搜索结果列表
            filename: 输出文件名，None则自动生成

        Returns:
            输出文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_summary_{timestamp}.csv"

        output_path = self.output_dir / filename

        # 检查输出路径是否是目录
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # 生成摘要数据
        summary_data = self._generate_summary_data(results)

        # 写入CSV文件
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self._get_summary_fieldnames())
            writer.writeheader()

            for row in summary_data:
                writer.writerow(row)

        return str(output_path)

    def _filter_results(
        self, results: List[SearchResult], include_unqualified: bool
    ) -> List[SearchResult]:
        """
        过滤搜索结果

        Args:
            results: 原始结果列表
            include_unqualified: 是否包含不符合条件的项目

        Returns:
            过滤后的结果列表
        """
        if include_unqualified:
            return results
        return [result for result in results if result.is_qualified]

    def _get_fieldnames(self) -> List[str]:
        """
        获取CSV字段名

        Returns:
            字段名列表
        """
        return [
            "project_name",
            "owner",
            "repo_name",
            "url",
            "commit_hash",
            "star_count",
            "detection_type",
            "is_qualified",
            "priority",
            "superglobal_usage",
            "function_usage",
            "dynamic_include_usage",
            "rejection_reason",
            "analysis_timestamp",
        ]

    def _get_summary_fieldnames(self) -> List[str]:
        """
        获取摘要CSV字段名

        Returns:
            摘要字段名列表
        """
        return [
            "category",
            "count",
            "percentage",
            "description",
        ]

    def _format_result_row(self, result: SearchResult) -> Dict[str, Any]:
        """
        格式化结果行为CSV行

        Args:
            result: 搜索结果

        Returns:
            格式化的CSV行数据
        """
        csv_row = result.to_csv_row()

        # 添加额外的格式化
        csv_row["is_qualified"] = "Yes" if result.is_qualified else "No"
        csv_row["priority"] = self._format_priority(result.priority)
        csv_row["analysis_timestamp"] = self._format_timestamp(
            csv_row.get("analysis_timestamp", "")
        )

        return csv_row

    def _format_priority(self, priority: int) -> str:
        """
        格式化优先级

        Args:
            priority: 优先级数字

        Returns:
            格式化的优先级字符串
        """
        priority_map = {
            0: "Rejected",
            1: "High (Dynamic Functions)",
            2: "Medium (Dynamic Includes)",
        }
        return priority_map.get(priority, f"Unknown ({priority})")

    def _format_timestamp(self, timestamp: str) -> str:
        """
        格式化时间戳

        Args:
            timestamp: 时间戳字符串

        Returns:
            格式化的时间戳
        """
        if not timestamp:
            return ""
        try:
            # 尝试解析ISO格式时间戳
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return timestamp

    def _generate_summary_data(
        self, results: List[SearchResult]
    ) -> List[Dict[str, Any]]:
        """
        生成摘要数据

        Args:
            results: 搜索结果列表

        Returns:
            摘要数据列表
        """
        total_count = len(results)
        qualified_count = sum(1 for r in results if r.is_qualified)
        rejected_count = total_count - qualified_count

        # 按检测类型分组
        detection_types: Dict[str, int] = {}
        for result in results:
            if result.is_qualified:
                detection_type = result.detection_type
                detection_types[detection_type] = (
                    detection_types.get(detection_type, 0) + 1
                )

        summary_data = [
            {
                "category": "Total Projects",
                "count": total_count,
                "percentage": "100.0%",
                "description": "Total number of projects analyzed",
            },
            {
                "category": "Qualified Projects",
                "count": qualified_count,
                "percentage": (
                    f"{(qualified_count/total_count*100):.1f}%"
                    if total_count > 0
                    else "0.0%"
                ),
                "description": "Projects that meet the criteria",
            },
            {
                "category": "Rejected Projects",
                "count": rejected_count,
                "percentage": (
                    f"{(rejected_count/total_count*100):.1f}%"
                    if total_count > 0
                    else "0.0%"
                ),
                "description": "Projects that don't meet the criteria",
            },
        ]

        # 添加检测类型统计
        for detection_type, count in detection_types.items():
            summary_data.append(
                {
                    "category": f"Detection Type: {detection_type}",
                    "count": count,
                    "percentage": (
                        f"{(count/total_count*100):.1f}%" if total_count > 0 else "0.0%"
                    ),
                    "description": f"Projects detected by {detection_type}",
                }
            )

        return summary_data

    def export_detailed_results(
        self,
        results: List[SearchResult],
        filename: Optional[str] = None,
    ) -> str:
        """
        导出详细结果到CSV文件

        Args:
            results: 搜索结果列表
            filename: 输出文件名，None则自动生成

        Returns:
            输出文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_detailed_{timestamp}.csv"

        output_path = self.output_dir / filename

        # 检查输出路径是否是目录
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # 生成详细数据
        detailed_data = []
        for result in results:
            detailed_info = result.get_detailed_analysis()
            base_info = result.to_csv_row()

            # 为每个检测项创建一行
            for usage_type in [
                "superglobal_details",
                "function_details",
                "include_details",
            ]:
                details = detailed_info.get(usage_type, [])
                for detail in details:
                    row = base_info.copy()
                    row["usage_type"] = usage_type.replace("_details", "")
                    row["pattern"] = detail.get("pattern", "")
                    row["line_number"] = detail.get("line_number", "")
                    row["match"] = detail.get("match", "")
                    row["context"] = detail.get("context", "")
                    detailed_data.append(row)

        # 写入CSV文件
        fieldnames = self._get_fieldnames() + [
            "usage_type",
            "pattern",
            "line_number",
            "match",
            "context",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in detailed_data:
                writer.writerow(row)

        return str(output_path)

    def get_export_statistics(self, results: List[SearchResult]) -> Dict[str, Any]:
        """
        获取导出统计信息

        Args:
            results: 搜索结果列表

        Returns:
            统计信息字典
        """
        total_count = len(results)
        qualified_count = sum(1 for r in results if r.is_qualified)

        detection_types: Dict[str, int] = {}
        for result in results:
            if result.is_qualified:
                detection_type = result.detection_type
                detection_types[detection_type] = (
                    detection_types.get(detection_type, 0) + 1
                )

        return {
            "total_projects": total_count,
            "qualified_projects": qualified_count,
            "rejected_projects": total_count - qualified_count,
            "qualification_rate": (
                qualified_count / total_count if total_count > 0 else 0
            ),
            "detection_types": detection_types,
            "output_directory": str(self.output_dir),
        }
