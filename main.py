import os
import smtplib
import feedparser
import time
import urllib.parse
import random
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/2VkTZLnxpK", 
    "snack": "https://s.shopee.tw/2LR3N2obAJ", "cookie": "https://s.shopee.tw/2LR3N2obAJ", "chips": "https://s.shopee.tw/2LR3N2obAJ",
    "noodle": "https://s.shopee.tw/1VrwNVrlrA", "ramen": "https://s.shopee.tw/1VrwNVrlrA", "soup": "https://s.shopee.tw/1VrwNVrlrA",
    "drink": "https://s.shopee.tw/1LYWBCsPC9", "coffee": "https://s.shopee.tw/1LYWBCsPC9", "tea": "https://s.shopee.tw/1LYWBCsPC9",
    "cake": "https://s.shopee.tw/1qUmm7qVBG", "sweet": "https://s.shopee.tw/1qUmm7qVBG", "chocolate": "https://s.shopee.tw/1qUmm7qVBG"
}

genai.configure(api_key=GOOGLE_API_KEY)
def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
    except: return None
model = get_valid_model()
RSS_URL = "https://news.google.com/rss/search?q=food+recipes+snacks&hl=en-US&gl=US&ceid=US:en"

def get_food_image(title):
    magic_prompt = f"{title}, delicious food photography, mouth watering, cinematic lighting, 8k resolution, highly detailed"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>'

def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default": return link
    return SHOPEE_LINKS["default"]

def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    
    # === 美食人格轉盤 ===
    styles = [
        "風格：一位『深夜餓鬼』，在半夜寫文章，語氣充滿對食物的渴望，形容詞要讓人流口水，一直喊餓。",
        "風格：一位『嚴格的美食評論家』，嘴巴很刁，只推薦真正好吃的東西，語氣帶點傲嬌但誠懇。",
        "風格：一位『選擇困難症患者』，看到太多好吃的會崩潰，喜歡把所有口味都買一遍，強調『小孩才做選擇』。",
        "風格：一位『辦公室團購主』，喜歡揪團，強調『買多比較划算』，語氣很熱情，很會推坑。"
    ]
    selected_style = random.choice(styles)
    print(f"🤖 AI 今日人格：{selected_style}")

    prompt = f"""
    任務：將以下英文新聞改寫成「美食快訊」部落格文章。
    【標題】{title}
    【摘要】{summary}
    
    【寫作指令】
    1. **請嚴格扮演此角色**：{selected_style}
    2. **SEO標題**：必須包含「必吃、團購美食、食譜、熱量、評價」其中之一。
    3. **中段導購**：在第二段結束後，自然插入一句「💡 深夜肚子餓？點這裡馬上補貨」，並設為超連結({shopee_link})。
    
    【回傳 JSON】：{{"category": "美食日記", "html_body": "HTML內容"}}
    【文末按鈕】：<br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#D32F2F;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">🍔 點此補貨 (蝦皮美食特價)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "美食日記"), data.get("html_body", "")
    except: return "美食快訊", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body_html, 'html'))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 發布成功：{category}")
    except: pass

if __name__ == "__main__":
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_food_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html: send_email(entry.title, category, img_html + text_html)
    else: print("📭 無新文章")
