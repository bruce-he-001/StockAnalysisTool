import logging

import key_word_code
from key_word_code import PatternCode
from Pattern.PatternStrategy import PatternStrategy

class EngulfingStrategy(PatternStrategy):
    """看涨吞没策略"""

    def __init__(self):
        """
        吞没形态判断。
        """
        self.threshold = 0.06
        self.threshold_enhancement = 0.12

    def detect(self, kline_data, supports, resistances, gap_zone, pattern_result):
        logging.info("开始进行吞没形态检测")
        for i in range(len(kline_data) - 1, len(kline_data) - 6, -1):
            row = kline_data.iloc[i]

            # 获取当前K线和前一根K线的价格
            curr_open, curr_close = row['open'], row['close']
            prev_row = kline_data.iloc[i - 1]
            prev_open, prev_close = prev_row['open'], prev_row['close']
            # 计算两根K线的实体大小
            curr_body = abs(curr_close - curr_open)
            prev_body = abs(prev_close - prev_open)

            # 是否为看涨吞没形态
            # 条件1：前一根是阴线 (开盘价 > 收盘价)
            # 条件2：当前是阳线 (收盘价 > 开盘价)
            # 条件3：当前实体完全覆盖前一根实体 (当前开盘 <= 前收盘 且 当前收盘 >= 前开盘)
            is_bullish_engulfing = (
                    prev_open > prev_close and
                    curr_close > curr_open and
                    curr_open <= prev_close and
                    curr_close >= prev_open
            )

            # 是否为看跌吞没形态
            # 条件1：前一根是阳线 (收盘价 > 开盘价)
            # 条件2：当前是阴线 (开盘价 > 收盘价)
            # 条件3：当前实体完全覆盖前一根实体 (当前开盘 >= 前收盘 且 当前收盘 <= 前开盘)
            is_bearish_engulfing = (
                    prev_close > prev_open and
                    curr_open > curr_close and
                    curr_open >= prev_close and
                    curr_close <= prev_open
            )

            # 计算信号强度
            signal_strength = key_word_code.STANDARD_STRENGTH
            signal_strength_desc = "反转形态"

            avg_body = sum(
                abs(kline_data.iloc[j]['close'] - kline_data.iloc[j]['open']) for j in range(i - 5, i)) / 5.0
            if prev_body < avg_body * 0.5 and curr_body > avg_body * 1.5:
                signal_strength += 1
                signal_strength_desc += "，第一天的实体小而第二天的实体大"

            # 条件B：量能是过去五日平均量能的1.5倍，则强度+1
            # 因为列表长度 >= 10，且 i 最大为 len-1，所以 i-5 绝对安全
            current_volume = row['volume']
            avg_past_5_vol = sum(kline_data.iloc[j]['volume'] for j in range(i - 5, i)) / 5.0
            if current_volume >= 1.5 * avg_past_5_vol:
                signal_strength += 1
                signal_strength_desc += "，量能大"

            # 判断之前的趋势
            if is_bullish_engulfing:
                for j in range(i-1, 0, -1):
                    # 之前不能低于现在的价格
                    if kline_data.iloc[j]['close'] <= kline_data.iloc[i]['open'] * 0.97:
                        break
                    # 之前下跌超过threshold，认定为下跌行情
                    if pattern_result['has_reversal'] != 1 and abs(kline_data.iloc[i]['open'] - kline_data.iloc[j]['close']) / kline_data.iloc[j]['close'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.BULLISH_ENGULFING
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        if signal_strength >= key_word_code.STANDARD_STRENGTH:
                            pattern_result['buying_point'] = row['close']
                        else:
                            pattern_result['buying_point'] = row['low']
                        pattern_result['position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max((signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                        pattern_result['stop_loss_point'] = row['low']

                    if abs(kline_data.iloc[i]['open'] - kline_data.iloc[j]['close']) / kline_data.iloc[j]['close'] >= self.threshold_enhancement:
                        signal_strength += 1
                        pattern_result['signal_strength'] += 1  # 下跌行情超长，强度再+1
                        pattern_result['signal_strength_desc'] += "，超长行情"
                        pattern_result['position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max((signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                        break

            if is_bearish_engulfing:
                for j in range(i-1, 0, -1):
                    # 之前不能高于现在的价格
                    if kline_data.iloc[j]['close'] >= kline_data.iloc[i]['open'] * 1.03:
                        break
                    # 之前上涨超过threshold，认定为上涨行情
                    if pattern_result['has_reversal'] != 1 and abs(kline_data.iloc[i]['open'] - kline_data.iloc[j]['close']) / kline_data.iloc[j]['close'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.BEARISH_ENGULFING
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        pattern_result['take_profit_point'] = row['close']

                    if abs(kline_data.iloc[i]['open'] - kline_data.iloc[j]['close']) / kline_data.iloc[j]['close'] >= self.threshold_enhancement:
                        pattern_result['signal_strength'] += 1  # 上涨行情超长，强度再+1
                        pattern_result['signal_strength_desc'] += "，超长行情"
                        break

            if pattern_result['has_reversal'] == 1:
                self.hit_key_zone_analysis(row, supports, resistances, gap_zone, pattern_result)
                break

        logging.info("吞没形态检测完毕")
        return pattern_result