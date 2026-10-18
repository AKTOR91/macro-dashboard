import os
import json
import datetime
import pandas as pd
from fredapi import Fred
import yfinance as yf

# ==========================================
# 1. CONFIGURACIÓN DE CLAVES
# ==========================================
try:
    from config import FRED_API_KEY
except ImportError:
    FRED_API_KEY = os.environ.get('FRED_API_KEY')

fred = Fred(api_key=FRED_API_KEY)
print("Descargando datos macroeconómicos...")

# ==========================================
# 2. FUNCIONES DE AYUDA Y FORMATEO
# ==========================================
def get_fred(series_id):
    try:
        return fred.get_series(series_id)
    except Exception as e:
        print(f"Error al descargar {series_id}: {e}")
        return None

def calc_yoy(series):
    if series is None: return None
    return (series / series.shift(12) - 1) * 100

def to_dict(series, freq='monthly', limit=36):
    if series is None or len(series) == 0: 
        return {"dates": [], "values": []}
    s = series.dropna().tail(limit)
    dates = [d.strftime('%Y-%m-%d') for d in s.index]
    values = [round(float(v), 2) for v in s.values]
    return {"dates": dates, "values": values}

def get_current(series, decimals=2):
    if series is None or len(series) == 0: return 0.0
    return round(float(series.dropna().iloc[-1]), decimals)

def get_delta(series, decimals=2):
    if series is None or len(series.dropna()) < 2: return 0.0
    s = series.dropna()
    return round(float(s.iloc[-1] - s.iloc[-2]), decimals)

# ==========================================
# 3. DESCARGA DE DATOS (FRED y YAHOO)
# ==========================================
# --- A. Crecimiento ---
gdp = get_fred('A191RL1Q225SBEA')
ism_mfg = get_fred('GACDFSA066MSFRBPHI')
ism_svcs = get_fred('GACDISA066MSFRBNY')
nfp_raw = get_fred('PAYEMS')
nfp = nfp_raw.diff().dropna() if nfp_raw is not None else None

# --- B. Inflación ---
cpi = calc_yoy(get_fred('CPIAUCSL'))
core_cpi = calc_yoy(get_fred('CPILFESL'))
pce = calc_yoy(get_fred('PCEPI'))
core_pce = calc_yoy(get_fred('PCEPILFE'))

# --- C. Tipos de interés ---
fed_funds = get_fred('DFF')
yield_1y = get_fred('DGS1')
yield_2y = get_fred('DGS2')
yield_5y = get_fred('DGS5')
yield_10y = get_fred('DGS10')
yield_curve = get_fred('T10Y2Y')

# --- D. Riesgo ---
hy_spread = get_fred('BAMLH0A0HYM2')
m2_raw = get_fred('M2SL')
m2_yoy = calc_yoy(m2_raw)

print("Descargando datos de mercado (VIX, DXY)...")
tickers = yf.download(['^VIX', 'DX-Y.NYB'], period='2y', progress=False)['Close']
vix = tickers['^VIX'].dropna() if '^VIX' in tickers else None
dxy = tickers['DX-Y.NYB'].dropna() if 'DX-Y.NYB' in tickers else None

# ==========================================
# 4. CALENDARIO ECONÓMICO ESTÁTICO
# ==========================================
# Aquí puedes añadir o quitar eventos. 
# El formato es: {"date": "AÑO-MES-DÍA", "event": "Nombre", "estimate": "Previsión", "previous": "Anterior"}
def get_static_calendar():
    return [
        {"date": "2026-10-23", "event": "M2 Money Supply", "estimate": "1.8%", "previous": "1.7%"},
        {"date": "2026-10-28", "event": "Consumer Confidence", "estimate": "98.5", "previous": "98.7"},
        {"date": "2026-10-30", "event": "GDP QoQ (Avance)", "estimate": "2.1%", "previous": "3.0%"},
        {"date": "2026-10-30", "event": "Core PCE Price Index", "estimate": "2.8%", "previous": "2.8%"},
        {"date": "2026-11-01", "event": "ISM Manufacturing PMI", "estimate": "50.8", "previous": "50.2"},
        {"date": "2026-11-03", "event": "Non-Farm Payrolls (NFP)", "estimate": "165K", "previous": "254K"},
        {"date": "2026-11-03", "event": "Unemployment Rate", "estimate": "4.1%", "previous": "4.1%"},
        {"date": "2026-11-05", "event": "ISM Services PMI", "estimate": "52.3", "previous": "51.5"},
        {"date": "2026-11-07", "event": "Fed Interest Rate Decision", "estimate": "4.50%", "previous": "4.50%"},
        {"date": "2026-11-13", "event": "CPI YoY", "estimate": "2.9%", "previous": "3.1%"},
        {"date": "2026-11-13", "event": "Core CPI YoY", "estimate": "3.2%", "previous": "3.3%"}
    ]

print("Cargando calendario...")
calendar_events = get_static_calendar()

# ==========================================
# 5. CONSTRUCCIÓN DEL JSON FINAL
# ==========================================
data = {
    "lastUpdate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "current": {
        "gdp": get_current(gdp, 1),
        "ismMfg": get_current(ism_mfg, 1),
        "ismSvcs": get_current(ism_svcs, 1),
        "nfp": get_current(nfp, 0),
        "cpi": get_current(cpi, 1),
        "coreCpi": get_current(core_cpi, 1),
        "pce": get_current(pce, 1),
        "corePce": get_current(core_pce, 1),
        "fedFunds": get_current(fed_funds, 2),
        "yield1y": get_current(yield_1y, 2),
        "yield2y": get_current(yield_2y, 2),
        "yield5y": get_current(yield_5y, 2),
        "yield10y": get_current(yield_10y, 2),
        "yieldCurve": get_current(yield_curve, 2),
        "vix": get_current(vix, 1),
        "dxy": get_current(dxy, 1),
        "hySpread": get_current(hy_spread, 2),
        "m2YoY": get_current(m2_yoy, 1)
    },
    "deltas": {
        "gdp": get_delta(gdp, 1),
        "ismMfg": get_delta(ism_mfg, 1),
        "ismSvcs": get_delta(ism_svcs, 1),
        "nfp": get_delta(nfp, 0),
        "cpi": get_delta(cpi, 1),
        "coreCpi": get_delta(core_cpi, 1),
        "pce": get_delta(pce, 1),
        "corePce": get_delta(core_pce, 1),
        "fedFunds": get_delta(fed_funds, 2),
        "yield1y": get_delta(yield_1y, 2),
        "yield2y": get_delta(yield_2y, 2),
        "yield5y": get_delta(yield_5y, 2),
        "yield10y": get_delta(yield_10y, 2),
        "yieldCurve": get_delta(yield_curve, 2),
        "vix": get_delta(vix, 1),
        "dxy": get_delta(dxy, 1),
        "hySpread": get_delta(hy_spread, 2),
        "m2YoY": get_delta(m2_yoy, 1)
    },
    "fedWatch": {
        "meetings": [
            {"label": "Nov 2026", "cut": 15, "hold": 80, "hike": 5},
            {"label": "Dic 2026", "cut": 35, "hold": 60, "hike": 5},
            {"label": "Ene 2027", "cut": 50, "hold": 45, "hike": 5}
        ]
    },
    "weekEvents": calendar_events,
    "history": {
        "gdp": to_dict(gdp, 'quarterly', 12),
        "ismMfg": to_dict(ism_mfg, 'monthly', 24),
        "ismSvcs": to_dict(ism_svcs, 'monthly', 24),
        "nfp": to_dict(nfp, 'monthly', 24),
        "cpi": to_dict(cpi, 'monthly', 36),
        "coreCpi": to_dict(core_cpi, 'monthly', 36),
        "pce": to_dict(pce, 'monthly', 36),
        "corePce": to_dict(core_pce, 'monthly', 36),
        "yield1y": to_dict(yield_1y, 'monthly', 24),
        "yield2y": to_dict(yield_2y, 'monthly', 24),
        "yield5y": to_dict(yield_5y, 'monthly', 24),
        "yield10y": to_dict(yield_10y, 'monthly', 24),
        "yieldCurve": to_dict(yield_curve, 'monthly', 24),
        "fedFunds": to_dict(fed_funds, 'monthly', 36),
        "vix": to_dict(vix, 'daily', 90),
        "dxy": to_dict(dxy, 'daily', 90),
        "hySpread": to_dict(hy_spread, 'daily', 90),
        "m2YoY": to_dict(m2_yoy, 'monthly', 36)
    }
}

with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)

print("¡Hecho! Archivo 'data.json' generado correctamente con datos y calendario.")