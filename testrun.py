# coding:utf-8

import socket
import re
import requests
import pandas
import json
import csv
import os
import datetime
import threading
import time

from multiprocessing import Process

# main

JSONFILE='/var/www/cache.json'

end=datetime.datetime.now()
start=end-datetime.timedelta(days=365)
dates=pandas.date_range(start,end).strftime("%Y-%m-%d").to_list()
value_template={}
for date in dates:
    value_template[date]="-"
per_list=value_template.copy()
total_list=value_template.copy()
code=input("code : ")

def compute(code,dates,per_list,total_list,value_template):
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55'}
    file_path="/var/www/csv/"+code+".csv"
    if not os.path.exists(file_path):
        print(file_path)
        with open(file_path,"w") as new_file:
            csv_file = csv.writer(new_file)
            head = ["date","per","total"]
            csv_file.writerow(head)
            new_file.close()
    with open(file_path,"r") as read_file:
        reader=csv.reader(read_file)
        with open(file_path,"w") as write_file:
            writer=csv.writer(write_file)
            for row in reader:
                if row[0] in dates :
                    writer.writerow(row)
                    per_list[row[0]]=row[1]
                    total_list[row[0]]=row[2]
                elif row[0] == 'date':
                    writer.writerow(["date","per","total"])
            per_cache={}
            total_cache={}
            for key in value_template.keys():
                if per_list[key] == '-':
                    if not (key in per_cache.keys()):
                        start_date=key
                        end_date=dates[(dates.index(key)+30) if (dates.index(key)+30)<len(dates) else (len(dates)-1)]
                        # RECOMMENDED 基金代码 -> code
                        path = "https://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz&code="+code+"&per=30&sdate="+start_date+"&edate="+end_date
                        r = requests.get(path, headers=headers)
                        tr_re = re.compile(r'<tr>(.*?)</tr>')
                        item_re = re.compile(r'''<td>(\d{4}-\d{2}-\d{2})</td><td.*?>(.*?)</td><td.*?>(.*?)</td><td.*?>(.*?)</td><td.*?>(.*?)</td><td.*?>(.*?)</td><td.*?></td>''', re.X)
                        for line in tr_re.findall(r.text):
                            match = item_re.findall(line)
                            if match != []:
                                match_list=match[0]
                                if match_list[1]!= '':
                                    per_cache[match_list[0]]=match_list[1]
                                if match_list[2]!= '':
                                    total_cache[match_list[0]]=match_list[2]
                    if key in per_cache.keys() and key in total_cache.keys():
                        per_list[key]=per_cache[key]
                        total_list[key]=total_cache[key]
                        writer.writerow([key,per_list[key],total_list[key]])
                    else:
                        writer.writerow([key,'n','n'])
                        per_list[key]='n'
                        total_list[key]='n'
            write_file.close()
        read_file.close()
    # per_list 和 total_list 都是【字典】
    # FORMAT
    # key  : value
    # date : value(float)
    # 结果需要在 response_list 内添加
    per_values=[]
    total_values=[]
    for date in dates:
        if per_list[date] !='n':
            per_values.append(float(per_list[date]))
            total_values.append(float(total_list[date]))
    del per_list
    del total_list
    # *_values 列表数据均为float
    if len(total_values)==0 or len(per_values)==0:
        print(code,"'s total value's number or per value's is ZERO")
        drawdown="-"
        drawdownstr="-"
        weekup="-"  
    else:
        drawdown=10000
        for j in range(len(total_values)-1):
            mn=total_values[j+1]
            for k in range(j+2,len(total_values)):
                if total_values[k]<mn:
                    mn=total_values[k]
            tmp=(mn-total_values[j+1])/per_values[j+1]
            if tmp < drawdown:
                drawdown=tmp
        drawdown *= 100
        drawdownstr = str(round(drawdown,2))+"%"
        
        mondrawdown=10000
        for j in range(len(total_values)-20,len(total_values)-1):
            mn=total_values[j+1]
            for k in range(j+2,len(total_values)):
                if total_values[k]<mn:
                    mn=total_values[k]
            tmp=(mn-total_values[j+1])/per_values[j+1]
            if tmp < mondrawdown:
                mondrawdown=tmp
        mondrawdown *= 100
        mondrawdownstr = str(round(mondrawdown,2))+"%"
        
        ssdrawdown=10000
        for j in range(len(total_values)-60,len(total_values)-1):
            mn=total_values[j+1]
            for k in range(j+2,len(total_values)):
                if total_values[k]<mn:
                    mn=total_values[k]
            tmp=(mn-total_values[j+1])/per_values[j+1]
            if tmp < ssdrawdown:
                ssdrawdown=tmp
        ssdrawdown *= 100
        ssdrawdownstr = str(round(ssdrawdown,2))+"%"
        weekup=((total_values[-1]-total_values[-5])/per_values[-5])*100
        weekup=str(round(weekup,2))+"%"
    rpath = "http://fund.eastmoney.com/pingzhongdata/"+code+".js?v=20160518155842"
    rheaders = {'content-type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55'}
    r = requests.get(rpath, headers=rheaders)
    #############################################################
    try:
        pattern = r'var fund_Rate="(.*?)";'
        rate = json.loads(re.findall(pattern,r.text)[0])
        rate=str(round(rate,2))+"%"
    except:
        rate='-'
    try:
        pattern = r'var syl_1n="(.*?)";'
        yrup = json.loads(re.findall(pattern,r.text)[0])
        yrupstr=str(round(yrup,2))+"%"
    except:
        yrup='-'
    try:
        pattern = r'var syl_6y="(.*?)";'
        halfyrup = json.loads(re.findall(pattern,r.text)[0])
        halfyrup=str(round(halfyrup,2))+"%"
    except:
        halfyrup='-'
    try:
        pattern = r'var syl_3y="(.*?)";'
        seasonup = json.loads(re.findall(pattern,r.text)[0])
        seasonupstr=str(round(seasonup,2))+"%"
    except:
        seasonup = '-'
        seasonupstr = '-'
    try:
        pattern = r'var syl_1y="(.*?)";'
        monup = json.loads(re.findall(pattern,r.text)[0])
        monupstr=str(round(monup,2))+"%"
    except:
        monupstr='-'
        monup='-'
    if drawdown != '-':
        try:
            ddup=str( int(((total_values[-1]-total_values[0])/per_values[0])*10000/abs(mondrawdown))/100 )
        except:
            ddup='-'
    else:
        ddup='-'
    if ssdrawdown != '-':
        try:
            ssddup=str( int(((total_values[-1]-total_values[-60])/per_values[-60])*10000/abs(mondrawdown))/100 )
        except:
            ssddup='-'
    else:
        ssddup='-'
    if mondrawdown != '-':
        try:
            monddup=str( int(((total_values[-1]-total_values[-20])/per_values[-20])*10000/abs(mondrawdown))/100 )
        except:
            monddup='-'
    else:
        monddup='-'
    try:
        pattern = r'<tr><td>夏普比率</td><td class=\'num\'>(.*?)</td>'
        rpath = "http://fundf10.eastmoney.com/tsdata_"+code+".html"
        r = requests.get(rpath, headers=rheaders)
        sharpe= json.loads(re.findall(pattern,r.text)[0])
        sharpe= str(round(sharpe,2))
    except:
        sharpe='-'
    try:
        pattern=r"<span>近3年：</span><span class=\".*?\">(.*?)</span>"
        rpath = "http://fund.eastmoney.com/"+code+".html"
        r = requests.get(rpath, headers=rheaders)
        r.encoding='utf-8'
        threeyrup = json.loads(re.findall(pattern,r.text)[0][0:-1])
        threeyrup = str(round(threeyrup,2))+"%"
    except:
        threeyrup="-"
    try:
        rpath = "http://fundgz.1234567.com.cn/js/"+code+".js"
        r = requests.get(rpath, headers=rheaders)
        pattern = r'^jsonpgz\((.*)\)'
        search = json.loads(re.findall(pattern,r.text)[0])
        ontimeup = search["gszzl"]+"%"
    except:
        ontimeup='-'
    diction={
        "code":code,
        "drawdown":drawdownstr,
        "yrup":yrupstr,
        "monup":monupstr,
        "seasonup":seasonupstr,
        "halfyrup":halfyrup,
        "ddup":ddup,
        "rate":rate,
        "sharpe":sharpe,
        "threeyrup":threeyrup,
        "weekup":weekup,
        "ontimeup":ontimeup,
        "ssdrawdown":ssdrawdownstr,
        "mondrawdown":mondrawdownstr,
        "ssddup":ssddup,
        "monddup":monddup,
    }
    print(diction)

compute(code,dates,per_list,total_list,value_template)