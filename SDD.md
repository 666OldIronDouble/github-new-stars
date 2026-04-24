# GitHub New Stars 软件设计文档 (SDD)

## 1. 项目概述

**项目名称**: github-new-stars
**项目目标**: 自动抓取 GitHub 上一周内 star 增长最快的 10 个项目，对其 README 文件生成 AI 摘要，并将结果保存为日期命名的 txt 文件。

## 2. 技术选型

| 组件       | 技术方案                    |
|------------|-----------------------------|
| 语言       | Python 3.13                 |
| GitHub 数据| GitHub REST API (Search)    |
| AI 摘要    | Ollama 本地模型             |
| HTTP 请求  | httpx                      |
| 配置管理   | .env 文件 + python-dotenv   |

## 3. 系统架构

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  GitHub API │────▶│  github-new-stars │────▶│   Ollama    │
│  (数据源)   │     │                  │     │  (摘要生成) │
└─────────────┘     └──────────────────┘     └─────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  output/     │
                    │  2026-04-23.txt │
                    └──────────────┘
```

## 4. 模块设计

### 4.1 项目结构

```
github-new-stars/
├── main.py            # 入口，编排整个流程
├── config.py          # 配置加载（.env）
├── github_fetcher.py  # GitHub API 交互：获取热门项目
├── summarizer.py      # Ollama 交互：生成摘要
├── reporter.py        # 报告生成：格式化输出 txt 文件
├── requirements.txt
├── .env.example       # 环境变量示例
└── .gitignore
```

### 4.2 模块职责

#### config.py
- 从 `.env` 文件加载配置
- 配置项：
  - `GITHUB_TOKEN`: GitHub 个人访问令牌（可选，有 token 速率限制更高）
  - `OLLAMA_MODEL`: Ollama 模型名称（默认 `qwen3.5`）
  - `OLLAMA_BASE_URL`: Ollama 服务地址（默认 `http://localhost:11434`）
  - `TOP_N`: 获取项目数量（默认 `10`）

#### github_fetcher.py
- **`fetch_trending_repos(top_n: int = 10) -> list[RepoInfo]`**
  - 调用 GitHub Search API：`GET /search/repositories`
  - 查询参数：搜索一周内有推送的高 star 项目
  - 返回结构化数据列表

- **数据结构 `RepoInfo`**:
  ```python
  @dataclass
  class RepoInfo:
      name: str           # 项目名 (owner/repo)
      url: str            # GitHub URL
      stars: int          # 当前 star 数
      language: str       # 主要编程语言
      description: str    # 项目简述
  ```

- **`fetch_readme(repo_full_name: str) -> str`**
  - 调用 `GET /repos/{owner}/{repo}/readme`
  - 返回 README 文本内容（base64 解码）

#### summarizer.py
- **`generate_summary(repo: RepoInfo, readme: str) -> str`**
  - 调用 Ollama REST API：`POST /api/generate`
  - Prompt 模板：
    ```
    请用中文对以下 GitHub 项目生成摘要，包含：
    1. 项目用途（一句话）
    2. 核心功能（2-3个要点）
    3. 技术栈/依赖
    4. 适合哪类开发者使用

    项目：{name}
    Star数：{stars}
    语言：{language}
    描述：{description}

    README内容：
    {readme}
    ```
  - 返回生成的摘要文本

#### reporter.py
- **`generate_report(summaries: list[SummaryEntry]) -> str`**
  - 将所有项目摘要格式化为统一报告文本
  - 报告格式：

  ```
  ==========================================
  GitHub 一周热门项目摘要报告
  日期：2026-04-23
  ==========================================

  1. 项目名: owner/repo
     URL: https://github.com/owner/repo
     Star数: 12345
     语言: Python
     ----------------------------------------
     [AI 生成摘要内容]

  2. 项目名: ...

  ==========================================
  共 10 个项目
  ==========================================
  ```

- **`save_report(report: str, date: str, output_dir: str = "output") -> Path`**
  - 保存为 `output/{date}.txt`
  - 自动创建 output 目录

#### main.py
- 编排流程：
  1. 加载配置
  2. 获取热门项目列表
  3. 逐个获取 README 并生成摘要
  4. 汇总生成报告
  5. 保存为 txt 文件

## 5. GitHub API 策略

使用 GitHub Search API 获取一周内新建的高 star 增长项目：

```
GET https://api.github.com/search/repositories?q=created:>2026-04-17+stars:>10&sort=stars&order=desc&per_page=10
```

- `created:>{one_week_ago}`: 筛选一周内创建的项目（反映当下热门趋势）
- `stars:>10`: 过滤掉 star 过少的项目
- `sort=stars&order=desc`: 按 star 数降序排列
- 有 GITHUB_TOKEN 时在请求头中携带 `Authorization: Bearer {token}` 以提高速率限制
- 若一周内项目不足 top_n，补充两周内创建的项目

## 6. Ollama 集成

- 默认使用 `qwen3.5` 模型（需用户本地已安装）
- 通过 Ollama REST API 交互，无需额外 SDK
- 使用 `think: False` 禁用思考模式，避免 thinking 占满输出
- 请求超时设为 300 秒（大 README 可能需要较长生成时间）
- 失败时重试最多 3 次，每次重试前检测 Ollama 可用性
- Ollama 为本地服务，HTTP 请求显式绕过系统代理

## 7. 错误处理

| 场景                     | 处理方式                                  |
|--------------------------|-------------------------------------------|
| GitHub API 速率限制      | 跳过当前查询并提示配置 GITHUB_TOKEN       |
| 项目无 README 文件       | 跳过摘要，仅保留项目基本信息              |
| Ollama 服务不可用        | 重试 3 次，每次前检测可用性               |
| 网络请求超时             | 重试最多 3 次后跳过                       |
| README 内容过长          | 截取前 3000 字符送入 Ollama               |
| Ollama 连接中断          | 等待 5s 后重试，最多 3 次                 |

## 8. 使用方式

```bash
cd /home/wzl/Documents/qoder_project/github-new-stars

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 填入 GITHUB_TOKEN 等

# 运行
python main.py
```

输出文件位于 `output/2026-04-23.txt`。
