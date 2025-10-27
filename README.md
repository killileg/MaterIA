# Generic EPD Aggregator

[![Build](https://github.com/killileg/MaterIA/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/killileg/MaterIA/actions/workflows/ci.yml)
![Coverage](coverage.svg)
[![PyPI](https://img.shields.io/pypi/v/materia-epd.svg)](https://pypi.org/project/materia-epd/)
[![Python](https://img.shields.io/pypi/pyversions/materia-epd.svg)](https://pypi.org/project/materia-epd/)
[![License](https://img.shields.io/github/license/killileg/MaterIA?branch=dev)](https://github.com/killileg/MaterIA/blob/dev/LICENSE.txt)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Flake8](https://img.shields.io/badge/linting-flake8-blue)](https://flake8.pycqa.org/en/latest/)

---

# Features

- Parse ILCD process and flow XMLs
- Normalize material properties and LCIA modules
- Aggregate impacts and compute weighted averages
- Write new ILCD XML datasets

---

## Installation

Install via PyPI:

```bash
pip install materia-epd
```

Requires Python 3.10+.

---

## Usage
Here’s a minimal example:

```bash
python -m materia <generic_processes_dir> <epd_processes_dir> -o <output_dir>
```

Note the you need to provide a \matches folder in the generic data folder to link generic products and EPDs. .json files are named after corresponding generic products and should be strucured as follows:


```json
{
  "type": "<aggregation_type>",  // "average" or "assembled"
  "uuids": [
    "<uuid-1>",
    "<uuid-2>",
    "<uuid-3>",
    "... more UUIDs ..."
  ]
}
```
