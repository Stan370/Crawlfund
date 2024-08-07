from tiantianfund.crawler import FundCrawler
from tiantianfund.writer import DataWriter
from tiantianfund.async_manager import async_main
from config import THREAD_POOL
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

def main():
    # Fetch fund data
    crawler = FundCrawler(thread_pool_size=THREAD_POOL)
    fund_data = crawler.fetch_fund_data()
    
    # Write data to CSV
    writer = DataWriter()
    writer.write_to_csv(fund_data, 'fund_list.csv')

if __name__ == "__main__":
    choice = int(input("请选择获取基金详细信息的方式: 1.线程池+同步锁 2.异步协程"))
    if choice == 1:
        start = datetime.now()
        lock = Lock()
        with ThreadPoolExecutor(THREAD_POOL) as pool:
            for i in range(1, 100):
                pool.submit(crawler.fetch_single_fund, i)
        end = datetime.now()
        print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
    elif choice == 2:
        start = datetime.now()
        asyncio.run(async_main())
        end = datetime.now()
        print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
    else:
        print("Please input 1 or 2")

    main()
