# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Download TextBlob resources
python -c "import nltk; nltk.download('punkt')"
