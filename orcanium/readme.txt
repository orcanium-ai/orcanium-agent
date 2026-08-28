# run backend

source venv/bin/activate

uvicorn orcanium.app.main:app --host 0.0.0.0 --port 8000 --reload

or

cd /Users/macztf/Documents/Coding/orcanium

source venv/bin/activate

python3 -m orcanium.app.cli dashboard --host 0.0.0.0 --port 8000
