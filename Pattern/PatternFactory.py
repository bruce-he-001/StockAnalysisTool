from Pattern.PatternStrategy import PatternStrategy

class PatternFactory:
    def __init__(self):
        self.strategies = []

    def register(self, strategy: PatternStrategy):
        """注册新的形态策略"""
        self.strategies.append(strategy)

    def analyze(self, kline_data, supports, resistances, gap_zone):
        """遍历所有注册的策略，按优先级返回第一个匹配到的形态"""

        # 默认的空结果模板（避免返回 None 导致调用方报错）
        default_result = {
            'has_reversal': 0,
            'pattern_name': None,
            'reversal_date': None,
            'signal_strength': 0,
            'signal_strength_desc': None,
            'buying_point': None,
            'position_recommendation': 0,
            'stop_loss_point': 0,
            'take_profit_point': 0
        }

        for strategy in self.strategies:
            # 每次检测前，重置为干净的默认状态
            pattern_result = default_result.copy()

            # 执行检测（传入 kline_data 和当前干净的字典）
            strategy.detect(kline_data, supports, resistances, gap_zone, pattern_result)

            # 如果当前策略发现了反转信号，立即返回
            if pattern_result['has_reversal'] == 1:
                return pattern_result

        return default_result