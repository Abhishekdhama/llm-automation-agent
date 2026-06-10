# 🤖 LLM Automation Agent

An AI-powered automation agent built with **FastAPI** that accepts natural language tasks, interprets them using **GPT-4o-mini** (via AI Proxy), and executes them automatically. Simply describe what you want done in plain English, and the agent handles the rest.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Task | Example Command | Description |
|------|----------------|-------------|
| 📅 **Count Weekdays** | `"Count Mondays in the dates file"` | Counts occurrences of a specific weekday in `dates.txt` |
| 📦 **Install Packages** | `"Install the numpy package"` | Fuzzy-matches package names against PyPI and installs |
| 📊 **Sort CSV** | `"Sort data.csv by column 2"` | Sorts CSV files by a specified column |
| 📧 **Extract Emails** | `"Extract emails from contacts.txt"` | Finds and extracts email addresses from text files |
| 🔄 **Convert to JSON** | `"Convert data.csv to JSON"` | Converts CSV or text files to JSON format |
| 📝 **Word Count** | `"Count words in notes.txt"` | Counts words, lines, and characters in a file |

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│              │     │                  │     │                   │
│   Client     │────▶│  FastAPI Server  │────▶│  GPT-4o-mini      │
│  (HTTP)      │     │                  │     │  (AI Proxy)       │
│              │◀────│  POST /run       │◀────│                   │
│              │     │  GET  /read      │     └───────────────────┘
│              │     │  GET  /health    │
└──────────────┘     │                  │     ┌───────────────────┐
                     │  Task Router     │────▶│  Task Handlers    │
                     │  (keyword match) │     │  • count_days     │
                     │                  │     │  • install_pkg    │
                     └──────────────────┘     │  • sort_csv       │
                                              │  • extract_email  │
                                              │  • convert_json   │
                                              │  • count_words    │
                                              └───────────────────┘
```

### Request Flow

1. Client sends a natural language task via `POST /run`
2. Task is forwarded to **GPT-4o-mini** for interpretation
3. The **Task Router** matches keywords to determine which handler to invoke
4. The appropriate **Task Handler** executes the operation
5. Results are returned alongside the LLM's interpretation

---

## 📋 Prerequisites

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **AI Proxy Token** — Required for LLM features
- **Docker** *(optional)* — For containerized deployment

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Abhishekdhama/llm-automation-agent.git
cd llm-automation-agent
```

### 2. Set Up Environment

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your token
# AIPROXY_TOKEN=your_actual_token_here
```

### 4. Generate Package Cache *(optional, for install tasks)*

```bash
python getpackages.py
```

> **Note:** This fetches all PyPI package names (~550K+) and saves them locally for fuzzy matching. It only needs to be run once.

### 5. Run the Server

```bash
# Development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server will be available at **http://localhost:8000**

---

## 🐳 Docker

### Build and Run

```bash
# Build the image
docker build -t llm-automation-agent .

# Run the container
docker run -d \
  --name llm-agent \
  -p 8000:8000 \
  -e AIPROXY_TOKEN=your_token_here \
  -v ./data:/data \
  llm-automation-agent
```

### Docker Compose *(optional)*

```yaml
version: '3.8'
services:
  agent:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/data
    restart: unless-stopped
```

---

## 📡 API Documentation

### Interactive Docs

Once the server is running, visit:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoints

#### `GET /health`

Health check endpoint.

```bash
curl http://localhost:8000/health
```

```json
{ "status": "healthy" }
```

---

#### `GET /read?path=/data/dates.txt`

Read the contents of a file (restricted to `/data` directory).

```bash
curl "http://localhost:8000/read?path=/data/dates.txt"
```

```json
{
  "content": "2024-01-01\n2024-02-14\n..."
}
```

| Status | Description |
|--------|-------------|
| `200` | File contents returned |
| `403` | Path outside allowed directory |
| `404` | File not found |

---

#### `POST /run`

Execute a natural language task.

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Count Mondays in the dates file"}'
```

```json
{
  "status": "success",
  "task_output": "Based on the dates file, I count the Mondays...",
  "detail": "Counted 2 occurrence(s) of 'monday'."
}
```

**More examples:**

```bash
# Install a package
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Install the requests package"}'

# Sort a CSV file
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Sort data.csv by column 1"}'

# Extract emails
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Extract emails from contacts.txt"}'

# Convert to JSON
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Convert data.csv to JSON"}'

# Word count
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "Count words in notes.txt"}'
```

| Status | Description |
|--------|-------------|
| `200` | Task executed successfully |
| `400` | Invalid input or unknown weekday |
| `404` | Referenced file not found |
| `500` | Server error or missing token |
| `504` | Package installation timed out |

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AIPROXY_TOKEN` | ✅ Yes | — | AI Proxy authentication token |
| `DATA_DIR` | No | `/data` | Directory for data files |

---

## 📁 Project Structure

```
llm-automation-agent/
├── main.py               # FastAPI app, endpoints, task routing
├── functions.py           # Core task handler functions
├── getpackages.py         # PyPI package list fetcher/cacher
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── .gitignore             # Git exclusion rules
├── .dockerignore          # Docker build exclusion rules
├── LICENSE                # MIT License
├── README.md              # This file
├── data/                  # Runtime data directory
│   ├── dates.txt          # Sample dates for weekday counting
│   └── content.txt        # Sample content file
└── tests/                 # Test suite
    ├── __init__.py
    └── test_ai_proxy.py   # AI Proxy integration tests
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=.

# Run specific test
pytest tests/test_ai_proxy.py -v -k test_add_numbers
```

> **Note:** Tests that call the AI Proxy API require a valid `AIPROXY_TOKEN`. Tests are automatically skipped if the token is not set.

---

## 🔧 Adding New Task Types

To add a new task handler:

1. **Define the function** in `functions.py`:
   ```python
   def my_new_task(param: str) -> str:
       """Description of what this task does."""
       # Implementation here
       return "result"
   ```

2. **Add the routing logic** in `main.py` inside `run_task()`:
   ```python
   elif "keyword" in task_lower:
       result = my_new_task(param)
       return TaskResponse(
           status="success",
           task_output=task_output,
           detail=result,
       )
   ```

3. **Import the function** at the top of `main.py`:
   ```python
   from functions import my_new_task
   ```

4. **Add a test** in `tests/` *(optional but recommended)*

---

## 🔒 Security Notes

- **No hardcoded secrets** — All tokens are loaded from environment variables
- **Path traversal protection** — File reads are restricted to the data directory using `os.path.realpath()`
- **Non-root Docker** — Container runs as an unprivileged user
- **Input validation** — Request bodies are validated using Pydantic models
- **Subprocess safety** — Package installations use list arguments (no shell injection)

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Abhishek Dhama**  
IIT Madras BS Degree Programme

---

*Built with ❤️ using FastAPI and GPT-4o-mini*
