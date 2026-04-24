import time

from config import TOP_N
from github_fetcher import fetch_trending_repos, fetch_readme
from summarizer import create_backend, generate_summary
from reporter import SummaryEntry, generate_report, save_report


def main():
    start_time = time.time()

    print("[1/5] 检测 AI 后端...")
    backend = create_backend()
    print(f"  使用后端: {backend.name}")

    print(f"[2/5] 获取 GitHub 一周热门项目 (Top {TOP_N})...")
    repos = fetch_trending_repos(top_n=TOP_N)
    print(f"  已获取 {len(repos)} 个项目。")
    for i, repo in enumerate(repos, 1):
        print(f"    {i}. {repo.name} (★{repo.stars}, {repo.language})")

    summaries: list[SummaryEntry] = []
    success_count = 0
    for i, repo in enumerate(repos, 1):
        print(f"[3/5] 处理项目 {i}/{len(repos)}: {repo.name}")
        t0 = time.time()
        readme = fetch_readme(repo.name)
        if not readme:
            print(f"  无 README 文件，跳过摘要生成。")
        summary = generate_summary(repo, readme, backend)
        elapsed = time.time() - t0
        if summary.startswith("（"):
            print(f"  摘要生成失败 ({elapsed:.1f}s): {summary}")
        else:
            success_count += 1
            print(f"  摘要生成完成 ({elapsed:.1f}s)。")
        summaries.append(SummaryEntry(repo=repo, summary=summary))

    print("[4/5] 生成报告...")
    report = generate_report(summaries)

    print("[5/5] 保存报告...")
    file_path = save_report(report)

    total_time = time.time() - start_time
    print(f"\n完成！共 {len(summaries)} 个项目，{success_count} 个摘要成功生成。")
    print(f"报告已保存至: {file_path}")
    print(f"总耗时: {total_time:.1f}s")


if __name__ == "__main__":
    main()
