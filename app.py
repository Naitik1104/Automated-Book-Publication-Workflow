from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import chromadb
import os
import json
from datetime import datetime
import uuid
import asyncio
from book_publication_workflow import call_gemini_api, store_content_in_chromadb, rl_search, scrape_content_and_screenshot

app = Flask(__name__)

def get_chromadb_content(collection_name="book_content"):
    """Retrieve content from ChromaDB."""
    client = chromadb.PersistentClient(path="chromadb_data")
    try:
        collection = client.get_collection(collection_name)
        results = collection.get(include=["documents", "metadatas", "ids"])
        return [
            {
                "id": doc_id,
                "content": doc[:500],
                "metadata": meta
            }
            for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]
    except Exception as e:
        return [{"id": "Error", "content": f"Failed to load collection: {e}", "metadata": {}}]

def get_screenshots():
    """Get list of screenshot files."""
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        return []
    return [f for f in os.listdir(screenshots_dir) if f.endswith(".png")]

def get_output_files():
    """Get list of output JSON files."""
    output_dir = "output"
    if not os.path.exists(output_dir):
        return []
    return [f for f in os.listdir(output_dir) if f.endswith(".json")]

@app.route('/')
def index():
    """Main dashboard with ChromaDB content, screenshots, and outputs."""
    documents = get_chromadb_content()
    screenshots = get_screenshots()
    output_files = get_output_files()
    return render_template('index.html', documents=documents, screenshots=screenshots, output_files=output_files)

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve files from screenshots/."""
    return send_from_directory('screenshots', filename)

@app.route('/output/<path:filename>')
def serve_output(filename):
    """Serve files from output/."""
    return send_from_directory('output', filename)

@app.route('/feedback/<session_id>/<role>/<int:iteration>', methods=['GET', 'POST'])
def feedback(session_id, role, iteration):
    """Handle feedback via web form."""
    if request.method == 'POST':
        content = request.form['content']
        feedback = request.form['feedback']
        screenshot_paths = json.loads(request.form.get('screenshot_paths', '[]'))
        feedback_data = {
            "session_id": session_id,
            "role": role,
            "iteration": iteration,
            "content": content[:500],
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        os.makedirs("output", exist_ok=True)
        with open(f"output/feedback_{session_id}.json", 'a') as f:
            json.dump(feedback_data, f, indent=2)
            f.write("\n")
        
        if role == "reviewer" and iteration < 3 and feedback.lower() != 'approve':
            new_content = call_gemini_api(content, role="reviewer")
            return render_template('feedback.html', content=new_content, role="reviewer", iteration=iteration + 1, session_id=session_id, screenshot_paths=screenshot_paths)
        elif role == "reviewer":
            new_content = call_gemini_api(content, role="editor")
            return render_template('feedback.html', content=new_content, role="editor", iteration=1, session_id=session_id, screenshot_paths=screenshot_paths)
        else:
            metadata = {
                "url": "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1",
                "timestamp": datetime.now().isoformat(),
                "screenshot_paths": screenshot_paths,
                "session_id": session_id
            }
            final_content = f"{content} [Editor feedback: {feedback}]" if feedback.lower() != 'approve' else content
            doc_id = store_content_in_chromadb(final_content, metadata)
            output_data = {"content": final_content, "metadata": metadata, "document_id": doc_id}
            output_path = f"output/output_{uuid.uuid4()}.json"
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            search_result = rl_search("book_content", final_content[:50])
            return render_template('results.html', content=final_content, doc_id=doc_id, output_path=output_path, search_result=search_result, screenshot_paths=screenshot_paths)
    
    documents = get_chromadb_content()
    content = documents[-1]["content"] if documents else "Sample content"
    screenshot_paths = documents[-1]["metadata"].get("screenshot_paths", []) if documents else []
    return render_template('feedback.html', content=content, role=role, iteration=iteration, session_id=session_id, screenshot_paths=screenshot_paths)

@app.route('/start_workflow', methods=['GET'])
def start_workflow():
    """Start a new workflow session."""
    url = "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1"
    session_id = str(uuid.uuid4())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    content, screenshot_paths = loop.run_until_complete(scrape_content_and_screenshot(url))
    spun_content = call_gemini_api(content, role="writer")
    loop.close()
    return render_template('feedback.html', content=spun_content, role="reviewer", iteration=1, session_id=session_id, screenshot_paths=screenshot_paths)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)