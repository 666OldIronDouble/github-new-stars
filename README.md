# GitHub New Stars

Automatically discover the hottest new GitHub repositories created each week and generate AI-powered summaries.

## Features

- **Weekly trending repos** — Fetches repos created in the past week, sorted by stars
- **AI-powered summaries** — Generates structured Chinese summaries (purpose, features, tech stack, target users)
- **Multiple AI backends** — Ollama, Google Gemini, SiliconFlow, DeepSeek, with graceful degradation
- **Zero-config by default** — Works out of the box even without any AI service installed
- **Dated reports** — Saves results as `output/YYYY-MM-DD.txt`

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run (degraded mode, no AI needed)
python main.py
```

That's it. Without any AI backend configured, the tool outputs repo lists with basic descriptions.

## AI Backend Configuration

Copy the example config and fill in your preferred backend:

```bash
cp .env.example .env
```

### Backend Priority

When `AI_BACKEND=auto` (default), backends are tried in this order:

| Priority | Backend | Requirement | Cost |
|----------|---------|-------------|------|
| 1 | Ollama | Local install + model | Free |
| 2 | Google Gemini | API key | Free tier (15 RPM) |
| 3 | SiliconFlow | API key | Free tier available |
| 4 | DeepSeek | API key | Low cost |
| 5 | Degraded mode | None | Free |

You can also force a specific backend:

```bash
# Use Gemini only
AI_BACKEND=gemini python main.py

# Skip AI entirely
AI_BACKEND=none python main.py
```

### Ollama (Local)

```env
AI_BACKEND=ollama
OLLAMA_MODEL=qwen3.5
OLLAMA_BASE_URL=http://localhost:11434
```

Requires [Ollama](https://ollama.com) running locally with the model installed (`ollama pull qwen3.5`).

### Google Gemini (Cloud, Free Tier)

```env
AI_BACKEND=gemini
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).

### SiliconFlow (Cloud, Free Tier)

```env
AI_BACKEND=siliconflow
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen3-8B
```

Get an API key at [SiliconFlow](https://cloud.siliconflow.cn/).

### DeepSeek (Cloud, Low Cost)

```env
AI_BACKEND=deepseek
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

Get an API key at [DeepSeek Platform](https://platform.deepseek.com/).

## Output Example

```
==================================================
GitHub 一周热门项目摘要报告
日期：2026-04-25
==================================================

1. 项目名: kyegomez/OpenMythos
   URL: https://github.com/kyegomez/OpenMythos
   Star数: 10003
   语言: Python
   ----------------------------------------
   基于公开文献和第一性原理构建的 Claude Mythos 架构理论复现项目...
   (AI generated summary with purpose, features, tech stack, target users)

2. 项目名: alchaincyf/huashu-design
   ...

==================================================
共 10 个项目
==================================================
```

## Optional Config

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | | GitHub personal access token (increases API rate limit) |
| `TOP_N` | `10` | Number of repos to fetch |

## Project Structure

```
github-new-stars/
├── main.py              # Entry point
├── config.py            # Configuration loader (.env)
├── github_fetcher.py    # GitHub Search API integration
├── summarizer.py        # Multi-backend AI summarizer
├── reporter.py          # Report formatting and file output
├── requirements.txt
├── .env.example
└── .gitignore
```

## How It Works

1. Queries GitHub Search API for repos created in the past week with `stars:>10`
2. Falls back to repos created in the past two weeks if needed
3. Fetches each repo's README via GitHub API
4. Sends README to the selected AI backend for summarization
5. Compiles all summaries into a dated report file

## License

MIT
