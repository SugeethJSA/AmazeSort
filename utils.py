import os
import re
import hashlib
from collections import defaultdict
from fuzzywuzzy import fuzz
import PyPDF2
import ctypes, sys

def prevent_sleep():
    if sys.platform == "win32":
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED flags to prevent sleep
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        
def allow_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

def normalize(text):
    text = re.sub(r'[-_.\s]+', ' ', text.lower()).strip()
    text = re.sub(r'\b(ls|chapter|ch)\s*\d*\b', '', text)
    return text.split()

def improved_score(file_terms, keyword_terms):
    if not file_terms or not keyword_terms:
        return 0
    total_comparisons = len(file_terms) * len(keyword_terms)
    match_scores = []
    for term in file_terms:
        for kw in keyword_terms:
            r = fuzz.ratio(term, kw)
            pr = fuzz.partial_ratio(term, kw)
            if r > 85 or pr > 85:
                match_scores.append(max(r, pr))
    if not match_scores:
        return 0
    avg_match = sum(match_scores) / len(match_scores)
    fraction = len(match_scores) / total_comparisons
    final_score = avg_match * fraction
    return final_score

def extract_pdf_text(filepath):
    if filepath.lower().endswith('.pdf'):
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = " ".join(page.extract_text() or "" for page in reader.pages[:2])
                return text.lower()
        except Exception as e:
            print(f"Warning: Could not extract text from {filepath}: {e}")
            return ""
    return ""

def cluster_files(files):
    clusters = defaultdict(list)
    for filepath, filename in files:
        terms = normalize(filename)
        key = tuple(sorted(t for t in terms if len(t) > 3))
        clusters[key].append((filepath, filename))
    # Adjust threshold: clusters with 3 or more files, or singletons.
    return {k: v for k, v in clusters.items() if len(v) >= 3 or len(v) == 1}

def compute_file_hash(filepath, algorithm="md5"):
    hash_func = hashlib.new(algorithm)
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        print(f"Error computing hash for {filepath}: {e}")
        return None

def is_duplicate(filepath, hash_cache):
    file_hash = compute_file_hash(filepath)
    if file_hash is None:
        return False, None
    if file_hash in hash_cache:
        return True, hash_cache[file_hash]
    else:
        hash_cache[file_hash] = filepath
        return False, None

if __name__ == "__main__":
    print("Normalization test:", normalize("CLASS_XII_Chemistry_Ch_14-Polymerization.pdf"))
    file_terms = normalize("Maths_Stand.pdf")
    keyword_terms = ["math", "algebra", "geometry"]
    print("Improved score:", improved_score(file_terms, keyword_terms))
    test_file = "example.pdf"  # Change to an existing file for testing
    print("File hash:", compute_file_hash(test_file))
