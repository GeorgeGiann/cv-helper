# Getting Started with CV-Enhancer

Quick start guide for local development and testing.

## Prerequisites

- Python 3.11+
- One of the following LLM options:
  - **Ollama** (FREE, recommended for local dev)
  - **OpenAI API key**
  - **Anthropic API key**

## Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### 2. Choose Your LLM

#### Option A: Ollama (FREE - Recommended)

```bash
# Install Ollama from https://ollama.ai
# Then pull a model:
ollama serve
ollama pull llama3:8b
```

#### Option B: OpenAI

Get API key from https://platform.openai.com/api-keys

#### Option C: Anthropic Claude

Get API key from https://console.anthropic.com/

### 3. Configure Environment

```bash
# Copy example config
cp .env.local .env

# Edit .env and set your LLM choice
# For Ollama (default):
LLM_PROVIDER=ollama
LLM_MODEL=llama3:8b

# For OpenAI:
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=your-key-here

# For Anthropic:
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-5-haiku-20241022
# LLM_API_KEY=your-key-here
```

### 4. Run Test Pipeline

```bash
python test_pipeline.py
```

This will:
- Initialize all 6 ADK agents
- Demonstrate A2A communication
- Process a sample CV against a job description
- Generate tailored CV outputs

## Expected Output

```
======================================================================
CV-Enhancer Multi-Agent System - Pipeline Test
======================================================================

📋 Step 1: Loading Configuration...
   Mode: local
   LLM Provider: ollama
   LLM Model: llama3:8b
   Storage: local
   ✓ Configuration loaded

🔧 Step 2: Initializing Components...
   ✓ Storage backend: LocalStorage
   ✓ LLM provider: OllamaProvider
   ✓ Model: llama3:8b

🤖 Step 3: Initializing Orchestrator Agent...
   ✓ Orchestrator initialized
   ✓ Registered 5 agents for A2A communication:
      - cv_ingestion
      - job_understanding
      - user_interaction
      - knowledge_storage
      - cv_generator

...

🎉 PIPELINE COMPLETED SUCCESSFULLY!
======================================================================

📊 Results:
   Session ID: session_abc123
   Match Score: 85.5%
   Steps Completed: cv_ingestion → gap_analysis → knowledge_storage → cv_generation

📁 Generated Files:
   - MARKDOWN: ./data/outputs/John_Doe_CV_20251123.md
   - JSON: ./data/outputs/John_Doe_CV_20251123.json
```

## Project Structure

```
cv-helper/
├── src/
│   ├── agents/           # 6 ADK agents with A2A
│   │   ├── orchestrator.py      ← Master coordinator
│   │   ├── cv_ingestion.py      ← PDF parsing
│   │   ├── job_understanding.py ← Job analysis
│   │   ├── user_interaction.py  ← Q&A
│   │   ├── knowledge_storage.py ← Data persistence
│   │   └── cv_generator.py      ← CV generation
│   ├── tools/            # MCP tools
│   ├── llm/              # LLM providers
│   ├── storage/          # Storage backends
│   └── config.py         # Configuration
├── data/                 # Local data directory
├── schemas/              # JSON schemas
├── .env                  # Your configuration
└── test_pipeline.py      # Test script
```

## Understanding A2A Communication

The orchestrator coordinates all agents via `call_agent()`:

```python
# Example: Orchestrator calls CV Ingestion Agent
cv_result = await self.call_agent(
    agent="cv_ingestion",
    action="parse_cv",
    params={"file_path": "cv.pdf"}
)

# Then calls Job Understanding Agent
gap_result = await self.call_agent(
    agent="job_understanding",
    action="analyze_gap",
    params={"cv_data": cv_result["data"], "job_ad": job_text}
)
```

All agents communicate this way - no direct method calls!

## Next Steps

### For Local Development:
1. Create your own CV PDF
2. Modify `test_pipeline.py` to use your CV
3. Try different job descriptions
4. Experiment with different LLM providers

### For Kaggle Submission:
1. Upload source code as Kaggle dataset
2. Configure `.env.kaggle` for Gemini Flash (FREE)
3. Run via command line: `python test_pipeline.py --cv your_cv.pdf --job job_ad.txt`
4. **Note**: `notebooks/kaggle_submission.ipynb` is WIP and not required for submission

## Troubleshooting

### "No LLM provider configured"
- Make sure `.env` file exists
- Check LLM provider is set correctly
- For Ollama, ensure service is running: `ollama serve`

### "PDF not found"
- Script creates a test CV automatically
- Check `./data/uploads/test_cv.txt` exists

### "Module not found"
- Run `pip install -r requirements.txt`
- Make sure you're in the project root directory

### Ollama connection errors
```bash
# Check Ollama is running
ollama list

# Restart if needed
ollama serve
```

## Cost Information

- **Local Development**: $0 (use free Ollama models)
- **Kaggle Deployment**: $0 (free Gemini Flash + GCP free tier)

## Support

- See [documentation/](documentation/) for detailed documentation:
  - [Agent Architecture](documentation/cv_enhancement_architecture.md)
  - [JSON Resume Schema](documentation/json_resume_schema.md)
  - [Troubleshooting Guide](documentation/troubleshooting_guide.md)
- Review agent code in [src/agents/](src/agents/) for examples

---

**Ready to enhance CVs with AI agents! 🚀**
