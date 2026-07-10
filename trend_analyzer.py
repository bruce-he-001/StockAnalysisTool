from mootdx.quotes import Quotes
import pandas as pd

import key_word_code
from Pattern.half_engulfing import HalfEngulfingStrategy
from key_points_analyzer import KeyPointsAnalyzer
from key_word_code import PatternCode, MIN_KLINE_FOR_PATTERN
from Pattern.PatternFactory import PatternFactory
from Pattern.engulfing import EngulfingStrategy
from Pattern.star import StarStrategy
from Pattern.umbrella import UmbrellaStrategy
import logging


class TrendAnalyzer():
    """
    趋势分析器。

    负责基于 K 线数据分析股票当前趋势和可能的反转与延续，

    Attributes:
        kline_data (pd.DataFrame): 传入的股票历史 K 线数据。
    """

    def __init__(self, kline_data: pd.DataFrame):
        """
        初始化关键点分析器。

        Args:
            kline_data (pd.DataFrame): 包含 open, high, low, close 等字段的 K 线数据。
        """
        self.kline_data = kline_data

        # 初始化形态工厂并注册所有策略
        self.pattern_factory = PatternFactory()
        self._register_all_patterns()

    def trend_analysis(self, supports, resistances, current_price):
        """
         判断当前趋势

         Args:
             supports: 支撑位列表，元素为包含 date, price 的字典。
             resistances: 压力位列表，元素为包含 date, price 的字典。
             current_price: 当前股价

         Returns:
             tuple: (趋势信号, 变化幅度字符串)
                    趋势信号: 1(上涨), 0(下降), -1(未知)
                    变化幅度: 如 "2.50%"，若无法计算则返回 "0.00%"
         """
        # 获取最近的一个支撑点和压力点
        nearest_support = supports[-1] if supports else None
        nearest_resistance = resistances[-1] if resistances else None

        # 比较时间，判断趋势
        trend_signal = key_word_code.UNKNOWN_TREND
        change_str = "0.00%"

        if nearest_support is not None and nearest_resistance is not None:
            # 将字典中的年月日转换为 date 对象，直接进行比较，无需拼接字符串
            if nearest_support['date'] >= nearest_resistance['date']:
                trend_signal = key_word_code.UPWARD_TREND  # 支撑更近，上涨趋势
            else:
                trend_signal = key_word_code.DOWNWARD_TREND  # 压力更近，下降趋势
        elif nearest_support is not None:
            trend_signal = key_word_code.UPWARD_TREND  # 只有支撑点，默认偏多
        elif nearest_resistance is not None:
            trend_signal = key_word_code.DOWNWARD_TREND  # 只有压力点，默认偏空

        # 计算距离关键点的变化幅度
        try:
            if trend_signal == key_word_code.UPWARD_TREND and nearest_support:
                # 防止除零错误
                support_price = nearest_support['price'].item()
                if support_price > 0:
                    change = (current_price.item() - support_price) / support_price
                    change_str = f"{change:.2%}"

            elif trend_signal == key_word_code.DOWNWARD_TREND and nearest_resistance:
                # 防止除零错误
                resistance_price = nearest_resistance['price'].item()
                if resistance_price > 0:
                    change = (resistance_price - current_price.item()) / resistance_price
                    change_str = f"{change:.2%}"
        except (KeyError, TypeError, ZeroDivisionError) as e:
            # 如果数据结构异常或计算出错，安全降级为默认值
            change_str = "0.00%"
            logging.info(f"警告: 计算涨跌幅时发生异常: {e}")

        return trend_signal, change_str

    def _register_all_patterns(self):
        """集中注册所有的形态策略（未来新增只需在这里加一行）"""
        self.pattern_factory.register(UmbrellaStrategy())
        self.pattern_factory.register(EngulfingStrategy())
        self.pattern_factory.register(StarStrategy())
        self.pattern_factory.register(HalfEngulfingStrategy())
        # self.pattern_factory.register(ThreeWhiteSoldiersStrategy())

    def reversal_analysis(self, supports, resistances, gap_zone, current_price):
        """反转形态分析主入口"""
        if len(self.kline_data) <= MIN_KLINE_FOR_PATTERN:
            raise ValueError(
                f"K线数据不足，无法进行反转形态分析！"
                f"当前仅有 {len(self.kline_data)} 条，至少需要 {MIN_KLINE_FOR_PATTERN} 条。"
            )

        # 默认震荡行情 形态代码0
        result = {
            'trend': key_word_code.UNKNOWN_TREND,     # 当前趋势 (0: 下降, 1: 上升, -1: 未知)
            'change_range': None,
            'has_reversal': 0,      # 是否反转 (0： 没有反转, 1: 有反转, -1: 未知)
            'pattern_name': None,
            'reversal_date': None,
            'signal_strength': 0,
            'signal_strength_desc': None,
            'buying_point': 0,
            'position_recommendation': 0,
            'stop_loss_point': 0,
            'take_profit_point': 0,
            'risk_reward_ratio': 0.0,
        }

        trend_signal, change_str = self.trend_analysis(supports, resistances, current_price)
        result['trend'] = trend_signal
        result['change_range'] = change_str

        pattern_result = self.pattern_factory.analyze(self.kline_data, supports, resistances, gap_zone)
        result['has_reversal'] = pattern_result['has_reversal']
        result['pattern_name'] = pattern_result['pattern_name']
        result['reversal_date'] = pattern_result['reversal_date']
        result['signal_strength'] = pattern_result['signal_strength']
        result['signal_strength_desc'] = pattern_result['signal_strength_desc']
        result['buying_point'] = pattern_result['buying_point']
        result['position_recommendation'] = pattern_result['position_recommendation']
        result['stop_loss_point'] = pattern_result['stop_loss_point']
        result['take_profit_point'] = pattern_result['take_profit_point']

        if result['buying_point'] is None:
            return result

        # 计算风险报偿比
        support_closest, resistance_closest = KeyPointsAnalyzer(self.kline_data).find_closest_pressure_and_support(supports, resistances, gap_zone, result['buying_point'], result['reversal_date'])
        if len(resistance_closest) == 0:
            # 行情创新高，没有压力位
            result['take_profit_point'] = float('inf')
            result['risk_reward_ratio'] = 10.0

        result['take_profit_point'] = resistance_closest[0]
        risk = abs(result['buying_point'] - result['stop_loss_point'])  # 使用 abs 防止负数
        reward = abs(result['take_profit_point'] - result['buying_point'])
        if risk == 0:
            result['risk_reward_ratio'] = 10.0  # 或者 float('inf')，根据你的业务需求
        else:
            result['risk_reward_ratio'] = round(reward / risk, 2)

        # 是否跨越关键点

        return result



