# run_tests.ps1

# Step 1: Create virtual environment if not exists
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Virtual environment created."
} else {
    Write-Host "Virtual environment already exists."
}

# Step 2: Activate virtual environment
& .\.venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated."

# Step 3: Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install pandas pytz requests yfinance

# Step 4: Run tests
python -m unittest discover -s test -p "test*.py" -v

# Step 5: Deactivate virtual environment
deactivate
Write-Host "Virtual environment deactivated."