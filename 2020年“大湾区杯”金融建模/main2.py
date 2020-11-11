import csv
import datetime
from copy import deepcopy
global position
position = None
SERVICE_CHARGE = 0.00025
sum = 10000000.0
stocks = {}
stock = [None] * 1000
stop_list1 = []
stop_list2 = []
order = []
stk_price = {}

def day_interval(date1, date2):
    return date1 - date2

def row_float(row):
    for i in range(4, 10):
        row[i] = float(row[i])

def stoped(i):
    stp_ls = []
    min_index = 9999
    for stock in stocks:
        week_next = stocks[stock][i]
        if week_next is not None:
            if week_next[0][1] < min_index:
                min_index = week_next[0][1]
    if min_index == 9999:
        # 该周闭市
        return None

    for stock in stocks:
        week_next = stocks[stock][i]
        if week_next is None or week_next[0][1] != min_index:
            #     调仓日停牌
            stp_ls.append(stock)
    return stp_ls

def sell_out(i):
    # 判断是否有股票在调仓时停牌
    global sum
    cur = stocks[position[0]][i][0][4]
    rate = (cur - position[2]) / position[2]
    print("\t\t{}：\t买入市值：{:<10f} \t买入价：{:<10f} \t现价：{:.2f} \t涨幅：{:.2%}".format(position[0], position[1],
                                                                               position[2], cur, rate))
    sum = position[1] * (1 + rate)
    return sum

def stock_price(i):
    for stock in stocks:
        if stock not in stop_list2:
            stk_price[stock] = stocks[stock][i][0][4]

def choose_stock(week_index):
    # 计算一周的收益率，用该周的最后一天收盘价减去这周第一天开盘价
    global order
    order.clear()
    rates = {}
    for stock in stocks:
        if stock not in stop_list1 and stock not in stop_list2:
            week = stocks[stock][week_index]
            rates[stock] = (week[0][4] - stk_price[stock]) / stk_price[stock]
        else:
            rates[stock] = -1
    order = sorted(rates.items(), key=lambda x: x[1], reverse=True)
    temp = [stock[0] for stock in order]

    return temp[0]

def transaction(strong_stock):
    global position
    # if len(stop_list) != 0:
    #     for stock in stop_list:
    #         own_value = get_position(stock)
    #         if own_value != 0:
    #             new_position[stock] = (own_value, position[stock][1])
    #             count += 1
    if position is None:
        position = [strong_stock, sum * (1 - SERVICE_CHARGE), stk_price[strong_stock]]
    elif position[0] != strong_stock:
        # 换股
        position[0] = strong_stock
        position[1] = sum * (1 - SERVICE_CHARGE) * (1 - SERVICE_CHARGE)
        position[2] = stk_price[strong_stock]


#2011-01-03 为周一
last_date = datetime.datetime(2011, 1, 2)
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
    stop_list2 = stoped(0)
    stock_price(0)
    for i in range(1, max_week+1):
        if stop_list2 is not None:
            stop_list1 = stop_list2
        stop_list2 = stoped(i)
        if stop_list2 is None:
            print("\n第{}周，交易停止。".format(i+1))
            continue
        strong_stock = choose_stock(i)
        transaction(strong_stock)
        val = sell_out(i)
        print("\n第{}周，调仓前市值：{}".format(i+1, val))
        stock_price(i)
#    计算在最后一周买入的股票最终市值
    rates = {}
    for stock in stocks:
        if stock not in stop_list2:
            week = stocks[stock][max_week]
            rates[stock] = (week[-1][7] - stk_price[stock]) / stk_price[stock]
        else:
            rates[stock] = -1
    order = sorted(rates.items(), key=lambda x: x[1], reverse=True)
    transaction(order[0][0])
    cur = stocks[stock][max_week][-1][7]
    rate = order[0][1]
    print("\t\t{}：\t买入市值：{:<10f} \t买入价：{:<10f} \t现价：{:.2f} \t涨幅：{:.2%}".format(position[0], position[1],
                                                                               position[2], cur, rate))
    sum = position[1] * (1 + rate)
    print("\n513周结束总市值:{}".format(sum))

