import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

# ====== TELEGRAM BOT CONFIG =======
bot_token = "7257895245:AAFSp_G4-3y_TcatCMCO61ZVMTLAdu0BX8M"
chat_id = "-1002526959615"

# ====== CHARTINK CONFIG =======
chartink_link = "https://chartink.com/screener/"
chartink_url = 'https://chartink.com/screener/process'

# ====== GET DATA FUNCTION =======
def get_data_from_chartink(payload):
    try:
        with requests.Session() as s:
            r = s.get(chartink_link)
            soup = BeautifulSoup(r.text, "html.parser")
            csrf = soup.select_one("[name='csrf-token']")['content']
            s.headers['x-csrf-token'] = csrf
            r = s.post(chartink_url, data={'scan_clause': payload})
            data = r.json().get('data', [])
            return pd.DataFrame(data)
    except Exception as e:
        print(f"[ERROR] Chartink fetch failed: {e}")
        return pd.DataFrame()

# ====== SEND IMAGE TO TELEGRAM =======
def send_image(image_path):
    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                data={"chat_id": chat_id, "caption": "📊 Chartink Report"},
                files={"photo": f}
            )
        if response.status_code != 200:
            print(f"[ERROR] Telegram API error: {response.text}")
        else:
            print("Image sent to Telegram successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send image: {e}")

# ====== SEND EXCEL TO TELEGRAM =======
def send_excel(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                data={"chat_id": chat_id},
                files={"document": f}
            )
        if response.status_code != 200:
            print(f"[ERROR] Telegram Excel send failed: {response.text}")
        else:
            print(" Excel file sent to Telegram successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send Excel: {e}")

# ====== SAVE IMAGE WITH DUPLICATES =======
def save_combined_image(df, all_headers, duplicate_df, image_path):
    has_duplicates = not duplicate_df.empty

    # Dynamic sizing
    max_col_width = max([len(str(col)) for col in df.columns] + [len(str(x)) for x in df.values.flatten()])
    fig_width = max(12, max_col_width * len(df.columns) * 0.09)
    fig_height = max(6, len(df) * 0.5 + len(all_headers) * 0.9)
    if has_duplicates:
        fig_height += len(duplicate_df) * 0.5 + 1

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')

    # Header Summary
    summary_data = []
    summary_labels = []
    for header in all_headers:
        summary_labels.append(header["name"])
        summary_data.append([f"{k}: {v}" for k, v in header["header"].items()])

    header_table = plt.table(
        cellText=summary_data,
        rowLabels=summary_labels,
        loc='top',
        cellLoc='left'
    )
    header_table.auto_set_font_size(False)
    header_table.set_fontsize(12)
    header_table.scale(1.2, 1.2)
    plt.subplots_adjust(top=0.55)

    # Main Table
    table = plt.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.2)

    # Duplicate Table
    if has_duplicates:
        # Add gap
        gap_y = -0.3
        ax.text(0, gap_y, 'Duplicate NSE Codes (Appeared in Multiple Reports)', fontsize=12, weight='bold')
        dup_table = plt.table(
            cellText=duplicate_df.values,
            colLabels=duplicate_df.columns,
            colLoc='center',
            loc='bottom'
        )
        dup_table.auto_set_font_size(False)
        dup_table.set_fontsize(11)
        dup_table.scale(1.2, 1.2)

    plt.tight_layout()
    plt.savefig(image_path, dpi=150, bbox_inches='tight')
    plt.close()

# ====== MAIN FUNCTION =======
def main():
    try:
        with open("conditions.json") as f:
            conditions = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load JSON: {e}")
        return

    all_data = []
    all_headers = []

    for item in conditions:
        name = item['name']
        condition = item['condition']
        header = item.get('header', {})

        print(f"🔍 Fetching data for: {name}")
        df = get_data_from_chartink(condition)

        if not df.empty:
            df['Condition'] = name
            all_data.append(df)
            all_headers.append({"name": name, "header": header})
        else:
            print(f"No data for: {name}")

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        cols = ['Condition'] + [col for col in combined_df.columns if col != 'Condition']
        combined_df = combined_df[cols]

        # Find duplicates by nsecode
        dup_df = combined_df[combined_df.duplicated(subset=["nsecode"], keep=False)]
        dup_df = dup_df.sort_values(by="nsecode")

        # Save Excel
        excel_path = "combined_report.xlsx"
        with pd.ExcelWriter(excel_path) as writer:
            combined_df.to_excel(writer, index=False, sheet_name="All Data")
            if not dup_df.empty:
                dup_df.to_excel(writer, index=False, sheet_name="Duplicates")

        # Save Image
        image_path = "combined_report.png"
        save_combined_image(combined_df, all_headers, dup_df, image_path)

        # Send
        send_image(image_path)
        send_excel(excel_path)
    else:
        print("No data found for any condition.")

if __name__ == "__main__":
    main()
