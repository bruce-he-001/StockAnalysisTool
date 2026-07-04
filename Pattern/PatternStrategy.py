from abc import ABC, abstractmethod

import key_word_code


class PatternStrategy(ABC):
    """所有K线形态识别策略的抽象基类"""

    @abstractmethod
    def detect(self, kline_data, supports, resistances, gap_zone, pattern_result):
        """
        形态识别接口。
        Args:
            kline_data: K线数据 (DataFrame)
            supports: 支撑点
            resistances: 压力点
            gap_zone: 跳空区域
            pattern_result: 检测结果
        """
        pass

    def hit_key_zone_analysis(self, row, supports, resistances, gap_zone, pattern_result):
        hit_result, hit_result_desc = self.is_hit_key_zone(row, supports, resistances, gap_zone)
        pattern_result['signal_strength'] += hit_result
        pattern_result['signal_strength_desc'] += hit_result_desc
        pattern_result['position_recommendation'] = pattern_result['position_recommendation'] + hit_result * key_word_code.ADD_POSITION if \
            pattern_result['position_recommendation'] > 0 else pattern_result['position_recommendation']

    def is_hit_key_zone(self, row, supports, resistances, gap_zone):
        key_levels = supports + resistances
        for level in key_levels:
            zone_lower = level['price'] * (1 - 0.01)
            zone_upper = level['price'] * (1 + 0.01)
            # 判断形态的最高点或最低点和该区间有交集
            if row['low'] <= zone_upper and zone_lower <= row['high']:
                return 1, f"，触及了关键点{level['price']}"

        for gap in gap_zone:
            # 计算扩展后的缺口区间 [zone_lower, zone_upper]
            zone_lower = gap['gap_bottom'] * (1 - 0.05)
            zone_upper = gap['gap_top'] * (1 + 0.05)

            # 判断形态区间与缺口区间是否有交集
            if row['low'] <= zone_upper and zone_lower <= row['high']:
                return 1, f"，触及了关键区间 {gap['gap_bottom']} - {gap['gap_top']}"

        return 0, None