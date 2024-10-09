from flask import Flask,render_template,request,g,redirect,url_for, flash,session
import mysql.connector
import requests
import math
import os
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import subprocess
from datetime import datetime, timedelta
import pandas as pd
import mplfinance as mpf
from io import BytesIO
import base64
from sklearn.linear_model import LinearRegression
import numpy as np
import io
import plotly.graph_objects as go
import plotly.io as pio
import mplcursors
from plotly.subplots import make_subplots


matplotlib.use('agg')

r=requests.get('https://tw.rter.info/capi.php')
currency=r.json()
j=requests.get('https://api.exchangerate-api.com/v4/latest/JPY')
jcurrency=j.json()
e=requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
ecurrency=e.json()

app=Flask(__name__, static_folder='static')
app.secret_key = '99bd02c79e92b6d02967b45ffab89476'

def get_db():
    if not hasattr(g,'_database'):
        g._database=mysql.connector.connect(
            host="localhost",
            user="firelu",
            password="atx121",
            database="finan",
            charset="utf8mb4",
            collation="utf8mb4_general_ci"
        )
        
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    if hasattr(g,'_database'):
        g._database.close()     

@app.route('/')
def index():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    conn=get_db()
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM cash WHERE user_id = %s", (session['user_id'],))
    cash_result=cursor.fetchall()
    #計算台幣與美元總和
    taiwanese_dollars=0
    us_dollars=0
    jp_dollars=0
    eu_dollars=0
    for row in cash_result:
        taiwanese_dollars+=row[1]
        us_dollars+=row[2]
        jp_dollars+=row[3]
        eu_dollars+=row[4]
    #獲取匯率
    r=requests.get('https://tw.rter.info/capi.php')
    currency=r.json()
    j=requests.get('https://api.exchangerate-api.com/v4/latest/JPY')
    jcurrency=j.json()
    e=requests.get('https://api.exchangerate-api.com/v4/latest/EUR')
    ecurrency=e.json()
    total=math.floor(taiwanese_dollars+us_dollars*currency['USDTWD']['Exrate']+jp_dollars*jcurrency['rates']['TWD']+eu_dollars*ecurrency['rates']['TWD'])
    #取得所有股票資訊
    cursor.execute("SELECT * FROM stock WHERE user_id = %s", (session['user_id'],))
    stock_result=cursor.fetchall()
    unique_stock_list=[]
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])
    #計算股票總市值
    total_stock_value=0
    
    #計算單一股票資訊
    stock_info=[]
    for stock in unique_stock_list:
        cursor.execute("SELECT * FROM stock WHERE stock_id = %s AND user_id = %s", (stock, session['user_id']))
        result=cursor.fetchall()
        stock_cost=0  #單一股票總花費
        shares=0  #單一股票股數
        for d in result:
            shares += d[2]
            stock_cost += d[2]*d[3]+d[4]+d[5]
        #取得目前股價
        url="https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo="+stock
        response=requests.get(url)
        data=response.json()
        price_array=data['data']
        current_price=float(price_array[len(price_array)-1][6])
        #單一股票總市值
        total_value=round(current_price*shares)
        total_stock_value += total_value
        #單一股票平均成本
        average_cost = round(stock_cost / shares ,2)
        #單一股票報酬率
        rate_of_return= round((total_value - stock_cost)*100 / stock_cost, 2)
        #單一股票投資報酬
        investment_return=total_value-stock_cost
        
        stock_info.append({'stock_id':stock,'stock_cost':stock_cost, 'total_value':total_value,'average_cost':average_cost, 'shares':shares, 'current_price':current_price, 'rate_of_return':rate_of_return, 'investment_return':investment_return})
        
        
    for stock in stock_info:
        stock['value_percentage'] = round(stock['total_value'] * 100 / total_stock_value, 2)
    
    #繪製股票圓餅圖
    if len(unique_stock_list) !=0:
        labels=tuple(unique_stock_list)
        sizes=[d['total_value'] for d in stock_info]
        fig, ax=plt.subplots(figsize=(6,5))
        # ax.pie(sizes, labels=labels, autopct='%1.1f%%', shadow=None, pctdistance=1.25, labeldistance=.6)
        ax.pie(sizes, labels=labels,autopct='%1.1f%%', shadow=None)
        fig.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart.jpg", dpi=200)
    else:
        try:
          os.remove("static/piechart.jpg")
        except:
            pass
        
    #繪製股票現金圓餅圖
    if us_dollars != 0 or taiwanese_dollars != 0 or jp_dollars != 0 or eu_dollars != 0 or total_stock_value != 0:
        labels=('USD','TWD','JPY','EUR','Stock')
        sizes=(us_dollars*currency['USDTWD']['Exrate'], taiwanese_dollars,jp_dollars*jcurrency['rates']['TWD'],eu_dollars*ecurrency['rates']['TWD'], total_stock_value)
        fig, ax=plt.subplots(figsize=(6,5))
        ax.pie(sizes, labels=labels,autopct='%1.1f%%', shadow=None, labeldistance=1.1)
        fig.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart2.jpg", dpi=200)        
    else:
        try:
          os.remove("static/piechart2.jpg")
        except:
            pass
    
    
        
    data={'show_pic_1':os.path.exists('static/piechart.jpg') ,'show_pic_2':os.path.exists('static/piechart2.jpg'), 'total':total,'td':taiwanese_dollars,'ud':us_dollars,'jd':jp_dollars,'ed':eu_dollars,'currency':currency['USDTWD']['Exrate'],'jcurrency':jcurrency['rates']['TWD'],'ecurrency':ecurrency['rates']['TWD'],'cash_result':cash_result, 'stock_info':stock_info}
    return render_template('index.html',data=data)
 
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form['account']
        pwd = request.form['pwd']
        
        # 假設驗證成功
        session['user_id'] = account
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        pwd1 = request.form['pwd1']
        pwd2 = request.form['pwd2']

        # 密碼匹配檢查
        if pwd1 != pwd2:
            flash('密碼不匹配')
            return redirect(url_for('register'))

        conn = get_db()
        cursor = conn.cursor()

        # 檢查電子郵件是否已存在
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('電子郵件已被使用')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))

        # 密碼加密
        hashed_password = generate_password_hash(pwd1, method='pbkdf2:sha256')

        # 儲存用戶資料
        try:
          cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', 
                   (name, email, hashed_password))
          conn.commit()
          print("Data committed to the database")
        except Exception as e:
          conn.rollback()
          flash(f"資料插入失敗，錯誤訊息: {e}")
          return redirect(url_for('register'))

        conn.commit()
        cursor.close()
        conn.close()

        flash('註冊成功，請登入')
        return redirect(url_for('login'))  # 註冊成功後重定向到登入頁面

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
 
    
@app.route('/cash')
def cash_form():
    return render_template('cash.html')

@app.route('/cash',methods=['POST'])
def submit_cash():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    #取得金額與日期資料
    taiwanese_dollars=0
    us_dollars=0
    jp_dollars=0
    eu_dollars=0
    
    if request.values['taiwanese-dollars'] != '':
        taiwanese_dollars=request.values['taiwanese-dollars']
    if request.values['us-dollars'] != '':
        us_dollars=request.values['us-dollars']
    if request.values['jp-dollars'] != '':
        jp_dollars=request.values['jp-dollars']
    if request.values['eu-dollars'] != '':
        eu_dollars=request.values['eu-dollars']
    note=request.values['note']
    date=request.values['date']
    
    #將資料寫入資料庫
    conn=get_db()
    cursor=conn.cursor()
    cursor.execute(
        "INSERT INTO cash (taiwanese_dollars,us_dollars,jp_dollars,eu_dollars,note,date_info, user_id) VALUES (%s, %s, %s, %s,%s,%s,%s)",
        (taiwanese_dollars,us_dollars,jp_dollars,eu_dollars,note,date, session['user_id'])
    )
    conn.commit()
       
    #將使用者導回主頁
    return redirect('/')

@app.route('/cash-delete',methods=['post'])
def cash_delete():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    transaction_id=request.values['id']
    conn=get_db()
    cursor=conn.cursor()
    cursor.execute("DELETE FROM cash WHERE transaction_id = %s AND user_id = %s", (transaction_id, session['user_id']))
    conn.commit()
    return redirect('/')
    


@app.route('/stock')
def stock_form():
    return render_template('stock.html')

@app.route('/stock_analyze_k')
def stock_analyze_k():
    return render_template('stock_analyze_k.html')

@app.route('/stock_analyze_w')
def stock_analyze_w():
    return render_template('stock_analyze_w.html')

@app.route('/stock_analyze_m')
def stock_analyze_m():
    return render_template('stock_analyze_m.html')

@app.route('/all_stock')
def all_stock():
    current_date = datetime.now()
    today = current_date.strftime('%Y-%m-%d')
    url = "https://api.finmindtrade.com/api/v3/data"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRlIjoiMjAyNC0wNy0yOSAxMzoxNjozOSIsInVzZXJfaWQiOiJmaXJlbHUiLCJpcCI6IjYwLjI0OC4yNy45NyJ9.YVvyzwMl2rVix04C6L6DbTn3O_b04qwwglzxa_sozek"  
    params = {
      "dataset": "TaiwanStockInfo",
      "date": today
    }
    headers = {
      "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    return render_template('all_stock.html', data=data['data'])




@app.route('/stock_detail_year', methods=['POST'])
def stock_detail_year():
    # 取得當前日期
    current_date = datetime.now()
    # 將日期設置為一年前
    one_year_ago = current_date - timedelta(days=365)
    # 格式化為 'yyyy-mm-dd'
    today = current_date.strftime('%Y-%m-%d')
    year_ago = one_year_ago.strftime('%Y-%m-%d')

    stock_id = request.values['stock_id']
    date = year_ago
    end_date = today
    url = "https://api.finmindtrade.com/api/v3/data"
    headers = {
        'x-api-key': 'M5eNfByz5THRCYAH6akFsCADQaygvuzynUHx4rw9rNdbYSgTAwvCQF4G36yAFxkA'
    }
    params = {
        "dataset": "TaiwanStockPrice",
        "stock_id": stock_id,
        "date": date,
        "end_date": end_date,
    }
    response = requests.get(url, params=params, headers=headers, verify=False)
    data = response.json()

    # 確認是否有資料
    if 'data' not in data or len(data['data']) == 0:
        return render_template('stock_detail_year.html', stock_id=stock_id, k_line_html='No data available.')

    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # 選擇需要的欄位並重新命名
    df = df[['open', 'max', 'min', 'close', 'Trading_Volume']].rename(columns={
        'open': 'Open',
        'max': 'High',
        'min': 'Low',
        'close': 'Close',
        'Trading_Volume': 'Volume'
    })

    # 計算移動平均線，全部顯示
    moving_averages = [5, 10, 20, 60, 120, 240]
    color_map = {5: 'blue', 10: 'orange', 20: 'yellow', 60: 'purple', 120: 'brown', 240: 'red'}

    for ma in moving_averages:
        if len(df) >= ma:
            df[f'MA{ma}'] = df['Close'].rolling(window=ma).mean()
        else:
            df[f'MA{ma}'] = None  # 資料不足，設為 None

    # 創建K線圖
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=('', '', 'RSI and MACD'),
                        row_heights=[0.7, 0.15, 0.15])

    # K線圖
    fig.add_trace(go.Candlestick(x=df.index,
                                  open=df['Open'],
                                  high=df['High'],
                                  low=df['Low'],
                                  close=df['Close'],
                                  name='Candlestick',
                                  increasing_line_color='red',
                                  decreasing_line_color='green'), row=1, col=1)

    # 添加移動平均線
    for ma in moving_averages:
        if ma <= len(df):
            if df[f'MA{ma}'].isnull().all():
                continue  # 如果移動平均線全為 None，則不繪製該平均線
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{ma}'], mode='lines', name=f'MA{ma}', line=dict(color=color_map[ma])), row=1, col=1)

    # 計算 RSI 指標
    if len(df) >= 14:
        delta = df['Close'].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

    # 計算 MACD 指標
    if len(df) >= 26:
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # 檢查 MACD 和 Signal 線的交叉
        df['MACD_diff'] = df['MACD'] - df['Signal']
        df['MACD_prev_diff'] = df['MACD_diff'].shift(1)

        # 找到黃金交叉和死亡交叉的點
        df['Golden_Cross'] = (df['MACD_diff'] > 0) & (df['MACD_prev_diff'] <= 0)
        df['Death_Cross'] = (df['MACD_diff'] < 0) & (df['MACD_prev_diff'] >= 0)

        # 獲取黃金交叉和死亡交叉的日期和數據點
        golden_crosses = df[df['Golden_Cross']]
        death_crosses = df[df['Death_Cross']]

    # 在第二個子圖中添加交易量，並使顏色與K線一致
    volume_colors = ['red' if df['Close'][i] > df['Open'][i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Trading Volume', marker_color=volume_colors), row=2, col=1)

    # 在第三個子圖中添加 RSI 和 MACD
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='purple')), row=3, col=1)

    if 'MACD' in df.columns and 'Signal' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Signal', line=dict(color='red')), row=3, col=1)

        # 添加黃金交叉和死亡交叉的標記
        fig.add_trace(go.Scatter(
            x=golden_crosses.index,
            y=golden_crosses['MACD'],
            mode='markers',
            marker=dict(color='red', symbol='arrow-up', size=10),
            name='Golden Cross'
        ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=death_crosses.index,
            y=death_crosses['MACD'],
            mode='markers',
            marker=dict(color='green', symbol='arrow-down', size=10),
            name='Death Cross'
        ), row=3, col=1)

    # 更新佈局設置
    fig.update_layout(
        height=750,
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        plot_bgcolor='white'
    )

    # 將圖表儲存為 HTML 格式以便於顯示
    fig_html = fig.to_html(full_html=False)

    return render_template('stock_detail_year.html', stock_id=stock_id, k_line_html=fig_html)




# 畫個股K線圖
@app.route('/stock_detail_k', methods=['POST'])
def stock_detail_k():
    stock_id = request.values['stock_id']
    date = request.values['date']
    end_date = request.values['end_date']
    
    url = "https://api.finmindtrade.com/api/v3/data"
    headers = {
        'x-api-key': 'M5eNfByz5THRCYAH6akFsCADQaygvuzynUHx4rw9rNdbYSgTAwvCQF4G36yAFxkA'
    }
    params = {
        "dataset": "TaiwanStockPrice",
        "stock_id": stock_id,
        "date": date,
        "end_date": end_date,
    }

    response = requests.get(url, params=params, headers=headers, verify=False)
    data = response.json()
    
    # 確認是否有資料
    if 'data' not in data or len(data['data']) == 0:
        return render_template('stock_detail_k.html', stock_id=stock_id, k_line_html='No data available.')

    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 選擇需要的欄位並重新命名
    df = df[['open', 'max', 'min', 'close', 'Trading_Volume']].rename(columns={
        'open': 'Open',
        'max': 'High',
        'min': 'Low',
        'close': 'Close',
        'Trading_Volume': 'Volume'
    })

    # 檢查是否有足夠的資料來計算技術指標（至少20筆資料）
    if len(df) >= 20:
        # 計算布林帶與移動平均線
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['stddev'] = df['Close'].rolling(window=20).std()
        df['Upper_BB'] = df['MA20'] + (df['stddev'] * 2)
        df['Lower_BB'] = df['MA20'] - (df['stddev'] * 2)

    selected_mas = request.form.getlist('moving_averages')
    selected_mas = [int(ma) for ma in selected_mas]

    color_map = {5: 'blue', 10: 'orange', 20: 'yellow', 60: 'purple', 120: 'brown', 240: 'red'}
    
    for ma in selected_mas:
        if len(df) >= ma:
            df[f'MA{ma}'] = df['Close'].rolling(window=ma).mean()

    # 創建子圖，使用 row_heights 調整高度
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=('','' , 'RSI and MACD'),
                        row_heights=[0.7, 0.15, 0.15])

    # K線圖
    fig.add_trace(go.Candlestick(x=df.index,
                                  open=df['Open'],
                                  high=df['High'],
                                  low=df['Low'],
                                  close=df['Close'],
                                  name='Candlestick',
                                  increasing_line_color='red', 
                                  decreasing_line_color='green'), row=1, col=1)

    # 添加移動平均線
    for ma in selected_mas:
        if ma <= len(df):
            fig.add_trace(go.Scatter(x=df.index, y=df[f'MA{ma}'], mode='lines', name=f'MA{ma}', line=dict(color=color_map[ma])), row=1, col=1)

    # 檢查布林帶是否存在
    if 'Upper_BB' in df.columns and 'Lower_BB' in df.columns:
        # 添加布林帶
        fig.add_trace(go.Scatter(x=df.index, y=df['Upper_BB'], mode='lines', name='Upper BB', line=dict(color='gray', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower_BB'], mode='lines', name='Lower BB', line=dict(color='gray', dash='dash')), row=1, col=1)

    # 計算 RSI 指標
    if len(df) >= 14:  # 檢查資料長度是否足夠計算 RSI
        delta = df['Close'].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

    # 計算 MACD 指標
    if len(df) >= 26:  # 檢查資料長度是否足夠計算 MACD
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 決定交易量顏色（漲紅跌綠）
    volume_colors = ['red' if df['Close'][i] > df['Open'][i] else 'green' for i in range(len(df))]

    # 在第二個子圖中添加交易量，顏色與K線圖一致
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Trading Volume', marker_color=volume_colors), row=2, col=1)
    
    # 在第三個子圖中添加 RSI 和 MACD
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='purple')), row=3, col=1)
    
    if 'MACD' in df.columns and 'Signal' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], mode='lines', name='Signal', line=dict(color='red')), row=3, col=1)

    # 更新母圖 x 軸標籤的顯示，僅在 K 線圖下方顯示日期
    fig.update_xaxes(
        showticklabels=True,  # 顯示日期標籤
        tickfont=dict(family='Arial', size=12, color='black'),
        tickangle=45,  # 避免日期重疊
        row=1, col=1  # 只在 K 線圖部分顯示日期
    )

    # 隱藏其他子圖（交易量和 RSI/MACD）的 x 軸標籤
    fig.update_xaxes(showticklabels=False, row=2, col=1)  # 隱藏交易量的日期標籤
    fig.update_xaxes(showticklabels=False, row=3, col=1)  # 隱藏 RSI 和 MACD 的日期標籤

    # 更新布局，設置更酷的視覺效果與互動選項
    fig.update_layout(
        height=750,
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',  # 統一顯示同一日期的所有數據
        legend=dict(
            orientation="h",  # 水平放置圖例
            yanchor="bottom", y=1, 
            xanchor="center", x=0.5
        ),
        plot_bgcolor='white',  # 更清晰的背景色
        xaxis=dict(
            showline=True, showgrid=False, showticklabels=True, linecolor='black', linewidth=2
        ),
        yaxis=dict(
            showline=True, showgrid=False, linecolor='black', linewidth=2
        )
    )

    # 將圖表儲存為 HTML 格式以便於顯示
    fig_html = fig.to_html(full_html=False)

    return render_template('stock_detail_k.html', stock_id=stock_id, k_line_html=fig_html)








# 畫個股週線圖
@app.route('/stock_detail_w', methods=['POST'])
def stock_detail_w():
    stock_id = request.values['stock_id']
    date = request.values['date']
    end_date = request.values['end_date']
    
    url = "https://api.finmindtrade.com/api/v3/data"
    headers = {
        'x-api-key': 'M5eNfByz5THRCYAH6akFsCADQaygvuzynUHx4rw9rNdbYSgTAwvCQF4G36yAFxkA'
    }
    params = {
        "dataset": "TaiwanStockPrice",
        "stock_id": stock_id,
        "date": date,
        "end_date": end_date,
    }

    response = requests.get(url, params=params, headers=headers, verify=False)
    data = response.json()
    
    # 確認是否有資料
    if 'data' not in data or len(data['data']) == 0:
        return render_template('stock_detail_w.html', stock_id=stock_id, k_line_html='No data available.')

    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 將日資料轉換為週資料
    df_weekly = df.resample('W').agg({
        'open': 'first',
        'max': 'max',
        'min': 'min',
        'close': 'last',
        'Trading_Volume': 'sum'
    })

    # 選擇需要的欄位並重新命名
    df_weekly = df_weekly[['open', 'max', 'min', 'close', 'Trading_Volume']].rename(columns={
        'open': 'Open',
        'max': 'High',
        'min': 'Low',
        'close': 'Close',
        'Trading_Volume': 'Volume'
    })

    # 檢查是否有足夠的資料來計算技術指標（至少20筆資料）
    if len(df_weekly) >= 20:
        # 計算布林帶與移動平均線
        df_weekly['MA20'] = df_weekly['Close'].rolling(window=20).mean()
        df_weekly['stddev'] = df_weekly['Close'].rolling(window=20).std()
        df_weekly['Upper_BB'] = df_weekly['MA20'] + (df_weekly['stddev'] * 2)
        df_weekly['Lower_BB'] = df_weekly['MA20'] - (df_weekly['stddev'] * 2)

    selected_mas = request.form.getlist('moving_averages')
    selected_mas = [int(ma) for ma in selected_mas]

    color_map = {5: 'blue', 10: 'orange', 20: 'yellow', 60: 'purple', 120: 'brown', 240: 'red'}
    
    for ma in selected_mas:
        if len(df_weekly) >= ma:
            df_weekly[f'MA{ma}'] = df_weekly['Close'].rolling(window=ma).mean()

    # 創建子圖，使用 row_heights 調整高度
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=('','' , 'RSI and MACD'),
                        row_heights=[0.7, 0.15, 0.15])

    # K線圖
    fig.add_trace(go.Candlestick(x=df_weekly.index,
                                  open=df_weekly['Open'],
                                  high=df_weekly['High'],
                                  low=df_weekly['Low'],
                                  close=df_weekly['Close'],
                                  name='Candlestick',
                                  increasing_line_color='red', 
                                  decreasing_line_color='green'), row=1, col=1)

    # 添加移動平均線
    for ma in selected_mas:
        if ma <= len(df_weekly):
            fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly[f'MA{ma}'], mode='lines', name=f'MA{ma}', line=dict(color=color_map[ma])), row=1, col=1)

    # 檢查布林帶是否存在
    if 'Upper_BB' in df_weekly.columns and 'Lower_BB' in df_weekly.columns:
        # 添加布林帶
        fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly['Upper_BB'], mode='lines', name='Upper BB', line=dict(color='gray', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly['Lower_BB'], mode='lines', name='Lower BB', line=dict(color='gray', dash='dash')), row=1, col=1)

    # 計算 RSI 指標
    if len(df_weekly) >= 14:  # 檢查資料長度是否足夠計算 RSI
        delta = df_weekly['Close'].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss
        df_weekly['RSI'] = 100 - (100 / (1 + rs))

    # 計算 MACD 指標
    if len(df_weekly) >= 26:  # 檢查資料長度是否足夠計算 MACD
        df_weekly['EMA12'] = df_weekly['Close'].ewm(span=12, adjust=False).mean()
        df_weekly['EMA26'] = df_weekly['Close'].ewm(span=26, adjust=False).mean()
        df_weekly['MACD'] = df_weekly['EMA12'] - df_weekly['EMA26']
        df_weekly['Signal'] = df_weekly['MACD'].ewm(span=9, adjust=False).mean()

    # 決定交易量顏色（漲紅跌綠）
    volume_colors = ['red' if df_weekly['Close'][i] > df_weekly['Open'][i] else 'green' for i in range(len(df_weekly))]

    # 在第二個子圖中添加交易量，顏色與K線圖一致
    fig.add_trace(go.Bar(x=df_weekly.index, y=df_weekly['Volume'], name='Trading Volume', marker_color=volume_colors), row=2, col=1)
    
    # 在第三個子圖中添加 RSI 和 MACD
    if 'RSI' in df_weekly.columns:
        fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly['RSI'], mode='lines', name='RSI', line=dict(color='purple')), row=3, col=1)
    
    if 'MACD' in df_weekly.columns and 'Signal' in df_weekly.columns:
        fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly['MACD'], mode='lines', name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_weekly.index, y=df_weekly['Signal'], mode='lines', name='Signal', line=dict(color='red')), row=3, col=1)

    # 更新布局，設置更酷的視覺效果與互動選項
    fig.update_layout(
        height=750,
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',  # 統一顯示同一日期的所有數據
        legend=dict(
            orientation="h",  # 水平放置圖例
            yanchor="bottom", y=1, 
            xanchor="center", x=0.5
        ),
        plot_bgcolor='white',  # 更清晰的背景色
        xaxis=dict(
            showline=True, showgrid=False, showticklabels=True, linecolor='black', linewidth=2
        ),
        yaxis=dict(
            showline=True, showgrid=False, linecolor='black', linewidth=2
        )
    )

    # 強制顯示 x 軸日期，只在K線圖下方顯示
    fig.update_xaxes(
        showticklabels=True,  # 這裡只會在第一個子圖顯示日期
        tickfont=dict(family='Arial', size=12, color='black'),
        tickangle=45,  # 避免日期重疊
        row=1, col=1  # 只在K線圖部分顯示日期
    )

    # 隱藏其他子圖的 x 軸標籤
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)

    # 將圖表儲存為 HTML 格式以便於顯示
    fig_html = fig.to_html(full_html=False)

    return render_template('stock_detail_w.html', stock_id=stock_id, k_line_html=fig_html)








# 畫個股月線圖
@app.route('/stock_detail_m', methods=['POST'])
def stock_detail_m():
    stock_id = request.values['stock_id']
    date = request.values['date']
    end_date = request.values['end_date']
    
    url = "https://api.finmindtrade.com/api/v3/data"
    headers = {
        'x-api-key': 'M5eNfByz5THRCYAH6akFsCADQaygvuzynUHx4rw9rNdbYSgTAwvCQF4G36yAFxkA'
    }
    params = {
        "dataset": "TaiwanStockPrice",
        "stock_id": stock_id,
        "date": date,
        "end_date": end_date,
    }

    response = requests.get(url, params=params, headers=headers, verify=False)
    data = response.json()
    
    # 確認是否有資料
    if 'data' not in data or len(data['data']) == 0:
        return render_template('stock_detail_m.html', stock_id=stock_id, k_line_html='No data available.')

    df = pd.DataFrame(data['data'])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 將日資料轉換為月資料
    df_monthly = df.resample('M').agg({
        'open': 'first',
        'max': 'max',
        'min': 'min',
        'close': 'last',
        'Trading_Volume': 'sum'
    })

    # 選擇需要的欄位並重新命名
    df_monthly = df_monthly[['open', 'max', 'min', 'close', 'Trading_Volume']].rename(columns={
        'open': 'Open',
        'max': 'High',
        'min': 'Low',
        'close': 'Close',
        'Trading_Volume': 'Volume'
    })

    # 檢查是否有足夠的資料來計算技術指標（至少20筆資料）
    if len(df_monthly) >= 20:
        # 計算布林帶與移動平均線
        df_monthly['MA20'] = df_monthly['Close'].rolling(window=20).mean()
        df_monthly['stddev'] = df_monthly['Close'].rolling(window=20).std()
        df_monthly['Upper_BB'] = df_monthly['MA20'] + (df_monthly['stddev'] * 2)
        df_monthly['Lower_BB'] = df_monthly['MA20'] - (df_monthly['stddev'] * 2)

    selected_mas = request.form.getlist('moving_averages')
    selected_mas = [int(ma) for ma in selected_mas]

    color_map = {5: 'blue', 10: 'orange', 20: 'yellow', 60: 'purple', 120: 'brown', 240: 'red'}
    
    for ma in selected_mas:
        if len(df_monthly) >= ma:
            df_monthly[f'MA{ma}'] = df_monthly['Close'].rolling(window=ma).mean()

    # 創建子圖，使用 row_heights 調整高度
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=('','' , 'RSI and MACD'),
                        row_heights=[0.7, 0.15, 0.15])

    # K線圖
    fig.add_trace(go.Candlestick(x=df_monthly.index,
                                  open=df_monthly['Open'],
                                  high=df_monthly['High'],
                                  low=df_monthly['Low'],
                                  close=df_monthly['Close'],
                                  name='Candlestick',
                                  increasing_line_color='red', 
                                  decreasing_line_color='green'), row=1, col=1)

    # 添加移動平均線
    for ma in selected_mas:
        if ma <= len(df_monthly):
            fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly[f'MA{ma}'], mode='lines', name=f'MA{ma}', line=dict(color=color_map[ma])), row=1, col=1)

    # 檢查布林帶是否存在
    if 'Upper_BB' in df_monthly.columns and 'Lower_BB' in df_monthly.columns:
        # 添加布林帶
        fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly['Upper_BB'], mode='lines', name='Upper BB', line=dict(color='gray', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly['Lower_BB'], mode='lines', name='Lower BB', line=dict(color='gray', dash='dash')), row=1, col=1)

    # 計算 RSI 指標
    if len(df_monthly) >= 14:  # 檢查資料長度是否足夠計算 RSI
        delta = df_monthly['Close'].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss
        df_monthly['RSI'] = 100 - (100 / (1 + rs))

    # 計算 MACD 指標
    if len(df_monthly) >= 26:  # 檢查資料長度是否足夠計算 MACD
        df_monthly['EMA12'] = df_monthly['Close'].ewm(span=12, adjust=False).mean()
        df_monthly['EMA26'] = df_monthly['Close'].ewm(span=26, adjust=False).mean()
        df_monthly['MACD'] = df_monthly['EMA12'] - df_monthly['EMA26']
        df_monthly['Signal'] = df_monthly['MACD'].ewm(span=9, adjust=False).mean()

    # 決定交易量顏色（漲紅跌綠）
    volume_colors = ['red' if df_monthly['Close'][i] > df_monthly['Open'][i] else 'green' for i in range(len(df_monthly))]

    # 在第二個子圖中添加交易量，顏色與K線圖一致
    fig.add_trace(go.Bar(x=df_monthly.index, y=df_monthly['Volume'], name='Trading Volume', marker_color=volume_colors), row=2, col=1)
    
    # 在第三個子圖中添加 RSI 和 MACD
    if 'RSI' in df_monthly.columns:
        fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly['RSI'], mode='lines', name='RSI', line=dict(color='purple')), row=3, col=1)
    
    if 'MACD' in df_monthly.columns and 'Signal' in df_monthly.columns:
        fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly['MACD'], mode='lines', name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_monthly.index, y=df_monthly['Signal'], mode='lines', name='Signal', line=dict(color='red')), row=3, col=1)

    # 更新布局，設置更酷的視覺效果與互動選項
    fig.update_layout(
        height=750,
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',  # 統一顯示同一日期的所有數據
        legend=dict(
            orientation="h",  # 水平放置圖例
            yanchor="bottom", y=1, 
            xanchor="center", x=0.5
        ),
        plot_bgcolor='white',  # 更清晰的背景色
        xaxis=dict(
            showline=True, showgrid=False, showticklabels=True, linecolor='black', linewidth=2
        ),
        yaxis=dict(
            showline=True, showgrid=False, linecolor='black', linewidth=2
        )
    )

    # 強制顯示 x 軸日期，只在K線圖下方顯示
    fig.update_xaxes(
        showticklabels=True,  # 這裡只會在第一個子圖顯示日期
        tickfont=dict(family='Arial', size=12, color='black'),
        tickangle=45,  # 避免日期重疊
        row=1, col=1  # 只在K線圖部分顯示日期
    )

    # 隱藏其他子圖的 x 軸標籤
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)

    # 將圖表儲存為 HTML 格式以便於顯示
    fig_html = fig.to_html(full_html=False)

    return render_template('stock_detail_m.html', stock_id=stock_id, k_line_html=fig_html)



@app.route('/stock',methods=['post'])
def submit_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    #取得股票資訊、日期資料
    stock_id=request.values['stock-id']
    stock_num=request.values['stock-num']
    stock_price=request.values['stock-price']
    processing_fee=0
    tax=0
    if request.values['processing-fee'] != '':
       processing_fee=request.values['processing-fee']
    if request.values['tax'] != '':
       tax=request.values['tax']   
    date=request.values['date']
    #更新資料庫資料
    conn=get_db()
    cursor=conn.cursor()
    cursor.execute("INSERT INTO stock (stock_id,stock_num,stock_price,processing_fee,tax,date_info, user_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",(stock_id,stock_num,stock_price,processing_fee,tax,date, session['user_id']))
    conn.commit()   
    #將使用者導至首頁   
    return redirect('/')

@app.route('/stock-delete',methods=['post'])
def stock_delete():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    stock_id=request.values['stock_id']
    conn=get_db()
    cursor=conn.cursor()
    cursor.execute("delete from stock where stock_id=%s AND user_id = %s",(stock_id,session['user_id']))
    conn.commit()
    return redirect('/')
    



@app.route('/currency')
def currency():
    r = requests.get('https://tw.rter.info/capi.php')
    currency = r.json()
    return render_template('currency.html', currency=currency)



@app.route('/twcurrency')
def twcurrency():
    r = requests.get('https://tw.rter.info/capi.php')
    r.raise_for_status()
    currency_data = r.json()

    # 獲取台幣對美元的匯率
    twd_to_usd_rate = currency_data.get('USDTWD', {}).get('Exrate', None)
    
    if twd_to_usd_rate is None or twd_to_usd_rate == 0:
        return "台幣對美元的匯率未找到或為 0", 404

    twcurrency = {}
    for key, value in currency_data.items():
        if key.startswith('USD') and key != 'USDTWD':
            # 正確計算外幣對台幣的匯率
            exchange_rate =1 / (value['Exrate'] / twd_to_usd_rate) 
            # 去掉 "USD" 來顯示貨幣對
            if len(key) > 3:
              currency_pair = key[3:]  # 去掉前面的 "USD"
              twcurrency[currency_pair] = exchange_rate
    
    return render_template('twcurrency.html', twcurrency=twcurrency)



@app.route('/mcurrency')
def mcurrency():
    r = requests.get('https://cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01M01')
    mcurrency = r.json()
    
    # 抓取匯率數據
    currencies = mcurrency['data']['dataSets']
    headers = [header['data'] for header in mcurrency['data']['structure']['Table1']]

    # 根據日期進行降序排序
    sorted_currencies = sorted(currencies, key=lambda x: x[0], reverse=True)

    # 準備轉換後的匯率資料
    converted_currencies = []

    for row in sorted_currencies:
        try:
            ntd_to_usd = float(row[1])  # 新台幣對美元的匯率
            if ntd_to_usd == 0:  # 避免除以零的情況
                continue
                        
            # 開始轉換，每個貨幣轉換為針對台幣的匯率
            converted_row = [row[0]]  # 日期不變

            for i in range(1, len(row)):
                if i == 1:  # 新台幣對美元本身不變
                    converted_row.append(row[i])
                else:
                    try:
                        # 轉換為台幣對應的匯率
                        usd_rate = float(row[i])
                        if i==3 or i==9 or i==14:
                          converted_rate = round(ntd_to_usd * usd_rate, 4)
                        else:                          
                          converted_rate = round(ntd_to_usd / usd_rate, 4)  # 轉換後四捨五入保留四位小數
                        converted_row.append(str(converted_rate))
                    except ValueError:
                        converted_row.append(row[i])  # 處理非數字的欄位
                    except ZeroDivisionError:
                        converted_row.append('-')  # 避免除以零的錯誤
                
            converted_currencies.append(converted_row)
            
        except ValueError:
            continue  # 若匯率無法轉換，跳過這筆資料

    # 渲染到 HTML 模板中
    return render_template('mcurrency.html', currencies=converted_currencies, headers=headers)



# 可選擇的貨幣列表
currency_options = {
    'USD': '美金',
    'JPY': '日圓',
    'GBP': '英鎊',
    'HKD': '港幣',
    'KRW': '韓元',
    'CAD': '加拿大幣',
    'SGD': '新加坡元',
    'CNY': '人民幣',
    'AUD': '澳幣',
    'IDR': '印尼盾',
    'THB': '泰銖',
    'MYR': '馬來西亞幣',
    'PHP': '菲律賓披索',
    'EUR': '歐元',
    'VND': '越南盾',
}

@app.route('/acurrency', methods=['GET', 'POST'])
def acurrency():
    if request.method == 'POST':
        # 取得使用者選擇的貨幣與區間
        currency_code = request.form['acurrency']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m')  # 轉換為日期物件
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m')      # 轉換為日期物件
        
        r = requests.get('https://cpx.cbc.gov.tw/API/DataAPI/Get?FileName=BP01M01')
        acurrency = r.json()

        # 進行資料處理 (篩選使用者選擇的貨幣)
        currencies = acurrency['data']['dataSets']
               
        # 依據日期篩選資料
        filtered_data = []
        for row in currencies:
            date_str = row[0]  # 格式為 'YYYYMmm'
            date = datetime.strptime(date_str, '%YM%m')  # 使用正確的日期格式
            rate_index = list(currency_options.keys()).index(currency_code) + 1  # 對應的匯率索引
            
            # 檢查選擇的貨幣是否為越南盾
            if currency_code == 'VND':
                currency_to_usd = float(row[18]) if row[18] != '-' else None
                usd_to_twd = float(row[1]) if row[1] != '-' else None
                if usd_to_twd is not None and currency_to_usd is not None:
                    currency_to_twd = usd_to_twd / currency_to_usd
                else:
                    currency_to_twd = None
            else:
                # 原有的匯率計算邏輯
                usd_to_twd = float(row[1]) if row[1] != '-' else None

                if currency_code == 'USD':
                    currency_to_twd = usd_to_twd
                else:
                    currency_to_usd = float(row[rate_index]) if row[rate_index] != '-' else None

                    # 檢查是否為 GBP、AUD 或 EUR
                    if currency_code in ['GBP', 'AUD', 'EUR']:
                        if usd_to_twd is not None and currency_to_usd is not None:
                            currency_to_twd = usd_to_twd * currency_to_usd
                        else:
                            currency_to_twd = None
                    else:
                        if usd_to_twd is not None and currency_to_usd is not None:
                            currency_to_twd = usd_to_twd / currency_to_usd
                        else:
                            currency_to_twd = None
            
            # 只篩選在指定日期範圍內的數據
            if start_date <= date <= end_date and currency_to_twd is not None:
                filtered_data.append((date, currency_to_twd))

        # 設置日期與匯率
        dates = [date.strftime('%Y-%m') for date, _ in filtered_data]
        rates = [rate for _, rate in filtered_data]

        # 確保資料量足夠進行計算
        df = pd.DataFrame({'dates': dates, 'rates': rates})

        if len(filtered_data) >= 3:  # 需要3個月的數據
            df['3_month_SMA'] = df['rates'].rolling(window=3).mean()
            df['ROC'] = df['rates'].pct_change() * 100
            df['volatility'] = df['rates'].rolling(window=3).std()
            df['cumulative_return'] = (1 + df['ROC'] / 100).cumprod() - 1  # 累積回報
        else:
            df['3_month_SMA'] = None
            df['ROC'] = None
            df['volatility'] = None
            df['cumulative_return'] = None

        # 使用 Plotly 繪製圖形
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4])  # 設定相對高度

        # 第一個子圖：匯率與移動平均線
        trace = go.Scatter(x=df['dates'], y=df['rates'], mode='lines', name=f'{currency_options[currency_code]} 對台幣匯率')
        sma_trace = go.Scatter(x=df['dates'], y=df['3_month_SMA'], mode='lines', name='3個月移動平均線', line=dict(dash='dash'))
        
        fig.add_trace(trace, row=1, col=1)
        fig.add_trace(sma_trace, row=1, col=1)

        # 第二個子圖：匯率變動百分比、波動性、累積回報
        if len(filtered_data) >= 3:
            roc_trace = go.Scatter(x=df['dates'], y=df['ROC'], mode='lines', name='匯率變動百分比')
            volatility_trace = go.Scatter(x=df['dates'], y=df['volatility'], mode='lines', name='波動性')
            cumulative_return_trace = go.Scatter(x=df['dates'], y=df['cumulative_return'], mode='lines', name='累積回報')

            fig.add_trace(roc_trace, row=2, col=1)
            fig.add_trace(volatility_trace, row=2, col=1)
            fig.add_trace(cumulative_return_trace, row=2, col=1)

        # 設置圖形佈局
        fig.update_layout(title=f'{currency_options[currency_code]} 對台幣匯率', xaxis=dict(title='日期'), yaxis=dict(title='價格:台幣'))

        # 設定整個圖表的高度
        fig.update_layout(height=600)  # 設定總高度

        # 轉換圖表為 HTML 嵌入代碼
        graph_html = pio.to_html(fig, full_html=False)

        # 渲染到 HTML 模板中
        return render_template('acurrency.html', graph_html=graph_html)

    # 初次加載表單
    return render_template('acurrency_form.html', currency_options=currency_options)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/service')
def service():
    return render_template('service.html')

if __name__=='__main__':
    app.run(debug=True,port=80)