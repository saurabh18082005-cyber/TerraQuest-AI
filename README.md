# 🌿 TerraQuest AI (HACTOBERFEST WEEK CHALLENGE)

**Explore. Discover. Compete.**

TerraQuest AI is an AI-assisted outdoor biodiversity explorer that encourages people to spend time outside, photograph their discoveries, and learn about the natural world.

## ✨ Features

- 🧭 Time-based outdoor missions
- 📸 Photo upload for nature discoveries
- 🤖 AI-assisted image identification using OpenRouter
- 🔎 Visible-evidence descriptions and identification limitations
- 🏆 Prototype explorer profiles and leaderboard foundations
- ✅ Explicit unverified status for AI-generated suggestions

## 🛠️ Tech Stack

- Python and Flask
- HTML, CSS, and JavaScript
- SQLite
- OpenRouter vision-model API

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/saurabh18082005-cyber/TerraQuest-AI.git
cd TerraQuest-AI
```

### 2. Install dependencies

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the API key

Create a `.env` file in the same directory as `app.py`:

```dotenv
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openrouter/free
```

Replace the placeholder with your own OpenRouter API key. Never commit `.env` or expose API credentials publicly.

### 4. Start the application

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## 🌱 Responsible AI

AI-generated identifications are suggestions, not scientific verification. Exact species and rarity should not be claimed without adequate evidence. The prototype keeps uncertain observations unverified.

## 🔭 Future Improvements

- Improve identification accuracy and verification.
- Add evidence-backed rarity scoring.
- Expand shared discovery records and leaderboard functionality.
- Explore open-weight models and local inference.

## 📄 Project Status

TerraQuest AI is a working prototype. Some features remain under development.

---

Built with curiosity for nature and open innovation.
