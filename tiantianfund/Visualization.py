import requests
import re
import json
import pandas as pd
import datetime
from pyecharts.charts import Bar, Line, Grid
from pyecharts import options as opts

class FundDataVisualizer:
    def __init__(self, fund_code: int, page_range: int = None, file_name=None):
        self.fund_code = fund_code
        self.page_range = page_range
        self.file_name = file_name if file_name else f'{self.fund_code}.csv'
        self.session = requests.session()
        self.headers = {
            'Host': 'api.fund.eastmoney.com',
            'User-Agent': 'Mozilla/5.0',
            'Referer': f'http://fundf10.eastmoney.com/jjjz_{self.fund_code}.html',
        }
        self.root_url = 'http://api.fund.eastmoney.com/f10/lsjzt'
        self.bar, self.line, self.grid = self.init_chart()

    def fount_info(self):
        search_url = 'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx'
        params = {"callback": "jQuery18309325043269513131_1618730779404", "m": 1, "key": self.fund_code}
        res = self.session.get(search_url, params=params)
        try:
            content = self.content_formatter(res.text)
            fields = '，'.join([i['TTYPENAME'] for i in content['Datas'][0]['ZTJJInfo']])
            print(f"基金代码: {self.fund_code}")
            print(f"名称：{content['Datas'][0]['NAME']}")
            print(f"基金类型：{content['Datas'][0]['FundBaseInfo']['FTYPE']}")
            print(f"基金经理：{content['Datas'][0]['FundBaseInfo']['JJJL']}")
            print(f"相关领域：{fields}")
            return True
        except TypeError:
            print(f'Fail to pinpoint fund code, {self.fund_code}, please check.')

    @staticmethod
    def content_formatter(content):
        params = re.compile(r'jQuery.+?\((.*)\)')
        return json.loads(params.findall(content)[0])

    def page_data(self, page_index):
        params = {
            'callback': 'jQuery18308909743577296265_1618718938738',
            'fundCode': self.fund_code,
            'pageIndex': page_index,
            'pageSize': 20,
        }
        res = self.session.get(url=self.root_url, headers=self.headers, params=params)
        return self.content_formatter(res.text)

    def page_iter(self):
        for page_index in range(self.page_range):
            yield self.page_data(page_index + 1)

    def get_all_data(self):
        total_count = float('inf')
        page_index = 0
        while page_index * 20 <= total_count:
            item = self.page_data(page_index + 1)
            page_index += 1
            total_count = item['TotalCount']
            yield item

    def crawl_data(self):
        if self.fount_info():
            df = pd.DataFrame()
            if self.page_range:
                for data in self.page_iter():
                    df = df.append(data['Data']['LSJZList'], ignore_index=True)
                    print("Downloading data...", end='\r')
            else:
                for data in self.get_all_data():
                    df = df.append(data['Data']['LSJZList'], ignore_index=True)
                    print("Downloading data...", end='\r')
            df.to_csv(self.file_name)
            print(f"Data saved to {self.file_name}")
            return self.file_name

    @staticmethod
    def load_data(file):
        df = pd.read_csv(file)
        df['FSRQ'] = pd.to_datetime(df['FSRQ'])
        df.sort_values(by=['FSRQ'], inplace=True)
        df['JZZZL'].fillna(0, inplace=True)
        max_date = df['FSRQ'].max()
        min_date = datetime.datetime.strptime('2021-1-1', '%Y-%m-%d')
        df = df[df['FSRQ'].isin(pd.date_range(start=min_date, end=max_date))]
        data_x, data_y_day, data_y_total = [], [], []
        money = 10000
        for _, row in df.iterrows():
            data_x.append(pd.to_datetime(row['FSRQ']).strftime('%Y-%m-%d'))
            money_diff = money * (float(row['JZZZL']) / 100)
            money += money_diff
            data_y_day.append(round(money_diff, 2))
            data_y_total.append(round(money, 0))
        return data_x, data_y_day, data_y_total

    def init_chart(self):
        bar = Bar()
        line = Line()
        grid = Grid(
            init_opts=opts.InitOpts(
                theme='white',
                width='1600px',
                height='900px'
            )
        )
        return bar, line, grid

    def bar_viz(self, data_x, data_y_day):
        self.bar.add_xaxis(data_x)
        self.bar.add_yaxis(
            self.fund_code,
            data_y_day,
            itemstyle_opts={
                "normal": {
                    'shadowBlur': 10,
                    'shadowColor': 'rgba(0, 0, 0, 0.5)',
                    'shadowOffsetX': 10,
                    'shadowOffsetY': 10,
                    'borderColor': 'rgb(220,220,220)',
                    'borderWidth': 1
                }
            },
            gap='50%',
            tooltip_opts=opts.TooltipOpts(is_show=True, formatter='{b}<br>当日收益：{c}元'),
            label_opts=opts.LabelOpts(is_show=False)
        )
        self.bar.set_global_opts(
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                is_piecewise=True,
                pieces=[{"max": 0, "color": 'green'},
                        {"min": 1, "color": 'red'},]
            ),
            yaxis_opts=opts.AxisOpts(
                name='日收益/元',
                type_="value",
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(
                        type_='dashed'))
            ),
            xaxis_opts=opts.AxisOpts(
                name='日期',
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(
                        type_='dashed'))),
            legend_opts=opts.LegendOpts(is_show=False),
        )
        return self

    def line_viz(self, data_x, data_y_total):
        self.line.add_xaxis(data_x)
        self.line.add_yaxis(
            self.fund_code,
            data_y_total,
            is_symbol_show=True,
            symbol='circle',
            symbol_size=1,
            is_smooth=True,
            linestyle_opts={'shadowBlur': 5,
                            'shadowColor': 'rgba(0, 0, 0, 0.5)',
                            'shadowOffsetY': 10,
                            'shadowOffsetX': 10,
                            'width': 2,},
            tooltip_opts=opts.TooltipOpts(is_show=False),
            label_opts=opts.LabelOpts(is_show=False)
        )
        self.line.set_global_opts(
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                is_piecewise=True,
                pieces=[{"max": 0, "color": 'green'},
                        {"min": 1, "color": 'red'},]
            ),
            yaxis_opts=opts.AxisOpts(
                name='持仓/元', type_="value", is_scale=True,
                splitline_opts=opts.SplitLineOpts(is_show=True,
                                                  linestyle_opts=opts.LineStyleOpts(
                                                      type_='dashed'))
            ),
            xaxis_opts=opts.AxisOpts(
                name='日期',
                splitline_opts=opts.SplitLineOpts(is_show=True,
                                                  linestyle_opts=opts.LineStyleOpts(
                                                      type_='dashed'))),
            legend_opts=opts.LegendOpts(is_show=False),
            title_opts=opts.TitleOpts(
                title="1W元本金日收益趋势",
                pos_left='center',
                title_textstyle_opts=opts.TextStyleOpts(
                    color='#08A05C',
                    font_size=20,
                    font_weight='bold'),
                subtitle=f'{self.fund_code}',
            ),
            graphic_opts=[
                opts.GraphicGroup(
                    graphic_item=opts.GraphicItem(id_='1', left="250px", top="250px"),
                    children=[
                        opts.GraphicRect(
                            graphic_item=opts.GraphicItem(left="center", top="center", z=1),
                            graphic_shape_opts=opts.GraphicShapeOpts(width=250, height=120),
                            graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(
                                fill="rgba(0,0,0,0.5)", line_width=4, stroke="#000",),
                        ),
                        opts.GraphicText(
                            graphic_item=opts.GraphicItem(left="center", top="center", z=100),
                            graphic_textstyle_opts=opts.GraphicTextStyleOpts(
                                text=f'{self.fund_code}\n\n截止日期：{data_x[-1]}\n\n持有收益：{data_y_total[-1] - 10000}元
                                \n\n收益率：{(data_y_total[-1] - 10000) / 10000 * 100}%',
                                font="bold 20px Microsoft YaHei",
                                graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(fill="#fff")),
                        )
                    ])
            ]
        )
        return self

    def render(self):
        self.grid.add(self.bar, grid_opts=opts.GridOpts(pos_right="55%"))
        self.grid.add(self.line, grid_opts=opts.GridOpts(pos_left="50%"))
        self.grid.render(f'{self.fund_code}.html')

    def visualize(self):
        file = self.crawl_data()
        data_x, data_y_day, data_y_total = self.load_data(file)
        self.bar_viz(data_x, data_y_day)
        self.line_viz(data_x, data_y_total)
        self.render()

# Example of usage
fund_visualizer = FundDataVisualizer(320007, page_range=1)
fund_visualizer.visualize()
