# SPINE - Agentic Transport Logistics System

Backend system for managing agentic transport logistics using FastAPI and agent-based modeling.

## Setup

### Prerequisites

- Python 3.10 or higher
- Poetry (recommended) or pip
- Node.js (for semantic-release, optional for local dev)

### Installation

1. Install dependencies:
```bash
poetry install
```

2. Install pre-commit hooks:
```bash
poetry run pre-commit install
poetry run pre-commit install --hook-type commit-msg
```

3. Make validation script executable:
```bash
chmod +x scripts/validate-commit.sh
```

### Development

#### Running Tests

```bash
poetry run pytest
```

#### Code Quality

The project uses pre-commit hooks to ensure code quality:
- **ruff**: Linting and formatting
- **mypy**: Static type checking
- **Various fixers**: Trailing whitespace, end-of-file, etc.

Run manually:
```bash
poetry run pre-commit run --all-files
```

#### Code Coverage

```bash
poetry run pytest --cov
```

## Project Structure

```
spine/
├── agents/         # Agent implementations (vehicles, coordinators)
├── core/           # Core primitives (FSM, IDs, messages)
├── world/          # World graph and simulation
└── tests/          # Test suite
```

## Technology Stack

- **FastAPI**: High-performance async web framework
- **Pydantic v2**: Data validation and settings management
- **NetworkX**: Graph-based routing (early implementation)
- **Prometheus**: Metrics and monitoring
- **Structlog**: Structured logging
- **Poetry**: Dependency management

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) and [Semantic Versioning](https://semver.org/).

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature (→ minor version bump)
- `fix`: Bug fix (→ patch version bump)
- `docs`: Documentation changes
- `style`: Code style/formatting
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Testing changes
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes

**Examples:**
```bash
git commit -m "feat: add vehicle telemetry tracking"
git commit -m "fix: correct route calculation bug"
git commit -m "docs: update API documentation"
```

### Branch Naming Convention

Branches must follow: `<type>/<description>`

```bash
git checkout -b feat/add-user-authentication
git checkout -b fix/vehicle-routing-bug
git checkout -b docs/update-readme
```

### Versioning

Versions are **automatically managed** by semantic-release:
- Runs on every push to `main`
- Analyzes commit messages to determine version bump
- Updates `pyproject.toml` version
- Creates GitHub release with changelog
- Generates `CHANGELOG.md`

**You don't need to manually bump versions!**

## Docker Deployment

### Quick Start with Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f spine-backend
```

### Configuration

Set environment variables in `.env` file or directly:

```bash
# Custom port and log level
SPINE_PORT=8080 SPINE_LOG_LEVEL=DEBUG docker-compose up
```

The application will be available at:
- **WebSocket**: `ws://localhost:8000/ws`
- **Health Check**: `http://localhost:8000/health`

For detailed Docker documentation, see [Docker Containerization](docs/modules/docker.md).

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for detailed guidelines.

**Quick start:**
1. Create a feature branch following naming convention: `feat/your-feature`
2. Make changes with conventional commits: `feat: add your feature`
3. Ensure tests pass: `poetry run pytest`
4. Pre-commit hooks will validate commits automatically
5. Submit a pull request to `main`
