# Installation Guide

## Quick Start

### 1. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install the package
```bash
# Option A: Standard installation (recommended)
pip install -e .

# Option B: If you encounter NumPy/PyArrow compilation issues on macOS
pip install --only-binary=numpy,pyarrow numpy pyarrow
pip install -e . --no-deps
pip install -r requirements.txt
```

## Troubleshooting

### NumPy/PyArrow Compilation Issues (macOS/ARM64)

If you encounter C++ compilation errors with NumPy 2.x or PyArrow on macOS (especially with newer Xcode versions), use the pre-compiled binaries:

```bash
# Install problematic packages from binaries first
pip install --only-binary=numpy numpy>=2.0.1
pip install --only-binary=pyarrow pyarrow>=17.0.0

# Then install the package without dependencies
pip install -e . --no-deps

# Finally install remaining dependencies
pip install -r requirements.txt
```

### Common Error Messages

- **"C++ compilation failed"** → Use `--only-binary` flag
- **"metadata-generation-failed"** → Use `--only-binary` flag  
- **"ResolutionImpossible"** → Check Python version compatibility (requires Python 3.8+)

## Verification

Test your installation:
```bash
python -c "import common; import neurons; import bittensor; print('Installation successful!')"
```

## Development Setup

After installation, you can run tests:
```bash
python -m pytest tests/
```

## Requirements

- Python 3.8+
- Virtual environment (recommended)
- On macOS: Xcode command line tools (`xcode-select --install`)
