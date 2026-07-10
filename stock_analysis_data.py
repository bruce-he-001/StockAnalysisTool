from datetime import datetime, timedelta

from mootdx.quotes import Quotes
import pandas as pd
import baostock as bs
import re

from key_points_analyzer import KeyPointsAnalyzer
from trend_analyzer import TrendAnalyzer
import logging

class StockAnalysisData:
    """
    股票分析数据核心类。

    该类作为整个量化分析流程的入口，负责统筹管理股票的 K 线数据获取、
    包含关键点分析数据、趋势分析数据。
    """

    # 内部成员类：昨日参考点
    class YesterdayReference:
        """
        昨日参考点数据类。

        用于封装前一个交易日的关键价格信息，通常作为当日开盘、盘中支撑与压力的参考基准。
        """
        def __init__(self, high: float, low: float):
            """
            初始化昨日参考点。

            Args:
                high (float): 昨日最高价。
                low (float): 昨日最低价。
            """
            self.high = high
            self.low = low

        def __repr__(self):
            """返回昨日参考点的格式化字符串表示。"""
            return f"昨日参考点(最高: {self.high}, 最低: {self.low})"

    def __init__(self):
        # 股票代码，默认茅台
        self.stock_code: str = "603799"
        # 至少为30
        self.period = 120
        self.kline_data: pd.DataFrame = None
        self.current_price = None
        self.yesterday_ref: StockAnalysisData.YesterdayReference = None
        # 支撑点和压力点,
        self.support_levels = []
        self.resistance_levels = []
        # 跳空区
        self.gap_zone = None
        # 形态分析结果
        self.pattern_result = None
        # 关键点分析器
        self.kp_instance: KeyPointsAnalyzer = None
        # 趋势分析器
        self.trend_analyzer: TrendAnalyzer = None

    def get_data(self):
        # 实时数据获取
        client = Quotes.factory(market='std', bestip=True, timeout=15)
        # # frequency=9 通常代表日线，offset=30 代表获取30根K线
        # bars = client.bars(symbol=self.stock_code, frequency=9, offset=self.period, adjust='qfq')
        # df = pd.DataFrame(bars)
        quotes = client.quotes(symbol=self.stock_code)
        self.current_price = quotes['price'].values

        # 历史k线数据获取
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=self.period)).strftime('%Y-%m-%d')
        bs.login()
        rs = bs.query_history_k_data_plus(
            self.add_exchange_prefix(self.stock_code),
            "date,open,high,low,close,volume",
            start_date=start_date,
            end_date=end_date,
            frequency="d",  # 日K线
            adjustflag="2"  # 前复权
        )
        # 将结果转换为 Pandas DataFrame
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        self.kline_data = pd.DataFrame(data_list, columns=rs.fields)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        self.kline_data[numeric_cols] = self.kline_data[numeric_cols].apply(pd.to_numeric)
        bs.logout()

        self.kp_instance = KeyPointsAnalyzer(self.kline_data)
        self.trend_analyzer = TrendAnalyzer(self.kline_data)

        # 获取数据总行数
        total_rows = len(self.kline_data)
        # 获取前两行数据（如果数据不足2行，head(2) 会安全地返回所有可用行）
        preview_data = self.kline_data[['date', 'open', 'high', 'low', 'close', 'volume']].head(2).to_string(
            index=False)
        # 使用 logging 记录日志
        logging.info(f"成功获取 {self.stock_code} 行情数据，共 {total_rows} 条记录。")
        logging.info(f"数据预览（前2行）:\n{preview_data} ...")
        #      date          open          high           low         close   volume
        # 2026-04-02 73.2105377000 74.1536532800 72.9533243600 73.7059115400 32631797
        # 2026-04-03 73.6392266000 73.6868587000 72.5913204000 72.7342167000 17277260

    def analyze(self):
        if self.kline_data is None or self.kline_data.empty:
            raise ValueError("股票数据调用错误，或者股票数据为空！")

        logging.info("🚀 开始执行K线数据分析...")

        # 1. 提取昨日参考点（取倒数第一行数据作为昨日）
        last_row = self.kline_data.iloc[-1]
        self.yesterday_ref = self.YesterdayReference(last_row['high'], last_row['low'])
        logging.info(f"📅 昨日参考点提取完成 -> 最高价: {self.yesterday_ref.high}, 最低价: {self.yesterday_ref.low}")

        # 2. 实例化外部关键点分析器，并调用对应的方法
        self.support_levels, self.resistance_levels = self.kp_instance.previous_high_low_analysis()
        self.gap_zone = self.kp_instance.gap_zone_analysis()

        logging.info(
            f"🎯 关键点位识别完成 -> "
            f"支撑位: {len(self.support_levels)}个, "
            f"阻力位: {len(self.resistance_levels)}个, "
            f"缺口区域: {len(self.gap_zone)}个"
        )

        # 3. 调度外部趋势分析器
        self.pattern_result = self.trend_analyzer.reversal_analysis(self.support_levels, self.resistance_levels, self.gap_zone, self.current_price)

        logging.info("✅ 数据分析完成，所有核心指标已成功提取并缓存。")

    def key_points_show(self, csv_path):
        unified_levels = []
        # 处理支撑位
        for item in self.support_levels:
            unified_levels.append({
                "日期": item['date'],
                "类型": "支撑位",
                "价格": item['price']
            })
        # 处理压力位
        for item in self.resistance_levels:
            unified_levels.append({
                "日期": item['date'],
                "类型": "压力位",
                "价格": item['price']
            })
        # 处理跳空区间
        for item in self.gap_zone:
            unified_levels.append({
                "日期": item['date'],
                "类型": "跳空区间",
                "价格": f"{item['gap_bottom']} - {item['gap_top']}"
            })
        # 按日期从左到右（升序）排列
        levels_df = pd.DataFrame(unified_levels)
        if not levels_df.empty:
            levels_df['日期'] = pd.to_datetime(levels_df['日期'])
            levels_df = levels_df.sort_values(by='日期').reset_index(drop=True)
            levels_df['日期'] = levels_df['日期'].dt.strftime('%Y-%m-%d')

        try:
            header_desc = f"以下是分析 {self.stock_code} 股票在 {self.period} 个交易日数据后给出的买卖指引。\n"
            section_title = "1.关键点与关键区间展示\n"  # <--- 新增：章节标题
            with open(csv_path, 'w', encoding='utf-8-sig') as f:
                f.write(header_desc)
                f.write(section_title)  # <--- 写入标题

            levels_df.to_csv(
                csv_path,
                mode='a',  # 追加模式，写在标题下方
                index=False,
                encoding='utf-8-sig'
            )

            logging.info(f"💾 关键点与关键区间展示 已成功保存至: {csv_path}")
        except Exception as e:
            logging.error(f"❌ 保存CSV文件失败: {e}")

    def generate_level_evaluation(self, level_list, level_name):
        """通用的点位评估生成器"""
        if not level_list:
            return f"当前没有有效的{level_name}。"
        elif len(level_list) == 1:
            return f"当前存在{level_name}，价格为：{level_list[0]}。"
        elif len(level_list) == 2:
            return f"当前存在{level_name}区间，区间范围为：{level_list[0]} - {level_list[1]}。"
        else:
            return f"{level_name}数据异常，请检查关键点位计算逻辑。"

    def current_price_evaluate(self, csv_path):
        support_closest, resistance_closest = self.kp_instance.find_closest_pressure_and_support(self.support_levels, self.resistance_levels, self.gap_zone, self.current_price)
        support_evaluation = self.generate_level_evaluation(support_closest, "支撑点")
        resistance_evaluation = self.generate_level_evaluation(resistance_closest, "压力点")
        evaluation = f"{support_evaluation} {resistance_evaluation}"

        try:
            section_title = "2.关键点与关键区间对当前股价的参考\n"
            with open(csv_path, 'a', encoding='utf-8-sig') as f:
                f.write(section_title)
                f.write(f"当前股票价格为：{self.current_price}, {evaluation}, 昨日最高点{self.yesterday_ref.high}, 昨日最低点{self.yesterday_ref.low}\n")

            logging.info(f"💾 关键点与关键区间展示 已成功保存至: {csv_path}")
        except Exception as e:
            logging.error(f"❌ 保存CSV文件失败: {e}")

    def trend_evaluate(self, csv_path):
        trend_map = {1: "上升", 0: "下降", -1: "未知"}
        trend_text = trend_map.get(self.pattern_result['trend'], "未知")
        analysis_desc = f"当前趋势为{trend_text}"

        if self.pattern_result['trend'] != -1:
            analysis_desc += f"，距离上一个转折的变化幅度为{self.pattern_result['change_range']}"
        analysis_desc += "。\n"

        pattern_name = {0: "震荡", 1: "锤子线", 2: "上吊线", 3: "看涨吞没", 4: "看跌吞没", 5: "启明星", 6: "黄昏星", 7: "刺透", 8: "乌云盖顶"}
        if self.pattern_result['has_reversal'] == 1:
            analysis_desc += f"存在转折迹象，迹象（形态）名为{pattern_name.get(self.pattern_result['pattern_name'])}，转折发生日期为{self.pattern_result['reversal_date']}，信号强度为{self.pattern_result['signal_strength']}，强度描述为{self.pattern_result['signal_strength_desc']}"
            analysis_desc += "。\n"

            # 5. 若信号强度描述不为None，追加交易点位信息
            if self.pattern_result['signal_strength_desc'] is not None:
                analysis_desc += (
                    f"买点为{self.pattern_result['buying_point']}"
                    f"，建议仓位为{self.pattern_result['position_recommendation']}"
                    f"，止损点为{self.pattern_result['stop_loss_point']}"
                    f"，止盈点为{self.pattern_result['take_profit_point']}"
                    f"，风险回报比为{self.pattern_result['risk_reward_ratio']}"
                )
        else:
            analysis_desc += "当前不存在转折迹象"


        try:
            section_title = "3.当前趋势，转折分析、买卖点、仓位、风险盈利比分析\n"
            with open(csv_path, 'a', encoding='utf-8-sig') as f:
                f.write(section_title)
                f.write(analysis_desc)
                f.write('。\n')

            logging.info(f"💾 当前趋势，转折分析、买卖点、仓位、风险盈利比分析: {csv_path}")
        except Exception as e:
            logging.error(f"❌ 保存CSV文件失败: {e}")

    def generate_strategy(self):
        csv_path = f"strategy_result/strategy_guide_{self.stock_code}.csv"
        self.key_points_show(csv_path)
        self.current_price_evaluate(csv_path)
        self.trend_evaluate(csv_path)
        logging.info(f"💾 策略指引已成功保存至: {csv_path}")

    def add_exchange_prefix(self, code):
        if code.startswith('6'):  # 沪市主板(60) + 科创板(688)
            return f"sh.{code}"
        elif code.startswith(('00', '3')):  # 深市主板(000/002) + 创业板(300)
            return f"sz.{code}"
        elif code.startswith('92'):  # 北交所(920)
            return f"bj.{code}"
        else:
            return code  # 无法识别的代码直接返回原值


def main():
    logging.basicConfig(level=logging.INFO)
    print("程序开始运行...")
    stock_analysis_data = StockAnalysisData()
    stock_analysis_data.get_data()
    stock_analysis_data.analyze()
    stock_analysis_data.generate_strategy()
    print("程序运行结束。")

if __name__ == '__main__':
    main()