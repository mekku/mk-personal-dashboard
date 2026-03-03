from flask import Flask, render_template
from flask_socketio import SocketIO
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from binance.client import Client
from binance import ThreadedWebsocketManager
from binance.enums import FuturesType
from threading import Thread
import os
import math
import ccxt
from joblib import Parallel, delayed
import json
import paho.mqtt.client as mqtt

# Config logging to file
import logging
from logging.handlers import RotatingFileHandler

# Kill process if unexpected error occurs or uncaught exception
import sys
import signal
import time
import os

import json
import requests
from base64 import b64encode

def signal_handler(sig, frame):
    sys.exit(9)
    
signal.signal(signal.SIGINT, signal_handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.exit(9)
    
sys.excepthook = handle_exception


# Create a logger object
logger = logging.getLogger(__name__)

# Put logs in the logs folder
if not os.path.exists("logs"):
    os.makedirs("logs")

# Create a file handler
log_file = os.path.join(os.path.dirname(__file__), "logs/web.log")
handler = RotatingFileHandler(log_file, backupCount=1)
handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(handler)

# Set the logging level
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[handler])

# Initialize Flask and Flask-SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

interval_until_update = 0
    
# Initialize Binance Client (replace with your API keys)
futures_keys = {
    "MS1": {
        "name": "VAR-BOT-MK-S1",
        "api_key": "40T4BsIRiJXxDJfTIaqWDEZ7IAz9zsCTvHc8WElWMHdnlzOCpWc2JwPxju1GQlcb",
        "api_secret": "xU4YEkEGeBlsgnw0lpDjur7g58gTbcMevxEZFPtnjDhfKSbv1CMuff9k9d2umyYi",
        "symbols": ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "SOLUSDT", "AVAXUSDT"]
    },
    "MOM": {
        "name": "VAR-BOT-CBT2-S1-MOM",
        "api_key": "EssxG13YnQxI3IdLC8NMkExW0vxKceGdx2MW7jndt0IzxffhRIgnD2o8PUOgW04A",
        "api_secret": "qT8mNOYjY1Nw2AaCInpPZMnv45bkDsDNheYqHp3eifLb0RILCLiHCXgeTrYdZCkB",
        "symbols": ["BTCUSDT"]
    },
     "C2 COIN-M": {
        "name": "VAR-BOT-CBT2-CM",
        "api_key": "T36Nh7Ed0XdohGhcxAYSIdvHlf4y2VeNDsHuR00DfG9RVdJCzxvObxx6OOFIXjHo",
        "api_secret": "l0QtrPOJ7m4oqYmkDglJyGRxvIj4cAskTsodvx4XkkdwfzpRa8QJISMwvDya0iKz",
        "symbols": ["BTCUSD"]
    },
     
    "YY": {
        "name": "VAR-BOT-YY",
        "api_key": "6duXjOFTQRTaYnptMdNWXUkDFXfLrYpcuPpP4KJJjR54A7YoZZXJ8pFY3wNuIJvZ",
        "api_secret": "nN0e25ctfeJBiSuoayTp0VxVx33eKcIF2Vniw5jHvZIUaDwfXURwsuiFeRnn4gbj",
        "symbols": [ "BTCUSDT", "ETHUSDT",]
    },
    "MK": {
        "name": "VAR-BOT-MK",
        "api_key": "93ozx04amw21tnuiqGUcHDBHtbA98LyZXEgkOBTFnHOJYzW9pA2Im0Dh1brplVDt",
        "api_secret": "mfRvDaa7qoJxxYpI5igL2YlHwxMlujqd4r74D0meqRsMiUTrTmeEhvXtYiJtCo2X",
        "symbols": [ "BTCUSDT", "ETHUSDT",]
    },
    "ABT1": {
        "name": "VAR-BOT-ABT1",
        "api_key": "ZRaoNyvFOSmdc9yl7JrygKGwuIdm37BqG90SfS4yLxvFpft1a9wC47msWfLo4z2B",
        "api_secret": "LjrafiZmYlAizKsmoLhb63xT8kwPrAZ2CVfeKpfP1U6fyoud2O6exu3twfh5mA0i",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
    },
    "ABT3": {
        "name": "VAR-BOT-ABT3",
        "api_key": "coOTRf6642zLAThNCoS0RNLgJrlaYEEWX5EzcCcDBXJL8GYxeE1lyHtOdvLO8Umt",
        "api_secret": "xMhcykp4PW55pDeUO35qL7oM4v0jPExnTJT69xhFprGYw4pZx8Dt312iU17hldIJ",
        "symbols": ["BTCUSDT", "ETHUSDT",]
    },
    #"C2-CP": {
    #    "name": "VAR-BOT-CBT2-COPY",
    #    "api_key": "RNhWdKN2U6na1BTEKsAFdWhMBkuW6HUsR1gFEoYOjiOcgmgOVlYNZMRKAgYTas6D",
    #    "api_secret": "ExZmeTJdJpngYDgITiyiz6ntSWznKSGszLRQ8Ur0cd846L9LQkeP7BU7rmrVzps9",
    #    "symbols": ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT"]
    #},
    # "C2": {
    #     "name": "VAR-BOT-CBT2",
    #     "api_key": "T36Nh7Ed0XdohGhcxAYSIdvHlf4y2VeNDsHuR00DfG9RVdJCzxvObxx6OOFIXjHo",
    #     "api_secret": "l0QtrPOJ7m4oqYmkDglJyGRxvIj4cAskTsodvx4XkkdwfzpRa8QJISMwvDya0iKz",
    #     "symbols": ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "SUIUSDT", "UNIUSDT", "LTCUSDT", "ADAUSDT", "BNBUSDT", "LINKUSDT", "OPUSDT", "ARBUSDT",]
    # },
    # "C2S2": {
    #     "name": "VAR-BOT-CBT2S2",
    #     "api_key": "V3BeVwZyxM0lgpFmzFqhTqmjjawvNKlmZU4oCtVS4OZUudRwNhUApkkfgn9vzkfB",
    #     "api_secret": "rbCkv4bKmqgYPK9dHgw4h7d57yEP4G7YjvRokYTGjoWlsN9Kze9iRGCfQmNcETsE",
    #     "symbols": ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "SUIUSDT", "UNIUSDT", "LTCUSDT", "ADAUSDT", "BNBUSDT", "LINKUSDT", "OPUSDT", "ARBUSDT",]
    # },
}

bot_clients = {}

tsm = ThreadedWebsocketManager("", "")

realtime_price = {
    "BTCUSDT": 0,
    "ETHUSDT": 0,
    "DOGEUSDT": 0,
    "SOLUSDT": 0,
    "AVAXUSDT": 0,
    "XRPUSDT": 0,
#    "DOTUSDT": 0,
#    "SUIUSDT": 0,
#    "UNIUSDT": 0,
#    "LTCUSDT": 0,
#    "ADAUSDT": 0,
#    "BNBUSDT": 0,
#    "LINKUSDT": 0,
#    "OPUSDT": 0,
#    "ARBUSDT": 0,
    
    "BTCUSD": 0,
    # "ETHUSD": 0,
}

realtime_vosc = {
    "BTCUSDT": 0,
    "ETHUSDT": 0,
    "DOGEUSDT": 0,
    "SOLUSDT": 0,
    "AVAXUSDT": 0,
    "XRPUSDT": 0,
#    "DOTUSDT": 0,
#    "SUIUSDT": 0,
#    "UNIUSDT": 0,
#    "LTCUSDT": 0,
#    "ADAUSDT": 0,
#    "BNBUSDT": 0,
#    "LINKUSDT": 0,
#    "OPUSDT": 0,
#    "ARBUSDT": 0,
    
    
    "BTCUSD": 0,
    # "ETHUSD": 0,
}

website_targets = [
    "https://www.masci.or.th",
    "https://events.ipst.ac.th",
    "https://timewfh.ipst.ac.th",
    "https://ideractive.com",
    "https://intelligence.masci.or.th",
    "https://studio.buildx.app",
    "https://api.buildx.app/status",
    "https://staffcoffeeapp.vercel.app",
    "https://occocoffeeapp.vercel.app",
]

ping_time = {}
futures = {}
port_loading = False
website_db_path = os.path.join(os.path.dirname(__file__), "logs", "website_monitor.db")
BOT_OFFLINE_SECONDS = 60
BOT_MONITOR_GRACE_SECONDS = 180
bot_monitor_started_at = datetime.now()


def init_website_monitor_db():
    conn = sqlite3.connect(website_db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS website_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            is_up INTEGER NOT NULL,
            status_code INTEGER,
            latency_ms INTEGER,
            error TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS website_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            down_at TEXT NOT NULL,
            up_at TEXT,
            duration_sec INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            is_up INTEGER NOT NULL,
            ping_age_sec INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name TEXT NOT NULL,
            down_at TEXT NOT NULL,
            up_at TEXT,
            duration_sec INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def website_db_connect():
    return sqlite3.connect(website_db_path)


def log_website_check(url, checked_at, is_up, status_code, latency_ms, error):
    conn = website_db_connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT is_up
        FROM website_checks
        WHERE url = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (url,),
    )
    last_row = cur.fetchone()
    last_is_up = bool(last_row[0]) if last_row is not None else None

    cur.execute(
        """
        INSERT INTO website_checks (url, checked_at, is_up, status_code, latency_ms, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            url,
            checked_at.strftime("%Y-%m-%d %H:%M:%S"),
            1 if is_up else 0,
            status_code,
            latency_ms,
            error,
        ),
    )

    # Transition: UP -> DOWN, open incident
    if last_is_up is True and not is_up:
        cur.execute(
            """
            INSERT INTO website_incidents (url, down_at)
            VALUES (?, ?)
            """,
            (url, checked_at.strftime("%Y-%m-%d %H:%M:%S")),
        )

    # Transition: DOWN -> UP, close latest open incident
    if last_is_up is False and is_up:
        cur.execute(
            """
            SELECT id, down_at
            FROM website_incidents
            WHERE url = ? AND up_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (url,),
        )
        incident = cur.fetchone()
        if incident is not None:
            incident_id, down_at_str = incident
            down_at = datetime.strptime(down_at_str, "%Y-%m-%d %H:%M:%S")
            duration_sec = int((checked_at - down_at).total_seconds())
            cur.execute(
                """
                UPDATE website_incidents
                SET up_at = ?, duration_sec = ?
                WHERE id = ?
                """,
                (
                    checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                    duration_sec,
                    incident_id,
                ),
            )

    conn.commit()
    conn.close()


def get_monthly_uptime_report(months=6):
    now = datetime.now()
    month_points = []
    for i in range(months):
        point = (now.replace(day=1) - timedelta(days=31 * i)).replace(day=1)
        month_points.append(point)

    month_points = sorted({p.strftime("%Y-%m"): p for p in month_points}.values())
    month_keys = [p.strftime("%Y-%m") for p in month_points]

    conn = website_db_connect()
    cur = conn.cursor()

    report = []
    for url in website_targets:
        month_stats = []
        for month_key in month_keys:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN is_up = 1 THEN 1 ELSE 0 END) AS up_count
                FROM website_checks
                WHERE url = ? AND strftime('%Y-%m', checked_at) = ?
                """,
                (url, month_key),
            )
            total_count, up_count = cur.fetchone()
            total_count = total_count or 0
            up_count = up_count or 0
            uptime_pct = round((up_count / total_count) * 100, 2) if total_count > 0 else None
            month_stats.append(
                {
                    "month": month_key,
                    "uptime_pct": uptime_pct,
                    "checks": total_count,
                }
            )

        report.append(
            {
                "url": url,
                "months": month_stats,
            }
        )

    cur.execute(
        """
        SELECT url, down_at, up_at, duration_sec
        FROM website_incidents
        ORDER BY down_at DESC
        LIMIT 200
        """
    )
    incidents = [
        {
            "url": r[0],
            "down_at": r[1],
            "up_at": r[2],
            "duration_sec": r[3],
        }
        for r in cur.fetchall()
    ]

    conn.close()

    return {
        "months": month_keys,
        "report": report,
        "incidents": incidents,
    }


def get_bot_targets():
    return sorted({futures_keys[f]["name"] for f in futures_keys})


def log_bot_check(bot_name, checked_at, is_up, ping_age_sec):
    conn = website_db_connect()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT is_up
        FROM bot_checks
        WHERE bot_name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (bot_name,),
    )
    last_row = cur.fetchone()
    last_is_up = bool(last_row[0]) if last_row is not None else None

    cur.execute(
        """
        INSERT INTO bot_checks (bot_name, checked_at, is_up, ping_age_sec)
        VALUES (?, ?, ?, ?)
        """,
        (
            bot_name,
            checked_at.strftime("%Y-%m-%d %H:%M:%S"),
            1 if is_up else 0,
            ping_age_sec,
        ),
    )

    if (last_is_up is True or last_is_up is None) and not is_up:
        cur.execute(
            """
            INSERT INTO bot_incidents (bot_name, down_at)
            VALUES (?, ?)
            """,
            (bot_name, checked_at.strftime("%Y-%m-%d %H:%M:%S")),
        )

    if last_is_up is False and is_up:
        cur.execute(
            """
            SELECT id, down_at
            FROM bot_incidents
            WHERE bot_name = ? AND up_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (bot_name,),
        )
        incident = cur.fetchone()
        if incident is not None:
            incident_id, down_at_str = incident
            down_at = datetime.strptime(down_at_str, "%Y-%m-%d %H:%M:%S")
            duration_sec = int((checked_at - down_at).total_seconds())
            cur.execute(
                """
                UPDATE bot_incidents
                SET up_at = ?, duration_sec = ?
                WHERE id = ?
                """,
                (
                    checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                    duration_sec,
                    incident_id,
                ),
            )

    conn.commit()
    conn.close()


def run_bot_checks(should_log=True):
    now = datetime.now()
    results = []
    elapsed_since_start = int((now - bot_monitor_started_at).total_seconds())

    for bot_name in get_bot_targets():
        last_ping = ping_time.get(bot_name)
        ping_age_sec = None
        if last_ping is not None:
            ping_age_sec = int((now - last_ping).total_seconds())

        is_up = ping_age_sec is not None and ping_age_sec < BOT_OFFLINE_SECONDS
        in_grace = ping_age_sec is None and elapsed_since_start < BOT_MONITOR_GRACE_SECONDS

        if should_log and not in_grace:
            log_bot_check(bot_name, now, is_up, ping_age_sec)

        results.append(
            {
                "bot_name": bot_name,
                "is_up": is_up,
                "ping_age_sec": ping_age_sec,
                "in_grace": in_grace,
                "last_ping": last_ping.strftime("%Y-%m-%d %H:%M:%S") if last_ping is not None else None,
                "checked_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return results


def bot_monitor_loop():
    while True:
        try:
            run_bot_checks(should_log=True)
        except Exception as e:
            logger.error(f"Bot monitor loop failed: {e}")
        time.sleep(60)


def get_monthly_bot_uptime_report(months=6):
    now = datetime.now()
    month_points = []
    for i in range(months):
        point = (now.replace(day=1) - timedelta(days=31 * i)).replace(day=1)
        month_points.append(point)

    month_points = sorted({p.strftime("%Y-%m"): p for p in month_points}.values())
    month_keys = [p.strftime("%Y-%m") for p in month_points]

    conn = website_db_connect()
    cur = conn.cursor()

    report = []
    for bot_name in get_bot_targets():
        month_stats = []
        for month_key in month_keys:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN is_up = 1 THEN 1 ELSE 0 END) AS up_count
                FROM bot_checks
                WHERE bot_name = ? AND strftime('%Y-%m', checked_at) = ?
                """,
                (bot_name, month_key),
            )
            total_count, up_count = cur.fetchone()
            total_count = total_count or 0
            up_count = up_count or 0
            uptime_pct = round((up_count / total_count) * 100, 2) if total_count > 0 else None
            month_stats.append(
                {
                    "month": month_key,
                    "uptime_pct": uptime_pct,
                    "checks": total_count,
                }
            )

        report.append(
            {
                "bot_name": bot_name,
                "months": month_stats,
            }
        )

    cur.execute(
        """
        SELECT bot_name, down_at, up_at, duration_sec
        FROM bot_incidents
        ORDER BY down_at DESC
        LIMIT 200
        """
    )
    incidents = [
        {
            "bot_name": r[0],
            "down_at": r[1],
            "up_at": r[2],
            "duration_sec": r[3],
        }
        for r in cur.fetchall()
    ]

    conn.close()

    return {
        "months": month_keys,
        "report": report,
        "incidents": incidents,
    }


init_website_monitor_db()


def run_website_checks(should_log=True):
    results = []

    for url in website_targets:
        checked_at = datetime.now()
        start = time.time()
        status_code = None
        error = None
        is_up = False

        try:
            response = requests.get(
                url,
                timeout=8,
                allow_redirects=True,
                headers={"User-Agent": "mk-dashboard-monitor/1.0"},
            )
            status_code = response.status_code
            is_up = status_code < 500
        except Exception as e:
            error = str(e)

        latency_ms = int((time.time() - start) * 1000)

        if should_log:
            log_website_check(url, checked_at, is_up, status_code, latency_ms, error)

        results.append({
            "url": url,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "is_up": is_up,
            "error": error,
            "checked_at": checked_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return results


def website_monitor_loop():
    while True:
        try:
            run_website_checks(should_log=True)
        except Exception as e:
            logger.error(f"Website monitor loop failed: {e}")
        time.sleep(60)

# List of tasks and their corresponding dates (in "YYYY-MM-DD" format)
tasks_dates = [
    # ("KCC", "2024-06-30"),
    # ("MASCI", "2024-06-26"),
    # ("Life", "2044-12-25")
]

# List of stock tickers to display
bought_prices = {
     "AAPL": None,
     "GOOG": None,
     "NVDA": None,
     "BTC-USD": None,
     "ETH-USD": None,
    #  "BNB-USD": None,
    #  "SOL-USD": None,
     "GLD": None,
     "^SET.BK": None,
}

stock_tickers = list(bought_prices.keys())

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code):
    logger.info(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")
    client.publish("hello", str({"name":"mk-dashboard"}), 0)
    
    client.subscribe("binance/price/#")
    client.subscribe("bot/update/#")
    client.subscribe("hello")
    client.subscribe("ping")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global realtime_price, ping_time, interval_until_update
    # print(msg.topic+" "+str(msg.payload))
    # logger.warning(f"Received message: {msg.topic} {msg.payload}")
    # Received message: binance/price/ETHUSDT b"{'price': 2457.16, 'vosc': -32.27497714181611}"
    if msg.topic.startswith("bot/update/"):
        data = eval(msg.payload)    
        interval_until_update = 0   
        
    if msg.topic.startswith("binance/price/"):
        realtime_price[msg.topic.split("/")[-1]] = float(eval(msg.payload)["price"])
        realtime_vosc[msg.topic.split("/")[-1]] = float(eval(msg.payload)["vosc"])
        socketio.emit("realtime_price", realtime_price)
        socketio.emit("realtime_vosc", realtime_vosc)
    if msg.topic == "ping" or msg.topic == "hello":
        payload = eval(msg.payload)
        
        name = payload["name"].replace("bot-var/", "")
        ping_time[name] = datetime.now()
        socketio.emit("ping", json.dumps({"name": name, "ping_time": ping_time[name].strftime("%Y-%m-%d %H:%M:%S")}))

def mqtt_thread():
    logger.info("Starting MQTT client...")
    mqttc = mqtt.Client()
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    mqttc.username_pw_set(username="mekku",password="gavi0tic")
    mqttc.connect("122.155.168.31", 1883, 60)
    mqttc.loop_forever()
    
def position_update():
    global futures, interval_until_update
    time.sleep(10)
    
    while True:
        try:
            results = Parallel(n_jobs=2, prefer="threads")(delayed(get_info)(futures_keys[f]["api_key"], futures_keys[f]["api_secret"], futures_keys[f]["symbols"], futures_keys[f]["name"], ) for f in futures_keys)
            futures = {f: result for f, result in zip(futures_keys, results)}
            
            for i in range(60):
                time.sleep(10)
                
                for f in futures_keys:
                    # for symbol in futures_keys[f]["symbols"]:
                    # logger.error(f"Updating {f}")
                    # futures[f] = get_info(futures_keys[f]["api_key"], futures_keys[f]["api_secret"], futures_keys[f]["symbols"], futures_keys[f]["name"])
                    socketio.emit("bot_info_update", json.dumps(futures[f]))
            
        except Exception as e:
            logger.error(f"Failed to update positions: {e}")
            sys.exit(9)
            os._exit(9)
        
    
# # Emit real-time data to the client
def handle_message(msg):
    global realtime_price
    # logger.error(msg)
    # {'stream': 'btcusdt@bookTicker', 'data': {'e': 'bookTicker', 'u': 5382506839460, 's': 'BTCUSDT', 'b': '63340.00', 'B': '3.803', 'a': '63340.10', 'A': '9.366', 'T': 1726962979326, 'E': 1726962979326}}
    if "data" in msg:
        msg = msg["data"]

    if msg["e"] == "error":
        logger.error(msg)
        return

    if msg["e"] == "24hrTicker":
        symbol = msg["s"]
        price = float(msg["c"])
        realtime_price[symbol] = price
        socketio.emit("realtime_price", realtime_price)
    elif msg["e"] == "bookTicker":
        symbol = msg["s"]
        price = float(msg["b"])
        realtime_price[symbol] = price
        socketio.emit("realtime_price", realtime_price)
    elif msg["e"] == "markPriceUpdate":
        symbol = msg["s"]
        if symbol == "BTCUSD_PERP":
            symbol = "BTCUSD"
            
        price = float(msg["p"])
        realtime_price[symbol] = price
        socketio.emit("realtime_price", realtime_price)


tsm.start()
# tsm.start_user_socket(callback=handle_message)
# Get price feed

for symbol in realtime_price.keys():
    if symbol[-4:] == "USDT":
        tsm.start_symbol_mark_price_socket(callback=handle_message, symbol=symbol)
    else:
        tsm.start_symbol_mark_price_socket(callback=handle_message, symbol="BTCUSD_PERP", futures_type=FuturesType.COIN_M)
    
# Get portfolio balance

def get_portfolio_balance(binance, futures_type = "usdtm", price = 1):
    global logger
    
    try:
        if futures_type == "usdtm":
            response = binance.fetch_balance()
            # logger.info(response)
            balance = float(response["total"]["USDT"])
            initial = float(response["info"]["totalWalletBalance"])
            profit = float(response["info"]["totalUnrealizedProfit"])
        elif futures_type == "coinm":            
            response = binance.fetch_balance()
            # logger.error(response)
            balance = float(response["total"]["BTC"]) * price
            initial = float(response["total"]["BTC"]) * price
            profit = 0
        return balance, initial, profit
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
        return 0, 0, 0

def get_portfolio_positions(binance, symbol=None):
    global logger
    
    try:
        positions = binance.fetch_positions()
        
        if symbol is not None:
            positions = [position for position in positions if symbol in position["symbol"].replace("/", "")]
            
            if symbol == "BTCUSD":
                # Symbol is BTCUSD is COIN-M futures then convert contracts to USD
                for position in positions:
                    position["contracts"] = position["contracts"] * 100 / realtime_price["BTCUSD"]
                    position["entryPrice"] = position["entryPrice"]
                    position["unrealizedPnl"] = position["unrealizedPnl"] * realtime_price["BTCUSD"]

        # logger.info(positions)
        return positions
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
        return []

def get_orders(binance, symbol="BTCUSDT"):
    orders = []
    try:
        if symbol == "BTCUSD":
            symbol = "BTCUSD_PERP"
            
        orders = binance.fetchOpenOrders(symbol)
        try:
            conditional_orders = binance.fetchOpenOrders(
                symbol, params={"trigger": True}
            )
            existing_ids = {order["id"] for order in orders}
            for algo_order in conditional_orders:
                if algo_order["id"] not in existing_ids:
                    orders.append(algo_order)
                    existing_ids.add(algo_order["id"])
        except Exception as e:
            print(f"Error while fetching binance conditional orders: {e}")
        # Sort orders by trigger price
        orders = sorted(orders, key=lambda x: x["triggerPrice"], reverse=False)
        print(orders)
        print(f"Found {len(orders)} orders")

        for o in orders:
            orderInfoType = o["info"]["orderType"] if "info" in o and "orderType" in o["info"] and o["info"]["orderType"] is not None else ""
            orderType = o["type"] if "type" in o and o["type"] is not None else ""
            print(orderInfoType)
            print(orderType)
            if "STOP" in orderInfoType or "stop" in orderType:
                o["type"] = "SL"
            elif "TAKE" in orderInfoType or "take" in orderType:
                o["type"] = "TP"
        # logger.error(orders)
        return orders
    except Exception as e:
        print(e)
        logger.error(f"Failed to fetch orders: Code {e}")
        
        return orders 

####################################################################

# Function to calculate days left until each date
def calculate_days_left(dates):
    today = datetime.today()
    days_left_list = [(datetime.strptime(date, "%Y-%m-%d") - today).days for date in dates]
    return days_left_list

# Function to fetch stock data and calculate EMAs
def fetch_stock_data(ticker):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Fetch daily stock data
        df = yf.download(ticker, start=start_date, end=end_date)
        
        if df.empty:
            raise ValueError(f"No data found for {ticker}")
        
        # Calculate EMAs
        df["EMA12"] = df["Close"].ewm(span=12, adjust=True).mean()
        df["EMA25"] = df["Close"].ewm(span=26, adjust=True).mean()
        
        latest_data = df.iloc[-1]  # Get the latest row of data
        return {
            "change": latest_data["Close"] - df.iloc[-2]["Close"],
            "current_price": latest_data["Close"],
            "ema12": latest_data["EMA12"],
            "ema25": latest_data["EMA25"]
        }
    except Exception as e:
        logger.error(f"Failed to download data for {ticker}: {e}")
        return None

# Function to determine the background color based on EMAs
def get_background_color(ema12, ema25):
    return "green" if ema12 > ema25 else "red"

# Function to determine the border color based on PnL
def get_border_color(current_price, bought_price):
    return "blue" if current_price > bought_price else "red"

def get_info(api_key, api_secret, symbols, name):
    global bot_clients
    # logger = logging.getLogger(__name__)
    # logger.addHandler(handler)
    # logger.setLevel(logging.INFO)

    timer_start = time.time()
    is_coinm = "BTCUSD" in symbols
    
    if bot_clients.get(name) is None:
        if is_coinm:
            binance = ccxt.binancecoinm({
                "apiKey": api_key,
                "secret": api_secret,
                "options": {
                    "defaultType": "future",
                },
                'adjustForTimeDifference': False,
                'enableRateLimit': False,
                'verbose': False
            })
            
        else:
            binance = ccxt.binance({
                "apiKey": api_key,
                "secret": api_secret,
                "options": {
                    "defaultType": "future",
                },
                'adjustForTimeDifference': False,
                'enableRateLimit': False,
                'verbose': False
            })
        bot_clients[name] = binance
    else:
        binance = bot_clients[name]
        
    # logger.info(f"Time taken for balance: {time.time() - timer_start:.2f} seconds")
    positions = get_portfolio_positions(binance)
    
    print ("Get portfolio positions")
    
    info = {}
    info["name"] = name
    info["balance"], info["initial"], info["upnl"] = get_portfolio_balance(binance, futures_type="usdtm" if not is_coinm else "coinm", price=realtime_price["BTCUSD"])
    info["positions"] = {}
    info["symbols"] = symbols
    
    for symbol in symbols:
        logger.info(f"Fetching {name} {symbol}...")
        
        positions_info = {}
        current_price = realtime_price[symbol]
        positions_info["symbol"] = symbol
        # logger.info(f"Time taken for balance: {time.time() - timer_start:.2f} seconds")
        
        positions_info["positions"] = [position for position in positions if symbol in position["symbol"].replace("/", "")]
        # logger.info(f"Time taken for balance: {time.time() - timer_start:.2f} seconds")
        
        positions_info["pnl"] = f'{sum([position["unrealizedPnl"] for position in positions_info["positions"]]):,.0f}'
        if positions_info["pnl"] == "0":
            positions_info["pnl"] = ""
        positions_info["orders"] = get_orders(binance, symbol)
        # logger.info(f"Time taken for balance: {time.time() - timer_start:.2f} seconds")
        
        buy_order = [order for order in positions_info["orders"] if order["side"] == "buy"]
        sell_order = [order for order in positions_info["orders"] if order["side"] == "sell"]
        if buy_order and len(buy_order) > 0:
            positions_info["buy_order"] = buy_order[0]
        if sell_order and len(sell_order) > 0:
            positions_info["sell_order"] = sell_order[0]
            
        if name in ping_time and ping_time[name] is not None:
            positions_info["ping_time"] = ping_time[name].strftime("%Y-%m-%d %H:%M:%S")
            
        
        info["positions"][symbol] = positions_info
        
    socketio.emit("bot_info_update", json.dumps(info))
    
    logger.info(f"Time taken for {name}: {time.time() - timer_start:.2f} seconds")
    
    return info

@app.route("/")
def dashboard():
    global port_loading, futures, ping_time
    days_left_list = calculate_days_left([date for task, date in tasks_dates])
    tasks = [{"task": task, "days_left": days_left} for task, days_left in zip(tasks_dates, days_left_list)]

    # Get info for each futures account parallelly
    start_time = time.time()
    # if not port_loading:
    #     logger.info("Fetching futures info...")
    #     futures = {}
    #     port_loading = True
    #     # results = Parallel(n_jobs=8)(delayed(get_info)(futures_keys[f]["api_key"], futures_keys[f]["api_secret"], futures_keys[f]["symbol"], futures_keys[f]["name"], ) for f in futures_keys)
    #     # futures = {f: result for f, result in zip(futures_keys, results)}
    #     # for f in futures_keys:
    #     #     futures[f] = get_info(futures_keys[f]["api_key"], futures_keys[f]["api_secret"], futures_keys[f]["symbol"], futures_keys[f]["name"])
    #     logger.info(f"Time taken for all futures: {time.time() - start_time:.2f} seconds")
    
    #     port_loading = False
    # else:
    #     while port_loading:
    #         time.sleep(1)
            
    # logger.error(results)


    # for f in futures_keys:
    #     logger.info(f)
    #     futures[f] = get_info(futures_keys[f]["api_key"], futures_keys[f]["api_secret"], futures_keys[f]["symbol"])
    
    aum = sum([futures[f]["balance"] for f in futures])
    
    # stocks = []
    # for ticker in stock_tickers:
    #     data = fetch_stock_data(ticker)
    #     if data:
    #         bg_color = get_background_color(data["ema12"], data["ema25"])
    #         border_color = "gray"
    #         if ticker in bought_prices and bought_prices[ticker] is not None:
    #             border_color = get_border_color(data["current_price"], bought_prices[ticker])
    #         stocks.append({
    #             "ticker": ticker,
    #             "change": round(data["change"] * 100) / 100,
    #             "current_price": round(data["current_price"] * 100) / 100,
    #             "bg_color": bg_color,
    #             "border_color": border_color
    #         })
    #     else:
    #         stocks.append({
    #             "ticker": ticker,
    #             "change": "-",
    #             "current_price": "-",
    #             "bg_color": "gray",
    #             "border_color": "gray"
    #         })
    
    initial_ping_time = {}
    for f in futures_keys:
        name = futures_keys[f]["name"]
        if name in ping_time and ping_time[name] is not None:
            initial_ping_time[name] = ping_time[name].strftime("%Y-%m-%d %H:%M:%S")
        else:
            initial_ping_time[name] = None

    for name in ping_time:
        if name not in initial_ping_time:
            if ping_time[name] is not None:
                initial_ping_time[name] = ping_time[name].strftime("%Y-%m-%d %H:%M:%S")
            else:
                initial_ping_time[name] = None

    return render_template(
        "dashboard.html",
        tasks=tasks,
        futures=futures,
        aum=aum,
        initial_ping_time=initial_ping_time,
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    # return render_template("dashboard.html", tasks=tasks, stocks=stocks, futures=futures, aum=aum, update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route("/jenkins")
def jenkins():
            #   const url = 'https://mkjk.ideractive.com/api/json';
            #         const headers = {
            #             "Authorization": "Basic " + btoa(`nakara:1121756eb3f5e37e2a7be9006ef0ab19e1`),
            #             "Content-Type": "application/json"
            #         };
            #         const response = await fetch(url, {
            #             method: 'GET',
            #             headers: headers
            #         });

            #         console.log(response);
            #         // {"_class":"hudson.model.Hudson","assignedLabels":[{"name":"built-in"},{"name":"master"}],"mode":"NORMAL","nodeDescription":"the Jenkins controller's built-in node","nodeName":"","numExecutors":4,"description":null,"jobs":[{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"BuildX-Server-DEV","url":"https://mkjk.ideractive.com/job/BuildX-Server-DEV/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"BuildX-Server-Lambda-DEV","url":"https://mkjk.ideractive.com/job/BuildX-Server-Lambda-DEV/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"BuildX-Studio-DEV","url":"https://mkjk.ideractive.com/job/BuildX-Studio-DEV/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"ipone-b2b (staging)","url":"https://mkjk.ideractive.com/job/ipone-b2b%20(staging)/","color":"blue"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"ipone-b2c (staging)","url":"https://mkjk.ideractive.com/job/ipone-b2c%20(staging)/","color":"blue"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"KCC-E-Memo-BuildX-Server","url":"https://mkjk.ideractive.com/job/KCC-E-Memo-BuildX-Server/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"KCC-E-Memo-BuildX-Studio","url":"https://mkjk.ideractive.com/job/KCC-E-Memo-BuildX-Studio/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"KCC-E-Memo-BuildX-Studio-UAT","url":"https://mkjk.ideractive.com/job/KCC-E-Memo-BuildX-Studio-UAT/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"MASCI-BuildX-Studio","url":"https://mkjk.ideractive.com/job/MASCI-BuildX-Studio/","color":"blue"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"MASCI-E-Memo-BuildX-Server","url":"https://mkjk.ideractive.com/job/MASCI-E-Memo-BuildX-Server/","color":"blue"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"mini-line-app-production","url":"https://mkjk.ideractive.com/job/mini-line-app-production/","color":"red"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"mini-line-app-staging","url":"https://mkjk.ideractive.com/job/mini-line-app-staging/","color":"blue"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"\ud83d\ude80 ipone-b2b (production)","url":"https://mkjk.ideractive.com/job/%F0%9F%9A%80%20ipone-b2b%20(production)/","color":"notbuilt"},{"_class":"org.jenkinsci.plugins.workflow.job.WorkflowJob","name":"\ud83d\ude80 ipone-b2c (production)","url":"https://mkjk.ideractive.com/job/%F0%9F%9A%80%20ipone-b2c%20(production)/","color":"blue"}],"overallLoad":{},"primaryView":{"_class":"hudson.model.AllView","name":"all","url":"https://mkjk.ideractive.com/"},"quietingDown":false,"slaveAgentPort":50000,"unlabeledLoad":{},"useCrumbs":true,"useSecurity":true,"views":[{"_class":"hudson.model.AllView","name":"all","url":"https://mkjk.ideractive.com/"}]}

    # Fetch Jenkins data with compact fields including last build timestamp
    url = "https://mkjk.ideractive.com/api/json"
    headers = {
        "Authorization": "Basic " + b64encode(b"nakara:1121756eb3f5e37e2a7be9006ef0ab19e1").decode("utf-8"),
        "Content-Type": "application/json"
    }
    params = {
        "tree": "jobs[name,url,color,lastBuild[timestamp]]"
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    try:
        data = response.json()

        for job in data.get("jobs", []):
            last_build = job.get("lastBuild") or {}
            job["last_build_ts"] = last_build.get("timestamp")
    
        # Return as json
        return json.dumps(data)
    except:
        return []

@app.route("/website_status")
def website_status():
    results = run_website_checks(should_log=False)
    return json.dumps({"websites": results})


@app.route("/website_report")
def website_report():
    report_data = get_monthly_uptime_report(months=6)
    return render_template("website_report.html", report_data=report_data)


@app.route("/bot_report")
def bot_report():
    report_data = get_monthly_bot_uptime_report(months=6)
    return render_template("bot_report.html", report_data=report_data)

@app.route("/abt_status")
def abt_status():
    global ping_time
    status = {}
    filtered_ping_time = {k: v for k, v in ping_time.items() if "ABT" in k}
    for f in ping_time:
        status[f] = "offline"
        if f in ping_time:
            if (datetime.now() - ping_time[f]).seconds < 60:
                status[f] = "online"
                
    return render_template("ping_status.html", ping_time=filtered_ping_time, status=status)

@app.route("/bot_status")
def ping_status():
    global ping_time
    status = {}
    for f in ping_time:
        status[f] = "offline"
        if f in ping_time and ping_time[f] is not None:
            if (datetime.now() - ping_time[f]).seconds < 60:
                status[f] = "online"
                
    # Add missing bots
    for f in futures_keys:
        name = futures_keys[f]["name"]
        if name not in ping_time and name not in status:
            ping_time[name] = None
            status[name] = "offline"
            
    # Sort by name
    sorted_status = dict(sorted(status.items(), key=lambda item: item[0]))
    ping_time = dict(sorted(ping_time.items(), key=lambda item: item[0]))
                
    return render_template("ping_status.html", ping_time=ping_time, status=sorted_status)

if __name__ == "__main__":    

    for f in futures_keys:
        futures[f] = {
            "current_price": 0,
            "name": futures_keys[f]["name"],
            "balance": 0,
            "initial": 0,
            "upnl": 0,
            "pnl": "",
            "positions": [],
            "buy_order": None,
            "sell_order": None,
            "ping_time": None,
        }  
    
    # Start the MQTT client in a separate thread
    mqtt_thread = Thread(target=mqtt_thread)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # Start the position update thread
    position_update_thread = Thread(target=position_update)
    position_update_thread.daemon = True
    position_update_thread.start()

    # Start website monitor thread
    website_monitor_thread = Thread(target=website_monitor_loop)
    website_monitor_thread.daemon = True
    website_monitor_thread.start()

    # Start bot monitor thread
    bot_monitor_thread = Thread(target=bot_monitor_loop)
    bot_monitor_thread.daemon = True
    bot_monitor_thread.start()

    logger.info("Running the socket server...")
    # Open chrome browser when the server starts 5 seconds later
    # os.system("chromium-browser --kiosk http://127.0.0.1:5000")
    # os.system("sleep 5 && DISPLAY=:0 chromium-browser --kiosk http://127.0.0.1:5000 &")
    # os.spawnl(os.P_NOWAIT, "chromium-browser", "chromium-browser", "--kiosk", "http://127.0.0.1:5000")
    
    # Start the Flask web server
    socketio.run(app, host="0.0.0.0", debug=True, use_reloader=False, allow_unsafe_werkzeug=True)

    # logger.info("Running the webserver...")
    # app.run(debug=True, host="0.0.0.0")
