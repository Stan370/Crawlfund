from fund_crawler.crawler import FundCrawler
from fund_crawler.writer import DataWriter
from config import THREAD_POOL

def main():
    # 主页基金下载
    # start = datetime.now()
    x = GetPage()
    x.GetByURL()
    # end = datetime.now()
    # print((end - start).total_seconds(), "秒")
    choice = int(input("请选择获取基金详细信息的方式: 1.线程池+同步锁 2.异步协程"))
    if choice == 1:
        start = datetime.now()
        lock = Lock()
        with ThreadPoolExecutor(THREAD_POOL) as pool:
            for i in range(1, 100):
                pool.submit(getSingle, i)
        end = datetime.now()
        print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
    elif choice == 2:
        start = datetime.now()
        loop = asyncio.get_event_loop()
        # 异步操作
        tasks = [manager(i) for i in range(1, 300)]
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()
        end = datetime.now()
        print((end - start).total_seconds(), "秒 数据已下载到manager.csv")
    else:
        print("Please input 1 or 2")


    crawler = FundCrawler(thread_pool_size=THREAD_POOL)
    fund_data = crawler.fetch_fund_data()
    
    writer = DataWriter()
    writer.write_to_csv(fund_data, 'fund_list.csv')

if __name__ == "__main__":
    main()
