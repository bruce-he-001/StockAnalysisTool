from enum import IntEnum

class PatternCode(IntEnum):
    """K线反转形态代码映射"""
    CONSOLIDATION = 0   # 震荡行情
    HAMMER = 1          # 锤子线
    HANG = 2            # 上吊线
    BULLISH_ENGULFING = 3       # 看涨吞没
    BEARISH_ENGULFING= 4        # 看跌吞没
    MORNING_STAR = 5    # 启明星
    EVENING_STAR = 6    # 黄昏之星
    PIERCE = 7          # 刺透
    DARK_CLOUD_OVER = 8     # 乌云盖顶
    # THREE_SOLDIERS = 9  # 红三兵
    # THREE_CROWS = 10     # 黑三兵
    UNKNOWN = -1        # 未知形态

MIN_KLINE_FOR_PATTERN = 10
UPWARD_TREND = 1
DOWNWARD_TREND = 0
UNKNOWN_TREND = -1
STANDARD_STRENGTH = 3
STANDARD_POSITION = 4
ADD_POSITION = 1
TOLERANCE = 0.05