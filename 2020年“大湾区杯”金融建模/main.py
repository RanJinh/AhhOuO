import csv
import datetime
from copy import deepcopy

SERVICE_CHARGE = 0.00025
STOCK_NUM = 10
position = {}
sum = 10000000.0
stocks = {}
stock = [None] * 1000
stop_list = []
order = []

def get_position(stock):
    try:
        own_value = position[stock][0]
    except:
        own_value = 0
    return own_value

def day_interval(date1, date2):
    return date1 - date2

def row_float(row):
    for i in range(4, 10):
        row[i] = float(row[i])

def sell_out(i):
    # 判断是否有股票在调仓时停牌
    global sum
    if i == 1: return sum
    stop_list.clear()
    min_index = 9999
    for stock in stocks:
        week_next = stocks[stock][i]
        if week_next is not None:
            if week_next[0][1] < min_index:
                min_index = week_next[0][1]
    if min_index == 9999:
        # 该周闭市
        return -1

    for stock in stocks:
        week_next = stocks[stock][i]
        if week_next is None or week_next[0][1] != min_index:
            #     调仓日停牌
            stop_list.append(stock)
    val = 0
    print("\t第{}周买入内容：".format(i))
    val_stop = 0
    for item in position:
        if item not in stop_list:
            cur = stocks[item][i][0][4]
            rate = (cur - position[item][1]) / position[item][1]
            print("\t\t{}：\t买入市值：{:<10f} \t买入价：{:<10f} \t下周价：{:.2f} \t涨幅：{:.2%}".format(item, position[item][0], position[item][1], cur, rate))
            val += position[item][0] * (1 + rate)
        else:
            val_stop += position[item][0]
            print("\t\t{}：\t买入市值：{:<10f} \t买入价：{:<10f} \t下周价：停牌 \t涨幅：-".format(item, position[item][0], position[item][1], ))
    sum = val*(1-SERVICE_CHARGE)
    return val + val_stop


def choose_stocks(week_index, stocks):
    # 计算一周的收益率，用该周的最后一天收盘价减去这周第一天开盘价
    global order
    order.clear()
    rates = {}
    for stock in stocks:
        week = stocks[stock][week_index]
        if week is not None:
            rates[stock] = (float(week[-1][7]) - week[0][4]) / week[0][4]
        else:
            rates[stock] = -1
    order = sorted(rates.items(), key=lambda x: x[1], reverse=True)
    temp = [stock[0] for stock in order]
    return temp

def transaction(strong_stocks, i):
    global position
    count = 0
    new_position = {}
    if len(stop_list) != 0:
        for stock in stop_list:
            own_value = get_position(stock)
            if own_value != 0:
                new_position[stock] = (own_value, position[stock][1])
                count += 1
    each_val = sum/(STOCK_NUM - count)
    for stock in strong_stocks:
        if count < STOCK_NUM and stock not in stop_list:
            # 计算新持仓，记录买入价
            new_position[stock] = (each_val*(1-SERVICE_CHARGE), stocks[stock][i][0][4])
            count += 1
        elif count >= STOCK_NUM:
            break
    if len(new_position) != STOCK_NUM:
        print("Error! No enough stocks!")
    else:
        position = new_position


#2011-01-03 为周一
last_date = datetime.datetime(2011, 1 ,2)
last_week = 0
max_week = -1
with open('附录一：30支股票行情.csv')as f:
    f_csv = csv.reader(f)
    rows = [row for row in f_csv]
    last_stock = ""
    week = []
    for row in rows[1:]:
        s = row[1]
        if last_stock == "":
            last_stock = row[2]
        if row[2] != last_stock:
            if len(week) != 0:
                stock[last_week] = deepcopy(week)
                week.clear()
                if last_week > max_week: max_week = last_week
                last_week = 0
            stocks[last_stock] = deepcopy(stock)
            stock = [None] * 1000
            last_stock = row[2]
        date = datetime.datetime(int(s[:4]), int(s[5:7]), int(s[8:10]))
        index = day_interval(date, last_date).days
        row.insert(1, index)
        row_float(row)
        if int((index-1)/7) != last_week:
            stock[last_week] = deepcopy(week)
            week.clear()
            last_week = int((index-1)/7)
        week.append(row)
    if len(week) != 0:
        stock[last_week] = deepcopy(week)
        week.clear()
        last_week = 0
    stocks[last_stock] = deepcopy(stock)
    for stock in stocks:
        del stocks[stock][max_week+1:]
    closed = False
    for i in range(1, max_week+1):
        if not closed:
            strong_stocks = choose_stocks(i-1, stocks)
        val = sell_out(i)
        if val == -1:
            closed = True # 下周全闭市
            print("\n第{}周，交易停止。".format(i+1))
            continue
        closed = False
        print("\n第{}周，调仓前市值：{}".format(i+1, val))
        transaction(strong_stocks, i)
#    计算在最后一周买入的股票最终市值
    val = 0
    for item in position:
        if item not in stop_list:
            val += position[item][0] * (1 + (stocks[item][-1][-1][7] - position[item][1]) / position[item][1])
    sum = val
    print("\n513周结束总市值:{}".format(sum))

