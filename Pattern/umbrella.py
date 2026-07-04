import logging

import pandas as pd

import key_word_code
from key_word_code import PatternCode
from Pattern.PatternStrategy import PatternStrategy

class UmbrellaStrategy(PatternStrategy):

    def __init__(self):
        """
        伞形态判断。
        """
        self.threshold = 0.12

    """伞形态策略"""
    def detect(self, kline_data, supports, resistances, gap_zone, pattern_result):
        logging.info("开始进行伞形态检测")
        # 在 kline_data 列表末尾添加一条伪造的 K 线数据,用来统一锤子线和上吊线的搜索
        new_row = {
            'date': '9999-12-31 15:00',
            'open': float('inf'),
            'high': float('inf'),
            'low': float('inf'),
            'close': float('inf'),
            'volume': 0
        }
        # 将字典转为 DataFrame 后拼接，ignore_index=True 用于重置索引
        kline_data = pd.concat([kline_data, pd.DataFrame([new_row])], ignore_index=True)

        for i in range(len(kline_data) - 2, len(kline_data) - 7, -1):
            row = kline_data.iloc[i]

            open_p, close_p, high_p, low_p = row['open'], row['close'], row['high'], row['low']
            body = abs(close_p - open_p)
            lower_shadow = min(open_p, close_p) - low_p
            upper_shadow = high_p - max(open_p, close_p)
            # 防止除零错误（如一字板）
            if body == 0:
                continue
            # 是否为伞形态。条件：下影线 >= 2倍实体，且上影线极短（<= 0.5倍实体）
            if lower_shadow < 2 * body or upper_shadow > body * 0.5:
                continue

            # 计算信号强度
            signal_strength = key_word_code.STANDARD_STRENGTH
            signal_strength_desc = "反转形态"
            # 条件A：若下影线长度是实体的4倍以上，强度+1
            # 增加 body > 0 的防御，防止一字板导致除零错误
            if body > 0 and lower_shadow >= 4 * body:
                signal_strength += 1
                signal_strength_desc += "，长下影线"

            # 条件B：量能是过去五日平均量能的1.5倍，则强度+1
            # 因为列表长度 >= 10，且 i 最大为 len-1，所以 i-5 绝对安全
            current_volume = row['volume']
            past_volumes = kline_data.iloc[i - 5:i]['volume']
            avg_past_5_vol = past_volumes.mean()

            if current_volume >= 1.5 * avg_past_5_vol:
                signal_strength += 1
                signal_strength_desc += "，量能大"
            # 条件B：量能小于过去五日平均量能，则强度-1
            if current_volume < avg_past_5_vol:
                signal_strength -= 1
                signal_strength_desc += "，量能低"

            prev_close = kline_data.iloc[i - 1]['close']
            prev2_close = kline_data.iloc[i - 2]['close']
            is_dropping = prev_close < prev2_close
            is_drop_enough = (prev_close / prev2_close) <= 0.985
            # 之前为下跌趋势的话（短暂的下跌都可以）
            if is_dropping and is_drop_enough:
                pattern_result['has_reversal'] = 1
                pattern_result['pattern_name'] = PatternCode.HAMMER
                pattern_result['reversal_date'] = row['date']
                pattern_result['signal_strength'] = signal_strength
                pattern_result['signal_strength_desc'] = signal_strength_desc
                if signal_strength >= key_word_code.STANDARD_STRENGTH:
                    pattern_result['buying_point'] = row['close']
                else:
                    pattern_result['buying_point'] = row['low']
                pattern_result['position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max((signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                pattern_result['stop_loss_point'] = row['low']
                break
            # 若之前不为下跌，判断是否为上涨趋势
            if not is_dropping:
                past_max_close = kline_data.iloc[:i]['close'].max()
                for j in range(i-1, 0, -1):
                    past_row = kline_data.iloc[j]
                    # 之前不能高过现在的价格
                    if past_row['close'] >= close_p * 1.03:
                        break
                    # 之前上涨超过threshold，认定为长足的上涨行情
                    next_row = kline_data.iloc[i + 1]
                    if (close_p - past_row['low']) / past_row['low'] >= self.threshold and next_row['close'] < close_p:
                        if close_p >= past_max_close:
                            signal_strength += 1  # 创新高，强度再+1
                            signal_strength_desc += '，行情创新高'
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.HANG
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        pattern_result['take_profit_point'] = row['close']
                        break

            if pattern_result['has_reversal'] == 1:
                self.hit_key_zone_analysis(row, supports, resistances, gap_zone, pattern_result)
                break

        logging.info("伞形态检测完毕")
        return pattern_result

