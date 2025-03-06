# AmazeSort
A Python-based app to sort files using rule-based, hybrid-approach and/or fully AI-based approach to sort files.
Current Head Maintainer: SugeethJSA

## Note: 

Currently, this app is in the alpha testing stage. However, there are multiple bugs and unimplemented features that may cause the app to crash or sort incorrectly. The aim of the roadmap currently is to ensure that the app's UI is properly fixed. Over time, there will be logic. At this stage, the app is self-contained./

To ensure the app works properly, run the following before starting to use the app:

`pip install -r requirements.txt` 

`python -m spacy download en_core_web_sm`

AI Notice: AI has been used in the development of the majority part of this app, as this my first time developing an actual python app. I have usually developed complex Apple Shortcuts, but I ended up creating this app only to help me sort the myriads of files on my laptop.

## Contributions and Licensing

This project currently follows a dual-licensing strategy.
The public version of the project is licensed under the GNU General Public License v3.0 (GPL-3.0), however if you require a more permissive license for proprietary use or general use, please contact the head maintainer. 
By downloading, modifying, or contributing to this project, you agree to the terms of GPL-3.0.  

Contributors are required to sign a CLA before contributing, to ensure that the future of this project can remain under my purview; for now. Since this is the first time I'm opening up a project for community development, I wanna have my reservations.
There is a generic CLA that is set for hassle-free contributions. If you want a more permissive CLA, please contact the head maintainer.


## Short Description
Hello guys! I'm SugeethJSA, the head maintainer and original creator of this app along with multiple AI "co-creators" (I have used so many different AI models that I'm not sure which models to mention.)

I created this app to solve a huge frustation of mine, that is organising files. This is a hugely irritating part of maintaining perfect set-ups while documenting our digital lives. We just keep download stuff and tell ourselves that we'll store it somewhere else later.

The logic behind the app, that is, how the UI is drawn, how the sorting logic is done... all of that was mostly decided by me. I have worked to tune different aspects of this app, because AI being AI has limited context, thus it keeps deciding things for itself. AI has a very small context window... so this is what they call "AI slop", i guess?

Anyways, this app has been desgined with the intent to use transformer models to find connections between folders and files in your existing folder setup and store files accordingly.

We have three modes:
1. Rule-based approach (traditional approach)
2. Hybrid approach (traditional, but uses an Associations.json created by transformer models to sort files)
3. AI-based approach

# AmazeSort Knowledge Transfer Document

## Overview

**AmazeSort** is supposed to be an enterprise-grade file sorter application that organizes educational files (and other types) into a structured directory based on user-defined rules, enriched associations, and AI model predictions. The system is designed to be fully configurable and generalized—users supply a guidebook (in JSON format) that describes associations (e.g., subjects, chapters, keywords), and the application scans destination directories to build an enriched associations tree. The sorter then uses a transformer-based model (DistilBERT) to classify files based on file name and content, combine results with heuristic fuzzy matching, and finally move files into appropriate subdirectories.

Designed around a 4 year old laptop, it leverages CPU and integrated GPU (or you could update the code to support discrete GPUs too)
Original Laptop Specs:
CPU: Intel 11th Gen i5 mobile-platform
GPU: Intel iRIS Xe Graphics

## Purpose

- **Generalization:**\
  AmazeSort is not limited to a fixed curriculum. It allows users to define their own hierarchical guidebook (known as syllabus.json) and even supply extra training examples via a dictionary file.

- **AI-Enhanced Classification:**\
  The system uses a transformer-based classifier, trained on data derived from the guidebook and the destination directory structure, to assign files to categories (or directories) with high accuracy.

- **Dynamic Association Generation:**\
  The associations module scans the destination directories recursively and merges that structure with the user-supplied guidebook. An optional transformer-based synonym generator (using DistilGPT2) enriches these associations. The system supports both full rebuild and incremental updates with configurable options.

- **Duplicate Detection:**\
  Before moving files, AmazeSort detects duplicates (using file hashes) to avoid redundant processing.

- **Modern, Responsive UI:**\
  The user interface is built with PySide6 and styled with a Fluent/Material-inspired look. It provides real-time progress updates, logs all operations in a log area, and exposes all configuration options (including thresholds, method strengths, and update modes).

- **Extensibility:**\
  The design is modular so that future enhancements (such as native WinUI3 integration, a more advanced logging system, or integration with external databases) can be added without rewriting the entire system.

## Architecture & Modules

### 1. **Configuration Module (********`config.py`********)**

- **Purpose:**\
  Manages application settings such as source/destination directories, scoring thresholds, method strengths (rule‑based, hybrid, AI‑based), duplicate handling options, UI styling, and association update settings.

- **Key Features:**

  - Reads and writes a JSON file (e.g., `sorter_config.json`) to persist user settings.
  - Provides helper methods (`get()`, `set()`, and `update()`) for accessing and updating configuration.

### 2. **Utilities Module (********`utils.py`********)**

- **Purpose:**\
  Contains common helper functions used across the application.

- **Key Features:**

  - **Normalization & Fuzzy Matching:** Functions to clean and tokenize file names and calculate F1-like scores using fuzzy matching (with fuzzywuzzy).
  - **PDF Text Extraction:** Uses PyPDF2 to extract text from PDF files.
  - **Duplicate Detection:** Functions to compute file hashes (e.g., MD5 or SHA‑256) and check for duplicates.
  - **Directory Clustering:** Groups similar files based on their normalized terms.

### 3. **Associations Module (********`associations.py`********)**

- **Purpose:**\
  Generates a comprehensive associations tree that enriches the destination directory structure with keywords. It combines the user-supplied guidebook with a recursive scan of the destination directories and optionally uses a transformer (e.g., distilgpt2) to generate additional synonyms.

- **Key Features:**

  - **Recursive Directory Scanning:** Builds a nested dictionary of the destination directory.
  - **Enrichment with Guidebook:** Merges the scanned structure with the guidebook.
  - **Configurable Update Modes:** Supports “full” vs. “incremental” updates and an option to retain old associations using a helper function (`deep_merge_associations()`).
  - **Output:** Saves the enriched associations to a JSON file (e.g., `associations.json`).

### 4. **AI Model Module (********`ai_model.py`********)**

- **Purpose:**\
  Implements a transformer-based classification model using Hugging Face’s DistilBERT.

- **Key Features:**

  - **Tokenizer and Model Initialization:** Loads DistilBertTokenizerFast and DistilBertForSequenceClassification.
  - **Training:** The `train()` method converts training texts and labels, tokenizes the data (with explicit truncation and padding), and uses Hugging Face’s Trainer to fine-tune the model.
  - **Prediction:** The `predict()` method processes input text and returns the predicted label and confidence.
  - **Saving and Loading:** The model and its tokenizer, along with the label encoder, are saved and loaded via pickle and Hugging Face’s native save methods.
  - **GPU Acceleration:** Uses `torch-directml` if available on Windows 11, otherwise defaults to CPU.

- **Note:**\
  The model is only as good as the training data. It must be trained on a comprehensive dataset built from the guidebook, a dictionary of extra examples, and the recursively scanned directory structure.

### 5. **File Sorter Module (********`file_sorter.py`********)**

- **Purpose:**\
  Contains the core logic for scanning, clustering, and sorting files into the correct directories.

- **Key Features:**

  - **Clustering:** Groups files based on normalized terms.
  - **Multi-Method Decision Making:** Implements three scoring methods: rule-based (using enriched associations), hybrid (combining rule-based scores with additional bonuses), and fully AI-based (using the transformer’s prediction).
  - **Weighted Aggregation:** Uses user-configurable strengths to select the final destination.
  - **File Movement:** Moves files to their target directories and logs each operation.
  - **Duplicate Handling:** Checks for duplicates and either skips or renames them based on configuration.

### 6. **UI Module (********`main_ui.py`******** and ********`settings_dialog.py`******** )**

- **Purpose:**\
  Provides a modern, attractive user interface using PySide6 (with a Fluent/Material-inspired design) to manage configuration, initiate training and sorting, and display logs and progress.

- **Key Features:**

  - **Directory and Configuration Management:** Users can add/remove source and destination directories and modify thresholds, method strengths, and association update settings via the UI.
  - **Progress and Log Display:** Dual progress bars for training and sorting, plus a text area that captures and displays all log output.
  - **Worker Threads:** Uses QThread subclasses (AssociationsWorker, TrainWorker, SortWorker) to perform long-running operations in the background, keeping the UI responsive.
  - **Splash Screen (Optional):** A splash screen is displayed during startup for a smoother user experience.
  - **Redirecting Logs:** Standard output and error are redirected to the UI’s log area.

### 7. **Entry Point (********`app.py`********)**

- **Purpose:**\
  Ties all modules together and launches the UI.

- **Key Features:**
  
  - **Splash Screen**: Has a splash screen that starts up at launch to ensure that the user doesn't panic.
  - **Configuration Loading:** Loads the config file from a relative path using `__file__` to ensure correct file locations.
  - **Associations Generation:** Checks for existing associations and, if necessary, defers generation to the UI’s training routine.
  - **UI Launch:** Initializes the QApplication and MainWindow, and starts the event loop.


---

## Design Decisions and Future Enhancements

1. **Separation of Concerns:**\
   Each module is designed to be independent. Configuration management, utility functions, associations generation, AI model training, file sorting logic, and UI(s) are all handled in separate files. This makes the code easier to maintain and extend.

2. **User Configurability:**\
   All key parameters (e.g., method strengths, update modes, duplicate handling, etc.) are exposed through the configuration file and the UI. This gives users complete control over the behavior of the file sorter.

3. **Incremental vs. Full Update:**\
   The associations module can operate in either a full rebuild mode or an incremental update mode. In incremental mode, only changes in the destination directory are processed, and optionally, old associations can be merged.

4. **Worker Threads for Responsiveness:**\
   All long-running tasks (associations generation, model training, file sorting) run in separate threads. This keeps the UI responsive and allows for progress reporting and cancellation.

5. **Prevention of System Sleep:**\
   During long operations, system sleep is prevented by calling Windows API functions (using `ctypes`) to maintain performance.

6. **Splash Screen and Log Redirection:**\
   The UI includes a splash screen to provide immediate visual feedback on startup. Standard output and error are redirected to the UI’s log area so that the terminal remains silent during normal operation.

7. **Future Migration to WinUI3:**\
   While the current UI is built with PySide6 for rapid development, a future version could use WinUI3 for deeper Windows integration if needed. This would involve using pythonnet or a web-based approach.

---

## Steps for Setup and Execution

1. **Configuration:**

   - Update `sorter_config.json` with valid source directories, destination directories, and paths for the guidebook (`syllabus.json`) and associations file.
   - Configure thresholds, method strengths, and association update options.

2. **Training Data:**

   - Ensure that your guidebook (syllabus) and optional dictionary (extra examples) are correctly formatted in JSON.
   - The training process will combine data from the guidebook and recursively scanned directories to create a comprehensive training dataset.

3. **Launching the Application:**

   - Run `app.py` (ensuring relative paths are correctly resolved).
   - The application starts with a splash screen, then loads the main UI.
   - The user can then initiate training, which will first generate or update associations, and then train the transformer model with progress feedback.
   - Sorting and duplicate handling are triggered via the UI.

4. **Monitoring and Debugging:**

   - All logs are redirected to the UI’s log area.
   - Use the progress bars to monitor both associations generation and training.
   - If any errors occur, they are logged in the UI.

---

## Wanna know more about me?

Then  visit my bio-page at [(https://sugeeth.craft.me)]


