import json
import re
import time
from pathlib import Path

import pandas as pd
import pyodbc
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Connect to the database
conn = pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;')

# Get all unique journals from the database
query = """
SELECT DISTINCT j.id, j.name
FROM journal j
ORDER BY j.name;
"""

df = pd.read_sql_query(query, conn)
conn.close()

journals = df.to_dict('records')

output_dir = Path(__file__).parent
results_path = output_dir / "journal_metrics_results.json"
unresolved_path = output_dir / "journal_metrics_unresolved.json"

def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        return []

successes = _load_json(results_path)
unresolved = _load_json(unresolved_path)

# Index by requested_name to avoid overwriting existing entries
success_index = {item.get("requested_name"): item for item in successes if item.get("requested_name")}
unresolved_index = {item.get("requested_name"): item for item in unresolved if item.get("requested_name")}

def _flush():
    results_path.write_text(json.dumps(successes, indent=2), encoding="utf-8")
    unresolved_path.write_text(json.dumps(unresolved, indent=2), encoding="utf-8")

def record_success(entry):
    key = entry.get("requested_name")
    if not key or key in success_index:
        return
    successes.append(entry)
    success_index[key] = entry
    _flush()

def record_unresolved(entry):
    key = entry.get("requested_name")
    if key and key in unresolved_index:
        return
    unresolved.append(entry)
    if key:
        unresolved_index[key] = entry
    _flush()

# Initialize Selenium driver
driver = webdriver.Chrome()  # Make sure you have ChromeDriver installed

print(f"Found {len(journals)} unique journals to search\n")
print("=" * 80)

for idx, journal_row in enumerate(journals, 1):
    journal_id = journal_row['id']
    journal_name = journal_row['name']
    print(f"\n[{idx}/{len(journals)}] Searching for: {journal_name} (ID: {journal_id})")
    print("-" * 80)
    
    try:
        # Navigate to Journal Metrics main page (only once)
        if idx == 1:
            driver.get("https://www.journalmetrics.org/")
            time.sleep(2)
        
        # Find the search bar
        search_bar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input[type='text'], input[placeholder*='search' i]"))
        )
        
        # Clear the search bar and type the journal name
        search_bar.clear()
        search_bar.send_keys(journal_name)
        # Some pages require ENTER to trigger search; do both
        search_bar.send_keys(Keys.ENTER)
        time.sleep(2)

        # Wait until at least one ISSN appears somewhere on the page (indicates results loaded)
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.XPATH, "//*[contains(text(),'ISSN')]") ) > 0
            )
        except TimeoutException:
            print("  ❌ No results appeared")
            record_unresolved({
                "journal_id": journal_id,
                "requested_name": journal_name,
                "reason": "timeout/no_results"
            })
            continue

        # Locate journal cards by finding containers that include an ISSN label
        # Use a broad XPath to capture card-like divs containing ISSN
        results = driver.find_elements(By.XPATH, "//div[.//*[contains(text(),'ISSN')]]")
        if not results:
            # Fallback: grab ancestors of any ISSN text nodes
            issn_nodes = driver.find_elements(By.XPATH, "//*[contains(text(),'ISSN')]")
            results = []
            for node in issn_nodes:
                try:
                    card = node.find_element(By.XPATH, "ancestor::div[1]")
                    results.append(card)
                except Exception:
                    pass
        
        if not results:
            print(f"  ❌ No results found")
            record_unresolved({
                "journal_id": journal_id,
                "requested_name": journal_name,
                "reason": "no_results"
            })
            continue
        
        # Process each result
        # Build parsed candidates with title matching and metrics
        parsed = []
        for result_idx, result in enumerate(results[:8], 1):  # Limit to first 8 results
            try:
                # Extract text from the result card
                result_text = result.text
                
                # Try to find the 5-year IF
                # Look for patterns like "3.8" following "5-YEAR IF" or similar
                lines = result_text.split('\n')
                
                journal_title = None
                issn = None
                if_2025 = None
                if_5year = None
                quartile = None
                
                for i, line in enumerate(lines):
                    # Title: choose the first non-empty line that doesn't start with a label or common page text
                    if journal_title is None and line.strip() and not re.search(r"^ISSN|^Found |^Back to Search|^English$|^Bookmark|^Latest|^Search journal|^About$|^Support$|^Resources$|^Legal$|^Related|^Journal Impact|^\u2728|^\u2318", line, re.I):
                        journal_title = line.strip()
                    
                    # Look for ISSN
                    if 'ISSN:' in line or 'issn' in line.lower():
                        issn = line.replace('ISSN:', '').strip()
                    
                    # Look for 2025 IF
                    m_if = re.search(r"(\d+(?:\.\d+)?)\s*2025\s*IF", result_text, re.I)
                    if m_if:
                        if_2025 = m_if.group(1)
                    
                    # Look for 5-YEAR IF
                    m_5 = re.search(r"(\d+(?:\.\d+)?)\s*5[- ]?YEAR\s*IF", result_text, re.I)
                    if m_5:
                        if_5year = m_5.group(1)
                    
                    # Look for quartile (JCR Q1, CAS B4, etc.)
                    if 'JCR' in line or 'CAS' in line or 'Q' in line:
                        quartile = line.strip()
                
                # Only include cards that have both a title and ISSN (real journals)
                if journal_title and issn and issn != 'N/A':
                    parsed.append({
                        'title': journal_title or '',
                        'issn': issn or '',
                        'if_2025': if_2025 or '',
                        'if_5year': if_5year or '',
                        'quartile': quartile or '',
                        'raw': result_text,
                    })
                
                # Print raw text for debugging if needed
                # print(f"\n    Raw text:\n    {result_text}\n")
                
            except Exception as e:
                print(f"    Error extracting from result {result_idx}: {str(e)}")

        print(f"  Parsed {len(parsed)} result(s) from {len(results)} card(s)")

        if not parsed:
            record_unresolved({
                "journal_id": journal_id,
                "requested_name": journal_name,
                "reason": "parse_failed"
            })
            continue

        # Prefer exact match on title; else show first few
        # Normalize: lowercase, collapse whitespace, replace '&' with 'and', remove punctuation
        def normalize_title(text):
            text = text.lower().strip()
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"\s*&\s*", " and ", text)
            text = re.sub(r"[^a-z0-9\s]", "", text)
            return text.strip()
        
        normalized_query = normalize_title(journal_name)
        exact = [p for p in parsed if normalize_title(p['title']) == normalized_query]

        best = exact[0] if exact else parsed[0]
        record_success({
            "journal_id": journal_id,
            "requested_name": journal_name,
            "matched_title": best.get('title', ''),
            "issn": best.get('issn', ''),
            "if_2025": best.get('if_2025', ''),
            "if_5year": best.get('if_5year', ''),
            "quartile": best.get('quartile', ''),
            "raw": best.get('raw', '')
        })

        to_show = exact[:1] if exact else parsed[:3]
        for i, p in enumerate(to_show, 1):
            print(f"\n  Result {i}:")
            if p['title']:
                print(f"    Title: {p['title']}")
            if p['issn']:
                print(f"    ISSN: {p['issn']}")
            if p['if_2025']:
                print(f"    2025 IF: {p['if_2025']}")
            print(f"    5-YEAR IF: {p['if_5year'] or 'Not found'}")
            if p['quartile']:
                print(f"    Quartile: {p['quartile']}")
        
    except TimeoutException:
        print(f"  ❌ Search timed out or page didn't load")
        record_unresolved({
            "journal_id": journal_id,
            "requested_name": journal_name,
            "reason": "timeout"
        })
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        record_unresolved({
            "journal_id": journal_id,
            "requested_name": journal_name,
            "reason": f"error: {str(e)}"
        })

output_dir = Path(__file__).parent
results_path = output_dir / "journal_metrics_results.json"
unresolved_path = output_dir / "journal_metrics_unresolved.json"

results_path.write_text(json.dumps(successes, indent=2), encoding="utf-8")
unresolved_path.write_text(json.dumps(unresolved, indent=2), encoding="utf-8")

print("\n" + "=" * 80)
print("Search complete!")
print(f"Saved results to {results_path}")
print(f"Saved unresolved to {unresolved_path}")

driver.quit()
