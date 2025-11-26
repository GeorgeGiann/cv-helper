# JSON Resume Schema - CV-Enhancer Format

## Overview
This document defines the canonical JSON Resume format used throughout the CV-Enhancer pipeline.

## Complete Schema

```json
{
  "basics": {
    "name": "string",
    "label": "string (optional)",
    "email": "string",
    "phone": "string",
    "url": "string (personal website)",
    "summary": "string (optional)",
    "location": {
      "address": "string (full address as single field)"
    },
    "profiles": [
      {
        "network": "string (e.g., LinkedIn, GitHub)",
        "username": "string (optional)",
        "url": "string"
      }
    ]
  },
  "work": [
    {
      "company": "string",
      "position": "string",
      "location": "string (optional)",
      "startDate": "YYYY-MM",
      "endDate": "YYYY-MM or null for current",
      "description": "string (optional)",
      "highlights": [
        "string (achievement/responsibility)"
      ]
    }
  ],
  "education": [
    {
      "institution": "string",
      "area": "string (field of study)",
      "studyType": "string (degree type)",
      "startDate": "YYYY-MM",
      "endDate": "YYYY-MM",
      "gpa": "string (optional)",
      "honors": "string (optional)"
    }
  ],
  "skills": [
    {
      "name": "string (category name)",
      "keywords": [
        "string (individual skill)"
      ]
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": [
        "string (description text)",
        "string (highlight 1)",
        "string (highlight 2)"
      ],
      "url": "string (optional)"
    }
  ],
  "certificates": [
    {
      "name": "string",
      "details": [
        "Issuer: string",
        "Date: YYYY-MM"
      ]
    }
  ]
}
```

## Field Name Rules (CRITICAL)

### Skills Section
- **MUST USE**: `name` and `keywords`
- **DO NOT USE**: `category`, `items`, `level`, `proficiency`

```json
// CORRECT
{"name": "Programming Languages", "keywords": ["Python", "Java"]}

// INCORRECT
{"category": "Programming", "items": ["Python", "Java"]}
{"name": "Python", "level": "Expert"}
```

### Projects Section
- **MUST USE**: `name` and `description` (array)
- **DO NOT USE**: `highlights`, `summary`, `technologies` as separate fields

```json
// CORRECT
{
  "name": "E-commerce Platform",
  "description": [
    "Built scalable platform",
    "Implemented payment gateway",
    "Achieved 99.9% uptime"
  ]
}

// INCORRECT
{
  "name": "E-commerce Platform",
  "summary": "Built scalable platform",
  "highlights": ["Implemented payment gateway"]
}
```

### Certificates Section
- **MUST USE**: `name` and `details` (array)
- **DO NOT USE**: `issuer`, `date`, `credential` as separate fields

```json
// CORRECT
{
  "name": "AWS Certified Solutions Architect",
  "details": [
    "Issuer: Amazon Web Services",
    "Date: 2023-06"
  ]
}

// INCORRECT
{
  "name": "AWS Certified Solutions Architect",
  "issuer": "Amazon Web Services",
  "date": "2023-06"
}
```

### Location Field
- **MUST USE**: `address` as single string
- **DO NOT USE**: Separate `city`, `state`, `country`, `postalCode` fields

```json
// CORRECT
{"location": {"address": "San Francisco, CA, USA"}}

// INCORRECT
{"location": {"city": "San Francisco", "state": "CA", "country": "USA"}}
```

## Format Conversion

### From Extractor to Profile Format

#### Skills Conversion
```python
# Extractor output
{"category": "Programming Languages", "items": ["Python", "Java"]}

# Convert to profile format
{"name": "Programming Languages", "keywords": ["Python", "Java"]}
```

#### Projects Conversion
```python
# Extractor output
{
  "name": "Project X",
  "description": "Main description",
  "highlights": ["Achievement 1", "Achievement 2"],
  "technologies": ["Python", "React"],
  "url": "https://example.com"
}

# Convert to profile format
{
  "name": "Project X",
  "description": [
    "Main description",
    "Achievement 1",
    "Achievement 2"
  ],
  "url": "https://example.com"
}
```

#### Certificates Conversion
```python
# Extractor output
{
  "name": "AWS Certification",
  "issuer": "Amazon",
  "date": "2023-06",
  "credential": "ABC123"
}

# Convert to profile format
{
  "name": "AWS Certification",
  "details": [
    "Issuer: Amazon",
    "Date: 2023-06",
    "Credential: ABC123"
  ]
}
```

## Validation Rules

### Required Fields
- `basics.name`: Must be present
- `basics.email`: Must be present and valid email format
- `work`: Must have at least one entry (for professionals)
- `education`: Must have at least one entry
- `skills`: Must have at least one skill category

### Optional Fields
- `basics.phone`
- `basics.url`
- `basics.summary`
- `basics.location`
- `projects`
- `certificates`

### Date Formats
- Standard format: `YYYY-MM` (e.g., "2023-06")
- Current position: `endDate: null` or omit field
- In progress: "Present", "Current" (converted to null)

## Usage in Pipeline

### 1. CV Ingestion
- Extracts raw data from PDF/text
- Converts to JSON Resume format
- Validates completeness

### 2. Knowledge Storage
- Stores in profile format
- Creates vector embeddings
- Enables semantic search

### 3. CV Generator
- LLM tailors CV for job
- Maintains strict format
- Validates output before use
- Falls back to original if format invalid

### 4. DOCX Generation
- Reads JSON Resume format
- Renders to formatted document
- Applies styling and layout

## Common Pitfalls

1. **LLM Format Drift**: LLMs may change field names during CV tailoring
   - Solution: Use strict prompts with explicit examples
   - Validate output format before using

2. **Inconsistent Arrays**: Mixing strings and objects in arrays
   - Solution: Always use consistent types within arrays

3. **Missing Required Fields**: Omitting mandatory fields
   - Solution: Validate before storage/generation

4. **Date Format Variations**: Inconsistent date representations
   - Solution: Normalize to YYYY-MM format

## References

- Official JSON Resume schema: https://jsonresume.org/schema/
- This implementation extends the standard with `projects` and `certificates` sections
