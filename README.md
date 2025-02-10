# AI Context Builder Pro – Supabase Edition  
**The Ultimate Repo Prompt Alternative for Windows, Mac, and Linux**  

A **lightweight** and **open-source** Python GUI tool that helps developers generate AI context prompts by **merging code files, project structure, and Supabase database exports** into a single output file.  

If you're looking for a **Repo Prompt Windows alternative** or an **open-source solution** to manage your AI context generation, this tool is designed to streamline your workflow with complete control over your AI-driven projects.  

📌 **Repository:** [github.com/l-media/AI-context-builder-pro-supabase-edition](https://github.com/l-media/AI-context-builder-pro-supabase-edition)

---

## 🔥 Features

✅ **Supabase Database Export**  
   - Connect to your **Supabase** database.  
   - Select specific tables and export both **schema** and **data** in JSON format.  
   - The tool automatically generates a Supabase-aware prompt to enhance AI context.  

✅ **Project Directory & Code Context**  
   - **Browse and select** specific code files and directories from your project.  
   - The interface automatically excludes unnecessary folders like `node_modules` and `.next`.  

✅ **Advanced Prompt Builder**  
   - Add and manage custom **pre-saved prompts** from the `prompts/` folder.  
   - The AI context will **combine database exports, project structure, and your selected prompts** in an optimized way.  

✅ **Full Control Over Output**  
   - Generates an `output.txt` file with:  
     - **Directory tree structure**  
     - **Important code files**  
     - **Selected Supabase database information**  
   - No forced formatting—use it however you want for AI integrations.  

✅ **Secure Credentials Management**  
   - Saves your Supabase connection details locally in `supabase_config.local` (Make sure to **add this file to `.gitignore`** to keep it private).  

---

## 🚀 Why Use This Tool?

If you're searching for a **Repo Prompt Windows alternative** or an **open-source tool** to generate AI context, this software is perfect for:  

- Developers who need **AI context generation** but want more control over **file selection and database prompts**.  
- Users who want **lightweight, local-first software** without relying on proprietary tools.  
- Anyone who prefers an **open-source alternative** to manage their AI projects seamlessly on Linux, macOS, and Windows.  

Unlike other tools, **this is fully customizable** and does **not lock you into a specific format or AI model**.  

---

## 📌 Prerequisites

- **Python 3.6+**
- **psycopg2-binary** (for Supabase integration)  
  Install via:
  ```bash
  pip install psycopg2-binary
  ```

---

## 🔧 Installation

1️⃣ **Clone the Repository**  
```bash
git clone https://github.com/l-media/AI-context-builder-pro-supabase-edition.git
cd AI-context-builder-pro-supabase-edition
```

2️⃣ **Secure Your Credentials**  
   - Add `supabase_config.local` to your `.gitignore` file to **keep your Supabase credentials private**.  

---

## 🖥️ Usage Guide

### 1️⃣ Run the GUI  
```bash
python AI-context-builder-pro.py
```
*(Replace `AI-context-builder-pro.py` with the actual filename if different.)*  

### 2️⃣ Connect to Supabase  
   - Enter your **Supabase Host, Port, Database, User, and Password**.  
   - Click **Connect** to fetch your database schema and tables.  
   - Select the tables you want to export and include them in the AI context.  

### 3️⃣ Select Code Files & Prompts  
   - **Click on files and directories** in the GUI to **add** or **exclude** them.  
   - Clicking an item again will **toggle its selection/exclusion**.  
   - Use the **"Clear All"** button to reset all choices instantly.  

### 4️⃣ Generate Your AI Context  
   - Click **"Generate Output"** and get an `output.txt` file containing:  
     - **Supabase export (if selected)**  
     - **Directory tree structure**  
     - **Selected code files and content**  

---

## 🎯 Key Improvements in This Version  

- **NEW:** Toggle selection/exclusion for files & folders by clicking again.  
- **NEW:** Compact **"Name" column** to keep **Add Code** and **Exclude** buttons closer for better usability.  
- **NEW:** "Clear All" button to **reset all selections** instantly.  
- **Improved:** Supabase **database prompt format**, removing unnecessary text.  
- **Improved:** No unnecessary **"Selected Prompts"** header in the output.  

This release makes the tool even more powerful and flexible for developers looking for an open-source solution to manage AI context generation. 🚀  

---

## ⚖️ License

This project is licensed under the [MIT License](LICENSE).  

## 💬 Contact

Contact us at: [Lince Media](https://lince.media/)  
