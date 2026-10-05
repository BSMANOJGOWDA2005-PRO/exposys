import os
import re
import time
import threading
import webbrowser
import urllib.parse
import pandas as pd
from flask import Flask, render_template, jsonify, request

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

app = Flask(__name__)

# Path to the CSV dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset', 'dataset.csv')


def clean_phone_number(phone_raw):
    """
    Cleans and standardizes an Indian phone number.
    - Strips whitespace, dashes, plus signs, brackets.
    - Ensures the 91 country code is prefixed if missing.
    - Returns None if the phone number is invalid.
    """
    if pd.isna(phone_raw):
        return None
    
    # Convert to string and remove non-digit characters
    phone_str = re.sub(r'\D', '', str(phone_raw).strip())
    
    # If standard 10-digit Indian number, prepend '91'
    if len(phone_str) == 10:
        return '91' + phone_str
    # If 12 digits starting with '91'
    elif len(phone_str) == 12 and phone_str.startswith('91'):
        return phone_str
    # If 11 digits starting with '0' (e.g. trunk prefix 07892053145)
    elif len(phone_str) == 11 and phone_str.startswith('0'):
        return '91' + phone_str[1:]
    
    return None


def generate_personalized_message(name, score, your_name=None, roll_number=None):
    """
    Generates the personalized WhatsApp shortlist message.
    STEP 5 & 12 requirement:
    Replace:
      {{Name}} -> candidate name
      {{Score}} -> candidate score
      {{Your Name}} -> user entered name (fallback: 'Your Name')
      {{Roll Number}} -> user entered roll number (fallback: 'Roll Number')
    """
    sender_name = your_name.strip() if (your_name and your_name.strip()) else "Your Name"
    sender_roll = roll_number.strip() if (roll_number and roll_number.strip()) else "Roll Number"
    
    message = (
        f"Dear {name},\n\n"
        f"Congratulations!\n\n"
        f"You have been shortlisted for the Exposys Data Labs Coding Round.\n\n"
        f"Your assessment score is {score}.\n\n"
        f"Regards,\n"
        f"{sender_name}\n\n"
        f"Roll Number: {sender_roll}"
    )
    return message


def build_whatsapp_url(phone_cleaned, message_text):
    """
    STEP 7 & 12 requirement:
    Builds the click-to-chat WhatsApp link:
    - https://wa.me/<PHONE_NUMBER>?text=<URL_ENCODED_MESSAGE> (universal / mobile / desktop app)
    - https://web.whatsapp.com/send?phone=<PHONE_NUMBER>&text=<URL_ENCODED_MESSAGE> (direct browser WhatsApp Web)
    """
    encoded_message = urllib.parse.quote(message_text, safe='')
    return f"https://wa.me/{phone_cleaned}?text={encoded_message}"


def build_whatsapp_web_url(phone_cleaned, message_text):
    """Direct WhatsApp Web fallback URL."""
    encoded_message = urllib.parse.quote(message_text, safe='')
    return f"https://web.whatsapp.com/send?phone={phone_cleaned}&text={encoded_message}"


def load_and_process_dataset(file_path=DATASET_PATH):
    """
    Loads, validates, and processes the candidates dataset.
    
    Interview Explanation Steps:
    1. Check if the CSV file exists on disk.
    2. Read CSV using Pandas (pd.read_csv).
    3. Validate required columns ('Name', 'Phone', 'Score').
    4. Row-by-row data validation:
       - Name is not empty or null.
       - Phone number is validated and converted to standard 91XXXXXXXXXX.
       - Score is numeric and bounded between 0 and 100.
    5. Retain original CSV order using original_index for stable tie-breaking.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found at: {file_path}")

    # Step 1: Read CSV using Pandas
    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError("The provided dataset is empty.")

    # Strip column names of any surrounding whitespace
    df.columns = [str(col).strip() for col in df.columns]

    # Verify required columns exist
    required_cols = {"Name", "Phone", "Score"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"Missing required columns. Expected {required_cols}, found {list(df.columns)}")

    valid_candidates = []
    invalid_rows = []

    # Step 2: Validate Data row-by-row
    for idx, row in df.iterrows():
        raw_name = row.get("Name")
        raw_phone = row.get("Phone")
        raw_score = row.get("Score")

        # 1. Validate Name
        if pd.isna(raw_name) or not str(raw_name).strip():
            invalid_rows.append({"row_index": idx + 1, "reason": "Missing or empty name", "data": dict(row)})
            continue
        name = str(raw_name).strip()

        # 2. Validate & Clean Phone Number
        clean_phone = clean_phone_number(raw_phone)
        if not clean_phone:
            invalid_rows.append({"row_index": idx + 1, "reason": f"Invalid phone number '{raw_phone}'", "data": dict(row)})
            continue

        # 3. Validate Score (must be numeric and between 0 and 100)
        try:
            score = float(raw_score)
            if score < 0 or score > 100:
                invalid_rows.append({"row_index": idx + 1, "reason": f"Score {score} out of bounds (0-100)", "data": dict(row)})
                continue
            # Format integer if no decimal part
            display_score = int(score) if score.is_integer() else round(score, 2)
        except (ValueError, TypeError):
            invalid_rows.append({"row_index": idx + 1, "reason": f"Non-numeric score '{raw_score}'", "data": dict(row)})
            continue

        valid_candidates.append({
            "id": idx + 1,                      # 1-based unique identifier
            "name": name,
            "raw_phone": str(raw_phone).strip(),
            "phone": clean_phone,               # e.g. 917892053145
            "score": display_score,
            "original_order": idx               # Stable tie-breaker
        })

    return valid_candidates, invalid_rows


def get_ranked_candidates(your_name=None, roll_number=None):
    """
    Ranks candidates and selects Top 6.
    
    Interview Explanation Steps:
    1. Sort candidates by Score descending (Score DESC).
    2. If two candidates have the same score, use original CSV order (original_order ASC) as tie-breaker.
    3. Assign dynamic rank (Rank 1, Rank 2, ...).
    4. Select Top 6 candidates (or all available if < 6).
    5. Generate personalized message and WhatsApp click-to-chat URL for each.
    """
    candidates, invalid_rows = load_and_process_dataset()

    if not candidates:
        return [], [], invalid_rows

    # Step 3: Sort by Score DESC, then original_order ASC
    # Python's sort is Timsort (stable), sorting with key=( -score, original_order )
    ranked = sorted(candidates, key=lambda c: (-c["score"], c["original_order"]))

    # Step 4: Assign Rank and WhatsApp metadata
    for rank_idx, cand in enumerate(ranked, start=1):
        cand["rank"] = rank_idx
        cand["rank_label"] = f"Rank {rank_idx}"
        cand["is_top6"] = (rank_idx <= 6)
        cand["status"] = "Shortlisted" if rank_idx <= 6 else "Waitlisted"
        
        # Message & WhatsApp link
        msg = generate_personalized_message(
            cand["name"],
            cand["score"],
            your_name=your_name,
            roll_number=roll_number
        )
        cand["personalized_message"] = msg
        cand["whatsapp_url"] = build_whatsapp_url(cand["phone"], msg)
        cand["whatsapp_web_url"] = build_whatsapp_web_url(cand["phone"], msg)

    top6 = ranked[:6]
    return ranked, top6, invalid_rows


# -------------------------------------------------------------
# FLASK WEB ROUTES & REST APIS
# -------------------------------------------------------------

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')


@app.route('/api/candidates', methods=['GET'])
def api_all_candidates():
    """
    GET /api/candidates
    Returns all valid candidates sorted with summary statistics.
    Optional query params:
      - your_name: Sender name
      - roll_number: Sender roll number
    """
    try:
        your_name = request.args.get('your_name', '')
        roll_number = request.args.get('roll_number', '')

        all_ranked, top6, invalid_rows = get_ranked_candidates(your_name, roll_number)

        total_count = len(all_ranked)
        scores = [c["score"] for c in all_ranked]
        highest_score = max(scores) if scores else 0
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        return jsonify({
            "success": True,
            "total_candidates": total_count,
            "selected_candidates_count": len(top6),
            "highest_score": highest_score,
            "average_score": avg_score,
            "candidates": all_ranked,
            "invalid_rows": invalid_rows,
            "has_less_than_6": total_count < 6
        }), 200

    except FileNotFoundError as fnf_err:
        return jsonify({"success": False, "error": str(fnf_err), "code": "FILE_NOT_FOUND"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "SERVER_ERROR"}), 500


@app.route('/api/top6', methods=['GET'])
def api_top6():
    """
    GET /api/top6
    Returns the Top 6 candidates with summary cards and message links.
    Optional query params:
      - your_name: Sender name
      - roll_number: Sender roll number
    """
    try:
        your_name = request.args.get('your_name', '')
        roll_number = request.args.get('roll_number', '')

        all_ranked, top6, invalid_rows = get_ranked_candidates(your_name, roll_number)

        total_count = len(all_ranked)
        scores = [c["score"] for c in all_ranked]
        highest_score = max(scores) if scores else 0
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        return jsonify({
            "success": True,
            "total_candidates": total_count,
            "selected_candidates_count": len(top6),
            "highest_score": highest_score,
            "average_score": avg_score,
            "top6": top6,
            "invalid_rows_count": len(invalid_rows),
            "has_less_than_6": total_count < 6,
            "message": f"Successfully selected top {len(top6)} candidates." if total_count >= 6 else "Fewer than 6 candidates available; displaying all shortlisted."
        }), 200

    except FileNotFoundError as fnf_err:
        return jsonify({"success": False, "error": str(fnf_err), "code": "FILE_NOT_FOUND"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "code": "SERVER_ERROR"}), 500


@app.route('/api/candidate/<int:cand_id>', methods=['GET'])
def api_candidate_detail(cand_id):
    """
    GET /api/candidate/<id>
    Returns detailed candidate information including personalized message.
    """
    try:
        your_name = request.args.get('your_name', '')
        roll_number = request.args.get('roll_number', '')

        all_ranked, _, _ = get_ranked_candidates(your_name, roll_number)

        for candidate in all_ranked:
            if candidate["id"] == cand_id:
                return jsonify({
                    "success": True,
                    "candidate": candidate
                }), 200

        return jsonify({"success": False, "error": f"Candidate with ID {cand_id} not found."}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------
# BATCH AUTO-SEND MANAGEMENT (ONE-CLICK SEND TO ALL)
# -------------------------------------------------------------
batch_lock = threading.Lock()
batch_state = {
    "active": False,
    "status": "idle",  # "idle", "running", "completed", "cancelled", "error"
    "current_index": 0,
    "total": 0,
    "current_candidate": None,
    "current_phone": None,
    "seconds_remaining": 0,
    "wait_seconds": 12,
    "logs": [],
    "should_cancel": False,
    "error_message": None
}


def auto_send_all_worker(candidates, wait_seconds=12):
    """
    Sequentially opens WhatsApp Web for each candidate and automatically
    sends the personalized shortlist message via simulated Enter key.
    """
    global batch_state
    with batch_lock:
        batch_state["active"] = True
        batch_state["status"] = "running"
        batch_state["total"] = len(candidates)
        batch_state["current_index"] = 0
        batch_state["wait_seconds"] = wait_seconds
        batch_state["should_cancel"] = False
        batch_state["error_message"] = None
        batch_state["logs"] = [
            {
                "id": c["id"],
                "rank": c["rank"],
                "name": c["name"],
                "phone": c["phone"],
                "status": "pending"
            }
            for c in candidates
        ]

    for idx, cand in enumerate(candidates):
        with batch_lock:
            if batch_state["should_cancel"]:
                batch_state["status"] = "cancelled"
                batch_state["active"] = False
                break
            batch_state["current_index"] = idx + 1
            batch_state["current_candidate"] = cand["name"]
            batch_state["current_phone"] = cand["phone"]
            batch_state["logs"][idx]["status"] = "sending"

        # Open candidate WhatsApp Web URL
        url = cand.get("whatsapp_web_url") or f"https://web.whatsapp.com/send?phone={cand['phone']}&text={urllib.parse.quote(cand['personalized_message'], safe='')}"
        try:
            webbrowser.open(url)
        except Exception as we:
            print(f"[Auto-Send-All] Error opening browser for {cand['name']}: {we}")

        # Wait with responsive cancellation check each second
        for s in range(wait_seconds, 0, -1):
            with batch_lock:
                if batch_state["should_cancel"]:
                    break
                batch_state["seconds_remaining"] = s
            time.sleep(1)

        with batch_lock:
            if batch_state["should_cancel"]:
                batch_state["status"] = "cancelled"
                batch_state["active"] = False
                batch_state["logs"][idx]["status"] = "cancelled"
                break

        # Simulate pressing Enter via PyAutoGUI
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.press('enter')
                print(f"[Auto-Send-All] Enter key pressed for {cand['name']} (+{cand['phone']})")
            except Exception as pe:
                print(f"[Auto-Send-All] PyAutoGUI error for {cand['name']}: {pe}")

        with batch_lock:
            batch_state["logs"][idx]["status"] = "sent"

        # Brief pause between candidate tabs
        time.sleep(2)

    with batch_lock:
        if batch_state["status"] != "cancelled":
            batch_state["status"] = "completed"
        batch_state["active"] = False
        batch_state["seconds_remaining"] = 0


@app.route('/api/send_whatsapp_all_auto', methods=['POST'])
def api_send_whatsapp_all_auto():
    """
    POST /api/send_whatsapp_all_auto
    Triggers automated WhatsApp sending for all Top 6 shortlisted candidates in one click.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        your_name = data.get('your_name', '')
        roll_number = data.get('roll_number', '')
        wait_seconds = int(data.get('wait_seconds', 12))

        with batch_lock:
            if batch_state["active"]:
                return jsonify({
                    "success": False,
                    "error": "An auto-send batch is already running. Please wait or cancel it first.",
                    "batch_state": batch_state
                }), 409

        _, top6, _ = get_ranked_candidates(your_name, roll_number)
        if not top6:
            return jsonify({"success": False, "error": "No shortlisted candidates found to send."}), 400

        threading.Thread(
            target=auto_send_all_worker,
            args=(top6, wait_seconds),
            daemon=True
        ).start()

        return jsonify({
            "success": True,
            "message": f"Auto-sending WhatsApp messages to all {len(top6)} candidates in one click.",
            "total_candidates": len(top6),
            "candidates": top6
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/batch_send_status', methods=['GET'])
def api_batch_send_status():
    """
    GET /api/batch_send_status
    Returns the real-time status of the batch auto-sending task.
    """
    with batch_lock:
        return jsonify({
            "success": True,
            "batch_state": dict(batch_state)
        }), 200


@app.route('/api/cancel_batch_send', methods=['POST'])
def api_cancel_batch_send():
    """
    POST /api/cancel_batch_send
    Cancels the active batch auto-sending process.
    """
    with batch_lock:
        if batch_state["active"]:
            batch_state["should_cancel"] = True
            return jsonify({"success": True, "message": "Batch auto-send cancellation requested."}), 200
        else:
            return jsonify({"success": False, "message": "No active batch auto-send to cancel."}), 200


def auto_send_whatsapp_worker(phone, message_text, wait_seconds=12):
    """
    Automated background worker:
    1. Opens WhatsApp Web with candidate phone number and pre-filled message text.
    2. Waits for WhatsApp Web to load the conversation and populate the input box.
    3. Simulates pressing the 'Enter' key automatically via pyautogui.
    """
    try:
        # Use direct WhatsApp Web URL for reliable browser loading
        url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(message_text, safe='')}"
        webbrowser.open(url)
        
        if PYAUTOGUI_AVAILABLE:
            # Wait for WhatsApp Web UI to render and message to appear in the typing area
            time.sleep(wait_seconds)
            pyautogui.press('enter')
            print(f"[Auto-Send] Successfully pressed Enter for candidate phone: {phone}")
    except Exception as e:
        print(f"[Auto-Send] Error during automated WhatsApp sending: {e}")


@app.route('/api/send_whatsapp_auto', methods=['POST'])
def api_send_whatsapp_auto():
    """
    POST /api/send_whatsapp_auto
    Triggers automated WhatsApp sending:
    - Opens WhatsApp Web with pre-typed text
    - Automatically presses 'Enter' to send after loading
    """
    try:
        data = request.get_json(force=True) or {}
        cand_id = data.get('id')
        your_name = data.get('your_name', '')
        roll_number = data.get('roll_number', '')
        wait_seconds = int(data.get('wait_seconds', 12))

        all_ranked, _, _ = get_ranked_candidates(your_name, roll_number)
        target_cand = next((c for c in all_ranked if c["id"] == cand_id), None)

        if not target_cand:
            return jsonify({"success": False, "error": f"Candidate ID {cand_id} not found"}), 404

        # Start non-blocking daemon thread so API returns immediately to the frontend
        threading.Thread(
            target=auto_send_whatsapp_worker,
            args=(target_cand["phone"], target_cand["personalized_message"], wait_seconds),
            daemon=True
        ).start()

        return jsonify({
            "success": True,
            "message": f"WhatsApp opened for {target_cand['name']} (+{target_cand['phone']}). Message will auto-send in {wait_seconds}s.",
            "candidate": target_cand
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("Exposys Data Labs – Top 6 Candidate Selection & WhatsApp Notification")
    print("Server running locally at: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host='127.0.0.1', port=5000, debug=True)
