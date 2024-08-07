import requests
import re
import random
from bs4 import BeautifulSoup
from Config import USER_AGENT, CODE, THREAD_POOL
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import asyncio


class GetPage:
    def __init__(self):
        self.ua = USER_AGENT

    def __getattr__(self, item):
        try:
            if item == 'random':
                random.choice(self.ua)
        except KeyError:
            raise AttributeError(r"Object does'n has attribute '%s'" % item)

    def GetByURL(self):
        """
            用于爬取页面 爬取特定的网页
            :param url:要爬取的url
            :return: 返回二元组 爬取结果，网页内容
        """
        headers = {
            "User-Agent": GetPage().random,
            'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
            'Cookie': 'st_si=74949607860286; st_asi=delete; ASP.NET_SessionId=gekyucnll0wte0wrks2rr23b; _adsame_fullscreen_18503=1; EMFUND1=null; EMFUND2=null; EMFUND3=null; EMFUND4=null; EMFUND5=null; EMFUND6=null; EMFUND7=null; EMFUND8=null; EMFUND0=null; EMFUND9=02-07 16:37:21@#$%u521B%u91D1%u5408%u4FE1%u5DE5%u4E1A%u5468%u671F%u80A1%u7968A@%23%24005968; st_pvi=90009717841707; st_sp=2021-02-07%2012%3A14%3A29; st_inirUrl=https%3A%2F%2Fwww.baidu.com%2Flink; st_sn=21; st_psi=2021020716562364-0-0372414431'
        }
        params = {
            'pi': 1,
            'pn': 3000,
        }
        url = 'http://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft=all&rs=&gs=0&sc=6yzf&st=desc&sd=2021-04-11&ed=2022-04-11&qdii=&tabSubtype=,,,,,&dx=1&v=0.8381695977921375'
        # 1. 发送请求
        resp = requests.get(url=url, headers=headers, params=params)
        # 2. 获取数据
        fund_code = resp.content.decode()
        # 3. 数据处理解析，并存储到fund_tuple列表中
        fund_code = re.findall('\[(.*)\],', fund_code)[0]
        data = eval(fund_code)
        # print(data)

        # 4. 数据保存
        with open('fund_list.csv', mode='w')as f:
            f.write(
                "基金代码,   基金名称, 基金简称,        日期,	单位净值,	累计净值,	日增长率,	近1周,	近1月,	近3月,	近6月,	近1年,	近2年,	近3年,	今年来,	成立来,自定义")
            f.write('\n')

        for sub_data in data:
            with open('fund_list.csv', mode='a')as f:
                f.write(sub_data)
                f.write('\n')


def getSingle(num):
    url = 'http://fund.eastmoney.com/' + CODE[num] + '.html'
    headers = {
        'headers': USER_AGENT[random.randint(0, 15)],
        'Referer': 'http://fund.eastmoney.com/'
    }
    with lock:
        page = requests.get(url, headers=headers)
        html = str(page.content, 'utf-8')
        soup = BeautifulSoup(html, 'lxml')

        name = soup.find('a', {'href': url, 'target': "_self"}).getText()
        date = soup.find('dl', {'class': "dataItem02"}).find('p').getText()[6:-1]
        value = soup.find_all('dd', {'class': 'dataNums'})[1].find('span').getText()
        # manager = re.findall(r'"fund.eastmoney.com/manager/(.*?).html',page)[0]
        manager = soup.find('a', {'href': 'http://fundf10.eastmoney.com/jjjl_' + CODE[num] + '.html'}).getText()
        # print("基金编号:",CODE[num],'\n基金名:',name,"\n日期:",date,"净值:",value,"经理",manager)
        with open('manager.csv', mode='a')as f:
            f.write(CODE[num] + ',' + name + ',' + manager)
            f.write('\n')


async def manager(num):
    url = 'http://fund.eastmoney.com/' + CODE[num] + '.html'
    headers = {
        'headers': USER_AGENT[random.randint(0, 15)],
        'Referer': 'http://fund.eastmoney.com/'
    }
    page = requests.get(url, headers=headers)
    html = str(page.content, 'utf-8')
    content = page.content.decode()
    soup = BeautifulSoup(html, 'lxml')

    name = soup.find('a', {'href': url, 'target': "_self"}).getText()
    # manager = re.findall(r'"fund.eastmoney.com/manager/(.*?).html',page)[0]
    manager = soup.find('a', {'href': 'http://fundf10.eastmoney.com/jjjl_' + CODE[num] + '.html'}).getText()
    # print("基金编号:",CODE[num],'\n基金名:',name,"\n日期:",date,"净值:",value,"经理",manager)
    with open('manager.csv', mode='a')as f:
        f.write(CODE[num] + ',' + name + ',' + manager)
        f.write('\n')

class FundCrawler:
    def __init__(self, thread_pool_size):
        self.thread_pool_size = thread_pool_size
        self.lock = Lock()
    
    def fetch_fund_data(self):
        headers = {
            "User-Agent": get_random_user_agent(USER_AGENT),
            'Referer': 'http://fund.eastmoney.com/data/fundranking.html'
        }
        response = requests.get(BASE_URL, headers=headers, params=PARAMS)
        fund_codes = FundParser.parse_fund_codes(response.content.decode())
        
        with ThreadPoolExecutor(self.thread_pool_size) as pool:
            fund_data = list(pool.map(self.fetch_single_fund, fund_codes))
        
        return fund_data
    
    def fetch_single_fund(self, code):
        url = f'http://fund.eastmoney.com/{code}.html'
        headers = {
            "User-Agent": get_random_user_agent(USER_AGENT),
            'Referer': 'http://fund.eastmoney.com/'
        }
        response = requests.get(url, headers=headers)
        fund_info = FundParser.parse_fund_info(response.content.decode(), code)
        return fund_info

# from datetime import datetime

# if __name__ == '__main__':
#     # 主页基金下载
#     # start = datetime.now()
#     x = GetPage()
#     x.GetByURL()
#     # end = datetime.now()
#     # print((end - start).total_seconds(), "秒")
#     choice = int(input("请选择获取基金详细信息的方式: 1.线程池+同步锁 2.异步协程"))
#     if choice == 1:
#         start = datetime.now()
#         lock = Lock()
#         with ThreadPoolExecutor(THREAD_POOL) as pool:
#             for i in range(1, 100):
#                 pool.submit(getSingle, i)
#         end = datetime.now()
#         print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
#     elif choice == 2:
#         start = datetime.now()
#         loop = asyncio.get_event_loop()
#         # 异步操作
#         tasks = [manager(i) for i in range(1, 300)]
#         loop.run_until_complete(asyncio.wait(tasks))
#         loop.close()
#         end = datetime.now()
#         print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
#     else:
#         print("Please input 1 or 2")
