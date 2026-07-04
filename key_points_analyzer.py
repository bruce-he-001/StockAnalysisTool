from mootdx.quotes import Quotes
import pandas as pd

import key_word_code


class KeyPointsAnalyzer():
    """
    关键点分析器。

    负责基于 K 线数据寻找并管理重要的技术点位，
    包括最新交易日分析、前高前低支撑压力分析以及跳空区域捕捉。

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
        # 应该区分，科技股为12%，老登股为6%(经常出现8%、9%的变化的用12%）
        self.threshold = 0.06

    def previous_high_low_analysis(self):
        """
        使用 ZigZag 算法寻找关键转折点（支撑位和压力位）

        """

        highs = self.kline_data['high'].values
        lows = self.kline_data['low'].values
        dates = self.kline_data['date'].values

        n = len(self.kline_data)
        support_levels = []
        resistance_levels = []

        # 初始化：寻找第一个极值点来确定初始趋势
        # 我们假设第一天的最高价和最低价作为初始参考
        last_pivot_high = highs[0]
        last_pivot_low = lows[0]
        last_pivot_high_idx = 0
        last_pivot_low_idx = 0

        # 初始状态：0-未定，1-上升趋势，-1-下降趋势
        trend = key_word_code.UNKNOWN_TREND

        for i in range(1, n):
            current_high = highs[i]
            current_low = lows[i]

            # --- 1. 初始趋势确定阶段 ---
            if trend == key_word_code.UNKNOWN_TREND:

                if current_high > last_pivot_high:
                    last_pivot_high = current_high
                    last_pivot_high_idx = i
                if last_pivot_low < current_low:
                    last_pivot_low = current_low
                    last_pivot_low_idx = i
                # 如果当前最高价比上一个高点涨了 12%，确立为上升趋势
                if (current_high - last_pivot_low) / last_pivot_low >= self.threshold:
                    trend = key_word_code.UPWARD_TREND
                # 如果当前最低价比上一个低点跌了 12%，确立为下降趋势
                elif (last_pivot_high - current_low) / last_pivot_high >= self.threshold:
                    trend = key_word_code.DOWNWARD_TREND
                continue

            # --- 2. 处于上升趋势 ---
            if trend == key_word_code.UPWARD_TREND:
                # 在上升趋势中，不断更新最高点
                if current_high > last_pivot_high:
                    last_pivot_high = current_high
                    last_pivot_high_idx = i
                # 如果从最高点回撤超过 12%，趋势反转为下降
                elif (last_pivot_high - current_low) / last_pivot_high >= self.threshold:
                    # 记录压力位
                    resistance_levels.append({
                        'date': dates[last_pivot_high_idx],
                        'price': last_pivot_high,
                        'drop': f"{(last_pivot_high - current_low) / last_pivot_high:.2%}"
                    })
                    # 切换趋势为下降，重置最低点
                    trend = -1
                    last_pivot_low = current_low
                    last_pivot_low_idx = i

            # --- 3. 处于下降趋势 ---
            elif trend == key_word_code.DOWNWARD_TREND:
                # 在下降趋势中，不断更新最低点
                if current_low < last_pivot_low:
                    last_pivot_low = current_low
                    last_pivot_low_idx = i
                # 如果从最低点反弹超过 12%，趋势反转为上升
                elif (current_high - last_pivot_low) / last_pivot_low >= self.threshold:
                    # 记录支撑位
                    support_levels.append({
                        'date': dates[last_pivot_low_idx],
                        'price': last_pivot_low,
                        'bounce': f"{(current_high - last_pivot_low) / last_pivot_low:.2%}"
                    })
                    # 切换趋势为上升，重置最高点
                    trend = 1
                    last_pivot_high = current_high
                    last_pivot_high_idx = i
        if trend == 0:
            # 震荡行情，没有趋势和关键点
            return [], []

        if not support_levels and not resistance_levels:
            # 说明此时市场为单边行情，没有反转，没有支撑点和压力位
            absolute_low = self.kline_data['low'].min()
            low_label = self.kline_data['low'].idxmin()
            absolute_low_idx = self.kline_data.index.get_loc(low_label)
            absolute_high = self.kline_data['high'].max()
            high_label = self.kline_data['high'].idxmax()
            absolute_high_idx = self.kline_data.index.get_loc(high_label)
            if absolute_high_idx >= absolute_low_idx:
                # 单边上升
                support_levels.append({
                    'date': dates[absolute_low_idx],
                    'price': absolute_low,
                    'bounce': f"{(absolute_high - absolute_low) / absolute_low:.2%}"
                })
            else:
                # 单边下降
                resistance_levels.append({
                    'date': dates[absolute_high_idx],
                    'price': absolute_high,
                    'drop': f"{(absolute_high - absolute_low) / absolute_high:.2%}"
                })

        # tudo:改为log
        # self.print_support_resistance(support_levels, resistance_levels)
        return support_levels, resistance_levels

    def gap_zone_analysis(self):
        """向量化捕捉跳空区域（不区分向上/向下）"""
        prev_high = self.kline_data['high'].shift(1)
        prev_low = self.kline_data['low'].shift(1)

        # 1. 合并跳空条件（向上跳空 或 向下跳空）
        gap_cond = (self.kline_data['low'] > prev_high) | (self.kline_data['high'] < prev_low)

        # 2. 向量化提取缺口下沿和上沿（不满足条件自动为 NaN）
        # 向上跳空时，下沿是昨日最高价；向下跳空时，下沿是今日最高价
        self.kline_data['gap_bottom'] = self.kline_data.loc[gap_cond, 'high'].where(
            self.kline_data['high'] < prev_low,
            prev_high[gap_cond]
        )
        # 向上跳空时，上沿是今日最低价；向下跳空时，上沿是昨日最低价
        self.kline_data['gap_top'] = self.kline_data.loc[gap_cond, 'low'].where(
            self.kline_data['low'] > prev_high,
            prev_low[gap_cond]
        )

        # 3. 筛选出有跳空的数据
        gaps = self.kline_data[gap_cond].copy()

        # 4. 打印跳空区域
        # self.print_gap_zone(gaps)
        return gaps.to_dict('records')

    def find_closest_pressure_and_support(self, support_levels, resistance_levels, gap_zone, current_price, date = '9999-12-31'):
        for gap in gap_zone:
            if gap['gap_bottom'] <= current_price <= gap['gap_top'] and gap['date'] < date:
                return [gap['gap_bottom']], [gap['gap_top']]

        all_levels = []
        # 添加支撑点
        for sup in support_levels:
            if sup['date'] < date:
                all_levels.append({"price": sup['price'], "display": [sup['price']]})
        # 添加压力点
        for res in resistance_levels:
            if res['date'] < date:
                all_levels.append({"price": res['price'], "display": [res['price']]})
        # 添加跳空区间（将区间上下沿都加入池中）
        for gap in gap_zone:
            all_levels.append({"price": gap['gap_bottom'], "display": [gap['gap_bottom'], gap['gap_top']]})
            all_levels.append({"price": gap['gap_top'], "display": [gap['gap_bottom'], gap['gap_top']]})
        all_levels.sort(key=lambda x: x['price'])
        support_result = []
        resistance_result = []
        for i, level in enumerate(all_levels):
            if level['price'] > current_price:
                # 找到了第一个大于当前价格的（最近上方）
                resistance_result = level['display']

                # 它的前一个（如果存在）就是小于当前价格的（最近下方）
                if i > 0:
                    prev_level = all_levels[i - 1]
                    support_result = prev_level['display']
                break  # 找到第一个大于的就立刻跳出循环，保证效率

        # 处理边界情况：如果当前价格比所有关键点都大（没有上方）
        if not resistance_result:
            support_result = all_levels[-1]['display']

        return support_result, resistance_result