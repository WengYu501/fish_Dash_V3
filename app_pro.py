import sqlite3
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

# --- 初始主題模式（可切換）---
external_stylesheets = [dbc.themes.BOOTSTRAP]  # Default Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "專業財經儀表板"

app.layout = html.Div([
    dcc.Store(id='theme-mode', data='dark'),

    dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("📊 多市場流動性與價格儀表板"), width=9),
            dbc.Col(dbc.Button(id='toggle-theme', children="切換主題 ☀️/🌙", color="secondary"), width=3)
        ], align="center", className="my-3"),

        dbc.Row([
            dbc.Col(dcc.Dropdown(id='asset-dropdown', options=[], placeholder="請選擇資產", value=None), width=6),
            dbc.Col(dcc.DatePickerRange(id='date-range'), width=6),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col(dcc.Graph(id='price-graph'), width=12),
        ]),

        dbc.Row([
            dbc.Col(dcc.Graph(id='amihud-graph'), width=12),
        ]),

        dbc.Row([
            dbc.Col(html.Hr()),
            dbc.Col(html.H5("📋 原始資料表")),
            dbc.Col(dash_table.DataTable(id='data-table', page_size=10, style_table={"overflowX": "auto"})),
        ], className="mt-4")
    ], fluid=True)
])

# --- 讀取資產列表 ---
def get_assets():
    conn = sqlite3.connect("liquidity_cache.db")
    df = pd.read_sql("SELECT DISTINCT symbol FROM asset_data", conn)
    conn.close()
    return [{'label': s, 'value': s} for s in df['symbol']]

# --- 主畫面回傳資料 ---
@app.callback(
    [Output('price-graph', 'figure'),
     Output('amihud-graph', 'figure'),
     Output('data-table', 'data'),
     Output('data-table', 'columns')],
    [Input('asset-dropdown', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date')]
)
def update_figures(symbol, start_date, end_date):
    if not symbol:
        return go.Figure(), go.Figure(), [], []

    conn = sqlite3.connect("liquidity_cache.db")
    df = pd.read_sql("SELECT * FROM asset_data WHERE symbol = ?", conn, params=(symbol,))
    conn.close()

    df['date'] = pd.to_datetime(df['date'])
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(x=df['date'], y=df['adj_close'], name="收盤價", mode="lines+markers"))
    price_fig.update_layout(title=f"{symbol} 價格走勢圖", xaxis_title="日期", yaxis_title="價格")

    amihud_fig = go.Figure()
    amihud_fig.add_trace(go.Bar(x=df['date'], y=df['amihud'], name="Amihud"))
    amihud_fig.add_trace(go.Scatter(x=df['date'], y=df['z_score'], name="Z-Score", yaxis="y2", mode="lines"))
    amihud_fig.update_layout(
        title=f"{symbol} 流動性與 Z 分數",
        xaxis_title="日期",
        yaxis=dict(title="Amihud"),
        yaxis2=dict(title="Z-score", overlaying="y", side="right")
    )

    columns = [{'name': c, 'id': c} for c in df.columns]
    data = df.to_dict('records')

    return price_fig, amihud_fig, data, columns

# --- 資產選單初始化 ---
@app.callback(
    Output('asset-dropdown', 'options'),
    Input('asset-dropdown', 'id')
)
def populate_assets(_):
    return get_assets()

# --- 主題切換邏輯 ---
@app.callback(
    Output('theme-mode', 'data'),
    Input('toggle-theme', 'n_clicks'),
    State('
