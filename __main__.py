# run.py
from app.api import app

if __name__ == '__main__':
    # You would typically use a tool like 'gunicorn' for production
    # Set debug=True for development
    app.run(debug=True)
