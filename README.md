# Automated Book Publication Workflow

A Python-based system to scrape web content, apply AI-powered content "spinning," and enable human-in-the-loop review, with full version tracking and intelligent retrieval via ChromaDB.

> ✨ Ideal for automating the publishing pipeline of classic texts, articles, or educational material.

---

## Features

- **Content Scraping**: Scrapes chapters and saves screenshots from sources like Wikisource.
- **AI Writer & Reviewer**: Uses LLMs (e.g., Gemini or GPT) to rewrite and review content.
- **Human-in-the-Loop**: Provides a clean interface for human editing and finalization.
- **Versioned Storage**: Saves all content versions in ChromaDB.
- **RL-Based Search**: Uses reinforcement-style ranking to retrieve final published content.
- **Dual Interface**: Operates via CLI or Flask-based GUI.

---

## 🛠 Tech Stack

| Functionality       | Tool / Library     |
|---------------------|--------------------|
| Language            | Python 3.10+       |
| Web Scraping        | Playwright         |
| LLM Integration     | Gemini / GPT-4     |
| Web Interface (UI)  | Flask (CLI/GUI)    |
| Versioned Storage   | ChromaDB           |
| Smart Retrieval     | RL-inspired Search |
| Optional UI         | Streamlit / Gradio |

---

## Project Directory Structure

| Path                        | Description                                             |
|-----------------------------|---------------------------------------------------------|
| `main.py`                   | CLI pipeline script to scrape, spin, review, store     |
| `app.py`                    | Flask app controller for human-in-the-loop interface   |
| `requirements.txt`          | Python dependencies                                    |
| `README.md`                 | Project documentation                                  |
| `chromadb_data/`            | Auto-generated folder for ChromaDB database files    |
| `screenshots/`              | will be auto-generated: saves web page screenshots          |
| `output/`                   | will be auto-generated: stores scraped/spun/reviewed content |
| `templates/`                | HTML files for Flask UI                                |
| ├── `index.html`            | Landing/editor page for human review                   |
| ├── `feedback.html`         | Form for reviewer suggestions                          |
| └── `result.html`           | Final result preview after edits                       |

**Generate an API key from aistudio.google.dev and store in an .env file**
---

##  How to Run

```bash
# 1. Clone the repository
git clone https://github.com/your-username/automated-book-workflow.git
cd automated-book-workflow

# 2. Install required packages
pip install -r requirements.txt

# 3. Start the workflow via CLI
python main.py

# 4. (Optional) Launch the Flask interface
python app.py
