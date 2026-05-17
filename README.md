# DataSnoop 🔍

Your friendly data detective — upload a CSV or fetch live web data and DataSnoop breaks it all down for you, identifies data quality issues, and suggests actionable fixes.

DataSnoop is a FastAPI-based web application with a lightweight vanilla JavaScript frontend. It's designed to be a fast, interactive first step in any data cleaning and analysis workflow.

## ✨ Features

*   **Comprehensive Data Profiling**: Get a quick overview of your dataset, including:
    *   Overall health score.
    *   Key stats: row/column counts, missing data percentage, outlier counts.
    *   Per-column analysis: data type, nulls, unique values, and descriptive statistics.
*   **Advanced Data Quality Detection**: DataSnoop goes beyond the basics to find:
    *   **Outliers**: Extreme or implausible values (e.g., negative age).
    *   **Missing Values**: Identifies nulls in every column.
    *   **Inconsistent Formatting**: (e.g., mixed date formats, categorical typos).
    *   **Data Type Mismatches**: (e.g., text in a numeric column).
*   **Actionable Recommendations**: For each issue found, DataSnoop provides a plain-English summary and suggests a concrete fix.
*   **Interactive Cleaning**: (Coming soon) Apply suggested fixes directly from the UI and download the cleaned dataset.
*   **Multiple Data Sources**:
    *   **Upload CSVs**: Analyze your local CSV files (up to 500 MB).
    *   **Fetch Live Data**: Analyze datasets directly from live web APIs (e.g., crypto prices, world countries, SpaceX launches).
    *   **Local File Analysis**: Analyze pre-loaded CSVs in the `data/` directory.
*   **REST API**: All functionality is exposed via a clean, documented REST API (viewable at `/docs`).

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, Pandas, Pydantic
*   **Frontend**: HTML, CSS, Vanilla JavaScript (no frameworks)
*   **Async**: `asyncio`, `aiohttp` for non-blocking API calls.

## 🚀 Getting Started

Follow these instructions to get the DataSnoop server running on your local machine.

### Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd python_project
```

### 2. Set up a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# For Windows
python -m venv venv
.\venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages from `requirements.txt`.

*(Note: If you don't have a `requirements.txt` file yet, you can create one with `pip freeze > requirements.txt` after installing the packages listed in the source files, such as `fastapi`, `uvicorn`, `pandas`, `pydantic`, `aiohttp`, `python-multipart`, etc.)*

```bash
pip install -r requirements.txt
```

### 4. Generate Test Data (Optional but Recommended)

The project includes a script to generate several sample CSV files with varying levels of data quality. These are great for testing the app's features.

```bash
python scripts/generate_test_data.py
```

This will create a `data/` directory and populate it with files like `employees.csv`, `sales.csv`, and more.

### 5. Run the Application

Start the FastAPI server using Uvicorn. The `--reload` flag enables hot-reloading, so the server will restart automatically when you make code changes.

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Access DataSnoop

Once the server is running, you can access the application:

*   **Main UI**: Open your browser and go to http://127.0.0.1:8000
*   **API Docs (Swagger)**: Go to http://127.0.0.1:8000/docs
*   **API Docs (ReDoc)**: Go to http://127.0.0.1:8000/redoc

You can now upload a file, fetch a live dataset, or analyze one of the local files you generated.