# LEO Constellation Design and Analysis

This project focuses on designing and analyzing a Low Earth Orbit (LEO) Earth observation constellation to achieve a global mean revisit time of ≤ 24 hours. The analysis uses AGI STK for scenario simulation and Python for post-processing.

## Project Structure
- `scenario/` – Contains the STK scenario files (`.sc`) and any custom report styles.
- `scripts/` – Python scripts and/or Jupyter notebooks for data ingestion, analysis, and plotting.
- `report/` – Final trade-study report (PDF format).
- `optional/` – (Optional) GMAT scripts, MATLAB calculations, or other supporting artefacts.

## Environment Setup

### Prerequisites
- [AGI STK](https://www.agi.com/products/stk)
- Python 3.8+
- Required Python packages:
  - `pystk`
  - `numpy`
  - `pandas`
  - `matplotlib`

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-folder>

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
