# Contributing to Plant Classification MLOps Pipeline

Thank you for your interest in contributing to this MLOps project! This document provides guidelines for contributing.

## 🎯 Project Goals

This is an educational MLOps project designed to demonstrate:
- End-to-end ML pipeline development
- Production-ready deployment patterns
- MLOps best practices
- Cloud-native architecture

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or screenshots

### Suggesting Enhancements

Feature suggestions are welcome! Please include:
- Clear description of the enhancement
- Use case and benefits
- Potential implementation approach
- Any breaking changes

### Pull Requests

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

## 📝 Development Guidelines

### Code Style

- Follow **PEP 8** Python style guide
- Use **type hints** for function signatures
- Write **docstrings** for classes and functions
- Keep functions **small and focused**
- Use **meaningful variable names**

Example:
```python
def preprocess_image(image_path: Path, target_size: tuple[int, int] = (224, 224)) -> torch.Tensor:
    """
    Preprocess an image for model inference.
    
    Args:
        image_path: Path to the image file
        target_size: Target dimensions (width, height)
        
    Returns:
        Preprocessed image tensor
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image is invalid
    """
    ...
```

### Testing

- Write **unit tests** for new features
- Ensure **existing tests pass**
- Aim for **>80% code coverage**
- Test edge cases

Run tests:
```bash
pytest tests/
pytest --cov=src tests/
```

### Documentation

- Update **README.md** for major changes
- Add **docstrings** to new code
- Update **relevant docs/** files
- Include **usage examples**

### Commit Messages

Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(api): add batch prediction endpoint
fix(training): resolve memory leak in DataLoader
docs(readme): update installation instructions
```

## 🏗️ Project Structure Guidelines

### Adding New Features

When adding new functionality:
1. Place code in appropriate `src/` subdirectory
2. Follow existing module structure
3. Add tests in `tests/` directory
4. Update documentation
5. Consider backward compatibility

### File Organization

```
src/
├── module_name/
│   ├── __init__.py        # Module exports
│   ├── main.py            # Main functionality
│   ├── utils.py           # Helper functions
│   └── constants.py       # Constants and configs
```

## 🧪 Testing Standards

### Unit Tests

- Test individual functions/classes
- Mock external dependencies
- Use pytest fixtures
- Test error handling

```python
def test_preprocess_image_valid():
    image = preprocess_image(Path("test.jpg"))
    assert image.shape == (3, 224, 224)

def test_preprocess_image_invalid():
    with pytest.raises(FileNotFoundError):
        preprocess_image(Path("nonexistent.jpg"))
```

### Integration Tests

- Test component interactions
- Use test database/storage
- Verify API endpoints
- Check Kubernetes deployments

## 📦 Dependencies

When adding dependencies:
1. Add to `requirements.txt` with pinned versions
2. Document why it's needed
3. Consider alternatives
4. Check license compatibility

## 🔄 CI/CD

All PRs must:
- ✅ Pass all tests
- ✅ Pass linting (flake8)
- ✅ Build Docker image successfully
- ✅ Deploy to test environment (if applicable)

## 🐛 Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Common issues:
- **Import errors**: Check PYTHONPATH and virtual environment
- **Model loading**: Verify model file exists and format is correct
- **API errors**: Check logs with `docker logs` or `kubectl logs`

## 📚 Resources

- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)

## ❓ Questions

For questions about contributing:
- Open a GitHub Discussion
- Ask in project Issues
- Contact maintainers

## 📜 Code of Conduct

### Our Standards

- **Be respectful** and inclusive
- **Give constructive** feedback
- **Accept criticism** gracefully
- **Focus on what's best** for the project
- **Show empathy** towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing private information
- Unprofessional conduct

## 🙏 Recognition

Contributors will be:
- Listed in project README
- Credited in release notes
- Acknowledged in documentation

Thank you for contributing to this MLOps learning project! 🚀
