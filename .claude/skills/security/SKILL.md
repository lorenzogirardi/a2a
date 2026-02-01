---
name: security
description: >-
  Security scanning patterns for A2A project. Covers Trivy, TruffleHog, Bandit,
  pip-audit, and Semgrep. Triggers on "security", "vulnerability", "cve",
  "secrets", "bandit", "trivy", "dependency scan", "security check".
  PROACTIVE: Invoke before committing code with new dependencies.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Security Skill

## Quick Reference

| Scanner | Purpose | What it Finds |
|---------|---------|---------------|
| **Trivy** | Vulnerability scanner | CVEs in deps, misconfigs |
| **TruffleHog** | Secrets scanner | API keys, passwords, tokens |
| **Bandit** | Python code security | SQL injection, exec(), etc. |
| **pip-audit** | Dependency vulnerabilities | Known CVEs in packages |
| **Semgrep** | Static analysis | Security anti-patterns |

---

## GitHub Actions Pipeline

```yaml
# Runs on every push/PR to main
.github/workflows/security.yml

Jobs:
├── trivy          # Filesystem vulnerability scan
├── trufflehog     # Secrets in git history
├── python-security
│   ├── bandit     # Code security linter
│   ├── pip-audit  # Dependency CVEs
│   ├── safety     # Dependency check
│   └── semgrep    # Static analysis
└── security-summary
```

---

## Local Security Checks

### Install Tools

```bash
# All security tools
pip install bandit safety pip-audit semgrep

# Trivy (macOS)
brew install trivy

# TruffleHog
brew install trufflehog
```

### Run Before Commit

```bash
# Quick security check
bandit -r . -x ./tests -ll

# Full scan
bandit -r . -x ./tests -f txt

# Dependency check
pip-audit

# Secrets scan
trufflehog filesystem . --only-verified

# Trivy scan
trivy fs --severity HIGH,CRITICAL .
```

---

## Trivy Usage

### Filesystem Scan (Dependencies)

```bash
# Basic scan
trivy fs .

# Strict (fail on HIGH/CRITICAL)
trivy fs --severity CRITICAL,HIGH --exit-code 1 .

# Ignore unfixed
trivy fs --severity CRITICAL,HIGH --ignore-unfixed .

# JSON output
trivy fs --format json --output trivy-report.json .
```

### Severity Policy

| Severity | Action | Block CI |
|----------|--------|----------|
| CRITICAL | Fix immediately | YES |
| HIGH | Fix or document | YES |
| MEDIUM | Plan remediation | NO |
| LOW | Track | NO |

---

## Bandit (Python Code Security)

### Common Issues Detected

| Issue | Code | Risk |
|-------|------|------|
| B101 | `assert` in production | Medium |
| B102 | `exec()` usage | High |
| B103 | `set_bad_permissions` | Medium |
| B104 | Hardcoded bind to 0.0.0.0 | Medium |
| B105 | Hardcoded password | High |
| B106 | Hardcoded password in func arg | High |
| B107 | Hardcoded password in default | High |
| B108 | Hardcoded temp file | Medium |
| B110 | `try/except/pass` | Low |
| B303 | Insecure hash (MD5/SHA1) | Medium |
| B311 | `random` for crypto | High |
| B324 | Insecure hash function | High |

### Configuration

```ini
# .bandit (or pyproject.toml)
[bandit]
exclude = tests,venv,.venv
skips = B101  # Skip specific checks if justified
```

### Fix Examples

```python
# BAD: Hardcoded secret
API_KEY = "sk-1234567890"

# GOOD: Environment variable
API_KEY = os.environ.get("API_KEY")

# BAD: exec usage
exec(user_input)

# GOOD: Safe alternative
# Avoid exec entirely, use specific parsers

# BAD: MD5 for security
import hashlib
hashlib.md5(password)

# GOOD: Use proper hashing
from passlib.hash import bcrypt
bcrypt.hash(password)
```

---

## TruffleHog (Secrets)

### What it Detects

- AWS keys
- GCP credentials
- GitHub tokens
- API keys
- Passwords in code
- Private keys
- JWT secrets

### Local Scan

```bash
# Current directory
trufflehog filesystem .

# Only verified secrets (less noise)
trufflehog filesystem . --only-verified

# Git history
trufflehog git file://. --only-verified

# Since specific commit
trufflehog git file://. --since-commit=abc123
```

### Prevention

```bash
# Add to .gitignore
.env
.env.local
*.pem
*.key
credentials.json
```

---

## pip-audit (Dependencies)

### Usage

```bash
# Basic scan
pip-audit

# Strict mode (fail on any vuln)
pip-audit --strict

# From requirements file
pip-audit -r requirements.txt

# JSON output
pip-audit --format json --output report.json

# Markdown output
pip-audit --format markdown
```

### Fixing Vulnerabilities

```bash
# Check which version fixes
pip-audit --fix --dry-run

# Auto-fix (updates requirements.txt)
pip-audit --fix
```

---

## Semgrep (Static Analysis)

### Usage

```bash
# Auto-detect language and rules
semgrep --config=auto .

# Python-specific rules
semgrep --config=p/python .

# Security rules only
semgrep --config=p/security-audit .

# OWASP rules
semgrep --config=p/owasp-top-ten .
```

### Common Findings

| Pattern | Risk | Fix |
|---------|------|-----|
| SQL injection | High | Use parameterized queries |
| Command injection | High | Avoid shell=True |
| SSRF | High | Validate URLs |
| Path traversal | High | Sanitize paths |
| XSS | Medium | Escape output |

---

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        args: ["-ll", "-x", "tests"]

  - repo: https://github.com/pyupio/safety
    rev: 2.3.5
    hooks:
      - id: safety
        args: ["check", "--full-report"]
```

---

## Checklist

Before committing with new dependencies:

- [ ] `pip-audit` passes
- [ ] `bandit -ll` passes
- [ ] No secrets in code (`trufflehog`)
- [ ] `trivy fs --severity HIGH,CRITICAL` clean
- [ ] Security workflow passes in CI
