import logging

import key_word_code
from key_word_code import PatternCode
from Pattern.PatternStrategy import PatternStrategy

class HalfEngulfingStrategy(PatternStrategy):
    """看涨吞没策略"""

    def __init__(self):
        """
        吞没形态判断。
        """
        self.threshold = 0.06
        self.threshold_enhancement = 0.12

    def is_dark_cloud(self, kline_data, i):
        k1, k2 = kline_data.iloc[i - 1], kline_data.iloc[i]

        # 1. 第一根K线是大阳线（实体长度 > 过去10日平均实体长度的 1.5 倍）
        # 提取 k1 之前的10根K线（即索引 i-12 到 i-3）
        past_10_klines = kline_data.iloc[i - 12: i - 2]
        # 计算这10根K线的平均实体长度
        avg_body_10 = (past_10_klines['close'] - past_10_klines['open']).abs().mean()
        # 计算当前第一根K线的实体长度
        k1_body = abs(k1['close'] - k1['open'])
        # 判断条件：必须是阳线，且实体长度大于10日均值的1.5倍
        is_k1_big_rise = (k1['close'] > k1['open']) and (k1_body > avg_body_10 * 1.5 or (k1['close'] - k1['open']) / k1['open'] >= 0.03)

        # 2. 第二根K线是阴线且深入第一根K线实体（超过50%）
        is_k2_yin = k2['close'] < k2['open']
        # 3b. 计算第一根阳线的实体中点
        k1_mid_point = (k1['open'] + k1['close']) / 2.0
        # 3c. 第三根K线的收盘价必须小于该中点（即向下深入实体50%以上）
        is_k2_penetrate = k2['close'] < k1_mid_point

        return is_k1_big_rise and is_k2_yin and is_k2_penetrate

    def is_pierce(self, kline_data, i):
        k1, k2 = kline_data.iloc[i - 1], kline_data.iloc[i]

        # 1. 第一根K线是大阴线（实体长度 > 过去10日平均实体长度的 1.5 倍）
        # 提取 k1 之前的10根K线（即索引 i-12 到 i-3）
        past_10_klines = kline_data.iloc[i - 12: i - 2]
        # 计算这10根K线的平均实体长度
        avg_body_10 = (past_10_klines['close'] - past_10_klines['open']).abs().mean()
        # 计算当前第一根K线的实体长度
        k1_body = abs(k1['close'] - k1['open'])
        # 判断条件：必须是阴线，且实体长度大于10日均值的1.5倍
        is_k1_big_drop = (k1['close'] < k1['open']) and (k1_body > avg_body_10 * 1.5 or (k1['open'] - k1['close']) / k1['open'] >= 0.03)

        # 2. 第二根K线是阳线且深入第一根K线实体（超过50%）
        is_k2_yang = k2['close'] > k2['open']
        # 3b. 计算第一根阴线的实体中点
        k1_mid_point = (k1['open'] + k1['close']) / 2.0
        # 3c. 第二根K线的收盘价必须大于该中点（即深入实体50%以上）
        is_k2_penetrate = k2['close'] > k1_mid_point

        return is_k1_big_drop and is_k2_yang and is_k2_penetrate

    def detect(self, kline_data, supports, resistances, gap_zone, pattern_result):
        logging.info("开始进行刺透、乌云盖顶形态检测")
        for i in range(len(kline_data) - 1, len(kline_data) - 6, -1):
            row = kline_data.iloc[i]

            is_dark_cloud = self.is_dark_cloud(kline_data, i)
            is_pierce = self.is_pierce(kline_data, i)
            if not is_dark_cloud and not is_pierce:
                continue

            # 计算信号强度
            k1, k2 = kline_data.iloc[i - 1], kline_data.iloc[i]
            k1_body = abs(k1['close'] - k1['open'])
            signal_strength = key_word_code.STANDARD_STRENGTH
            signal_strength_desc = "反转形态"
            # --- 加分条件 1：第二根K线收盘价深入第一根K线实体 ---
            if is_dark_cloud:
                # 乌云盖顶：第二根收盘价深入第一根80%
                penetrate = k2['close'] < k1['close'] - 0.8 * k1_body
            else:
                # 刺透：第二根收盘价 < 第一根开盘价
                penetrate = k2['close'] > k1['close'] + 0.8 * k1_body
            if penetrate:
                signal_strength += 1
                signal_strength_desc += "，第二根K线深入了第一根K线实体"

            # --- 加分条件 2：第二根K线开盘交易量极大（这个先按照交易量来评估) ---
            current_volume = k2['volume']
            avg_past_5_vol = sum(kline_data.iloc[j]['volume'] for j in range(i - 5, i)) / 5.0
            if current_volume >= 1.5 * avg_past_5_vol:
                signal_strength += 1
                signal_strength_desc += "，第二根K线交易量大"

            # --- 加分条件 3：k线呈现光头光脚且行情超长---
            is_k1_bare = self.is_bare(k1)
            is_k2_bare = self.is_bare(k2)

            # 判断之前的趋势
            if is_pierce:
                for j in range(i - 1, 0, -1):
                    # 之前不能低于现在的价格
                    if kline_data.iloc[j]['close'] <= kline_data.iloc[i]['open'] * 0.97:
                        break
                    # 之前下跌超过threshold，认定为下跌行情
                    if pattern_result['has_reversal'] != 1 and abs(
                            kline_data.iloc[i]['close'] - kline_data.iloc[j]['low']) / kline_data.iloc[j][
                        'low'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.PIERCE
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        if signal_strength >= key_word_code.STANDARD_STRENGTH:
                            pattern_result['buying_point'] = row['close']
                        else:
                            pattern_result['buying_point'] = row['low']
                        pattern_result[
                            'position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max(
                            (signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                        pattern_result['stop_loss_point'] = row['low']

                    if is_k1_bare and is_k2_bare and (kline_data.iloc[i]['close'] - kline_data.iloc[j]['low']) / kline_data.iloc[i][
                        'close'] >= self.threshold_enhancement:
                        signal_strength += 1
                        pattern_result['signal_strength'] += signal_strength  # 下跌行情超长且光头光脚，强度再+1
                        pattern_result['signal_strength_desc'] += "，光头光脚超长行情"
                        pattern_result[
                            'position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max(
                            (signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                        break

            if is_dark_cloud:
                for j in range(i - 1, 0, -1):
                    # 之前不能高于现在的价格
                    if kline_data.iloc[j]['close'] >= kline_data.iloc[i]['open'] * 1.03:
                        break
                    # 之前上涨超过threshold，认定为上涨行情
                    if pattern_result['has_reversal'] != 1 and abs(
                            kline_data.iloc[i]['close'] - kline_data.iloc[j]['low']) / kline_data.iloc[j][
                        'low'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.DARK_CLOUD_OVER
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        pattern_result['take_profit_point'] = row['close']

                    if abs(kline_data.iloc[i]['close'] - kline_data.iloc[j]['low']) / kline_data.iloc[j][
                        'low'] >= self.threshold_enhancement:
                        pattern_result['signal_strength'] += 1  # 上涨行情超长，强度再+1
                        pattern_result['signal_strength_desc'] += "，光头光脚超长行情"
                        break

            if pattern_result['has_reversal'] == 1:
                self.hit_key_zone_analysis(row, supports, resistances, gap_zone, pattern_result)
                break

        logging.info("刺透、乌云盖顶形态检测完毕")
        return pattern_result

    def is_bare(self, k):
        body_length = abs(k['close'] - k['open'])

        # 防止除零错误（如果开盘价等于收盘价，实体为0，无法计算比例）
        if body_length == 0:
            return False

        # 2. 计算上下影线长度
        upper_shadow = k['high'] - max(k['close'], k['open'])
        lower_shadow = min(k['close'], k['open']) - k['low']

        # 3. 判断影线是否在容差范围内
        # 上影线必须 <= 实体 * 容差
        # 下影线必须 <= 实体 * 容差
        is_top_clean = upper_shadow <= body_length * key_word_code.TOLERANCE
        is_bottom_clean = lower_shadow <= body_length * key_word_code.TOLERANCE

        # 4. 如果上下影线都极短，则根据收盘价判断阴阳
        if is_top_clean and is_bottom_clean:
            return True

        return False