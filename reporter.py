from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from github_fetcher import RepoInfo


@dataclass
class SummaryEntry:
    repo: RepoInfo
    summary: str


def generate_report(summaries: list[SummaryEntry]) -> str:
    """将所有项目摘要格式化为报告文本。"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "=" * 50,
        "GitHub 一周热门项目摘要报告",
        f"日期：{today}",
        "=" * 50,
        "",
    ]

    for i, entry in enumerate(summaries, 1):
        repo = entry.repo
        lines.append(f"{i}. 项目名: {repo.name}")
        lines.append(f"   URL: {repo.url}")
        lines.append(f"   Star数: {repo.stars}")
        lines.append(f"   语言: {repo.language}")
        lines.append("   " + "-" * 40)
        lines.append(f"   {entry.summary}")
        lines.append("")

    lines.append("=" * 50)
    lines.append(f"共 {len(summaries)} 个项目")
    lines.append("=" * 50)

    return "\n".join(lines)


def save_report(report: str, output_dir: str = "output") -> Path:
    """保存报告为日期命名的 txt 文件。"""
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    file_path = out_path / f"{today}.txt"
    file_path.write_text(report, encoding="utf-8")
    return file_path
