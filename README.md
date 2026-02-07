# Prod Scout - Product Insight Agent

Prod Scout is a product intelligence reconnaissance agent focused on the Data & AI domain (extensible to other fields). Based on RSS and LLM technologies, it automatically fetches information from various sources such as X (Twitter), WeChat Official Accounts, YouTube, and blogs. It utilizes Large Language Models for deep analysis and structured organization, ultimately generating high-quality Markdown intelligence weekly reports.

## ✨ Features

- **Multi-source RSS Fetching**: Supports WeChat Official Accounts, X (Twitter), YouTube, Blogs/News, etc.
- **Smart Classification**: Automatically groups and organizes content by source type.
- **Deep Content Parsing**: Automatically extracts blog links and YouTube videos from tweets or articles for recursive fetching.
- **Intelligent Video Transcription**: Integrates Whisper model to convert embedded videos in X or YouTube videos into text, and uses DeepSeek/LLM for context-aware subtitle optimization.
- **LLM Intelligent Organization**: Calls LLM APIs to structurally summarize fetched content.
- **Markdown Reports**: Automatically generates clear and structured Markdown weekly reports.
- **Flexible Configuration**: Supports custom LLM APIs, time ranges, RSS sources, etc.

## 📁 Project Structure

```
prod-scout/
├── config.ini              # Configuration file (LLM API, subscription sources, etc.)
├── rsshub-docker.env       # RSSHub Docker environment variables (for fetching X, requires TWITTER_AUTH_TOKEN, etc.)
├── native_scout/           # [Python Native Version] Intelligence Scout (Crawler + Organizer)
│   ├── pipeline.py         # Main pipeline entry point
│   ├── stages/             # Independent pipeline stages (Fetch, Enrich, Organize, Write)
│   └── utils/              # General utilities
│       ├── web_crawler.py      # Web page fetching + Screenshot/PDF
│       └── content_fetcher.py  # Deep content extraction and embedded resource handling
├── daft_scout/             # [Daft Version] High-performance distributed Scout
│   └── pipeline.py         # Daft data flow entry point
├── video_scribe/           # [General] Video transcription and subtitle optimization module
│   ├── core.py             # Core logic for transcription
│   ├── optimize.py         # LLM subtitle optimization and alignment
│   └── run_video_scribe.py # Standalone execution script
├── data/                   # Output directory (reports, screenshots, transcripts, etc.)
└── README.md
```

## 🚀 Quick Start

### 0. Configure Python Environment (Using uv)

It is recommended to use [uv](https://github.com/astral-sh/uv) to manage the Python environment, as it is faster and simpler than traditional pip/venv.

#### Install uv

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Create Project Virtual Environment

```bash
# Enter project directory
cd prod-scout

# Create virtual environment (automatically downloads and installs Python)
uv venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate
```

> 💡 **Tip**: uv will automatically detect and download a suitable Python version, no need to manually install Python. To specify a version, use `uv venv --python 3.12`.

### 1. Install Dependencies

```bash
# Install dependencies using uv (recommended, faster)
uv pip install feedparser openai python-dateutil beautifulsoup4 selenium webdriver-manager

# Or using traditional pip
pip install feedparser openai python-dateutil beautifulsoup4 selenium webdriver-manager
```

### 2. Configure LLM API

Create a `config.ini` file:

```ini
[llm]
api_key = your_api_key_here
base_url = https://api.openai.com/v1
model = gpt-4o
```

Supports OpenAI, DeepSeek, Moonshot, Doubao, and other OpenAI API compatible services.

### 3. Configure RSS Sources

Configure accounts to fetch in `config.ini`:

```ini
[rsshub]
# RSSHub service address
base_url = http://127.0.0.1:1200

[weixin_accounts]
# WeChat Official Accounts list
# Format: Display Name = RSS Address
TencentTech = https://wechat2rss.xlab.app/feed/xxx.xml

[x_accounts]
# X (Twitter) Accounts list
# Format: Display Name = Account ID
karpathy = karpathy
OpenAI = OpenAI
Anthropic = AnthropicAI
```

### 4. Run

```bash
cd native_scout
python pipeline.py
```

The report will be saved to `data/rss_report_YYYYMMDD_HHMMSS.md`.

---

## 🎥 Video Transcription & Deep Analysis

Prod Scout includes a powerful `video_scribe` module for deep content mining:

### 1. Automated Video Scribe
When the crawler finds a YouTube link in a tweet or article, it automatically triggers the following workflow:
1.  **Auto Download**: Extracts audio stream (no need to download the full video).
2.  **Whisper Transcription**: Uses `faster-whisper` model (supports GPU acceleration) to convert audio to subtitles.
3.  **Context-Aware Optimization**: Uses the original text of the tweet/article as **context** to guide the LLM (e.g., DeepSeek) in optimizing the subtitles.
    *   *Example: If "Pythagorean theorem" is mentioned in the tweet, the LLM will use this information to correct any misidentified mathematical terms in the subtitles.*
    *   Also removes filler words (um, uh, I mean) to generate fluent, article-like text.

### 2. Deep Link Extraction
In addition to videos, the crawler also automatically identifies and recursively fetches embedded blog links:
- Automatically filters out irrelevant social media links.
- Uses Selenium to dynamically render target web pages.
- Extracts main content and merges it into the intelligence report.

### 3. Standalone Use of Video Scribe
You can also use this module independently to process local files or URLs:

```bash
# Enter video_scribe directory
cd video_scribe

# Run the tool
python run_video_scribe.py
```

> **Dependency Note**: `video_scribe` will automatically download required dependencies (such as the `faster-whisper` program and models) on its first run, no manual configuration needed. Windows users please ensure GPU drivers are installed for optimal performance.

---

## 🐦 Fetching X (Twitter) using RSSHub

X needs to be fetched via a self-hosted RSSHub service. Here are the configuration steps:

### Step 1: Get Your X Account Cookie

RSSHub needs to simulate your identity to access X. You need to extract a few key parameters from your browser.

1. Open x.com in Chrome/Edge browser and log in to your account.
2. Press `F12` to open Developer Tools, switch to the **Network** tab.
3. Refresh the page and click on any request in the list (usually `HomeTimeline` or `guide.json`).
4. In the **Headers** -> **Request Headers** section on the right, find the `cookie` field.
5. Copy the following two values (make sure not to include the semicolon):
   - `auth_token`
   - `ct0` (sometimes called `x-csrf-token`)

### Step 2: Configure Environment Variables

Create an `rsshub-docker.env` file:

```env
TWITTER_AUTH_TOKEN=your_auth_token
TWITTER_CT0=your_ct0
XCSRF_TOKEN=your_ct0
```

### Step 3: Run RSSHub Container

```bash
docker run -d --name rsshub -p 1200:1200 --env-file rsshub-docker.env diygod/rsshub:chromium-bundled
```

### Step 4: Use RSS Source

After configuration, you can use RSS sources in the following format:

```
http://127.0.0.1:1200/twitter/user/{username}
```

Example: `http://127.0.0.1:1200/twitter/user/karpathy`

---

## 📝 Output Example

```markdown
# 🌍 Data&AI Intelligence Weekly Report (Automated RSS Crawler)

## 📂 weixin

### TencentTech

| Date | Event | Key Info | Original Link | Details | Supplement | External Links | Category | Domain |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-01-15 | Tencent Engineers Share AI Coding Tips | 1. Content aggregates practical experience from 10 Tencent engineers.<br>2. Core advice: use high-quality models, prioritize Commit backups, etc. | [Link](https://mp.weixin.qq.com/s?...) | Article discusses "failures" and tips in AI programming practice... | - | - | Opinion | AI Coding (IDE) |
| 2026-01-13 | Tencent Open Sources AngelSlim Toolkit | 1. Hunyuan team upgrades and open sources AngelSlim model compression toolkit.<br>2. Can increase model inference speed by up to 1.4-1.9x. | [Link](https://mp.weixin.qq.com/s?...) | Article announces major upgrade of Tencent AngelSlim toolkit... | - | - | Tech Release | LLM Tech & Product |

---

## 📂 X

### AI Researcher (Andrej)

| Date | Event | Key Info | Original Link | Details | Supplement | External Links | Category | Domain |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-02-01 | Analysis of New LLM Training Paradigm | 1. Video core point: SFT data quality is more important than quantity.<br>2. Deep fetch: Blog post details "Token Efficiency".<br>3. Mentions future trend is small models + high quality data. | [Link](https://x.com/karpathy/...) | Andrej deeply analyzes data strategy in current LLM training SFT stage... | **[Video Analysis]** Andrej explains in detail in the video... (based on Video Scribe transcription)<br>**[Blog Summary]** Attached article delves into... | [karpathy.ai](https://karpathy.ai) | Deep Insight | LLM Tech & Product |

### MLflow

| Date | Event | Key Info | Original Link | Details | Supplement | External Links | Category | Domain |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-01-16 | Podcast Released, Discussing MLflow Evolution to GenAI Platform | 1. Video content: MLflow team discusses evolution to AI Agent platform.<br>2. Key challenges: Evaluation and Governance are current pain points for enterprise adoption. | [Link](https://x.com/MLflow/...) | MLflow team released a new podcast episode focusing on... | **[Video Intelligent Transcription]** Podcast detailed discussion...<br>MLflow isn't just for traditional data scientists anymore... | - | Tech Release | AI Platform & Framework |

---
```

## 📚 More RSS Sources

- RSSHub Documentation: https://docs.rsshub.app/
- WeChat2RSS: https://wechat2rss.xlab.app/

## 📄 License

MIT
