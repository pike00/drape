# Contributing to drape

Thank you for your interest in contributing! This document outlines the process.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/drape.git`
3. Create a virtual environment: `python3 -m venv venv`
4. Activate it: `source venv/bin/activate`
5. Install in development mode: `pip install -e .`

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Run `black` for formatting (configured in `pyproject.toml`)
- Run `mypy` for type checking

### Adding Features

1. Create a branch for your feature: `git checkout -b feature/description`
2. Make your changes
3. Write tests in `tests/`
4. Ensure all tests pass
5. Commit with a clear message
6. Push to your fork
7. Open a pull request

## Security Considerations

drape is designed to prevent secrets from appearing in LLM conversation transcripts. When contributing:

- Do **not** weaken the masking strategy without discussion
- Consider the threat model (see [docs/architecture.md](docs/architecture.md))
- Test with real secrets (in a sandbox environment)
- Document any security implications in the PR

## Issues

- Bug reports: Please include `.env` file format/example (without real secrets)
- Feature requests: Describe the use case and expected behavior
- Check [docs/ROADMAP.md](docs/ROADMAP.md) to see planned features before requesting new ones

## Code of Conduct

Be respectful and inclusive. We're all here to make security better.
