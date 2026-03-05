import tkinter as tk
import requests
import feedparser
import threading
import json
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.basemap import Basemap

OLLAMA_MODEL = "llama3.2:1b"
UPDATE_INTERVAL = 300000

GREEN = "#00ff41"
BLACK = "#000000"

risk_history = []

HOTSPOTS = {
    "Ukraine": 0,
    "Taiwan": 0,
    "Middle East": 0,
    "South China Sea": 0,
    "Korean Peninsula": 0
}

ALERT_KEYWORDS = [
    "missile",
    "military",
    "strike",
    "nuclear",
    "invasion",
    "warship",
    "troops"
]


# ---------------- HEATMAP ----------------

def draw_world_heatmap(ax):

    ax.clear()

    m = Basemap(projection='robin', lon_0=0, resolution='c', ax=ax)

    m.drawcoastlines(color=GREEN)
    m.drawcountries(color=GREEN)
    m.fillcontinents(color="#001100", lake_color=BLACK)
    m.drawmapboundary(fill_color=BLACK)

    coords = {
        "Ukraine": (48.3, 31.2),
        "Taiwan": (23.7, 121),
        "Middle East": (33, 44),
        "South China Sea": (10, 115),
        "Korean Peninsula": (38.5, 127)
    }

    for region, (lat, lon) in coords.items():

        intensity = HOTSPOTS.get(region, 0)

        x, y = m(lon, lat)

        size = 100 + intensity * 50

        ax.scatter(x, y, s=size, c="red", alpha=0.6)

    ax.set_title("LIVE GLOBAL HOTSPOT MAP", color=GREEN)


# ---------------- SYSTEM FUNCTIONS ----------------

def get_defcon(risk):

    if risk < 20:
        return "DEFCON 5 - NORMAL", GREEN
    elif risk < 40:
        return "DEFCON 4 - ELEVATED", "yellow"
    elif risk < 60:
        return "DEFCON 3 - HIGH ALERT", "orange"
    elif risk < 80:
        return "DEFCON 2 - WAR PREPARATION", "red"
    else:
        return "DEFCON 1 - MAXIMUM ALERT", "red"


def fetch_news():

    feeds = [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
    ]

    headlines = []

    for url in feeds:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:5]:
                headlines.append(entry.title)

        except:
            pass

    return headlines


def update_hotspots(headlines):

    for region in HOTSPOTS:
        for h in headlines:
            if region.lower() in h.lower():
                HOTSPOTS[region] += 1


def detect_alerts(headlines):

    alerts = []

    for h in headlines:
        for word in ALERT_KEYWORDS:
            if word in h.lower():
                alerts.append(h)

    return alerts


def analyze_news(news):

    prompt = f"""
You are a geopolitical intelligence AI.

Based on these headlines:

{news}

Estimate global war risk (0-100).

Return JSON ONLY like this:

{{
"risk_score": 50,
"analysis": "short explanation"
}}
"""

    try:

        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        data = r.json()

        if "response" not in data:
            return '{"risk_score":0,"analysis":"AI returned empty response"}'

        return data["response"]

    except:
        return '{"risk_score":0,"analysis":"AI connection failed"}'


# ---------------- DASHBOARD ----------------

class Dashboard:

    def __init__(self, root):

        self.root = root
        self.root.configure(bg=BLACK)

        self.risk_score = 0

        self.build_ui()

        self.update_clock()
        self.start_analysis()

    # UI

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="GLOBAL STRATEGIC INTELLIGENCE SYSTEM",
            font=("Agency FB", 26, "bold"),
            fg=GREEN,
            bg=BLACK
        )
        title.pack(pady=10)

        self.clock = tk.Label(self.root, font=("Agency FB", 14), fg=GREEN, bg=BLACK)
        self.clock.pack()

        main = tk.Frame(self.root, bg=BLACK)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        left = tk.Frame(main, bg=BLACK)
        left.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.risk_label = tk.Label(left, text="WAR RISK: 0%", font=("Agency FB", 32, "bold"), fg=GREEN, bg=BLACK)
        self.risk_label.pack(anchor="w")

        self.defcon_label = tk.Label(left, text="DEFCON 5 - NORMAL", font=("Agency FB", 18), fg=GREEN, bg=BLACK)
        self.defcon_label.pack(anchor="w")

        tk.Label(left, text="INTELLIGENCE FEED", fg=GREEN, bg=BLACK).pack(anchor="w", pady=(20,0))

        self.news_box = tk.Text(left, height=15, bg=BLACK, fg=GREEN)
        self.news_box.pack(fill="both", expand=True)

        tk.Label(left, text="MILITARY ALERTS", fg=GREEN, bg=BLACK).pack(anchor="w", pady=(20,0))

        self.alert_box = tk.Text(left, height=6, bg=BLACK, fg="red")
        self.alert_box.pack(fill="x")

        right = tk.Frame(main, bg=BLACK)
        right.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        tk.Label(right, text="AI STRATEGIC ANALYSIS", fg=GREEN, bg=BLACK).pack(anchor="w")

        self.analysis_box = tk.Text(right, height=15, bg=BLACK, fg=GREEN)
        self.analysis_box.pack(fill="both", expand=True)

        tk.Label(right, text="GLOBAL HOTSPOTS", fg=GREEN, bg=BLACK).pack(anchor="w", pady=(20,0))

        self.hotspot_box = tk.Text(right, height=6, bg=BLACK, fg=GREEN)
        self.hotspot_box.pack(fill="x")

        fig = plt.Figure(figsize=(6,4), dpi=100)
        self.ax = fig.add_subplot(111)

        draw_world_heatmap(self.ax)

        fig.patch.set_facecolor(BLACK)
        self.ax.set_facecolor(BLACK)

        self.canvas = FigureCanvasTkAgg(fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=20)

    # CLOCK

    def update_clock(self):

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock.config(text=now)

        self.root.after(1000, self.update_clock)

    # START THREAD

    def start_analysis(self):

        threading.Thread(target=self.run_analysis, daemon=True).start()

    # ANALYSIS

    def run_analysis(self):

        headlines = fetch_news()

        if not headlines:
            news_text = "No news available"
        else:
            news_text = "\n• " + "\n• ".join(headlines)

        update_hotspots(headlines)

        alerts = detect_alerts(headlines)

        ai_output = analyze_news(news_text)

        try:

            start = ai_output.find("{")
            end = ai_output.rfind("}") + 1

            parsed = json.loads(ai_output[start:end])

            self.risk_score = int(parsed.get("risk_score", 0))
            analysis = parsed.get("analysis", "No analysis")

        except:
            self.risk_score = 0
            analysis = "AI parsing failed"

        self.root.after(
            0,
            lambda: self.update_ui(news_text, analysis, alerts)
        )

        self.root.after(UPDATE_INTERVAL, self.start_analysis)

    # UPDATE UI

    def update_ui(self, news, analysis, alerts):

        self.risk_label.config(text=f"WAR RISK: {self.risk_score}%")

        defcon_text, color = get_defcon(self.risk_score)
        self.defcon_label.config(text=defcon_text, fg=color)

        self.news_box.delete("1.0", tk.END)
        self.news_box.insert(tk.END, news)

        self.analysis_box.delete("1.0", tk.END)
        self.analysis_box.insert(tk.END, analysis)

        self.alert_box.delete("1.0", tk.END)

        for a in alerts:
            self.alert_box.insert(tk.END, f"⚠ {a}\n")

        self.hotspot_box.delete("1.0", tk.END)

        for region, score in HOTSPOTS.items():
            self.hotspot_box.insert(tk.END, f"{region}: {score}\n")

        draw_world_heatmap(self.ax)
        self.canvas.draw()


# ---------------- RUN ----------------
root = tk.Tk()
root.title("GLOBAL WAR INTELLIGENCE SYSTEM")
root.geometry("1400x900")
root.configure(bg=BLACK)

# container
container = tk.Frame(root, bg=BLACK)
container.pack(fill="both", expand=True)

# canvas
canvas = tk.Canvas(container, bg=BLACK, highlightthickness=0)
canvas.pack(side="left", fill="both", expand=True)

# vertical scrollbar
v_scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
v_scrollbar.pack(side="right", fill="y")

# horizontal scrollbar (NEW)
h_scrollbar = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
h_scrollbar.pack(side="bottom", fill="x")

canvas.configure(
    yscrollcommand=v_scrollbar.set,
    xscrollcommand=h_scrollbar.set
)

# scrollable frame
scrollable_frame = tk.Frame(canvas, bg=BLACK)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

# update scroll region
def configure_scroll(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_frame.bind("<Configure>", configure_scroll)

# mouse wheel scrolling (vertical)
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind_all("<MouseWheel>", _on_mousewheel)

# SHIFT + mouse wheel for horizontal scrolling (NEW)
def _on_shift_mousewheel(event):
    canvas.xview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)

# start dashboard inside scroll frame
app = Dashboard(scrollable_frame)

root.mainloop()