import requests
import re
import json
import pandas as pd
import datetime

fundCode = 162719


class SingleCrawler:
    def __init__(self,
                 fund_code: int,
                 page_range: int = None,
                 file_name=None):
        """
        :param fund_code:  基金代码
        :param page_range:  获取最大页码数，每页包含20天的数据
        """
        self.root_url = 'http://api.fund.eastmoney.com/f10/lsjzt'
        self.fund_code = fund_code
        self.session = requests.session()
        self.page_range = page_range
        self.file_name = file_name if file_name else '{}.csv'.format(self.fund_code)
        self.headers = {
            'Host': 'api.fund.eastmoney.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
            'Referer': 'http://fundf10.eastmoney.com/jjjz_%s.html' % self.fund_code,
        }

    def fount_info(self):
        search_url = 'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx'
        params = {
            "callback": "jQuery18309325043269513131_1618730779404",
            "m": 1,
            "key": self.fund_code,
        }
        res = self.session.get(search_url,
                               params=params
                               )
        try:
            content = self.content_formatter(res.text)
            fields = '，'.join([i['TTYPENAME'] for i in content['Datas'][0]['ZTJJInfo']])
            print("{:*^30}".format(self.fund_code))
            print("* 名称：{0:{1}>10} *".format(content['Datas'][0]['NAME'], chr(12288)))
            print("* 基金类型：{0:{1}>10} *".format(content['Datas'][0]['FundBaseInfo']['FTYPE'], chr(12288)))
            print("* 基金经理：{0:{1}>10} *".format(content['Datas'][0]['FundBaseInfo']['JJJL'], chr(12288)))
            print("* 相关领域：{0:{1}>10} *".format(fields, chr(12288)))
            print("*" * 30)
            return True
        except TypeError:
            print('Fail to pinpoint fund code, {}, please check.'.format(self.fund_code))

    @staticmethod
    def content_formatter(content1):
        params = re.compile('jQuery.+?\((.*)\)')
        data = json.loads(params.findall(content1)[0])

        return data

    def page_data(self,
                  page_index):
        params = {
            'callback': 'jQuery18308909743577296265_1618718938738',
            'fundCode': self.fund_code,
            'pageIndex': page_index,
            'pageSize': 20,
        }
        res = self.session.get(url=self.root_url, headers=self.headers, params=params)
        content = self.content_formatter(res.text)
        return content

    def page_iter(self):
        for page_index in range(self.page_range):
            item = self.page_data(page_index + 1)
            yield item

    def get_all(self):
        total_count = float('inf')
        page_index = 0
        while page_index * 20 <= total_count:
            item = self.page_data(page_index + 1)
            page_index += 1
            total_count = item['TotalCount']
            yield item

    def run(self):
        if self.fount_info():
            df = pd.DataFrame()
            if self.page_range:
                for data in self.page_iter():
                    df = df.append(data['Data']['LSJZList'], ignore_index=True)
                    print("\r{:*^30}".format(' DOWNLOADING '), end='')
            else:
                for data in self.get_all():
                    df = df.append(data['Data']['LSJZList'], ignore_index=True)
                    print("\r{:*^30}".format(' DOWNLOADING '), end='')
            df.to_csv(self.file_name)
            print("\r{:*^30}".format(' WORK DONE '))
            print("{:*^30}".format(' FILE NAME '))
            print("*{:^28}*".format(self.file_name))
            print("*" * 30)


def load_data(file):
    df = pd.read_csv(file)
    # 转换成时间格式
    df['FSRQ'] = pd.to_datetime(df['FSRQ'])
    # 按时间排序
    df.sort_values(by=['FSRQ'], inplace=True)
    # 日增长率填充0
    df['JZZZL'].fillna(0, inplace=True)
    max_date = df['FSRQ'].max()
    min_date = datetime.datetime.strptime('2021-1-1', '%Y-%m-%d')
    df = df[df['FSRQ'].isin(pd.date_range(start=min_date, end=max_date))]

    data_x, data_y_day, data_y_total = [], [], []
    money = 10000
    for _, row in df.iterrows():
        data_x.append(pd.to_datetime(row['FSRQ']).strftime('%Y-%m-%d'))
        money_diff = money * (float(row['JZZZL']) / 100)
        money = money + money_diff
        # print(diff_rate, money, money_diff)
        data_y_day.append(round(money_diff, 2))
        data_y_total.append(round(money, 0))
    return data_x, data_y_day, data_y_total


from pyecharts.charts import *
from pyecharts import options as opts


class DataViz:
    def __init__(self,
                 file,
                 name):
        self.file = file
        self.name = name
        self.bar, self.line, self.grid = self.init_char()
        self.data_x, self.data_y_day, self.data_y_total = load_data(file)
        print(self.data_x, self.data_y_day, self.data_y_total)

    @staticmethod
    def init_char():
        bar = Bar()
        line = Line()
        grid = Grid(
            init_opts=opts.InitOpts(
                theme='white',
                # bg_color=JsCode(bg_color_js),
                width='1600px',
                height='900px'

            )
        )
        return bar, line, grid

    def bar_viz(self):
        self.bar.add_xaxis(self.data_x)
        self.bar.add_yaxis(
            self.name,
            self.data_y_day,
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
                        {"min": 1,
                         "color": 'red'},
                        ]
            ),
            yaxis_opts=opts.AxisOpts(
                name='日收益/元',
                type_="value",
                # is_scale=True,
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

    def line_viz(self):
        self.line.add_xaxis(self.data_x)
        self.line.add_yaxis(
            self.name,
            self.data_y_total,
            is_symbol_show=True,
            symbol='circle',
            symbol_size=1,
            is_smooth=True,
            linestyle_opts={'shadowBlur': 5,
                            'shadowColor': 'rgba(0, 0, 0, 0.5)',
                            'shadowOffsetY': 10,
                            'shadowOffsetX': 10,
                            'width': 2,
                            'curve': 0.1,
                            },
            tooltip_opts=opts.TooltipOpts(is_show=False),
            label_opts=opts.LabelOpts(is_show=False)
        )
        self.line.set_global_opts(
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                is_piecewise=True,
                pieces=[{"max": 0, "color": 'green'},
                        {"min": 1,
                         "color": 'red'},
                        ]
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
            legend_opts=opts.LegendOpts(
                is_show=False
            ),
            title_opts=opts.TitleOpts(
                title="1W元本金日收益趋势",
                pos_left='center',
                title_textstyle_opts=opts.TextStyleOpts(
                    color='#08A05C',
                    font_size=20,
                    font_weight='bold'),
                subtitle='{}'.format(self.name),
            ),
            graphic_opts=[
                opts.GraphicGroup(
                    graphic_item=opts.GraphicItem(id_='1', left="250px", top="250px"),
                    children=[
                        opts.GraphicRect(
                            graphic_item=opts.GraphicItem(
                                left="center", top="center", z=1
                            ),
                            graphic_shape_opts=opts.GraphicShapeOpts(
                                width=250, height=120
                            ),
                            graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(
                                # 颜色配置，这里设置为黑色，透明度为0.5
                                fill="rgba(0,0,0,0.5)",
                                line_width=4,
                                stroke="#000",
                            ),
                        ),
                        opts.GraphicText(
                            graphic_item=opts.GraphicItem(
                                left="center", top="center", z=100
                            ),
                            graphic_textstyle_opts=opts.GraphicTextStyleOpts(
                                # 要显示的文本
                                text='{}\n\n截止日期：{}\n\n持有收益：{}元\n\n持有收益率：{:.2%}'.format(
                                    self.name,
                                    self.data_x[-1],
                                    self.data_y_total[-1] - 10000,
                                    self.data_y_total[-1] / 10000 - 1),
                                font="bold 14px Microsoft YaHei",
                                graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(
                                    fill="#fff"
                                ),
                            ),
                        )
                    ],
                ), ]
        )
        self.line.set_series_opts(
            label_opts=opts.LabelOpts(is_show=False),
            markline_opts=opts.MarkLineOpts(
                data=[
                    opts.MarkLineItem(type_="min", name="最小值"),
                    opts.MarkLineItem(type_="max", name="最大值"),
                ],
                label_opts=opts.LabelOpts(is_show=True, position='left', formatter='{b}：\n{c}元'),
            ),
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(
                        name="收益",
                        coord=[self.data_x[-1], self.data_y_total[-1]],
                        value=int(self.data_y_total[-1]),
                        symbol_size=[80, 50]
                    )
                ]
            )
        )

    def run(self):
        self.line_viz()
        self.bar_viz()
        self.grid.add(
            self.line,
            is_control_axis_index=False,
            grid_opts=opts.GridOpts(
                pos_left='7%',
                pos_right='7%',
                pos_top='10%',
                pos_bottom='50%')
        )

        self.grid.add(
            self.bar,
            is_control_axis_index=False,
            grid_opts=opts.GridOpts(
                pos_left='7%',
                pos_right='7%',
                pos_top='60%',
                pos_bottom='5%')
        )
        self.grid.render(self.file.replace('csv', 'html'))


if __name__ == "__main__":
    c = SingleCrawler(fundCode)
    c.run()
    vis = DataViz(file=('162719.csv'), name='广发道琼斯石油指数人民币A')
    vis.run()
