import os, pickle, json, sys, logging, subprocess

def detect_gpu_vendor():
    vendors = []

    try:
        # Check for NVIDIA GPU
        nvidia_check = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if nvidia_check.returncode == 0:
            vendors.append("NVIDIA")
    except FileNotFoundError:
        pass

    try:
        # Check for AMD GPU
        amd_check = subprocess.run(["rocminfo"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if amd_check.returncode == 0:
            vendors.append("AMD")
    except FileNotFoundError:
        pass

    try:
        # Check for Intel GPU
        intel_check = subprocess.run(["sycl-ls"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if intel_check.returncode == 0:
            vendors.append("Intel")
    except FileNotFoundError:
        pass

    return vendors if vendors else ["Unknown"]

gpu_vendors = detect_gpu_vendor()

if "NVIDIA" in gpu_vendors:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
if "AMD" in gpu_vendors:
    os.environ["HIP_VISIBLE_DEVICES"] = "0"
if "Intel" in gpu_vendors:
    os.environ["ONEAPI_DEVICE_SELECTOR"] = "gpu:0"

if "Unknown" in gpu_vendors:
    print("No supported GPU detected.")
else:
    print(f"Detected GPU vendor(s): {', '.join(gpu_vendors)}")

# -------------------------------

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
SITE_PACKAGES = os.path.join(APP_DIR, "site-packages")

# Add site-packages to sys.path so app.py can find the installed modules
if SITE_PACKAGES not in sys.path:
    sys.path.insert(0, SITE_PACKAGES)

# Now app.py can import torch, torchvision, torchaudio, etc.
try:
    import torch
    logging.info(f"Torch found! Version: {torch.__version__}")
except ImportError:
    logging.error("Torch not found. Make sure GPU installer ran successfully.")

import numpy as np
from sklearn.preprocessing import LabelEncoder
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast, Trainer, TrainingArguments, TrainerCallback
from datasets import Dataset
import ctypes
from utils import prevent_sleep, allow_sleep

class CancellationCallback(TrainerCallback):
    def __init__(self, cancel_flag_func):
        self.cancel_flag_func = cancel_flag_func
    def on_step_end(self, args, state, control, **kwargs):
        if self.cancel_flag_func():
            control.should_early_stop = True
            control.should_save = True

# Device selection update for CUDA support:
import torch
import logging

def get_device():
    """Detects the best available device for computation (CUDA, DirectML, ROCm, or CPU)."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logging.info("✅ Using NVIDIA CUDA for GPU acceleration.")
        return device

    try:
        import torch_directml
        device = torch_directml.device()
        logging.info(f"✅ Using Intel/AMD DirectML for GPU acceleration: {device}")
        return device
    except ImportError:
        logging.warning("⚠ torch-directml not found. Skipping DirectML support.")

    if hasattr(torch, "has_rocm") and torch.has_rocm:
        device = torch.device("rocm")
        logging.info("✅ Using AMD ROCm for GPU acceleration.")
        return device

    logging.info("⚠ No GPU detected. Falling back to CPU.")
    return torch.device("cpu")

device = get_device()

def build_training_dataset(guidebook, dictionary):
    texts = []
    labels = []
    # Loop through your guidebook (or dictionary) structure.
    for subject, content in guidebook.items():
        if isinstance(content, dict):
            for unit, chapters in content.items():
                for chapter, keywords in chapters.items():
                    text = f"{subject} {chapter} {' '.join(keywords)}"
                    texts.append(text)
                    labels.append(f"{subject}/{chapter}")
        elif isinstance(content, list):
            text = f"{subject} {' '.join(content)}"
            texts.append(text)
            labels.append(f"{subject}/General")
    # Optionally, you can also incorporate extra examples from dictionary.json
    # e.g., for additional training examples.
    # Merge or extend texts and labels as needed.
    return texts, labels

class TransformerAIModel:
    def __init__(self):
        self.tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")
        self.model = None
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.device = device
        self.cancelled = False  # Added cancellation flag

    def train(self, texts, labels, output_dir="transformer_model", epochs=2, progress_callback=None):

        prevent_sleep()

        # Reset cancellation flag.
        self.cancelled = False

        # Convert string labels to integers.
        self.label_encoder.fit(labels)
        int_labels = self.label_encoder.transform(labels)
        dataset = Dataset.from_dict({"text": texts, "label": int_labels})
        def tokenize_function(examples):
            return self.tokenizer(examples["text"], truncation=True, padding="max_length", max_length=128)
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        tokenized_dataset = tokenized_dataset.train_test_split(test_size=0.1)
        num_labels = len(self.label_encoder.classes_)
        self.model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=num_labels)
        self.model.to(self.device)
        training_arguments = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=8,
            per_device_eval_batch_size=8,
            evaluation_strategy="epoch",
            logging_steps=10,
            save_steps=50,
            disable_tqdm=True,
            logging_dir="./logs"
        )
        # Add the cancellation callback.
        trainer = Trainer(
            model=self.model,
            args=training_arguments,
            train_dataset=tokenized_dataset["train"],
            eval_dataset=tokenized_dataset["test"],
            callbacks=[CancellationCallback(lambda: self.cancelled)]
        )
        if progress_callback:
            progress_callback(10)
        trainer.train()
        if self.cancelled:
            raise Exception("Training cancelled by user.")
        if progress_callback:
            progress_callback(100)
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        self.is_trained = True
        logging.info(f"Transformer AI model trained with {len(texts)} examples.")
        logging.info("Training completed successfully.")
        allow_sleep()

    def stop(self):
        self.cancelled = True

    def predict(self, text):
        if not self.is_trained or self.model is None:
            raise ValueError("Model is not trained.")
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)[0].cpu().numpy()
        confidence = float(np.max(probs))
        pred_idx = int(np.argmax(probs))
        pred_label = self.label_encoder.inverse_transform([pred_idx])[0]
        return pred_label, confidence

    def save(self, filename):
        if self.model is None:
            raise ValueError("No model to save.")
        temp_dir = "temp_transformer_model"
        self.model.save_pretrained(temp_dir)
        self.tokenizer.save_pretrained(temp_dir)
        data = {"model_dir": temp_dir, "label_encoder": self.label_encoder}
        with open(filename, "wb") as f:
            pickle.dump(data, f)
        logging.info(f"Transformer model saved to {filename}")

    def load(self, filename):
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                data = pickle.load(f)
            self.label_encoder = data["label_encoder"]
            self.model = DistilBertForSequenceClassification.from_pretrained(data["model_dir"])
            self.model.to(self.device)
            self.is_trained = True
            logging.info(f"Transformer model loaded from {filename}")
            return True
        return False

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    # Load the guidebook and dictionary
    with open("syllabus.json", "r", encoding="utf-8") as f:
        guidebook = json.load(f)
    with open("dictionary.json", "r", encoding="utf-8") as f:
        dictionary_data = json.load(f)
    
    texts, labels = build_training_dataset(guidebook, dictionary_data)
    logging.info(f"Training data built with {len(texts)} examples.")
    
    model = TransformerAIModel()
    model.train(texts, labels, epochs=5)  # Increase epochs as needed
    pred, conf = model.predict("Organic Chemistry reaction mechanisms")
    logging.info("Prediction: " + str(pred) + " Confidence: " + str(conf))
    model.save("transformer_ai_model.pkl")
    new_model = TransformerAIModel()
    new_model.load("transformer_ai_model.pkl")
    pred2, conf2 = new_model.predict("Quantum mechanics introduction")
    logging.info("Reloaded prediction: " + str(pred2) + " Confidence: " + str(conf2))
