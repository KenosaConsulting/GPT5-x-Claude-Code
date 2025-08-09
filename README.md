# GPT-5 × Claude Code Terminal Orchestrator v2.0

A powerful AI-powered development orchestrator that combines GPT-5's planning capabilities with Claude Code's implementation skills to automate software development workflows.

## 🚀 Features

### ✨ **Enhanced Architecture**
- **Multi-agent workflow**: GPT-5 for planning/review, Claude for implementation
- **Tool-based execution**: Safe, sandboxed command execution
- **Structured logging**: Comprehensive monitoring and debugging
- **Token tracking**: Cost estimation and usage analytics
- **Retry logic**: Robust error handling with exponential backoff

### 🛡️ **Security & Safety**
- **Repository jailing**: All operations confined to target repository
- **Command allowlisting**: Only approved shell commands can execute
- **Timeout protection**: Prevents runaway processes
- **API key management**: Secure credential handling
- **Backup system**: Automatic file backups before modifications

### ⚙️ **Configuration**
- **YAML configuration**: Flexible, hierarchical settings
- **Environment variable support**: Easy deployment and CI/CD integration
- **Auto-detection**: Automatic tool discovery (npm, pip, cargo, etc.)
- **Model selection**: Choose between different AI models
- **Customizable prompts**: Tailor AI behavior for your use case

## 📦 Installation

### Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/KenosaConsulting/GPT5-x-Claude-Code.git
cd GPT5-x-Claude-Code

# Install with pip (creates aidev command)
pip install -e .

# Initialize configuration
aidev init

# Set up API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Development Installation

```bash
# Clone and install with dev dependencies
git clone https://github.com/KenosaConsulting/GPT5-x-Claude-Code.git
cd GPT5-x-Claude-Code

pip install -e ".[dev]"

# Run tests
pytest

# Code quality checks
black src tests
ruff check src tests
mypy src
```

## 🔧 Configuration

### Configuration File (`aidev.yaml`)

```yaml
# AI Models
models:
  openai_model: "gpt-4o"  # or "gpt-4-turbo", "gpt-3.5-turbo"
  anthropic_model: "claude-3-5-sonnet-20241022"
  openai_temperature: 0.2
  anthropic_max_tokens: 2000

# Tool Execution
tools:
  allowed_commands:
    - "pytest"
    - "npm test"
    - "pip install"
    - "ruff"
    - "black"
    - "mypy"
  default_timeout: 90
  max_timeout: 300

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # json or console
  file: null  # Optional log file path

# Safety
require_confirmation: true
max_iterations: 50
auto_detect_tools: true

# Repository (optional - defaults to current directory)
target_repo: "/path/to/your/project"
```

### Environment Variables

```bash
# Required API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional Overrides
export OPENAI_MODEL="gpt-4o"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
export AIDEV_REPO="/path/to/target/repo"
```

## 🎯 Usage

### 1. Generate Specification

Convert natural language requirements into detailed implementation specs:

```bash
# Basic usage
aidev spec "Add a REST API endpoint for user authentication with JWT tokens"

# Custom output file
aidev spec "Implement dark mode toggle" --output my_spec.json
```

**Example specification output:**
```json
{
  "title": "JWT Authentication API Endpoint",
  "summary": "Implement secure user authentication with JWT token generation",
  "tasks": [
    "Create user authentication model and database schema",
    "Implement password hashing and validation",
    "Design JWT token generation and validation logic",
    "Create POST /api/auth/login endpoint",
    "Add middleware for JWT token verification",
    "Write comprehensive unit and integration tests"
  ],
  "files": {
    "src/models/user.py": "User model with authentication fields",
    "src/auth/jwt_handler.py": "JWT token creation and validation",
    "src/api/auth.py": "Authentication endpoints",
    "tests/test_auth.py": "Authentication test suite"
  },
  "done_criteria": [
    "Login endpoint returns valid JWT token for correct credentials",
    "Invalid credentials return appropriate error messages",
    "JWT tokens are properly validated in protected routes",
    "All tests pass with >95% code coverage"
  ]
}
```

### 2. Implement Specification

Let Claude Code implement the specification using tools:

```bash
# Implement with default settings
aidev implement

# Custom specification file and settings
aidev implement --spec-file custom_spec.json --max-iterations 30

# Skip confirmation prompts (useful for CI/CD)
aidev implement --auto-confirm
```

**Implementation process:**
1. **Planning**: Claude analyzes the spec and existing codebase
2. **Implementation**: Systematic feature development with testing
3. **Quality Assurance**: Automatic linting, type checking, and testing
4. **Verification**: Ensures all done criteria are met

### 3. Code Review

Get comprehensive code review from GPT-5:

```bash
# Review current changes
aidev review

# Custom specification and output
aidev review --spec-file my_spec.json --output detailed_review.json
```

**Review includes:**
- **Security analysis** with vulnerability detection
- **Performance optimization** recommendations  
- **Code quality** assessment (maintainability, readability)
- **Test coverage** evaluation
- **Best practices** compliance
- **Actionable fixes** prioritized by impact

### 4. Apply Changes

Manage git patches:

```bash
# View current diff
aidev patch

# Apply changes to git staging area
aidev patch --apply
```

### 5. Status and Configuration

```bash
# Check configuration and API keys
aidev status

# Initialize new configuration
aidev init --path /path/to/project
```

## 🔄 Complete Workflow Example

```bash
# 1. Initialize project
cd my-project
aidev init
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Generate specification
aidev spec "Add user profile management with avatar upload and validation"

# 3. Review the generated specification
cat aidev_spec.json

# 4. Implement the specification  
aidev implement

# 5. Review the implementation
aidev review

# 6. Check what changed
aidev patch

# 7. Apply and commit
aidev patch --apply
git commit -m "feat: add user profile management with avatar upload

🤖 Generated with aidev v2.0
Co-Authored-By: GPT-5 <planning@openai.com>
Co-Authored-By: Claude <implementation@anthropic.com>"
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GPT-5 Model   │    │  Claude Model    │    │   Tool Executor │
│   (Planning &   │    │  (Implementation │    │   (Safe Shell   │
│   Review)       │    │   & Coding)      │    │   Commands)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ OpenAI Provider │    │ Anthropic Provider│    │ Security Layer  │
│ - Spec gen      │    │ - Tool calls     │    │ - Path jailing  │
│ - Code review   │    │ - File ops       │    │ - Cmd filtering │
│ - Retry logic   │    │ - Git ops        │    │ - Timeouts      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────┬───────────────────────┬────────────┘
                      ▼                       ▼
              ┌─────────────────┐    ┌─────────────────┐
              │  CLI Interface  │    │ Config Manager  │
              │  - Commands     │    │ - YAML config   │
              │  - Progress     │    │ - Env vars      │
              │  - Validation   │    │ - Validation    │
              └─────────────────┘    └─────────────────┘
```

### Key Improvements over v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| **Configuration** | Hard-coded settings | YAML config + env vars |
| **Error Handling** | Basic try/catch | Retry logic + backoff |
| **Security** | Simple allowlist | Multi-layer protection |
| **Monitoring** | No tracking | Structured logs + metrics |
| **Tool Detection** | Manual setup | Auto-detection |
| **CLI Interface** | Basic argparse | Rich click interface |
| **Token Tracking** | None | Usage + cost estimation |
| **File Safety** | Basic checks | Backups + validation |

## 🛠️ Available Tools

Claude Code has access to these tools for implementation:

### File Operations
- `read_file(path)` - Read files with size limits and encoding detection
- `write_file(path, content)` - Write files with automatic backups
- `list_files(pattern)` - List files matching glob patterns

### Command Execution  
- `bash(command, timeout)` - Execute allowed commands safely
- Supported by default: `pytest`, `npm test`, `pip install`, `ruff`, `black`, `mypy`
- Auto-detected based on project files (`package.json`, `requirements.txt`, etc.)

### Git Operations
- `git_diff(staged=False)` - View working tree or staged changes
- `git_apply(patch, staged=True)` - Apply patches to staging area

## 🚦 Safety Features

### Repository Jailing
All file operations are restricted to the target repository directory. Attempts to access files outside this boundary are blocked.

### Command Allowlisting  
Only pre-approved shell commands can execute. Commands are matched against configurable prefixes.

### Timeout Protection
All operations have configurable timeouts to prevent runaway processes.

### API Rate Limiting
Built-in retry logic with exponential backoff handles rate limits gracefully.

### Backup System
Files are automatically backed up before modification with `.bak` extensions.

## 📊 Monitoring & Logging

### Structured Logging
- JSON format for machine parsing
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Optional file output
- Rich console formatting

### Token Tracking
- Real-time usage monitoring
- Cost estimation
- Per-provider breakdown
- Session summaries

### Performance Metrics
- Operation timing
- Success/failure rates  
- Resource utilization

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/GPT5-x-Claude-Code.git
cd GPT5-x-Claude-Code

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Run quality checks
black src tests
ruff check src tests  
mypy src
pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/KenosaConsulting/GPT5-x-Claude-Code/issues)
- **Discussions**: [Community discussions and Q&A](https://github.com/KenosaConsulting/GPT5-x-Claude-Code/discussions)
- **Documentation**: [Full documentation and guides](https://github.com/KenosaConsulting/GPT5-x-Claude-Code/wiki)

## 🏢 About Kenosa Consulting

This project is developed and maintained by [Kenosa Consulting](https://kenosa.consulting), a team of AI and software engineering experts helping organizations leverage artificial intelligence for development workflows.

## 📈 Changelog

### v2.0.0 (Latest)
- ✨ Complete rewrite with modern Python packaging
- ✨ Enhanced configuration system with YAML support
- ✨ Structured logging and monitoring
- ✨ Retry logic and error handling
- ✨ Auto-detection of project tools
- ✨ Rich CLI interface with progress indicators
- ✨ Comprehensive security improvements
- ✨ Token usage tracking and cost estimation

### v1.0.0 (Original)
- 🎯 Basic GPT-5 × Claude Code orchestration
- 🛠️ Tool-based implementation
- 🔒 Simple security measures
- ⚙️ Environment variable configuration

---

**Built with ❤️ by the Kenosa Consulting Team**