import asyncio
import os
import uuid
import json
import time
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import chromadb
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import google.api_core.exceptions

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

def simulate_llm_spin(content, role="writer"):
    """Simulate LLM for fallback if Gemini API fails."""
    if role == "writer":
        return f"Spun content: {content[:50]}... [AI-modified version]"
    elif role == "reviewer":
        return f"Reviewed content: {content[:50]}... [AI-refined version]"
    elif role == "editor":
        return f"Edited content: {content[:50]}... [AI-finalized version]"
    return content

def call_gemini_api(content, role="writer", max_retries=3):
    """Call Gemini API with retry on rate limit errors."""
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = {
        "writer": f"Rewrite the following content with a creative spin, maintaining the original meaning but altering style and phrasing:\n{content[:1000]}",
        "reviewer": f"Refine the following content for clarity, coherence, and quality:\n{content[:1000]}",
        "editor": f"Finalize the content by polishing it for publication, ensuring consistency and professionalism:\n{content[:1000]}"
    }[role]
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            print(f"Gemini API call successful for {role} role")
            return response.text
        except google.api_core.exceptions.ResourceExhausted as e:
            print(f"Gemini API rate limit hit for {role} role: {e}. Retrying in {2 ** attempt}s...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"Gemini API max retries reached for {role} role. Using simulated LLM.")
                return simulate_llm_spin(content, role)
        except Exception as e:
            print(f"Gemini API failed for {role} role: {e}. Using simulated LLM.")
            return simulate_llm_spin(content, role)

async def scrape_content_and_screenshot(url, output_dir="screenshots"):
    """Scrape content and save four screenshots from top to bottom."""
    os.makedirs(output_dir, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        # Get page height
        page_height = await page.evaluate("document.body.scrollHeight")
        viewport_height = await page.evaluate("window.innerHeight")
        screenshot_paths = []
        
        # Take four screenshots at different scroll positions
        for i in range(4):
            scroll_position = (page_height / 4) * i
            await page.evaluate(f"window.scrollTo(0, {scroll_position})")
            await asyncio.sleep(0.5)  # Wait for scroll to settle
            screenshot_path = f"{output_dir}/chapter_screenshot_{uuid.uuid4()}_part{i+1}.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            screenshot_paths.append(screenshot_path)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        main_content = soup.find('div', {'id': 'mw-content-text'})
        text = main_content.get_text(strip=True) if main_content else ""
        
        await browser.close()
        return text, screenshot_paths

def store_content_in_chromadb(content, metadata, collection_name="book_content"):
    """Store content in ChromaDB with metadata."""
    client = chromadb.PersistentClient(path="chromadb_data")
    collection = client.create_collection(collection_name) if collection_name not in [c.name for c in client.list_collections()] else client.get_collection(collection_name)
    
    doc_id = str(uuid.uuid4())
    collection.add(
        documents=[content],
        metadatas=[metadata],
        ids=[doc_id]
    )
    return doc_id

def rl_search(collection_name, query, n_results=1):
    """Simulate RL-based search in ChromaDB."""
    client = chromadb.PersistentClient(path="chromadb_data")
    collection = client.get_collection(collection_name)
    results = collection.query(query_texts=[query], n_results=n_results)
    return results['documents'][0] if results['documents'] else []

def human_in_the_loop(content, role, iteration, session_id=None):
    """Facilitate human review with input prompt, storing feedback."""
    print(f"\n--- {role.capitalize()} Review (Iteration {iteration}) ---")
    print(f"Content preview: {content[:100]}...")
    human_input = input(f"Enter feedback for {role} (or 'approve' to continue): ")
    feedback_data = {
        "session_id": session_id or str(uuid.uuid4()),
        "role": role,
        "iteration": iteration,
        "content": content[:500],
        "feedback": human_input,
        "timestamp": datetime.now().isoformat()
    }
    os.makedirs("output", exist_ok=True)
    with open(f"output/feedback_{feedback_data['session_id']}.json", 'a') as f:
        json.dump(feedback_data, f, indent=2)
        f.write("\n")
    return human_input if human_input.lower() != 'approve' else None, feedback_data['session_id']

def save_output(content, metadata, doc_id, output_dir="output"):
    """Save final content and metadata to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    output_data = {
        "content": content,
        "metadata": metadata,
        "document_id": doc_id
    }
    output_path = f"{output_dir}/output_{uuid.uuid4()}.json"
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    return output_path

async def book_publication_workflow(url, output_dir="screenshots", session_id=None):
    """Main CLI workflow for book publication."""
    os.makedirs(output_dir, exist_ok=True)
    
    print("Scraping content and taking screenshots...")
    content, screenshot_paths = await scrape_content_and_screenshot(url, output_dir)
    
    print("AI Writer spinning content...")
    spun_content = call_gemini_api(content, role="writer")
    
    max_iterations = 3
    current_content = spun_content
    for iteration in range(1, max_iterations + 1):
        reviewed_content = call_gemini_api(current_content, role="reviewer")
        feedback, session_id = human_in_the_loop(reviewed_content, "reviewer", iteration, session_id)
        if feedback:
            current_content = f"{reviewed_content} [Human feedback: {feedback}]"
        else:
            current_content = reviewed_content
            break
    
    print("AI Editor finalizing content...")
    final_content = call_gemini_api(current_content, role="editor")
    feedback, session_id = human_in_the_loop(final_content, "editor", 1, session_id)
    if feedback:
        final_content = f"{final_content} [Editor feedback: {feedback}]"
    
    metadata = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "screenshot_paths": screenshot_paths,
        "session_id": session_id
    }
    doc_id = store_content_in_chromadb(final_content, metadata)
    print(f"Content stored with ID: {doc_id}")
    
    output_path = save_output(final_content, metadata, doc_id)
    print(f"Output saved to: {output_path}")
    
    search_result = rl_search("book_content", final_content[:50])
    print(f"Search result: {search_result[:100]}..." if search_result else "No search results found.")
    
    return final_content, doc_id, screenshot_paths, output_path, session_id

if __name__ == "__main__":
    url = "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1"
    asyncio.run(book_publication_workflow(url))