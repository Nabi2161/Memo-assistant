import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import serial
import time
import requests

# ====== 設定區 ======
# Arduino 串列埠名稱（請依實際調整）
ARDUINO_PORT = 'COM3'  # Windows 下常見為 COM3、COM4...
BAUD_RATE = 9600

# OpenAI API Key（如需串接 GPT，請填入金鑰）
OPENAI_API_KEY = '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'  # <--- 請將 YOUR_API_KEY 替換為你的 OpenAI 金鑰

# =====================

app = Flask(__name__)
CORS(app)

# 任務暫存（實際可用資料庫）
tasks = []

# 嘗試連接 Arduino
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # 等待 Arduino 重啟
except Exception as e:
    arduino = None
    print(f"無法連接 Arduino: {e}")

@app.route('/api/ai', methods=['POST'])
def ai_api():
    data = request.get_json()
    text = data.get('text', '')
    # 查詢未完成事項
    if '還有什麼沒做' in text or '未完成' in text or '剩下什麼' in text:
        undone = [t['text'] for t in tasks if not t.get('done')]
        return jsonify({
            'text': text,
            'undone': undone,
            'category': '查詢',
            'duplicate': False,
            'similar': ''
        })
    # ======= GPT API 串接 =======
    category = '其他'
    try:
        if OPENAI_API_KEY:
            prompt = f"""
你是一個智慧任務分類助理，請判斷下列任務內容屬於哪一類（課業、打工、其他），並只回傳分類名稱。
任務內容：「{text}」
"""
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {"role": "system", "content": "你是一個智慧任務分類助理，只回傳分類名稱。"},
                    {"role": "user", "content": prompt}
                ],
                'max_tokens': 10,
                'temperature': 0
            }
            resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
            if resp.status_code == 200:
                gpt_reply = resp.json()['choices'][0]['message']['content'].strip()
                if gpt_reply in ['課業', '打工', '其他']:
                    category = gpt_reply
    except Exception as e:
        print(f"GPT API error: {e}")
    # ======= 重複偵測 =======
    duplicate = False
    similar = ''
    for t in tasks:
        if t['text'] in text or text in t['text']:
            duplicate = True
            similar = t['text']
            break
    return jsonify({
        'text': text,
        'category': category,
        'duplicate': duplicate,
        'similar': similar
    })

@app.route('/api/arduino', methods=['POST'])
def arduino_api():
    data = request.get_json()
    task_list = data.get('tasks', [])
    unfinished = [t for t in task_list if not t.get('done')]
    # 控制 Arduino LED
    if arduino:
        try:
            if len(unfinished) == 0:
                arduino.write(b'G')  # 綠燈
            else:
                arduino.write(b'R')  # 紅燈
        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)})
    return jsonify({'status': 'ok', 'unfinished': len(unfinished)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
