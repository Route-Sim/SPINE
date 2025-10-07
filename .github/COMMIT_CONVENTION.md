# Commit Convention Quick Reference

## Commit Types

| Type | Description | Version Impact | Example |
|------|-------------|----------------|---------|
| `feat` | New feature | Minor (0.x.0) | `feat: add vehicle tracking` |
| `fix` | Bug fix | Patch (0.0.x) | `fix: correct route calculation` |
| `docs` | Documentation only | None | `docs: update README` |
| `style` | Code style/formatting | None | `style: format with ruff` |
| `refactor` | Code refactoring | Patch (0.0.x) | `refactor: simplify agent logic` |
| `perf` | Performance improvement | Patch (0.0.x) | `perf: optimize graph traversal` |
| `test` | Adding/updating tests | None | `test: add vehicle tests` |
| `build` | Build system changes | Patch (0.0.x) | `build: update dependencies` |
| `ci` | CI/CD changes | None | `ci: update GitHub Actions` |
| `chore` | Other changes | None | `chore: update gitignore` |
| `revert` | Revert previous commit | Patch (0.0.x) | `revert: undo feature X` |

## Breaking Changes

Add `!` after type or `BREAKING CHANGE:` in footer for major version bump:

```
feat!: redesign API

BREAKING CHANGE: API endpoints have changed
```

This triggers: Major (x.0.0)

## Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Rules

✅ **DO:**
- Use lowercase for type
- Keep header under 100 characters
- Use imperative mood ("add" not "added")
- Be descriptive but concise

❌ **DON'T:**
- End header with period
- Use past tense
- Be vague ("fix stuff")

### Examples

#### Good Commits ✅

```bash
feat: add vehicle telemetry tracking
fix: correct route calculation for multi-modal transport
docs: update API documentation
refactor: simplify message passing between agents
perf: optimize graph search algorithm
test: add integration tests for vehicle routing
feat(agents): add new truck vehicle type
fix(world): handle missing edge data gracefully
```

#### Bad Commits ❌

```bash
feat: stuff                          # Too vague
Fix: bug                             # Wrong case
added new feature                    # Not using type prefix
fix stuff.                           # Ends with period
```

## Branch Naming

Format: `<type>/<description-in-kebab-case>`

**Examples:**
```bash
feat/add-vehicle-telemetry
fix/route-calculation-bug
docs/update-api-docs
refactor/agent-communication
test/vehicle-state-transitions
```

## Scopes (Optional)

Use scopes to specify which part of the codebase is affected:

```bash
feat(agents): add new vehicle type
fix(world): correct graph edge handling
docs(api): update endpoint documentation
test(core): add FSM tests
```

Common scopes:
- `agents` - Agent-related code
- `core` - Core primitives (FSM, IDs, messages)
- `world` - World graph and simulation
- `api` - FastAPI endpoints
- `ci` - CI/CD configuration
- `deps` - Dependencies

## Testing Your Commits Locally

Before committing, test your commit message:

```bash
# Using the validation script
./scripts/validate-commit.sh "feat: add new feature"

# Pre-commit hook will automatically validate on commit
git commit -m "feat: add new feature"
```

## Commit Message Hook

The commit-msg hook is automatically installed and will:
- ✅ Validate format
- ✅ Check type is allowed
- ✅ Enforce character limits
- ❌ Reject invalid commits

## Need Help?

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Contributing Guide](.github/CONTRIBUTING.md)
