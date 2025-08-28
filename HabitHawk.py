import tkinter as tk
from tkinter import messagebox
import sqlite3
import datetime
import subprocess
import os
import sys
import customtkinter as ctk
from PIL import Image
import random
import difflib
from collections import defaultdict
import google.generativeai as genai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from dotenv import load_dotenv

def resource_path(relative_path):
    """PyInstallerでビルドされた際のリソースパスを取得する"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# データベースへの接続
conn = sqlite3.connect(resource_path('habit_log.db'))
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        start_time TEXT,
        end_time TEXT,
        activity_name TEXT
    )
''')
conn.commit()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 変数の初期化
        self.timers = {}
        
        # UIの構築
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("HabitHawk.exe")
        self.geometry("400x300")
        
        # ウィンドウアイコンの設定
        try:
            self.iconbitmap(resource_path("HabitHawk.ico"))
        except Exception as e:
            print(f"ウィンドウアイコンの設定中にエラーが発生しました: {e}")

        # ロゴの追加
        try:
            logo_path = resource_path('images/HabitHawk.png')
            logo_image = ctk.CTkImage(Image.open(logo_path), size=(100, 100))
            logo_label = ctk.CTkLabel(self, image=logo_image, text="")
            logo_label.pack(pady=(10, 0))
        except Exception as e:
            print(f"ロゴの読み込み中にエラーが発生しました: {e}")

        # タイマーを格納するコンテナフレーム
        self.timer_container = ctk.CTkScrollableFrame(self)
        self.timer_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 最初のタイマーを追加
        self.add_timer_ui()

        # タイマー追加ボタン
        add_button = ctk.CTkButton(self, text="+", command=self.add_timer_ui)
        add_button.pack(pady=5)

    def add_timer_ui(self):
        timer_id = f"timer_{len(self.timers)}"
        
        frame = ctk.CTkFrame(self.timer_container, fg_color="transparent")
        frame.pack(pady=5, fill="x")

        # UI要素の作成
        entry = ctk.CTkEntry(frame, width=280, font=("Helvetica", 12))
        entry.pack(pady=(0, 5))
        timer_label = ctk.CTkLabel(frame, text="00:00:00", font=("Helvetica", 24))
        timer_label.pack(pady=5)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(pady=(5, 0))

        start_button = ctk.CTkButton(button_frame, text="START", command=lambda: self.start_tracking(timer_id))
        start_button.pack(side=tk.LEFT, expand=True, padx=5, pady=0)
        stop_button = ctk.CTkButton(button_frame, text="STOP", command=lambda: self.stop_tracking(timer_id), state=tk.DISABLED)
        stop_button.pack(side=tk.RIGHT, expand=True, padx=5, pady=0)

        remove_button = ctk.CTkButton(frame, text="-", command=lambda: self.remove_timer_ui(timer_id))
        remove_button.pack(pady=(5, 0))

        self.timers[timer_id] = {
            'is_tracking': False,
            'start_time': None,
            'current_activity': "",
            'tracking_duration': 0,
            'frame': frame,
            'entry': entry,
            'timer_label': timer_label,
            'start_button': start_button,
            'stop_button': stop_button
        }

    def remove_timer_ui(self, timer_id):
        if len(self.timers) > 1:
            if self.timers[timer_id]['is_tracking']:
                messagebox.showwarning("Warning", "Please stop the timer before removing it.")
                return

            self.timers[timer_id]['frame'].destroy()
            del self.timers[timer_id]
        else:
            messagebox.showwarning("Warning", "At least one timer must remain.")


    def start_tracking(self, timer_id):
        timer = self.timers[timer_id]
        if not timer['is_tracking']:
            activity_name = timer['entry'].get().strip()
            if activity_name:
                timer['is_tracking'] = True
                timer['start_time'] = datetime.datetime.now()
                timer['current_activity'] = activity_name
                timer['tracking_duration'] = 0
                timer['start_button'].configure(state=tk.DISABLED)
                timer['stop_button'].configure(state=tk.NORMAL)
                self.update_timer(timer_id)
            else:
                messagebox.showwarning("Warning", "Please enter an activity!")

    def stop_tracking(self, timer_id):
        timer = self.timers[timer_id]
        if timer['is_tracking']:
            timer['is_tracking'] = False
            end_time = datetime.datetime.now()
            
            c.execute("INSERT INTO activities VALUES (?, ?, ?)", 
                      (timer['start_time'].strftime("%Y-%m-%d %H:%M:%S"), 
                       end_time.strftime("%Y-%m-%d %H:%M:%S"),
                       timer['current_activity']))
            conn.commit()
            
            timer['start_button'].configure(state=tk.NORMAL)
            timer['stop_button'].configure(state=tk.DISABLED)
            timer['timer_label'].configure(text="00:00:00")
            timer['entry'].delete(0, tk.END)

    def update_timer(self, timer_id):
        timer = self.timers[timer_id]
        if timer['is_tracking']:
            timer['tracking_duration'] = (datetime.datetime.now() - timer['start_time']).total_seconds()
            hours, remainder = divmod(timer['tracking_duration'], 3600)
            minutes, seconds = divmod(remainder, 60)
            timer['timer_label'].configure(text=f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}")
            self.after(1000, lambda: self.update_timer(timer_id))

# 以下、既存のレポート生成コードは変更なし
# --- report_generator.py から統合されたコード ---

# .envファイルから環境変数を読み込む
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ZenAntique-Regular.ttfフォントを登録
pdfmetrics.registerFont(TTFont('ZenAntique', resource_path('ZenAntique-Regular.ttf')))

# APIキーが設定されていない場合は警告を表示し、プログラムを終了
if not GEMINI_API_KEY:
    print("警告: .envファイルにGEMINI_API_KEYが設定されていません。")
    print("Gemini APIを使用するには、有効なキーを設定してください。")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# 同義語・クラスタリングのマッピング
SYNONYM_MAPPING = {
    '入浴': ['風呂', 'お風呂', 'シャワー', '温泉', 'bath'],
    '音楽活動': ['ギター', '作曲', '楽器練習', 'music'],
    '運動': ['散歩', 'ジョギング', '筋トレ', 'ランニング', 'walking', 'running'],
    '配信業務': ['配信', 'ライブ配信', 'OBS設定', '配信準備', 'stream'],
    'コンテンツ消費': ['youtube', 'netflix', 'hulu', '映画鑑賞', 'movie'],
}

def get_canonical_name(activity_name):
    lower_name = activity_name.lower()
    for canonical, synonyms in SYNONYM_MAPPING.items():
        if lower_name in [s.lower() for s in synonyms]:
            return canonical
        for s in synonyms:
            if difflib.SequenceMatcher(None, lower_name, s.lower()).ratio() > 0.8:
                 return canonical
    return activity_name.capitalize()

def get_activity_data(start_date, end_date):
    conn = sqlite3.connect(resource_path('habit_log.db'))
    c = conn.cursor()
    c.execute("SELECT start_time, end_time, activity_name FROM activities")
    all_data = c.fetchall()
    period_data = [
        row for row in all_data
        if start_date.strftime("%Y-%m-%d %H:%M:%S") <= row[0] <= end_date.strftime("%Y-%m-%d %H:%M:%S")
    ]
    conn.close()
    return period_data, all_data

def format_data_for_ai(raw_data):
    aggregated_data = defaultdict(lambda: {'duration': 0, 'count': 0})
    for row in raw_data:
        start = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
        duration_seconds = (end - start).total_seconds()
        canonical_name = get_canonical_name(row[2].strip())
        aggregated_data[canonical_name]['duration'] += duration_seconds
        aggregated_data[canonical_name]['count'] += 1
    formatted_string = "### Activities Log\n"
    for activity, data in sorted(aggregated_data.items()):
        formatted_string += f"- {activity}: {data['duration']:.2f} seconds ({data['count']} times)\n"
    return formatted_string, aggregated_data

def get_ai_feedback(formatted_data, aggregated_data, all_data, report_type):
    is_praise_mode = random.random() < 0.05
    all_activities = defaultdict(datetime.datetime)
    for row in all_data:
        end_time = datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
        canonical_name = get_canonical_name(row[2].strip())
        all_activities[canonical_name] = max(all_activities[canonical_name], end_time)
    long_absent_activities = []
    for activity, last_date in all_activities.items():
        if (datetime.datetime.now() - last_date).days > 30 and activity not in aggregated_data:
            long_absent_activities.append(activity)
    recorded_clusters = {get_canonical_name(row[2].strip()) for row in all_data}
    missing_clusters = [cluster for cluster in SYNONYM_MAPPING if cluster not in recorded_clusters]
    prompt = ""
    if is_praise_mode:
        prompt = f"""
        あなたはAI「Hawk Eye」です。ごくまれに、あなたはユーザーを褒めるモードに入ります。
        このデータに基づき、ユーザーの努力を客観的に褒めてください。
        感情的な表現は避け、「Hawkは〜と分析しています」のような三人称の視点で記述してください。
        データ:
        {formatted_data}
        """
    else:
        time_of_day_breakdown = defaultdict(float)
        for row in all_data:
            start_time = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
            duration_seconds = (end_time - start_time).total_seconds()
            hour = start_time.hour
            if 0 <= hour < 6:
                time_of_day_breakdown['深夜 (0時〜6時)'] += duration_seconds
            elif 6 <= hour < 12:
                time_of_day_breakdown['朝 (6時〜12時)'] += duration_seconds
            elif 12 <= hour < 18:
                time_of_day_breakdown['昼 (12時〜18時)'] += duration_seconds
            else:
                time_of_day_breakdown['夜 (18時〜0時)'] += duration_seconds
        
        time_of_day_prompt = "### 時間帯別活動時間\n"
        for time_range, duration in time_of_day_breakdown.items():
            time_of_day_prompt += f"- {time_range}: {duration:.2f} 秒\n"

        prompt = f"""
        あなたはAI「Hawk Eye」です。以下のデータはユーザーの活動記録です。
        データに基づき、Hawkが以下の点を厳格かつ感情を持たない三人称の口調で指摘してください。
        1. 今期の生産性スコアを100点満点で評価してください。
        2. 時間が減った、または完全に停止した活動について指摘。
        3. 活動時間の急増、偏重など、バランスの悪さを指摘。
        4. もし以下の活動が30日以上記録されていなければ、そのことを指摘してください。: {', '.join(long_absent_activities)}
        5. もし以下のクラスタに記録がなければ、そのことを指摘してください。: {', '.join(missing_clusters)}
        6. 時間帯別の活動時間データから、生活リズムの偏りや改善点を指摘してください。
        
        データ:
        {formatted_data}
        {time_of_day_prompt}
        """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini APIからフィードバックを取得できませんでした: {e}"

def generate_pdf_report(report_data, filename="report.pdf"):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    doc = SimpleDocTemplate(resource_path(filename), pagesize=A4)
    styles = getSampleStyleSheet()
    styles['Normal'].fontName = 'ZenAntique'
    styles['Heading1'].fontName = 'ZenAntique'
    styles['Title'].fontName = 'ZenAntique'
    styles['Normal'].leading = 14
    story = []
    log_text = "## Hawk's Time Log\n"
    for activity, data in sorted(report_data['aggregated_data'].items()):
        seconds = int(data['duration'])
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        log_text += f"* {activity}: {time_str} ({data['count']} times)\n"
    story.append(Paragraph(log_text, styles['Normal']))
    story.append(Spacer(1, 12))
    for paragraph in report_data['feedback'].split('\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith('### '):
            story.append(Paragraph(paragraph.replace('### ', ''), styles['Heading1']))
        elif paragraph.startswith('## '):
            story.append(Paragraph(paragraph.replace('## ', ''), styles['Heading1']))
        else:
            story.append(Paragraph(paragraph, styles['Normal']))
            story.append(Spacer(1, 6))
    doc.build(story)

def run_report_generator(report_type):
    today = datetime.date.today()
    if report_type == 'weekly':
        start_date = today - datetime.timedelta(days=7)
        end_date = today
        period_data, all_data = get_activity_data(start_date, end_date)
        formatted_data, aggregated_data = format_data_for_ai(period_data)
        ai_feedback = get_ai_feedback(formatted_data, aggregated_data, all_data, "weekly")
        report_data = {
            'title': f"Hawk Eye Report {start_date.strftime('%Y%m%d')}~{end_date.strftime('%Y%m%d')}",
            'feedback': ai_feedback,
            'aggregated_data': aggregated_data
        }
        filename = f"reports/weekly/weekly_report_{end_date.strftime('%Y%m%d')}.pdf"
        generate_pdf_report(report_data, filename)
        
    elif report_type == 'monthly':
        start_date = today.replace(day=1)
        end_date = today
        period_data, all_data = get_activity_data(start_date, end_date)
        formatted_data, aggregated_data = format_data_for_ai(period_data)
        ai_feedback = get_ai_feedback(formatted_data, aggregated_data, all_data, "monthly")
        report_data = {
            'title': f"Hawk Eye Report {start_date.strftime('%Y%m%d')}~{end_date.strftime('%Y%m%d')}",
            'feedback': ai_feedback,
            'aggregated_data': aggregated_data
        }
        filename = f"reports/monthly/monthly_report_{end_date.strftime('%Y%m%d')}.pdf"
        generate_pdf_report(report_data, filename)

# --- generate_hawk_eye_report()関数の修正 ---

def generate_hawk_eye_report():
    try:
        if not os.path.exists(resource_path("reports/weekly")):
            os.makedirs(resource_path("reports/weekly"))
        if not os.path.exists(resource_path("reports/monthly")):
            os.makedirs(resource_path("reports/monthly"))
            
        today = datetime.date.today()
        is_sunday = today.isoweekday() == 7
        last_day_of_month = (today + datetime.timedelta(days=1)).replace(day=1) - datetime.timedelta(days=1)
        is_last_day = today == last_day_of_month

        if is_last_day:
            run_report_generator('monthly')
            messagebox.showinfo("Success", "Hawk Eye Monthly Report ready.")
        elif is_sunday:
            run_report_generator('weekly')
            messagebox.showinfo("Success", "Hawk Eye Weekly Report ready.")
    except Exception as e:
        messagebox.showerror("Error", f"Report generation failed: {e}")

# アプリケーションの実行
if __name__ == "__main__":
    app = App()
    
    # Hawk Eyeボタンの表示ロジック
    today = datetime.date.today()
    is_sunday = today.isoweekday() == 7
    last_day_of_month = (today + datetime.timedelta(days=1)).replace(day=1) - datetime.timedelta(days=1)
    is_last_day = today == last_day_of_month

    if is_sunday or is_last_day:
        hawk_eye_button = ctk.CTkButton(app, text="Hawk Eye", command=generate_hawk_eye_report)
        hawk_eye_button.pack(pady=10)

    app.mainloop()

conn.close()