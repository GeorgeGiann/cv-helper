# CV-Enhancer Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: Skills Not Populating in DOCX

**Symptoms:**
- Skills data exists in JSON but doesn't appear in generated DOCX
- Skills section is empty or missing in Word document

**Root Cause:**
The `_tailor_cv` method in cv_generator uses an LLM that may change field names during CV tailoring.

**Solution:**
1. Check skill format in `cv_data`:
```python
logger.info(f"Skills format: {cv_data.get('skills', [])}")
```

2. Ensure skills use correct format:
```json
{"name": "Category", "keywords": ["skill1", "skill2"]}
```

3. Verify LLM prompt enforces format:
   - Prompt in [cv_generator.py:201-273](src/agents/cv_generator.py#L201-L273)
   - Contains explicit field name rules

4. Check validation logic catches format errors:
   - Validation in [cv_generator.py:284-330](src/agents/cv_generator.py#L284-L330)
   - Falls back to original data if format invalid

**Files to Check:**
- [src/agents/cv_generator.py](src/agents/cv_generator.py) - `_tailor_cv` method
- [src/agents/cv_ingestion.py](src/agents/cv_ingestion.py) - Skills conversion

### Issue 2: Format Inconsistency Through Pipeline

**Symptoms:**
- Data format changes between pipeline stages
- Field names don't match expected schema
- Validation errors

**Root Cause:**
Extractor uses different format than profile JSON format.

**Conversion Points:**
1. **Extractor → Profile** (cv_ingestion.py)
   - Skills: `category/items` → `name/keywords`
   - Projects: `highlights/description` → `description[]`
   - Certificates: `issuer/date` → `details[]`

2. **Profile → Tailored** (cv_generator.py)
   - LLM may change formats
   - Validation catches and corrects

3. **Tailored → DOCX** (cv_generator.py)
   - Expects profile format
   - Renders to Word document

**Solution:**
Add logging at each conversion point:
```python
logger.info(f"Before conversion: {data}")
logger.info(f"After conversion: {converted_data}")
```

### Issue 3: LLM Provider Errors

**Symptoms:**
- `LLM conversion failed` errors
- Pipeline falls back to basic conversion
- Missing tailored content

**Common Causes:**
1. Invalid API key
2. Rate limiting
3. Network issues
4. Invalid model name

**Solution:**
1. Check `.env` configuration:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
```

2. Test LLM connection:
```python
from src.config import get_llm_provider, get_config
config = get_config()
llm = get_llm_provider(config)
result = await llm.complete("Test")
```

3. Check logs for specific error:
```bash
grep "LLM" *.log
```

4. Verify fallback works:
   - System should continue with basic conversion
   - Check output quality

### Issue 4: PDF Parsing Failures

**Symptoms:**
- `PDF parsing failed` errors
- Empty text extraction
- Malformed output

**Common Causes:**
1. Corrupted PDF
2. Scanned image PDFs (need OCR)
3. Protected/encrypted PDFs
4. Unsupported PDF version

**Solution:**
1. Enable OCR for scanned PDFs:
```python
config = {"ocr_enabled": True}
```

2. Try converting to text first:
```bash
pdftotext cv.pdf cv.txt
python test_pipeline.py --cv cv.txt
```

3. Check PDF validity:
```bash
pdfinfo cv.pdf
```

4. Use alternative PDF library:
   - Install pdfplumber: `pip install pdfplumber`
   - Modify pdf_parser/main.py

### Issue 5: Vector Database Errors

**Symptoms:**
- ChromaDB initialization errors
- Embedding creation failures
- Search not working

**Common Causes:**
1. Missing dependencies
2. Incompatible ChromaDB version
3. Corrupted database files
4. Permission issues

**Solution:**
1. Reinstall ChromaDB:
```bash
pip uninstall chromadb
pip install chromadb==0.4.18
```

2. Clear vector database:
```bash
rm -rf ./data/vector_db/
```

3. Verify embeddings model:
```python
from chromadb.utils import embedding_functions
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
```

### Issue 6: DOCX Generation Formatting Issues

**Symptoms:**
- Incorrect formatting in Word document
- Missing sections
- Layout problems

**Common Causes:**
1. Invalid template
2. Missing python-docx features
3. Long content causing pagination issues

**Solution:**
1. Check template exists:
```bash
ls templates/cv_template.docx
```

2. Verify python-docx version:
```bash
pip install --upgrade python-docx
```

3. Test with minimal data:
```python
minimal_cv = {
    "basics": {"name": "Test", "email": "test@test.com"},
    "work": [],
    "skills": []
}
```

### Issue 7: Missing Projects or Certificates

**Symptoms:**
- Projects section not extracted
- Certificates section empty
- Data lost in pipeline

**Root Cause:**
Projects and certificates extraction may not be enabled.

**Solution:**
1. Verify extraction in cv_ingestion.py:
   - [Line 248-279](src/agents/cv_ingestion.py#L248-L279): Projects conversion
   - [Line 281-313](src/agents/cv_ingestion.py#L281-L313): Certificates conversion

2. Check extractor finds sections:
```python
sections = extractor.extract_sections(text)
logger.info(f"Sections found: {sections.keys()}")
```

3. Verify format conversion:
```python
logger.info(f"Projects: {sections.get('projects', [])}")
logger.info(f"Certificates: {sections.get('certifications', [])}")
```

## Debugging Techniques

### 1. Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Inspect Intermediate Data
```python
# After each agent call
logger.info(f"Agent result: {json.dumps(result, indent=2)}")
```

### 3. Test Individual Agents
```python
# Test CV ingestion alone
agent = CVIngestionAgent(llm_provider, storage)
result = await agent.parse_cv("test.pdf")
```

### 4. Validate Data Format
```python
# Check against schema
from src.utils.validation import validate_json_resume
errors = validate_json_resume(cv_data)
```

### 5. Compare Pipeline Stages
```bash
# Save data at each stage
echo $cv_data > stage1_ingestion.json
echo $tailored_cv > stage2_tailored.json
diff stage1_ingestion.json stage2_tailored.json
```

## Performance Issues

### Slow Pipeline Execution

**Causes:**
1. Large PDF processing
2. LLM API latency
3. Vector database indexing

**Solutions:**
1. Enable caching for LLM calls
2. Use faster embedding model
3. Parallelize independent operations
4. Use local LLM for development

### High Memory Usage

**Causes:**
1. Large vector database
2. Multiple PDF files in memory
3. ChromaDB memory leaks

**Solutions:**
1. Process PDFs in streaming mode
2. Clear vector DB periodically
3. Use batch processing for multiple CVs

## Error Messages Reference

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| `PDF parsing failed` | Corrupted PDF | Try text format or enable OCR |
| `LLM conversion failed` | API error | Check API key and network |
| `Vector DB initialization failed` | Missing dependencies | Reinstall chromadb |
| `Format validation failed` | Invalid JSON structure | Check field names |
| `Agent communication failed` | A2A messaging error | Check agent registration |
| `DOCX generation failed` | Template or data issue | Verify template and data format |

## Getting Help

1. Check logs in `./data/outputs/` directory
2. Review [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. Examine [cv_enhancement_architecture.md](.context/cv_enhancement_architecture.md)
4. Test with sample data: `python test_pipeline.py`
5. Enable debug logging for detailed traces

## Useful Commands

```bash
# Run full pipeline with logging
python test_pipeline.py --cv my_cv.pdf 2>&1 | tee debug.log

# Test specific agent
python -m src.agents.cv_ingestion

# Validate JSON format
python -c "import json; json.load(open('data/profiles/profile.json'))"

# Check dependencies
pip list | grep -E "openai|anthropic|chromadb|pypdf|docx"

# Clear caches
rm -rf __pycache__ .pytest_cache data/vector_db/
```
