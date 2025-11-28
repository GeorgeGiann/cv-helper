# CV-Enhancer Multi-Agent System
## Google/Kaggle Agents Web Seminar Project

A production-grade multi-agent system using **ADK**, **A2A communication**, and **MCP tools** to create job-tailored CVs with **intelligent template selection** and **professional DOCX output**.

## 🎯 Key Features

- ✅ **A2A Communication**: Proper Agent-to-Agent messaging
- ✅ **MCP Tools**: PDF parser, storage, vector DB, web fetcher
- ✅ **Template-Based CV Generation**: Intelligent template selection based on job position ⭐ NEW
- ✅ **Professional DOCX Output**: Word/Google Docs compatible documents ⭐ NEW
- ✅ **11 Template Categories**: Executive, Engineering, Design, Data, and more
- ✅ **Multiple LLM Support**: Ollama (free), OpenAI, Anthropic, Gemini
- ✅ **Cost**: $0 with Ollama or free tier LLMs

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Ollama (or use OpenAI/Anthropic/Gemini)
ollama serve
ollama pull llama3:8b

# 3. Configure
cp .env.local .env

# 4. Run test pipeline
python test_pipeline.py
```

### What Gets Generated

The pipeline produces:
- **Primary Output**: Professional `.docx` file (editable in Word/Google Docs)
- **Reference**: `.json` file (JSON Resume format)

Template is automatically selected based on job position in the advertisement!

## 📊 How It Works

```
CV (PDF/Text) + Job Ad → Pipeline → Tailored .docx CV
```

**5-Step Pipeline:**
1. **CV Ingestion**: Parse CV → JSON Resume format
2. **Job Understanding**: Extract requirements + job position
3. **User Interaction**: Collect missing info (optional)
4. **Knowledge Storage**: Store profile + embeddings
5. **CV Generator**:
   - Select template based on job position ⭐
   - Tailor content with LLM
   - Generate professional .docx file ⭐

## 🎨 Template Categories

The system automatically selects the appropriate template based on job title/position:

| Template | Job Types |
|----------|-----------|
| **Executive** | CEO, CTO, Director, VP |
| **Engineering** | Software Engineer, Developer, DevOps |
| **Management** | Manager, Lead, Supervisor |
| **Design** | Designer, UX/UI, Creative |
| **Data** | Data Scientist, Analyst, ML Engineer |
| **Marketing** | Marketing, SEO, Growth |
| **Sales** | Sales, Account Executive |
| **Finance** | Accountant, Financial Analyst |
| **Operations** | Operations Manager, Logistics |
| **HR** | Human Resources, Recruiter |
| **Consulting** | Consultant, Advisor, Strategist |

If no match is found, defaults to "professional" template.

## 📚 Documentation

- [Getting Started](GETTING_STARTED.md) - Detailed setup guide
- [Agent Architecture](documentation/cv_enhancement_architecture.md) - System architecture and agent design
- [JSON Resume Schema](documentation/json_resume_schema.md) - CV data format specification
- [Troubleshooting Guide](documentation/troubleshooting_guide.md) - Common issues and solutions

## 🛠️ Technical Stack

| Component | Technology |
|-----------|-----------|
| **CV Parsing** | pdfplumber |
| **Document Generation** | python-docx ⭐ |
| **LLM Providers** | Ollama, OpenAI, Anthropic, Gemini |
| **Vector Database** | FAISS (local), Vertex AI (cloud) |
| **Storage** | Local files, Google Cloud Storage |
| **A2A Communication** | Custom BaseAgent framework |

## 📦 Key Dependencies

```
python-docx>=1.1.0          # DOCX generation
pdfplumber>=0.10.3          # PDF parsing
faiss-cpu>=1.7.4            # Vector database
sentence-transformers       # Embeddings
openai / anthropic          # LLM providers
google-cloud-aiplatform     # Gemini
```
## 🧪 Testing

```bash
# Run the complete pipeline
python test_pipeline.py
```

This will:
- Initialize all 6 agents
- Process a sample CV and job advertisement
- Generate a tailored `.docx` CV file
- Save JSON Resume for reference
- Demonstrate A2A communication

## 📁 Project Structure

```
cv-helper/
├── src/
│   ├── agents/              # 6 ADK agents
│   │   ├── orchestrator.py
│   │   ├── cv_ingestion.py
│   │   ├── job_understanding.py
│   │   ├── user_interaction.py
│   │   ├── knowledge_storage.py
│   │   └── cv_generator.py  ⭐ Enhanced with template support
│   ├── llm/                 # LLM providers
│   ├── storage/             # Storage backends
│   └── tools/               # MCP tools
├── data/
│   └── outputs/             # Generated .docx and .json files
├── documentation/                # Documentation
├── test_pipeline.py         # Demo script
└── requirements.txt         # Dependencies
```
---


**Enhanced with intelligent template selection and professional DOCX generation!**
