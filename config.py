import json
import os, sys

if getattr(sys, 'frozen', False):  
    base_dir = os.path.dirname(sys.executable)  # Running as an .exe
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Running as a .py script

# Construct the path to sorter_config.json
CONFIG_FILE = os.path.join(base_dir, "sorter_config.json")

GUIDEBOOK_FILE = os.path.join(base_dir, "syllabus.json")
ASSOCIATIONS_FILE = os.path.join(base_dir, "associations.json")

DEFAULT_CONFIG = {
    "source_dirs": [],
    "dest_heads": [],
    "score_threshold": 40,
    "cluster_threshold": 3,
    "ai_confidence_threshold": 0.7,
    "method_strengths": {
         "rule_based": 0.3,
         "hybrid": 0.5,
         "ai_based": 0.2
    },
    "duplicate_handling": {
         "skip_duplicates": True,
         "rename_duplicates": False
    },
    "ui": {
         "theme": "fluent",
         "font": "Segoe UI",
         "font_size": 12,
         "window_width": 1100,
         "window_height": 700,
         "layout": "grid"
    },
    "guidebook_file": GUIDEBOOK_FILE,      # Path to your user-supplied guidebook JSON.
    "associations_file": ASSOCIATIONS_FILE ,# Path where enriched associations will be stored.
    "association_update_mode": "full",         # Options: "full" or "incremental"
    "retain_old_associations": True           # If True, merge new associations with existing ones in incremental mode.
}

class Config:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.settings = {}
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                self.settings = self.deep_merge(DEFAULT_CONFIG, data)
                print(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                print(f"Error loading config: {e}")
                self.settings = DEFAULT_CONFIG.copy()
        else:
            print("No config file found. Using default configuration.")
            self.settings = DEFAULT_CONFIG.copy()

    def deep_merge(self, defaults, override):
        result = defaults.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self.deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def save(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

    def update(self, updates: dict):
        def recursive_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    recursive_update(d[k], v)
                else:
                    d[k] = v
        recursive_update(self.settings, updates)

if __name__ == "__main__":
    config = Config()
    print("Current configuration:")
    print(json.dumps(config.settings, indent=4))
    # Modify and update some settings for testing.
    config.set("score_threshold", 45)
    config.update({"ui": {"theme": "material", "font_size": 14}})
    config.save()

