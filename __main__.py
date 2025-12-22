# run.py
from app.api import app

if __name__ == '__main__':
    # Set debug=True for development
    app.run(debug=True)
