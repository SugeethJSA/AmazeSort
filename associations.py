import os, json, re, ctypes, sys, torch
from transformers import pipeline
import transformers
transformers.logging.set_verbosity_error()

PARAPHRASER = None
def get_paraphraser():
    global PARAPHRASER
    if PARAPHRASER is None:
        if torch.cuda.is_available():
            PARAPHRASER = pipeline("text2text-generation",
                                   model="ramsrigouthamg/t5_paraphraser",
                                   tokenizer="ramsrigouthamg/t5_paraphraser",
                                   device=0)
        else:
            PARAPHRASER = pipeline("text2text-generation",
                                   model="ramsrigouthamg/t5_paraphraser",
                                   tokenizer="ramsrigouthamg/t5_paraphraser")
    return PARAPHRASER

def prevent_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        
def allow_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

def scan_directory_structure(root_dir, progress_callback=None):
    total_items = sum([len(files) for r, d, files in os.walk(root_dir)])
    if total_items == 0:
        total_items = 1
    processed_items = 0
    def scan_directory(dir_path):
        nonlocal processed_items
        dir_structure = {}
        try:
            for item in os.listdir(dir_path):
                path = os.path.join(dir_path, item)
                if os.path.isdir(path):
                    dir_structure[item] = {
                        "name": item,
                        "path": path,
                        "children": scan_directory(path)
                    }
                processed_items += 1
                if progress_callback:
                    progress_callback(int((processed_items / total_items) * 50))
        except Exception as e:
            print(f"Error scanning directory {dir_path}: {e}")
        return dir_structure
    return scan_directory(root_dir)

def load_guidebook(guidebook_file):
    if not os.path.exists(guidebook_file):
        print(f"Warning: Guidebook file '{guidebook_file}' not found. Proceeding without it.")
        return {}
    with open(guidebook_file, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_synonyms(folder_name, base_keywords=None, max_synonyms=5):
    try:
        paraphraser = get_paraphraser()
        prompt = f"paraphrase: {folder_name} in multiple ways and generate semantic synonyms. Do not output anything else."
        if base_keywords:
            prompt += " Context: " + ", ".join(base_keywords)
        results = paraphraser(prompt, num_beams=max_synonyms, num_return_sequences=max_synonyms, max_length=50)
        synonyms = [res['generated_text'].strip() for res in results if res.get("generated_text")]
        return list(dict.fromkeys(synonyms))[:max_synonyms]
    except Exception as e:
        print(f"Error generating synonyms for '{folder_name}': {e}")
        return []

def enrich_structure_with_associations(structure, guidebook, progress_callback=None):
    total_items = sum([len(folder_info["children"]) for folder_info in structure.values()])
    if total_items == 0:
        total_items = 1
    processed_items = 0

    def enrich_folder(folder_name, folder_info):
        nonlocal processed_items
        base_keywords = guidebook.get(folder_name, [])
        if not isinstance(base_keywords, list):
            if isinstance(base_keywords, dict):
                base_keywords = base_keywords.get("keywords", [])
            else:
                base_keywords = []
        try:
            generated_syns = generate_synonyms(folder_name, base_keywords)
            if not isinstance(generated_syns, list):
                generated_syns = []
        except Exception as e:
            print(f"Error generating synonyms for folder '{folder_name}': {e}")
            generated_syns = []
        try:
            associations = list(set(base_keywords + generated_syns))
        except Exception as e:
            print(f"Error merging keywords for folder '{folder_name}': {e}")
            associations = base_keywords
        folder_info["associations"] = associations

        if "children" in folder_info and isinstance(folder_info["children"], dict):
            folder_info["children"] = enrich_structure_with_associations(folder_info["children"], guidebook, progress_callback)
        
        processed_items += 1
        if progress_callback:
            progress = int((processed_items / total_items) * 100)
            progress = min(progress, 100)
            progress_callback(progress)

    for folder_name, folder_info in structure.items():
        enrich_folder(folder_name, folder_info)

    return structure

def deep_merge_associations(old_assoc, new_assoc):
    merged = old_assoc.copy()
    for key, new_val in new_assoc.items():
        if key in merged:
            old_assocs = merged[key].get("associations", [])
            new_assocs = new_val.get("associations", [])
            merged_assocs = list(set(old_assocs + new_assocs))
            merged[key]["associations"] = merged_assocs
            if "children" in new_val and "children" in merged[key]:
                merged[key]["children"] = deep_merge_associations(merged[key]["children"], new_val["children"])
            else:
                merged[key]["children"] = new_val.get("children", {})
        else:
            merged[key] = new_val
    return merged

def generate_associations(dest_dir, guidebook_file, output_file="associations.json", update_mode="full", retain_old=False, progress_callback=None):
    guidebook = load_guidebook(guidebook_file)
    structure = scan_directory_structure(dest_dir, progress_callback)
    new_enriched = enrich_structure_with_associations(structure, guidebook, progress_callback)

    if update_mode == "incremental" and os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                old_assoc = json.load(f)
            if retain_old:
                merged_assoc = deep_merge_associations(old_assoc, new_enriched)
            else:
                merged_assoc = new_enriched
            associations = merged_assoc
        except Exception as e:
            print(f"Error loading old associations: {e}. Proceeding with full rebuild.")
            associations = new_enriched
    else:
        associations = new_enriched

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(associations, f, indent=4, ensure_ascii=False)
        print(f"Enriched associations generated and saved to {output_file}")
    except Exception as e:
        print(f"Error saving associations: {e}")
    return associations

if __name__ == "__main__":
    dest_dir = input("Enter the destination directory path: ").strip()
    guidebook_file = input("Enter the guidebook JSON file path: ").strip()
    
    update_mode = input("Enter update mode (full/incremental) [full]: ").strip() or "full"
    retain_old_input = input("Retain old associations? (yes/no) [yes]: ").strip().lower() or "yes"
    retain_old = True if retain_old_input.startswith("y") else False
    
    prevent_sleep()
    associations = generate_associations(dest_dir, guidebook_file, output_file="associations.json", update_mode=update_mode, retain_old=retain_old)
    print(json.dumps(associations, indent=4, ensure_ascii=False))
    allow_sleep()
