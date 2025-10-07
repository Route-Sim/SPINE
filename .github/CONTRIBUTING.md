# Contributing to SPINE

Thank you for your interest in contributing to SPINE! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/SPINE.git`
3. Install dependencies: `poetry install`
4. Install pre-commit hooks: `poetry run pre-commit install`

## Development Workflow

### Branch Naming Convention

All branches must follow the conventional naming pattern:

```
<type>/<description>
```

**Allowed types:**
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `style/` - Code style/formatting changes
- `refactor/` - Code refactoring
- `perf/` - Performance improvements
- `test/` - Adding or updating tests
- `build/` - Build system changes
- `ci/` - CI/CD changes
- `chore/` - Other changes (dependencies, config, etc.)

**Examples:**
```
feat/add-user-authentication
fix/vehicle-routing-bug
docs/update-readme
refactor/simplify-agent-logic
```

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages. This allows us to automatically generate changelogs and version numbers.

**Format:**
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: A new feature (triggers minor version bump)
- `fix`: A bug fix (triggers patch version bump)
- `docs`: Documentation only changes
- `style`: Changes that don't affect code meaning (whitespace, formatting)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement (triggers patch version bump)
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes affecting the build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

**Examples:**
```
feat: add vehicle telemetry tracking
fix: correct route calculation for multi-modal transport
docs: update API documentation for agents
refactor: simplify message passing logic
perf: optimize graph traversal algorithm
test: add tests for vehicle state transitions
```

**Breaking Changes:**

Add `!` after the type or add `BREAKING CHANGE:` in the footer:

```
feat!: redesign agent communication protocol

BREAKING CHANGE: Agent message format has changed
```

This triggers a major version bump.

### Development Process

1. **Create a branch** following the naming convention:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** with proper commit messages:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

3. **Run tests and checks**:
   ```bash
   poetry run pytest
   poetry run pre-commit run --all-files
   ```

4. **Push your branch**:
   ```bash
   git push origin feat/your-feature-name
   ```

5. **Open a Pull Request** to the `main` branch

## Testing

- Write tests for all new features and bug fixes
- Ensure all tests pass: `poetry run pytest`
- Check coverage: `poetry run pytest --cov`
- Tests must pass in CI before merging

## Code Quality

- Pre-commit hooks will automatically run on commit
- Code must pass `ruff` linting and formatting
- Code must pass `mypy` type checking
- Follow the existing code style

## Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes (`feat!:` or `BREAKING CHANGE:`)
- **MINOR**: New features (`feat:`)
- **PATCH**: Bug fixes and minor improvements (`fix:`, `perf:`, `refactor:`, `build:`)

Versions are automatically bumped by semantic-release when PRs are merged to `main`.

## Questions?

If you have questions, please open an issue for discussion.
