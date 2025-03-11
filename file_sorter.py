import os, shutil, time, traceback, json, subprocess
from utils import normalize, improved_score, extract_pdf_text, cluster_files, is_duplicate
from ai_model import TransformerAIModel
from config import Config
from collections import deque

class FileSorter:
    def __init__(self, config: Config):
        self.config = config
        self.source_dirs = config.get("source_dirs", [])
        self.dest_heads = config.get("dest_heads", [])
        self.score_threshold = config.get("score_threshold", 40)
        self.cluster_threshold = config.get("cluster_threshold", 3)
        self.method_strengths = config.get("method_strengths", {"rule_based": 0.3, "hybrid": 0.5, "ai_based": 0.2})
        self.duplicate_handling = config.get("duplicate_handling", {"skip_duplicates": True, "rename_duplicates": False})
        self.associations = {}
        self.syllabus = {}  # Initialize an empty guidebook
        self.ai_model = TransformerAIModel()
        self.operation_history = deque(maxlen=100)  # Track last 100 operations

    def set_syllabus(self, syllabus):
        self.syllabus = syllabus

    def load_associations(self, associations_file):
        if os.path.exists(associations_file):
            with open(associations_file, "r", encoding="utf-8") as f:
                self.associations = json.load(f)
            print("Associations loaded from", associations_file)
        else:
            print("Associations file not found. Using empty associations.")
            self.associations = {}

    def _get_duplicate_cache(self):
        return {}

    def score_rule_based(self, cluster):
        all_terms = []
        for filepath, filename in cluster:
            all_terms.extend(normalize(filename))
        best_dest = "General"
        best_score = 0
        steps = []
        if self.associations:
            # For each top-level key in associations, compute a score.
            for folder, info in self.associations.items():
                keywords = info.get("associations", [])
                score = improved_score(all_terms, keywords)
                steps.append(f"Rule-based: Folder '{folder}' score {score:.2f} using keywords {keywords}")
                if score > best_score:
                    best_score = score
                    best_dest = folder
        return best_dest, best_score, steps

    def score_hybrid(self, cluster):
        dest, score, steps = self.score_rule_based(cluster)
        bonus = 5  # Configurable bonus for hybrid approach.
        score += bonus
        steps.append(f"Hybrid: Added bonus of {bonus} to rule-based score, new score {score:.2f}")
        return dest, score, steps

    def score_ai_based(self, cluster):
        all_terms = []
        for filepath, filename in cluster:
            all_terms.extend(normalize(filename))
        pdf_text = " ".join(extract_pdf_text(fp) for fp, _ in cluster)
        combined_text = " ".join(all_terms) + " " + pdf_text
        try:
            dest, conf = self.ai_model.predict(combined_text)
            steps = [f"AI-based: Predicted destination '{dest}' with confidence {conf:.2f}"]
            return dest, conf * 100, steps
        except Exception as e:
            return "General", 0, [f"AI-based: Error during prediction: {e}"]

    def _get_destination_for_cluster(self, cluster, log):
        log = log
        rule_dest, rule_score, rule_steps = self.score_rule_based(cluster)
        hybrid_dest, hybrid_score, hybrid_steps = self.score_hybrid(cluster)
        ai_dest, ai_score, ai_steps = self.score_ai_based(cluster)
        weights = self.method_strengths
        weighted_rule = rule_score * weights.get("rule_based", 0)
        weighted_hybrid = hybrid_score * weights.get("hybrid", 0)
        weighted_ai = ai_score * weights.get("ai_based", 0)
        scores = {"rule": weighted_rule, "hybrid": weighted_hybrid, "ai": weighted_ai}
        for filepath, filename in cluster:
            log["Predictions"].append({"file" : filepath, "predictions": {"rule-based": {"destination": rule_dest,"score": rule_score, "steps": rule_steps}, "hybrid": {"destination": hybrid_dest,"score": hybrid_score, "steps": hybrid_steps}}, "ai": {"destination": ai_dest,"score": ai_score, "steps": ai_steps} })
        best_method = max(scores, key=scores.get)
        if best_method == "rule":
            return rule_dest, rule_score, rule_steps, "rule", log
        elif best_method == "hybrid":
            return hybrid_dest, hybrid_score, hybrid_steps, "hybrid", log
        else:
            return ai_dest, ai_score, ai_steps, "AI", log

    def shift_folders(self, dest_base, dest_folder):
        final_path = os.path.join(dest_base, dest_folder)
        if not os.path.exists(final_path):
            os.makedirs(final_path)
        return final_path

    def sort_files(self, progress_callback=None):
        log = {"Sorted": [], "Unsorted": [], "Duplicates": [], "Errors": [], "Predictions": []}
        hash_cache = self._get_duplicate_cache()
        all_files = []
        for src in self.source_dirs:
            for root, _, files in os.walk(src):
                for f in files:
                    all_files.append((os.path.join(root, f), f))
        clusters = cluster_files(all_files)
        clusters_list = list(clusters.values())
        total_clusters = len(clusters_list)
        method = ""
        if progress_callback:
            progress_callback(0)
        for idx, cluster in enumerate(clusters_list):
            try:
                dest_folder, score, method_steps, method, log = self._get_destination_for_cluster(cluster, log)
                final_dest = self.shift_folders(self.dest_heads[0], dest_folder)
                for filepath, filename in cluster:
                    dup, dup_path = is_duplicate(filepath, hash_cache)
                    destination_path = os.path.join(final_dest, filename)
                    if dup:
                        log["Duplicates"].append({"file": filename, "source": filepath, "duplicate_of": dup_path})
                        continue
                    if score < self.score_threshold:
                        log["Unsorted"].append({"file": filename, "source": filepath, "reason": f"Low score: {score:.2f}", "predicted destination": destination_path})
                        print(f"Skipped '{filename}' due to low score: {score:.2f}; predicted destination was '{destination_path}'")
                        continue
                    try:
                        shutil.move(filepath, destination_path)
                        self.operation_history.append(("move", (filepath, destination_path)))  # Log operation
                        log["Sorted"].append({"file": filename, "source": filepath, "destination": destination_path,
                                               "detail": f"Matched via {method_steps}"})
                    except Exception as move_err:
                        log["Errors"].append({"move_error": str(move_err), "file": filepath, "trace": traceback.format_exc()})
            except Exception as cluster_err:
                log["Errors"].append({"cluster_error": str(cluster_err), "trace": traceback.format_exc()})
            if progress_callback and total_clusters:
                progress = int(((idx+1) / total_clusters) * 100)
                progress_callback(progress)
        with open("file_sorting_log.json", "w") as f:
            json.dump(log, f, indent=4)
        return log

if __name__ == "__main__":
    from config import Config
    config = Config()
    sorter = FileSorter(config)
    associations_file = config.get("associations_file", "associations.json")
    sorter.load_associations(associations_file)
    log = sorter.sort_files()
    print("Sorting completed. Log:")
    print(json.dumps(log, indent=4))
