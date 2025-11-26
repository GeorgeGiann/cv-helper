# CV Enhancement System - Architecture Overview

## System Purpose
Multi-agent system for CV/resume enhancement using ADK-compatible agent architecture with A2A (Agent-to-Agent) communication.

## Core Agents

### 1. Orchestrator Agent
- **Role**: Master coordinator
- **Responsibilities**:
  - Manages complete pipeline workflow
  - Coordinates A2A communication between all agents
  - Handles session state and error recovery
  - Ensures proper sequencing of operations

### 2. CV Ingestion Agent
- **Role**: CV parsing and extraction
- **Responsibilities**:
  - Parse PDF and text CV files
  - Extract structured data (contact, work, education, skills, projects, certificates)
  - Convert to JSON Resume format
  - Validate data completeness

### 3. Job Understanding Agent
- **Role**: Job analysis and gap detection
- **Responsibilities**:
  - Parse job advertisements (text or URL)
  - Extract job requirements and qualifications
  - Perform gap analysis against CV
  - Identify missing skills and experiences
  - Generate recommendations

### 4. User Interaction Agent
- **Role**: Interactive information gathering
- **Responsibilities**:
  - Collect additional information for identified gaps
  - Generate targeted questions
  - Update CV with user responses
  - Provide conversational interface

### 5. Knowledge Storage Agent
- **Role**: Data persistence and retrieval
- **Responsibilities**:
  - Store CV profiles with vector embeddings
  - Store sessions and interaction history
  - Enable semantic search across CVs
  - Support profile versioning

### 6. CV Generator Agent
- **Role**: Output generation
- **Responsibilities**:
  - Tailor CV for specific job requirements
  - Generate DOCX formatted documents
  - Export JSON Resume format
  - Apply formatting and styling

## Data Flow

```
1. User uploads CV + Job Ad
   ↓
2. Orchestrator initiates pipeline
   ↓
3. CV Ingestion: Parse CV → JSON Resume
   ↓
4. Job Understanding: Analyze job → Gap analysis
   ↓
5. User Interaction: Collect missing info (if gaps exist)
   ↓
6. Knowledge Storage: Store profile + session
   ↓
7. CV Generator: Generate tailored DOCX + JSON
   ↓
8. Return results to user
```

## A2A Communication Pattern

All inter-agent communication uses the `call_agent()` method:

```python
result = await orchestrator.call_agent(
    agent="cv_ingestion",
    action="parse_cv",
    params={"file_path": cv_file, "user_id": user_id}
)
```

## Key Design Principles

1. **Agent Autonomy**: Each agent is self-contained and independently testable
2. **A2A Messaging**: Structured communication via call_agent() method
3. **Error Resilience**: Graceful fallbacks and error handling
4. **Format Consistency**: Strict JSON Resume schema throughout pipeline
5. **Extensibility**: Easy to add new agents or capabilities

## Technology Stack

- **Language**: Python 3.8+
- **Async Framework**: asyncio
- **LLM Integration**: OpenAI, Anthropic, Google AI
- **Document Processing**: PyPDF2, python-docx
- **Vector Storage**: ChromaDB, FAISS
- **Storage Backend**: Local filesystem, cloud storage support

## Configuration

Supports multiple operational modes:
- **Local Development**: `.env.local` with local LLM
- **Cloud Deployment**: `.env.kaggle` for Kaggle/cloud environments
- **Testing**: `.env.example` as template

## Output Formats

### JSON Resume Format
Standard CV schema with sections:
- `basics`: Contact information
- `work`: Work experience
- `education`: Academic background
- `skills`: Technical and soft skills
- `projects`: Personal/professional projects
- `certificates`: Certifications and licenses

### DOCX Format
Professional formatted Word document with:
- Header with contact details
- Organized sections
- Bullet points for achievements
- Professional styling
