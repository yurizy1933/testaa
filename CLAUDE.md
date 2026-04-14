# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based AI-powered test case generation platform with two main components:
1. **Django Web Platform** (`testaa/`): Web application for managing projects, documents, and AI-generated test cases
2. **AI Training Tools** (`testaa/aitrain/`): Standalone Python tools for training and processing AI models

## Project Structure

```
django-test/
├── testaa/                    # Django project directory
│   ├── manage.py             # Django management script
│   ├── testaa/               # Project configuration
│   │   ├── settings.py       # Django settings (MySQL database)
│   │   └── urls.py           # URL routing
│   ├── normalTest/           # Basic testing functionality (legacy)
│   ├── aitestplatformlogin/  # Authentication module
│   ├── aitestcase/           # Core test case management (primary app)
│   ├── docs/                 # Document storage (docx files)
│   └── api_docs/             # API documentation files (HTML)
└── testaa/aitrain/           # AI training and processing tools
    ├── toc/                  # XMind to Excel/JSON converter
    └── word_rag_project/     # Word document RAG similarity matcher
```

## Django Commands

### Development Server
```bash
cd testaa
python manage.py runserver
```

### Database Operations
```bash
cd testaa
python manage.py makemigrations
python manage.py migrate
```

### Django Shell
```bash
cd testaa
python manage.py shell
```

### Creating Superuser
```bash
cd testaa
python manage.py createsuperuser
```

## Key Django Apps

### aittestcase (Primary App)
The core application for managing test cases and AI integration:

**Models:**
- `Project`: Test projects with documents and API docs
- `Doc`: Word documents (.docx) uploaded to projects
- `TestCase`: AI-generated test cases with soft delete support
- `AiJobManagement`: Tracks AI job status (pending/processing/completed)
- `ApiDoc`: API documentation files (HTML)
- `ApiInterface`: Parsed API interfaces from documentation
- `TestData`: Test data for API interfaces

**Key Features:**
- Upload Word documents for AI processing
- Upload HTML API documentation
- Parse API interfaces using AI (ZhipuAI)
- Generate test cases using AI
- Job management for async AI processing

### aitestplatformlogin
Simple authentication module for the AI test platform.

### normalTest
Legacy module for basic testing functionality.

## AI Integration

### AI Providers
The project integrates with multiple AI providers:
- **ZhipuAI** (Primary): Uses `zhipuai` library with GLM-4 model
- **DeepSeek**: Uses OpenAI-compatible client with `deepseek-chat` model

### AI Configuration
AI keys are hardcoded in `testaa/aitestcase/ai_tools.py`:
- `ZHIPU_API_KEY`: ZhipuAI API key
- `DEEPSEEK_API_KEY`: DeepSeek API key
- `DEEPSEEK_BASE_URL`: DeepSeek API endpoint

### AI Capabilities
1. **HTML API Document Parsing**: Extracts API interfaces from HTML documentation
2. **Test Case Generation**: Generates test cases for API interfaces
3. **Document Processing**: Processes Word documents for test case generation

## AI Training Tools

### toc/ (XMind Converter)
Converts XMind mind maps to Excel/JSON formats.

**Usage:**
```bash
cd testaa/aitrain/toc
python xmindtojson.py -x <xmind_path> [-e <excel_path>] [-j <json_path>] [-i <ignore_layers>]
```

**Dependencies:** See `testaa/aitrain/toc/requirements.txt`

### word_rag_project/ (RAG Similarity Matcher)
Word document RAG (Retrieval-Augmented Generation) similarity matcher for test case matching.

**Dependencies:** See `testaa/aitrain/word_rag_project/requirements.txt`

**Key Files:**
- `similarity_matcher.py` / `improved_similarity_matcher.py`: Core similarity matching logic
- `word_parser.py`: Word document parsing
- `vector_store.py`: Vector storage using FAISS
- `zhipuai_client.py`: ZhipuAI client integration

## Database

**Database Engine:** MySQL (configured in `testaa/testaa/settings.py`)
- Uses `pymysql` as the MySQL driver
- Database name: `test_database_name`
- Host: `43.139.212.116` (production server)

**Note:** Database credentials are currently hardcoded in settings.py for development.

## API Endpoints

### Project Management
- `GET /project/get` - List all projects
- `POST /project/create` - Create new project
- `POST /project/update` - Update project
- `POST /project/delete` - Delete project

### Document Management
- `GET /doc/get` - List documents
- `POST /doc/create` - Upload document
- `GET /doc/detail` - Get document details
- `POST /doc/delete` - Delete document

### Test Case Management
- `GET /testcase/get` - List test cases
- `GET /testcase/detail` - Get test case details
- `POST /testcase/update` - Update test case
- `POST /testcase/delete` - Delete test case (soft delete)

### AI Jobs
- `GET /ai_job/get` - List AI jobs
- `POST /ai_job/run` - Run AI test case generation job

### API Documentation
- `GET /api_doc/get` - List API docs
- `POST /api_doc/create` - Upload API doc
- `GET /api_doc/detail` - Get API doc details
- `POST /api_doc/delete` - Delete API doc
- `POST /api_doc/parse` - Parse API doc with AI

### API Interface & Test Data
- `GET /api_interface/get` - List API interfaces
- `GET /api_interface/detail` - Get API interface details
- `GET /test_data/get` - List test data
- `GET /test_data/detail` - Get test data details
- `POST /test_data/create` - Create test data
- `POST /test_data/update` - Update test data
- `POST /test_data/delete` - Delete test data

### AI Test Case Generation
- `POST /api_test_cases/generate` - Generate test cases for API interface

## Code Style & Quality

### Configuration Files
The project uses the following configuration files for code quality:
- `.flake8` - Python code linting (max line length: 120)
- `.editorconfig` - Editor settings (4-space indentation, UTF-8, LF line endings)
- `.pre-commit-config.yaml` - Pre-commit hooks (Black, isort, flake8, Django upgrade)
- `testaa/.gitignore` - Git ignore patterns for Django projects

### Code Style
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 120 characters
- **Import order**: Standard library → Third-party → Local modules
- **Naming conventions**:
  - Classes: CamelCase (e.g., `ConvertXmindToExcel`)
  - Functions/Variables: snake_case (e.g., `convert_to_excel`)
- **Comments/Docs**: Chinese comments and docstrings for business logic

### Pre-commit Hooks
Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

The hooks will automatically:
- Format code with Black
- Sort imports with isort
- Lint with flake8
- Check for merge conflicts
- Verify YAML/JSON syntax

### Django Views
- Uses `@csrf_exempt` decorator on POST endpoints (CSRF middleware disabled in settings)
- Returns JSON responses with standard format: `{'code': 200, 'message': '', 'data': {}}`
- Error responses use appropriate HTTP status codes (400, 500, etc.)
- Uses `get_object_or_404` for model lookups

### Models
- Uses `AutoField` as primary key (not default `BigAutoField`)
- Includes `create_time` and `update_time` on most models
- Uses soft delete pattern (status field) for `TestCase` model
- Foreign keys use explicit `related_name` parameters

### AI Tools
- Centralized in `aitestcase/ai_tools.py`
- Functions return structured data (dictionaries/lists)
- Includes error handling with try-except blocks
- AI responses are parsed to extract JSON data

## Security Notes

- **CSRF middleware is disabled** in settings.py (commented out line 52)
- **Secret key is hardcoded** in settings.py (development only)
- **Database credentials are hardcoded** in settings.py (development only)
- AI API keys are hardcoded in `ai_tools.py`

These security practices are suitable for development but should be addressed before production deployment.

## Virtual Environment

The project uses a virtual environment at `venv/`. Activate it before running Django commands:

```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

## Testing

Run unit tests:
```bash
cd testaa
python manage.py test
```

Run specific test:
```bash
cd testaa
python manage.py test <app_name>.tests.<TestClass>
```
