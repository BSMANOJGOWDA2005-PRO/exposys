# Exposys Data Labs – Top 6 Candidate Selection & WhatsApp Notification

A complete, production-grade local web application built for the **Exposys Data Labs** coding task. The system processes an official candidate CSV dataset using Pandas, validates data integrity, dynamically ranks candidates by score (with stable tie-breaking), shortlists the **Top 6 candidates**, and generates personalized, ready-to-send WhatsApp notifications with pre-filled messages.

---

## 📌 Problem Statement

Given a candidate dataset (`Name`, `Phone`, `Score`), automate the process of:
1. Reading and validating candidate records.
2. Ranking candidates dynamically based on assessment scores.
3. Selecting the **Top 6 candidates** for the interview round.
4. Generating personalized notification text for each selected candidate.
5. Providing direct **WhatsApp click-to-chat** links pre-filled with the candidate's invitation message and Indian country code (`+91`).

---

## ✨ Features

- **Automated CSV Processing**: Ingests `dataset/dataset.csv` automatically via **Pandas** without hardcoding.
- **Robust Data Validation**:
  - Name is validated (non-empty, non-null).
  - Indian phone numbers are cleaned and formatted (removes dashes/spaces, ensures `91` country code).
  - Scores are validated as numeric and constrained within the range `[0, 100]`.
  - Malformed rows are gracefully trapped without crashing the app.
- **Dynamic Ranking Algorithm**:
  - Scores are sorted in descending order.
  - Same score tie-breaker preserves original CSV insertion order.
  - Dynamically assigns `Rank 1` to `Rank 6`.
  - Gracefully handles cases where dataset has fewer than 6 candidates.
- **Interactive Technical Dashboard**:
  - **Summary Cards**: Displays Total Candidates, Selected Candidates, Highest Score, and Average Score.
  - **Dynamic Sender Form**: Interactive inputs for `Your Name` and `Roll Number` which immediately re-render message templates across all candidates.
  - **Shortlisted Badges**: Visual indicator tags for candidate statuses and gold/silver/bronze rank badges.
- **WhatsApp Click-to-Chat Integration**:
  - Constructs `https://wa.me/91<PHONE>?text=<URL_ENCODED_MESSAGE>` for each candidate.
  - One-click **Send WhatsApp** button directly opens the recipient's WhatsApp chat with message pre-filled.
- **Message Preview & Copy**:
  - Modal dialog with candidate details and full message preview.
  - One-click **Copy Message** to clipboard with toast notification.
- **RESTful API**: Standardized JSON endpoints consumed via JavaScript `fetch()`.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12+, Flask 3.1, Pandas 3.0
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+ with `fetch()` API)
- **Styling**: Modern responsive CSS with CSS custom properties (variables), Flexbox, CSS Grid
- **Architecture**: Client-Server architecture with REST APIs

---

## 🗂️ Project Structure

```text
Exposys/
│
├── app.py                  # Flask backend & CSV ranking engine
├── test_app.py             # Automated test suite
├── requirements.txt        # Python dependencies
├── README.md               # Documentation & interview guide
│
├── dataset/
│   └── dataset.csv         # Candidate CSV dataset (9 candidates)
│
├── templates/
│   └── index.html          # Dashboard HTML template
│
└── static/
    ├── css/
    │   └── style.css       # Responsive styling & components
    └── js/
        └── app.js          # REST API integration & UI state
```

---

## 📊 Dataset Description

The provided dataset is located at `dataset/dataset.csv`:

```csv
Name,Phone,Score
Exposys,7892053145,97
Prashanth,9972155027,98
Vishnu,7795207065,96
Chaitra,8197261688,73
Theertha,9481770008,94
Reecha,9206488709,92
Ramya,8762147487,80
Ksihore,8139921838,99
Mahindar,9346725307,99
```

---

## 🧮 Algorithm & Logic Explanation (Interview Prep)

### 1. How the CSV is loaded
`pandas.read_csv("dataset/dataset.csv")` loads the file into a DataFrame. The column names are stripped of whitespace and validated against `{"Name", "Phone", "Score"}`.

### 2. How Data is Validated & Phone Cleaned
Each row is iterated over:
- **Name**: Checked using `pd.isna()` and `.strip()`.
- **Phone**: Regex `re.sub(r'\D', '', phone)` extracts only numeric digits. If 10 digits, it prefixes `91`. If 11 digits starting with `0`, it drops `0` and prefixes `91`. If 12 digits starting with `91`, it leaves it intact.
- **Score**: Converted with `float(score)`. Checked if `0 <= score <= 100`.

### 3. How Candidates are Sorted & Tie-Breaking
Candidates are sorted using Python's built-in Timsort:
```python
ranked = sorted(candidates, key=lambda c: (-c["score"], c["original_order"]))
```
- `-c["score"]` ensures highest scores come first (descending).
- `c["original_order"]` serves as the tie-breaker: if scores match (e.g., Ksihore and Mahindar both have score 99), whoever appeared earlier in the CSV is awarded the higher rank.

### 4. How the Top 6 are Selected & Ranks Assigned
- Enumerate over the sorted array from index `1` to `N`.
- Assign `rank = rank_idx` and `rank_label = f"Rank {rank_idx}"`.
- Sliced using `top6 = ranked[:6]`.

### 5. How the Personalized Message is Generated
```python
def generate_personalized_message(name, score, your_name=None, roll_number=None):
    sender_name = your_name.strip() if your_name else "Your Name"
    sender_roll = roll_number.strip() if roll_number else "Roll Number"
    
    return (
        f"Dear {name},\n\n"
        f"Congratulations!\n\n"
        f"You have been shortlisted for the Exposys Data Labs Coding Round.\n\n"
        f"Your assessment score is {score}.\n\n"
        f"Regards,\n"
        f"{sender_name}\n\n"
        f"Roll Number: {sender_roll}"
    )
```

### 6. How the WhatsApp URL is Created
Using Python's standard `urllib.parse.quote`:
```python
encoded_message = urllib.parse.quote(message_text)
whatsapp_url = f"https://wa.me/{phone_cleaned}?text={encoded_message}"
```
Example generated link:
```text
https://wa.me/918139921838?text=Dear%20Ksihore%2C%0A%0ACongratulations%21...
```

---

## 🌐 REST API Documentation

| Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/` | None | Serves the HTML dashboard |
| `GET` | `/api/top6` | `your_name`, `roll_number` | Returns Top 6 candidates with summary metrics |
| `GET` | `/api/candidates` | `your_name`, `roll_number` | Returns all ranked candidates |
| `GET` | `/api/candidate/<id>`| `your_name`, `roll_number` | Returns single candidate details & message |

### Example API Response (`/api/top6`)

```json
{
  "average_score": 97.17,
  "has_less_than_6": false,
  "highest_score": 99,
  "selected_candidates_count": 6,
  "total_candidates": 9,
  "top6": [
    {
      "id": 8,
      "is_top6": true,
      "name": "Ksihore",
      "phone": "918139921838",
      "rank": 1,
      "rank_label": "Rank 1",
      "score": 99,
      "status": "Shortlisted",
      "personalized_message": "Dear Ksihore,\n\nCongratulations!\n\nYou have been shortlisted for the Exposys Data Labs Coding Round.\n\nYour assessment score is 99.\n\nRegards,\nManoj Gowda\n\nRoll Number: 12345",
      "whatsapp_url": "https://wa.me/918139921838?text=..."
    }
  ],
  "success": true
}
```

---

## 🏆 Top 6 Ranking Results

Based on the provided dataset of 9 candidates:

| Rank | Candidate Name | Phone Number | Assessment Score | Tie-Breaker Rule Applied |
|:---:|:---|:---:|:---:|:---|
| **1** | **Ksihore** | `+918139921838` | **99** | First entry with score 99 (Row 8) |
| **2** | **Mahindar** | `+919346725307` | **99** | Second entry with score 99 (Row 9) |
| **3** | **Prashanth** | `+919972155027` | **98** | Ranked by score |
| **4** | **Exposys** | `+917892053145` | **97** | Ranked by score |
| **5** | **Vishnu** | `+917795207065` | **96** | Ranked by score |
| **6** | **Theertha** | `+919481770008` | **94** | Ranked by score |

*(Candidates Reecha [92], Ramya [80], and Chaitra [73] are excluded from Top 6)*

---

## 🚀 Setup & Execution

### 1. Prerequisites
- Python 3.10+ installed

### 2. Installation
Install dependencies via pip:
```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
py -3.12 test_app.py
```

### 4. Start the Application
```bash
py -3.12 app.py
```
Open your browser at:
```text
http://127.0.0.1:5000
```
