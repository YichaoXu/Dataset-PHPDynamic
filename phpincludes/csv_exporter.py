"""
CSV Exporter

This module is responsible for exporting search results to CSV format files.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .search_result import SearchResult


class CSVExporter:
    """CSV exporter that exports search results to CSV files"""

    def __init__(self, output_dir: str = "data/output") -> None:
        """
        Initialize CSV exporter

        Args:
            output_dir: Output directory path
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
        Export search results to CSV file

        Args:
            results: Search result list
            filename: Output file name, None for auto-generation
            include_unqualified: Whether to include unqualified projects

        Returns:
            Output file path
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Check if output path is a directory (should not happen, but if directory exists it prevents file creation)
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # Filter results
        filtered_results = self._filter_results(results, include_unqualified)

        # Write to CSV file
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
        Export analysis summary to CSV file

        Args:
            results: Search result list
            filename: Output file name, None for auto-generation

        Returns:
            Output file path
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_summary_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Check if output path is a directory
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # Generate summary data
        summary_data = self._generate_summary_data(results)

        # Write to CSV file
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
        Filter search results

        Args:
            results: Original result list
            include_unqualified: Whether to include unqualified projects

        Returns:
            Filtered result list
        """
        if include_unqualified:
            return results
        return [result for result in results if result.is_qualified]

    def _get_fieldnames(self) -> List[str]:
        """
        Get CSV field names (only basic information needed for download and analysis)

        Returns:
            Field name list
        """
        return [
            "project_name",
            "owner",
            "repo_name",
            "url",
            "commit_hash",
            "star_count",
            "detection_type",
        ]

    def _get_summary_fieldnames(self) -> List[str]:
        """
        Get summary CSV field names

        Returns:
            Summary field name list
        """
        return [
            "category",
            "count",
            "percentage",
            "description",
        ]

    def _format_result_row(self, result: SearchResult) -> Dict[str, Any]:
        """
        Format result row as CSV row

        Args:
            result: Search forresult

        Returns:
            Formatted CSV row data (simplified through SearchResult.to_csv_row())
        """
        return result.to_csv_row()

    def _format_priority(self, priority: int) -> str:
        """
        格式化优先级

        Args:
            priority: 优先级数字

        Returns:
            格式化的优先级string
        """
        priority_map = {
            0: "Rejected",
            1: "High (Dynamic Functions)",
            2: "Medium (Dynamic Includes)",
        }
        return priority_map.get(priority, f"Unknown ({priority})")

    def _format_timestamp(self, timestamp: str) -> str:
        """
        Format timestamp

        Args:
            timestamp: Timestamp string

        Returns:
            Formatted timestamp
        """
        if not timestamp:
            return ""
        try:
            # Try to parse ISO format timestamp
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return timestamp

    def _generate_summary_data(
        self, results: List[SearchResult]
    ) -> List[Dict[str, Any]]:
        """
        Generate summary data

        Args:
            results: Search result list

        Returns:
            Summary data list
        """
        total_count = len(results)
        qualified_count = sum(1 for r in results if r.is_qualified)
        rejected_count = total_count - qualified_count

        # Group by detection type
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

        # Add detection type count
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
        Export detailed results to CSV file

        Args:
            results: Search result list
            filename: Output file name, None for auto-generation

        Returns:
            Output file path
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"php_projects_detailed_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Check if output path is a directory
        if output_path.exists() and output_path.is_dir():
            raise ValueError(
                f"Output path is a directory, not a file: {output_path}. "
                f"Please remove the directory or use a different filename."
            )

        # Generate detailed data
        detailed_data = []
        for result in results:
            detailed_info = result.get_detailed_analysis()
            base_info = result.to_csv_row()

            # Create one row for each detection item
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

        # Write to CSV file
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
        GetExportCount信息

        Args:
            results: Search result list

        Returns:
            Count信息字典
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
