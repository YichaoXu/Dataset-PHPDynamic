"""
Project downloader module for downloading GitHub repositories from CSV files.

Downloads repositories using GitHub archive links and extracts them to a specified directory.
"""

import csv
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import AnalysisError


class ProjectDownloader:
    """
    Downloads GitHub repositories from CSV files using archive links.
    """

    def __init__(self, output_dir: str, verbose: bool = False) -> None:
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded projects
            verbose: Enable verbose output
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def read_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """
        Read project information from CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of project dictionaries

        Raises:
            AnalysisError: CSV file cannot be read
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise AnalysisError(f"CSV file not found: {csv_path}")

        projects: List[Dict[str, str]] = []
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    projects.append(dict(row))
        except Exception as e:
            raise AnalysisError(f"Failed to read CSV file {csv_path}: {e}") from e

        return projects

    def generate_folder_name(
        self, owner: str, repo_name: str, commit_hash: str
    ) -> str:
        """
        Generate folder name in format: ownerName_projName_commit(first6digits).

        Args:
            owner: Repository owner
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            Folder name
        """
        commit_prefix = commit_hash[:6] if len(commit_hash) >= 6 else commit_hash
        return f"{owner}_{repo_name}_{commit_prefix}"

    def download_archive(
        self, owner: str, repo_name: str, commit_hash: str
    ) -> Optional[Path]:
        """
        Download GitHub repository archive for a specific commit.

        Args:
            owner: Repository owner
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            Path to downloaded archive file, or None if download failed
        """
        # Try .tar.gz first (smaller, preferred)
        archive_url = f"https://github.com/{owner}/{repo_name}/archive/{commit_hash}.tar.gz"

        try:
            if self.verbose:
                print(f"  📥 Downloading: {archive_url}")

            response = self.session.get(archive_url, stream=True, timeout=300)
            response.raise_for_status()

            # Save to temporary file
            temp_file = self.output_dir / f"{owner}_{repo_name}_{commit_hash}.tar.gz"
            with open(temp_file, "wb") as f:
                shutil.copyfileobj(response.raw, f)

            if self.verbose:
                print(f"  ✅ Downloaded: {temp_file.name}")

            return temp_file

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Try .zip as fallback
                archive_url = f"https://github.com/{owner}/{repo_name}/archive/{commit_hash}.zip"
                try:
                    if self.verbose:
                        print(f"  📥 Trying .zip: {archive_url}")

                    response = self.session.get(archive_url, stream=True, timeout=300)
                    response.raise_for_status()

                    temp_file = self.output_dir / f"{owner}_{repo_name}_{commit_hash}.zip"
                    with open(temp_file, "wb") as f:
                        shutil.copyfileobj(response.raw, f)

                    if self.verbose:
                        print(f"  ✅ Downloaded: {temp_file.name}")

                    return temp_file

                except Exception as e2:
                    if self.verbose:
                        print(f"  ❌ Failed to download .zip: {e2}")
                    return None
            else:
                if self.verbose:
                    print(f"  ❌ Failed to download: {e}")
                return None
        except Exception as e:
            if self.verbose:
                print(f"  ❌ Download error: {e}")
            return None

    def extract_archive(
        self, archive_path: Path, output_folder: Path
    ) -> bool:
        """
        Extract archive to output folder.

        Args:
            archive_path: Path to archive file
            output_folder: Destination folder

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            output_folder.mkdir(parents=True, exist_ok=True)

            if archive_path.suffix == ".gz" or archive_path.suffixes == [".tar", ".gz"]:
                # Extract .tar.gz
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Get the root directory name from the archive
                    members = tar.getmembers()
                    if members:
                        # Remove the root directory prefix from all members
                        root_dir = members[0].name.split("/")[0]
                        for member in members:
                            if member.name.startswith(root_dir + "/"):
                                member.name = member.name[len(root_dir) + 1 :]
                            elif member.name == root_dir:
                                # Skip root directory entry
                                continue
                        tar.extractall(output_folder, members=members)

            elif archive_path.suffix == ".zip":
                # Extract .zip
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    # Get the root directory name
                    members = zip_ref.namelist()
                    if members:
                        root_dir = members[0].split("/")[0]
                        # Extract without root directory
                        for member in members:
                            if member.startswith(root_dir + "/"):
                                # Extract to output folder with root directory removed
                                target_path = output_folder / member[len(root_dir) + 1 :]
                                if member.endswith("/"):
                                    # Directory
                                    target_path.mkdir(parents=True, exist_ok=True)
                                else:
                                    # File
                                    target_path.parent.mkdir(parents=True, exist_ok=True)
                                    with zip_ref.open(member) as source:
                                        with open(target_path, "wb") as target:
                                            target.write(source.read())

            # Clean up archive file
            archive_path.unlink()

            if self.verbose:
                print(f"  ✅ Extracted to: {output_folder}")

            return True

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Extraction error: {e}")
            return False

    def download_project(
        self, owner: str, repo_name: str, commit_hash: str
    ) -> bool:
        """
        Download and extract a single project.

        Args:
            owner: Repository owner
            repo_name: Repository name
            commit_hash: Commit hash

        Returns:
            True if download and extraction succeeded, False otherwise
        """
        folder_name = self.generate_folder_name(owner, repo_name, commit_hash)
        output_folder = self.output_dir / folder_name

        # Skip if already exists
        if output_folder.exists():
            if self.verbose:
                print(f"  ⏭️  Skipping (already exists): {folder_name}")
            return True

        # Download archive
        archive_path = self.download_archive(owner, repo_name, commit_hash)
        if archive_path is None:
            return False

        # Extract archive
        success = self.extract_archive(archive_path, output_folder)

        return success

    def download_from_csv(self, csv_path: str) -> Dict[str, int]:
        """
        Download all projects from CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Dictionary with download statistics
        """
        projects = self.read_csv(csv_path)

        stats = {
            "total": len(projects),
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

        print(f"\n📥 Downloading {stats['total']} projects...")
        print(f"📁 Output directory: {self.output_dir}")

        for idx, project in enumerate(projects, 1):
            owner = project.get("owner", "")
            repo_name = project.get("repo_name", "")
            commit_hash = project.get("commit_hash", "")

            if not owner or not repo_name or not commit_hash:
                print(f"\n[{idx}/{stats['total']}] ⚠️  Skipping: Missing required fields")
                stats["skipped"] += 1
                continue

            folder_name = self.generate_folder_name(owner, repo_name, commit_hash)
            print(f"\n[{idx}/{stats['total']}] 📦 {folder_name}")

            if self.download_project(owner, repo_name, commit_hash):
                stats["success"] += 1
            else:
                stats["failed"] += 1

        return stats

