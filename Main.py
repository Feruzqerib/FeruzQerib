import websocket
import json
import numpy as np
import pandas as pd
import time
import talib
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch

# Parametrlər
USE_BOLLINGER = True
USE_STOCH_RSI = True
USE_TREND_FILTER = True
TIMEFRAME_SECONDS = 60
HISTORY_LENGTH = 100
ASSETS = ['R_100', 'EURUSD', 'GBPUSD']
API_TOKEN = "fSxKy6d7pJRfvfO"
DERIV_WS = "wss://ws.binaryws.com/websockets/v3?app_id=1089"

# Siqnal gücü filtrasiyası üçün minimum MACD fərqi
SIGNAL_STRENGTH_THRESHOLD = 0.001

# DataFrame yaratmaq
price_data = pd.DataFrame(columns=["timestamp", "close"])

# Göstəricilərin hesablanması funksiyaları
def calculate_ema(data, period=10):
    return talib.EMA(np.array(data), timeperiod=period)

def calculate_rsi(data, period=14):
    return talib.RSI(np.array(data), timeperiod=period)

def calculate_macd(data, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, macdsignal, macdhist = talib.MACD(np.array(data), fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    return macd, macdsignal

def calculate_bollinger(data, period=20):
    upper, middle, lower = talib.BBANDS(np.array(data), timeperiod=period, nbdevup=2, nbdevdn=2, matype=0)
    return upper, middle, lower

def calculate_stoch_rsi(data, period=14):
    stoch_rsi = talib.STOCHRSI(np.array(data), timeperiod=period)
    return stoch_rsi

# Siqnalın yaranması funksiyası
def generate_signal(data):
    if len(data) < 30:
        return "No Signal"

    ema10 = calculate_ema(data, 10)
    ema20 = calculate_ema(data, 20)
    rsi = calculate_rsi(data)
    macd, macdsignal = calculate_macd(data)
    
    signal = "No Signal"
    
    if ema10[-1] > ema20[-1] and rsi[-1] > 50 and macd[-1] > macdsignal[-1]:
        signal = "UP"
    elif ema10[-1] < ema20[-1] and rsi[-1] < 50 and macd[-1] < macdsignal[-1]:
        signal = "DOWN"
    
    # Siqnal gücü filtrasiyası
    if abs(macd[-1] - macdsignal[-1]) < SIGNAL_STRENGTH_THRESHOLD:
        signal = "Weak Signal"
    
    return signal

# WebSocket bağlantısı və məlumat alışı
def on_message(ws, message):
    message = json.loads(message)
    if message["msg_type"] == "price":
        timestamp = message["tick"]["epoch"]
        price = message["tick"]["quote"]
        
        # Qiymətləri dataframe-ə əlavə et
        price_data.loc[len(price_data)] = [timestamp, price]

        if len(price_data) > HISTORY_LENGTH:
            price_data.drop(index=0, inplace=True)

        signal = generate_signal(price_data["close"].values)
        print(f"Signal: {signal} at {price} for asset")

# WebSocket parametrləri
def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Closed connection")
    ws.close()

def on_open(ws):
    print("Connected to Deriv WebSocket")
    subscription_message = {
        "req_id": "1",
        "ticks": ASSETS,
        "subscribe": 1,
        "app_id": API_TOKEN
    }
    ws.send(json.dumps(subscription_message))

# GUI tətbiqi (Kivy)
class FeruzQerubGUI(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.label = Label(text="FeruzQerub Trading Bot", font_size=32)
        self.spinner = Spinner(text="Select Asset", values=ASSETS, size_hint=(None, None), size=(200, 44))
        self.start_button = Button(text="Start Bot", size_hint=(None, None), size=(200, 44), on_press=self.start_bot)
        self.stop_button = Button(text="Stop Bot", size_hint=(None, None), size=(200, 44), on_press=self.stop_bot)
        self.signal_display = Label(text="Signal: None", font_size=20)
        
        layout.add_widget(self.label)
        layout.add_widget(self.spinner)
        layout.add_widget(self.start_button)
        layout.add_widget(self.stop_button)
        layout.add_widget(self.signal_display)

        return layout

    def start_bot(self, instance):
        self.ws = websocket.WebSocketApp(DERIV_WS, on_message=on_message, on_error=on_error, on_close=on_close)
        self.ws.on_open = on_open
        self.ws.run_forever()

    def stop_bot(self, instance):
        self.ws.close()
        self.signal_display.text = "Signal: None"

# Botun başladığı yerdə GUI-nin başlatılması
if __name__ == "__main__":
    FeruzQerubGUI().run()
