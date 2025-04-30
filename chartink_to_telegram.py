import requests
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# ====== CHARTINK Configuration =======
Charting_Link = "https://chartink.com/screener/"
Charting_url = 'https://chartink.com/screener/process'

Condition = "( {cash} ( latest open > latest low * 1.02 and latest close > latest open * 1.02 and latest close = latest high and latest sma ( close,10 ) > latest ema ( close,30 ) ) ) "

def GetDataFromChartink(payload):
    payload = {'scan_clause': payload}
    
    with requests.Session() as s:
        r = s.get(Charting_Link)
        soup = BeautifulSoup(r.text, "html.parser")
        csrf = soup.select_one("[name='csrf-token']")['content']
        s.headers['x-csrf-token'] = csrf
        r = s.post(Charting_url, data=payload)

        df = pd.DataFrame()
        for item in r.json()['data']:
            df = pd.concat([df, pd.DataFrame([item], index=[0])], ignore_index=True)
    return df

# ====== FETCH DATA =======
print("Fetching data from Chartink...")
data = GetDataFromChartink(Condition)

# ====== SAVE EXCEL =======
excel_path = "chartink_output.xlsx"
if not data.empty:
    data.to_excel(excel_path, index=False)
    print("Excel file saved.")
else:
    print("No data to save.")

# ====== TELEGRAM BOT CONFIG =======
bot_token = "7257895245:AAFSp_G4-3y_TcatCMCO61ZVMTLAdu0BX8M"
chat_id = "-1002526959615"

# ====== SEND EXCEL TO TELEGRAM =======
if not data.empty:
    with open(excel_path, "rb") as file:
        telegram_response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendDocument",
            data={"chat_id": chat_id},
            files={"document": file}
        )
    if telegram_response.status_code == 200:
        print("Excel sent to Telegram ✅")
    else:
        print("Excel send failed:", telegram_response.text)

# ====== CONVERT TO IMAGE WITH HEADER AND SEND =======
image_path = "chartink_output.png"
if not data.empty:
    # Header summary data
    header_labels = ["SLNO-CODE", "Overall BTST PROFIT %", "Overall 7 Day PROFIT %", "Overall BTST ROI", "Overall 7 Day ROI"]
    header_values = ["7495", "95.62", "98.20", "5.43", "12.62"]

    # Set size
    num_rows = len(data)
    fig_height = max(4, num_rows * 0.6 + 1.5)
    fig_width = max(8, len(data.columns) * 2)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')

    # Create header table
    header_table = plt.table(
        cellText=[header_values],
        colLabels=header_labels,
        cellLoc='center',
        colLoc='center',
        loc='top'
    )
    header_table.auto_set_font_size(False)
    header_table.set_fontsize(10)
    header_table.scale(1, 1.5)

    # Create main data table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        loc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    plt.tight_layout()
    plt.savefig(image_path, dpi=200)
    plt.close()
    print("Image file saved.")

    # Try sending as photo
    with open(image_path, "rb") as img:
        photo_response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": img}
        )

    if photo_response.status_code == 200:
        print("Image sent to Telegram as photo ✅")
    else:
        print("Photo send failed, trying as document...")

        with open(image_path, "rb") as img:
            doc_response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                data={"chat_id": chat_id},
                files={"document": img}
            )
        if doc_response.status_code == 200:
            print("Image sent as document ✅")
        else:
            print("Image send failed completely:", doc_response.text)
