# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About PypeIt

PypeIt is a Python package for semi-automated reduction of astronomical spectroscopic data. It supports data from many different spectrographs (Keck, Gemini, VLT, Magellan, etc.) through a plugin architecture. The package builds on decades of data reduction pipeline development and is designed for both expert spectroscopists and astronomers new to data reduction.

## Development Setup

### Installation for Development

Install from your fork in editable mode with all development dependencies:

```bash
pip install -e ".[dev]"
```

The `[dev]` optional dependencies install testing, documentation, and development tools.

### Git Workflow

- **Main branches**: `release` (production), `develop` (integration)
- Create feature branches from `develop`
- Submit PRs to `develop` branch
- Keep your fork updated: `git fetch upstream` regularly

## Common Commands

### Testing

```bash
# Run all tests
pytest --pyargs pypeit

# Run specific test file
pytest pypeit/tests/test_wavecalib.py

# Run single test
pytest pypeit/tests/test_wavecalib.py::test_function_name

# Run tests with coverage
pytest --pyargs pypeit --cov pypeit --cov-config=pyproject.toml

# Run tests using tox (multiple Python versions)
tox -e 3.12-test-alldeps
```

Test configuration is in `pyproject.toml` under `[tool.pytest.ini_options]`.

### Code Style

```bash
# Check for critical style errors (E9 errors)
pycodestyle pypeit --count --select=E9
```

### Documentation

```bash
cd doc
make html          # Build full documentation
make htmlonly      # Build without regenerating API docs
make clean         # Clean build files
```

Documentation is built with Sphinx and hosted on ReadTheDocs.

## Architecture Overview

### Core Pipeline Flow

The main reduction pipeline follows this sequence:

1. **PypeIt File Parsing** (`inputfiles.py`): Parse `.pypeit` file containing reduction parameters and file list
2. **Metadata Construction** (`metadata.py`): Build metadata table from raw FITS headers
3. **Calibrations** (`calibrations.py`): Generate calibration frames (bias, flat, arc, tilt, etc.)
4. **Science Processing** (`pypeit.py`): Main driver class coordinating the full reduction
5. **Object Finding** (`find_objects.py`): Detect and trace objects in 2D spectra
6. **Extraction** (`extraction.py`): Extract 1D spectra from 2D frames
7. **Flux Calibration** (`fluxcalibrate.py`, `sensfunc.py`): Apply flux calibration

### Key Architectural Components

#### Spectrograph Classes (`pypeit/spectrographs/`)

All instrument support is implemented via the `Spectrograph` abstract base class in `spectrographs/spectrograph.py`. Each instrument has its own module (e.g., `keck_deimos.py`, `gemini_gmos.py`).

Key responsibilities:
- Define detector properties (gain, read noise, etc.) via `DetectorContainer`
- Provide metadata mapping from FITS headers to PypeIt metadata model
- Override reduction parameter defaults
- Implement instrument-specific processing (e.g., bad pixel masks, file naming)

To add a new spectrograph, subclass `Spectrograph` and implement required methods.

#### Parameter System (`pypeit/par/`)

The `pypeitpar.py` module defines all reduction parameters using a hierarchical `ParSet` structure. Parameters cascade from defaults to user overrides specified in `.pypeit` files.

Main parameter classes:
- `PypeItPar`: Top-level container for all parameters
- `CalibrationsPar`: Calibration-specific parameters
- `ReducePar`: Science reduction parameters
- Each processing step has its own parameter class

#### Data Model (`datamodel.py`)

PypeIt uses `DataContainer` objects to enforce strict data models for all data products. All data classes inherit from `DataContainer` and define a `datamodel` class attribute specifying the structure.

Key data containers:
- `PypeItImage`: Raw or processed 2D image with metadata
- `SlitTraceSet`: Slit edge traces
- `WaveCalib`: Wavelength calibration solution
- `SpecObj`: Single extracted spectrum
- `SpecObjs`: Collection of extracted spectra

#### Calibration Framework (`calibrations.py`)

The `Calibrations` class orchestrates all calibration processing:
- **Edge Tracing** (`edgetrace.py`): Find slit edges
- **Flat Fielding** (`flatfield.py`): Pixel and illumination flats
- **Wavelength Calibration** (`wavecalib.py`): Arc line identification
- **Tilts** (`wavetilts.py`): Spectral tilt along spatial direction

Calibrations are cached and reused based on calibration groups defined by header keywords.

#### Image Processing (`pypeit/images/`)

Image handling classes:
- `RawImage`: Interface to raw detector data
- `PypeItImage`: Processed image with error and mask arrays
- `BuildImage`: Combine multiple raw images (bias, flat, arc, etc.)
- `DetectorContainer`: Detector properties and geometry

#### Core Algorithms (`pypeit/core/`)

Low-level algorithmic functions organized by task:
- `wavecal/`: Wavelength calibration algorithms
- `arc.py`: Arc line detection and identification
- `extract.py`: Optimal extraction algorithms
- `skysub.py`: Sky subtraction
- `flexure.py`: Flexure correction
- `flat.py`: Flat field processing
- `trace.py`: Object tracing

### Pipeline Types

PypeIt supports different pipeline configurations:
- **MultiSlit**: Standard long-slit and multi-slit reduction
- **Echelle**: Cross-dispersed echelle spectrograph reduction
- **IFU**: Integral field unit data cubes (via `coadd3d.py`)
- **SlitLess**: Slitless spectroscopy (limited support)

The pipeline type is set via the `Spectrograph.pypeline` attribute.

### Script Entry Points

All command-line scripts are in `pypeit/scripts/` and registered in `pyproject.toml` under `[project.scripts]`. Each script subclasses `ScriptBase` and implements an `entry_point()` classmethod.

Main scripts:
- `run_pypeit`: Primary reduction driver
- `pypeit_setup`: Initialize reduction directory structure
- `pypeit_coadd_1dspec`: Coadd 1D spectra
- `pypeit_flux_calib`: Apply flux calibration
- `pypeit_sensfunc`: Generate sensitivity function

## Important Development Guidelines

### Data Container Pattern

When creating new data products:
1. Inherit from `DataContainer`
2. Define `datamodel` class attribute with types and descriptions
3. Implement `_bundle()` to organize data for FITS output
4. Implement `_parse()` to read data from FITS
5. All attributes should be in the datamodel or set in `__init__`/`_validate()`

### Spectrograph Support

Adding or modifying spectrograph support:
- Detector numbering starts at 1 (not 0)
- The `meta` dict maps FITS header keywords to PypeIt metadata
- Test with data from the PypeIt-development-suite
- Update documentation in `doc/spectrographs/`

### Testing Strategy

- Unit tests in `pypeit/tests/` and `pypeit/*/tests/`
- Integration tests use data from PypeIt-development-suite
- Use `tstutils.py` helper functions for test data
- Tests should be deterministic and fast when possible
- Mark slow tests with `@pytest.mark.slow`

### Calibration File Versioning

Calibration files (e.g., arc line lists, sensitivity functions) are stored in `pypeit/data/`. These files:
- Are version controlled in the repository
- Can also be cached from AWS S3 (see `cache.py`)
- Use strict versioning to ensure reproducibility

### Messages and Logging

Use the `msgs` module (`pypeit.pypmsgs`) for all user-facing output:
- `msgs.info()`: Informational messages
- `msgs.warn()`: Warnings
- `msgs.error()`: Errors (raises exception)
- Never use `print()` in production code

### Code Structure Conventions

- Import `IPython.embed` for debugging but remove before committing
- Use numpy docstring format for all functions/classes
- Type hints encouraged but not required
- Avoid circular imports by importing within functions if needed

## Configuration Files

- `pyproject.toml`: Project metadata, dependencies, build config, pytest settings
- `tox.ini`: Multi-environment testing configuration
- `.github/workflows/ci_tests.yml`: CI/CD configuration
- `doc/conf.py`: Sphinx documentation configuration

## Data Directory Structure

- `pypeit/data/arc_lines/`: Wavelength calibration line lists
- `pypeit/data/standards/`: Standard star spectra and sensitivity functions
- `pypeit/data/telluric/`: Telluric correction templates
- `pypeit/data/static_calibs/`: Static calibration files (bad pixel masks, etc.)
- `pypeit/data/tests/`: Test data fixtures

## External Resources

- **Documentation**: https://pypeit.readthedocs.io/
- **User Slack**: https://pypeit-users.slack.com
- **Development Suite**: https://github.com/pypeit/PypeIt-development-suite
- **Example Data**: Google Drive folder (see README.rst for link)

## Communication

Before starting major development:
1. Discuss in PypeIt Users Slack or open a GitHub issue
2. Coordinate with core team to avoid duplicate work
3. Follow the development guidelines in `doc/dev/development.rst`
