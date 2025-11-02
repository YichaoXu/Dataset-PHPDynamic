#!/usr/bin/env python3
"""
项目设置脚本

本脚本用于初始化项目环境，安装依赖，验证配置。
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class ProjectSetup:
    """项目设置管理器"""

    def __init__(self) -> None:
        """初始化设置管理器"""
        self.project_root = Path(__file__).parent.parent
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def run_setup(self) -> bool:
        """
        运行完整的项目设置

        Returns:
            设置是否成功
        """
        print("🚀 开始项目设置...")
        print("=" * 50)

        # 检查Python版本
        self._check_python_version()

        # 检查uv是否安装
        self._check_uv_installation()

        # 安装依赖
        self._install_dependencies()

        # 检查Semgrep
        self._check_semgrep()

        # 验证配置
        self._validate_configuration()

        # 创建必要目录
        self._create_directories()

        # 显示结果
        self._print_results()

        return len(self.errors) == 0

    def _check_python_version(self) -> None:
        """检查Python版本"""
        print("🐍 检查Python版本...")

        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            self.errors.append(
                f"Python版本过低: {version.major}.{version.minor}，需要Python 3.9+"
            )
        else:
            print(f"   ✅ Python版本: {version.major}.{version.minor}.{version.micro}")

    def _check_uv_installation(self) -> None:
        """检查uv是否安装"""
        print("📦 检查uv安装...")

        try:
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, check=True
            )
            print(f"   ✅ uv已安装: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.errors.append(
                "uv未安装，请先安装uv: https://docs.astral.sh/uv/getting-started/installation/"
            )

    def _install_dependencies(self) -> None:
        """安装项目依赖"""
        print("📚 安装项目依赖...")

        try:
            # 安装主要依赖
            subprocess.run(["uv", "sync"], cwd=self.project_root, check=True)
            print("   ✅ 主要依赖安装完成")

            # 安装开发依赖
            subprocess.run(["uv", "sync", "--dev"], cwd=self.project_root, check=True)
            print("   ✅ 开发依赖安装完成")

        except subprocess.CalledProcessError as e:
            self.errors.append(f"依赖安装失败: {e}")

    def _check_semgrep(self) -> None:
        """检查Semgrep安装"""
        print("🔍 检查Semgrep安装...")

        try:
            result = subprocess.run(
                ["semgrep", "--version"], capture_output=True, text=True, check=True
            )
            print(f"   ✅ Semgrep已安装: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.warnings.append(
                "Semgrep未安装，将使用正则表达式fallback模式。"
                "建议安装Semgrep以获得更好的分析效果: pip install semgrep"
            )

    def _validate_configuration(self) -> None:
        """验证项目配置"""
        print("⚙️ 验证项目配置...")

        try:
            # 导入配置模块
            sys.path.insert(0, str(self.project_root))
            from phpincludes.settings import Settings

            # 验证配置
            validation_results = Settings.validate_config()

            for config_name, is_valid in validation_results.items():
                if is_valid:
                    print(f"   ✅ {config_name}: 配置有效")
                else:
                    self.warnings.append(f"{config_name}: 配置无效")

            # 检查GitHub令牌
            try:
                Settings.get_github_token()
                print("   ✅ GitHub令牌: 已配置")
            except ValueError:
                self.warnings.append(
                    f"GitHub令牌未配置，请设置 {Settings.GITHUB_API_TOKEN_ENV} 环境变量"
                )

        except ImportError as e:
            self.errors.append(f"配置模块导入失败: {e}")

    def _create_directories(self) -> None:
        """创建必要的目录"""
        print("📁 创建项目目录...")

        directories = [
            "data/cache",
            "data/temp",
            "data/output",
            "tests",
            "tests/integration",
        ]

        for dir_path in directories:
            full_path = self.project_root / dir_path
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"   ✅ 目录已创建: {dir_path}")
            except Exception as e:
                self.errors.append(f"无法创建目录 {dir_path}: {e}")

    def _print_results(self) -> None:
        """打印设置结果"""
        print("\n" + "=" * 50)
        print("📋 设置结果摘要")
        print("=" * 50)

        if self.errors:
            print("❌ 错误:")
            for error in self.errors:
                print(f"   • {error}")

        if self.warnings:
            print("⚠️ 警告:")
            for warning in self.warnings:
                print(f"   • {warning}")

        if not self.errors and not self.warnings:
            print("🎉 项目设置完成，所有检查通过!")
        elif not self.errors:
            print("✅ 项目设置完成，但有一些警告需要注意")
        else:
            print("❌ 项目设置失败，请修复上述错误")

    def check_environment(self) -> Dict[str, bool]:
        """
        检查环境状态

        Returns:
            环境检查结果
        """
        results = {}

        # 检查Python版本
        version = sys.version_info
        results["python_version"] = version.major >= 3 and version.minor >= 9

        # 检查uv
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            results["uv_installed"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results["uv_installed"] = False

        # 检查Semgrep
        try:
            subprocess.run(["semgrep", "--version"], capture_output=True, check=True)
            results["semgrep_installed"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results["semgrep_installed"] = False

        # 检查GitHub令牌
        try:
            sys.path.insert(0, str(self.project_root))
            from phpincludes.settings import Settings

            Settings.get_github_token()
            results["github_token"] = True
        except (ImportError, ValueError):
            results["github_token"] = False

        return results

    def install_semgrep(self) -> bool:
        """
        安装Semgrep

        Returns:
            安装是否成功
        """
        print("📦 安装Semgrep...")

        try:
            subprocess.run(["uv", "add", "semgrep"], cwd=self.project_root, check=True)
            print("   ✅ Semgrep安装完成")
            return True
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Semgrep安装失败: {e}")
            return False

    def setup_github_token(self, token: str) -> None:
        """
        设置GitHub令牌

        Args:
            token: GitHub API令牌
        """
        print("🔑 设置GitHub令牌...")

        try:
            sys.path.insert(0, str(self.project_root))
            from phpincludes.settings import Settings

            # 设置环境变量
            os.environ[Settings.GITHUB_API_TOKEN_ENV] = token
            print("   ✅ GitHub令牌已设置")
        except ImportError as e:
            self.errors.append(f"无法设置GitHub令牌: {e}")


def main() -> int:
    """
    主函数

    Returns:
        退出码
    """
    setup = ProjectSetup()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "check":
            # 检查环境
            results = setup.check_environment()
            print("🔍 环境检查结果:")
            for name, status in results.items():
                status_text = "✅" if status else "❌"
                print(f"   {status_text} {name}")
            return 0 if all(results.values()) else 1

        elif command == "install-semgrep":
            # 安装Semgrep
            success = setup.install_semgrep()
            return 0 if success else 1

        elif command == "set-token" and len(sys.argv) > 2:
            # 设置GitHub令牌
            token = sys.argv[2]
            setup.setup_github_token(token)
            return 0 if not setup.errors else 1

        else:
            print("❌ 未知命令")
            print("可用命令:")
            print("  python scripts/setup.py check")
            print("  python scripts/setup.py install-semgrep")
            print("  python scripts/setup.py set-token YOUR_TOKEN")
            return 1

    # 运行完整设置
    success = setup.run_setup()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
