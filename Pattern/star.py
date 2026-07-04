import logging

import key_word_code
from key_word_code import PatternCode
from Pattern.PatternStrategy import PatternStrategy

class StarStrategy(PatternStrategy):

    def __init__(self):
        """
        星线形态判断。
        """
        self.threshold = 0.06

    """星线形态策略"""
    def is_morning_star(self, kline_data, i):
        """
        启明星：底部反转形态，出现在下跌趋势末端。
        第一根：大阴线；第二根：小实体（十字星）；第三根：阳线，且收盘价深入第一根阴线实体50%。
        """
        if i < 2: return False
        k1, k2, k3 = kline_data.iloc[i - 2], kline_data.iloc[i - 1], kline_data.iloc[i]

        # 1. 第一根K线是大阴线（实体长度 > 过去10日平均实体长度的 1.5 倍）
        # 提取 k1 之前的10根K线（即索引 i-12 到 i-3）
        past_10_klines = kline_data.iloc[i - 12: i - 2]
        # 计算这10根K线的平均实体长度
        avg_body_10 = (past_10_klines['close'] - past_10_klines['open']).abs().mean()
        # 计算当前第一根K线的实体长度
        k1_body = abs(k1['close'] - k1['open'])
        # 判断条件：必须是阴线，且实体长度大于10日均值的1.5倍，或者变化超过3%
        is_k1_big_drop = (k1['close'] < k1['open']) and (k1_body > avg_body_10 * 1.5 or (k1['open'] - k1['close']) / k1['open'] >= 0.03)

        # 2. 第二根K线是小实体（实体长度 < 2%），代表多空犹豫
        k2_body = abs(k2['close'] - k2['open'])
        is_k2_small = (k2_body / k2['open']) < 0.02

        # 3. 第三根K线是大阳线（涨幅 > 3%），且收盘价高于第一根K线开盘价（深入实体）
        is_k3_yang = k3['close'] > k3['open']
        # 3b. 计算第一根阴线的实体中点
        k1_mid_point = (k1['open'] + k1['close']) / 2.0
        # 3c. 第三根K线的收盘价必须大于该中点（即深入实体50%以上）
        is_k3_penetrate = k3['close'] > k1_mid_point

        return is_k1_big_drop and is_k2_small and is_k3_yang and is_k3_penetrate

    def is_evening_star(self, kline_data, i):
        """
        黄昏星：顶部反转形态，出现在上升趋势末端。
        第一根：大阳线；第二根：小实体（十字星）；第三根：阴线，且收盘价深入第一根阳线实体50%。
        """
        if i < 2: return False
        k1, k2, k3 = kline_data.iloc[i - 2], kline_data.iloc[i - 1], kline_data.iloc[i]

        # 1. 第一根K线是大阳线（实体长度 > 过去10日平均实体长度的 1.5 倍）
        # 提取 k1 之前的10根K线（即索引 i-12 到 i-3）
        past_10_klines = kline_data.iloc[i - 12: i - 2]
        # 计算这10根K线的平均实体长度
        avg_body_10 = (past_10_klines['close'] - past_10_klines['open']).abs().mean()
        # 计算当前第一根K线的实体长度
        k1_body = abs(k1['close'] - k1['open'])
        # 判断条件：必须是阳线，且实体长度大于10日均值的1.5倍，或者变化超过3%
        is_k1_big_rise = (k1['close'] > k1['open']) and (k1_body > avg_body_10 * 1.5 or (k1['close'] - k1['open']) / k1['open'] >= 0.03)

        # 2. 第二根K线是小实体（实体长度 < 2%）
        k2_body = abs(k2['close'] - k2['open'])
        is_k2_small = (k2_body / k2['open']) < 0.02

        # 3. 第三根K线是大阴线（跌幅 > 3%），且收盘价低于第一根K线开盘价（深入实体）
        is_k3_yin = k3['close'] < k3['open']
        # 3b. 计算第一根阳线的实体中点
        k1_mid_point = (k1['open'] + k1['close']) / 2.0
        # 3c. 第三根K线的收盘价必须小于该中点（即向下深入实体50%以上）
        is_k3_penetrate = k3['close'] < k1_mid_point

        # 综合所有条件
        return is_k1_big_rise and is_k2_small and is_k3_yin and is_k3_penetrate

    def detect(self, kline_data, supports, resistances, gap_zone, pattern_result):
        logging.info("开始进行星形态检测")
        for i in range(len(kline_data) - 1, len(kline_data) - 6, -1):
            row = kline_data.iloc[i]

            is_morning = self.is_morning_star(kline_data, i)
            is_evening = self.is_evening_star(kline_data, i)
            if not is_morning and not is_evening:
                continue

            # 计算信号强度
            signal_strength = key_word_code.STANDARD_STRENGTH
            signal_strength_desc = "反转形态"

            k1, k2, k3 = kline_data.iloc[i - 2], kline_data.iloc[i - 1], kline_data.iloc[i]
            # --- 加分条件 ：第二根与第一根和第三根K线的实体之间不存在重叠（跳空）---
            if is_morning:
                # 启明星：第二根的最高价 < 第一根的最低价，且第二根的最低价 > 第三根的开盘价（向下跳空）
                no_overlap = k2['high'] < k1['low'] and k2['low'] > k3['open']
            else:
                # 黄昏星：第二根的最低价 > 第一根的最高价，且第二根的最高价 < 第三根的开盘价（向上跳空）
                no_overlap = k2['low'] > k1['high'] and k2['high'] < k3['open']
            if no_overlap:
                signal_strength += 1
                signal_strength_desc += "，中间小实体与两边大实体不接触"

            # --- 加分条件 2：第三根K线收盘价深入第一根K线实体 ---
            if is_morning:
                # 启明星：第三根收盘价 > 第一根开盘价
                penetrate = k3['close'] > k1['open']
            else:
                # 黄昏星：第三根收盘价 < 第一根开盘价
                penetrate = k3['close'] < k1['open']
            if penetrate:
                signal_strength += 1
                signal_strength_desc += "，第三根K线覆盖了第一根K线实体"

            # --- 加分条件 ：第一根K线交易量小，第三根交易量大 ---
            # 计算过去5日平均成交量（排除当前三根K线）
            avg_past_5_vol = sum(kline_data.iloc[j]['volume'] for j in range(i - 8, i - 3)) / 5.0
            if avg_past_5_vol > 0:
                # 第一根缩量（< 均量），第三根放量（> 2倍均量）
                if k1['volume'] < avg_past_5_vol and k3['volume'] >= 1.5 * avg_past_5_vol:
                    signal_strength += 1
                    signal_strength_desc += "，第一根K线交易量小且第三根交易量大"

            # 判断之前的趋势
            if is_morning:
                for j in range(i - 3, 0, -1):
                    # 之前不能低于现在的价格
                    if kline_data.iloc[j]['close'] <= kline_data.iloc[i-1]['close'] * 0.97:
                        break
                    # 之前下跌超过threshold，认定为下跌行情
                    if abs(kline_data.iloc[i-1]['close'] - kline_data.iloc[j]['close']) / kline_data.iloc[j][
                        'close'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.MORNING_STAR
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        if signal_strength >= key_word_code.STANDARD_STRENGTH:
                            pattern_result['buying_point'] = k3['close']
                        else:
                            pattern_result['buying_point'] = k2['close']
                        pattern_result[
                            'position_recommendation'] = key_word_code.STANDARD_POSITION + key_word_code.ADD_POSITION * max(
                            (signal_strength - key_word_code.STANDARD_STRENGTH), 0)
                        pattern_result['stop_loss_point'] = k2['close']
                        break

            if is_evening:
                for j in range(i - 3, 0, -1):
                    # 之前不能高于现在的价格
                    if kline_data.iloc[j]['close'] >= kline_data.iloc[i-1]['close'] * 1.03:
                        break
                    # 之前上涨超过threshold，认定为上涨行情
                    if abs(kline_data.iloc[i-1]['close'] - kline_data.iloc[j]['close']) / kline_data.iloc[j][
                        'close'] >= self.threshold:
                        pattern_result['has_reversal'] = 1
                        pattern_result['pattern_name'] = PatternCode.EVENING_STAR
                        pattern_result['reversal_date'] = row['date']
                        pattern_result['signal_strength'] = signal_strength
                        pattern_result['signal_strength_desc'] = signal_strength_desc
                        pattern_result['stop_loss_point'] = k3['close']
                        break

            if pattern_result['has_reversal'] == 1:
                self.hit_key_zone_analysis(row, supports, resistances, gap_zone, pattern_result)
                break

        logging.info("星形态检测完毕")
        return pattern_result