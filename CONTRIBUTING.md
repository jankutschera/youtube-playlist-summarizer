# Contributing to YouTube Playlist Summarizer

First off, thanks for taking the time to contribute! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When you are creating a bug report, please include as many details as possible using the bug report template.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:
- A clear and descriptive title
- A detailed description of the proposed feature
- Why this enhancement would be useful

### Pull Requests

1. Fork the repo
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer

# Create .env from example
cp .env.example .env
# Fill in your test credentials

# Run locally (without Docker)
python3 -m pip install -r requirements.txt
python3 youtube_summarizer.py

# Or with Docker
docker compose up --build
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small

## Testing

Before submitting a PR:
- [ ] Test with a real YouTube playlist
- [ ] Verify email delivery works
- [ ] Check Docker build succeeds
- [ ] Ensure no secrets in commits
- [ ] Update documentation if needed

## Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests

Examples:
```
Add support for Discord notifications (#123)
Fix OAuth token refresh bug
Update README with new setup instructions
```

## Questions?

Feel free to open a question issue!
