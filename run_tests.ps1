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
pip install coverage pandas pytz requests yfinance 

# Step 4: Run tests
python -m coverage run -m unittest discover -s . -p "test_*.py" -v
# 產生報告供 VS Code 顯示
python -m coverage xml
#  產生文字版摘要
python -m coverage report -m > coverage_summary.txt

# Step 5: Deactivate virtual environment
deactivate
Write-Host "Virtual environment deactivated."