# web2ebook

Convert any web page to an **EPUB ebook** with a simple Streamlit UI.

Paste a URL, click **Convert to EPUB**, and download the result — no command-line knowledge required.

---

## Features

- Fetches any publicly accessible web page
- Extracts the main article/body content and strips navigation, ads, and scripts
- Packages the content as a valid EPUB 3 file ready for any e-reader
- Simple one-page Streamlit interface

---

## Requirements

- Python 3.10 or newer
- `pip`

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/alexk195/web2ebook.git
cd web2ebook

# 2. Launch the app (installs dependencies automatically)
bash run.sh
```

The app opens in your browser at **http://localhost:8501**.

---

## Manual Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Project Structure

```
web2ebook/
├── app.py            # Streamlit application
├── requirements.txt  # Python dependencies
├── run.sh            # Convenience launch script
└── README.md
```

---

## License

See [LICENSE](LICENSE).

