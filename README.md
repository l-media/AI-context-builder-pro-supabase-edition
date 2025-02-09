# AI Context Builder Pro – Supabase Edition

A lightweight Python GUI tool for developers that creates AI context prompts by merging your project’s code files, directory structure, and Supabase (PostgreSQL) table exports—all in one output file.  
**Repository:** [github.com/l-media/AI-context-builder-pro-supabase-edition](https://github.com/l-media/AI-context-builder-pro-supabase-edition)

## Features

- **Supabase Integration:**  
  Connect to your Supabase database and export selected tables (both schema and data) as JSON.
- **Code & Directory Context:**  
  Browse and select code files and folders from your project to include essential context.
- **Prompt Builder:**  
  Combine exported database data with custom text prompts for comprehensive AI context.
- **Secure Credentials:**  
  Stores your Supabase connection details locally in `supabase_config.local` (remember to add this file to your `.gitignore`).

## Prerequisites

- **Python 3.6+**
- **psycopg2-binary**  
  Install via:
  ```bash
  pip install psycopg2-binary
  ```

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/l-media/AI-context-builder-pro-supabase-edition.git
   cd AI-context-builder-pro-supabase-edition
   ```

2. **Secure Your Credentials:**
   Add `supabase_config.local` to your `.gitignore` to keep your Supabase config safe.

## Usage

1. **Run the Script:**
   ```bash
   python AI-context-builder-pro.py
   ```
   Replace `AI-context-builder-pro.py` with the actual filename.

2. **Connect to Supabase:**
   - When the GUI opens, enter your Supabase host, port, database, user, and password.
   - Click **Connect** to fetch available tables.
   - Optionally, select and export tables to generate a custom prompt from the JSON export.

3. **Select Code Files & Prompts:**
   - Use the interface to check which code files and directories you want to include.
   - Manage preset prompts from the `prompts/` folder to further tailor your AI context.

4. **Generate Output:**
   - Click **Generate Output** to create an `output.txt` file that merges:
     - Supabase export prompt (if selected)
     - Your project’s directory structure
     - The contents of chosen code files

## License

This project is licensed under the [MIT License](LICENSE).
