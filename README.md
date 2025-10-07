# SPINE - Agentic Transport Logistics System

Backend system for managing agentic transport logistics using FastAPI and agent-based modeling.

## Setup

### Prerequisites

- Python 3.10 or higher
- Poetry (recommended) or pip

### Installation

1. Install dependencies:
```bash
poetry install
```

2. Install pre-commit hooks:
```bash
poetry run pre-commit install
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

## Contributing

1. Create a feature branch
2. Make your changes
3. Ensure tests pass: `poetry run pytest`
4. Pre-commit hooks will run automatically on commit
5. Submit a pull request
