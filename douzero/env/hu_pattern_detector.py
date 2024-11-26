"""
胡牌检测器模块。
用于检测玩家手牌是否构成有效的胡牌组合，并计算相应的番型倍数。

主要功能：
1. 检测是否可以胡牌
2. 计算胡牌的番型倍数
3. 判断具体的胡牌类型(如：独一无二、君临天下等)
"""

def get_hu_multiplier(hand_cards):
    """判断胡牌番型倍数
    Args:
        hand_cards: 玩家手牌列表(8张)，每张牌是一个元组(点数,花色)
                   点数：6-14，其中11=J,12=Q,13=K,14=A
                   花色：0=♠,1=♥,2=♣,3=♦,-1=癞子
    Returns:
        multiplier: 番型倍数，0表示不能胡牌
        pattern_name: 番型名称，如"独一无二"、"君临天下"等
    """
    if any(card == (1, -1) for card in hand_cards):
        return 0, "不能胡牌"

    # 1. 分离普通牌和癞子
    normal_cards = []
    joker_count = 0
    for card in hand_cards:
        if card[1] == -1:  # 癞子
            joker_count += 1
        else:  # 普通牌
            normal_cards.append(card)
    
    # 2. 生成所有可能的牌（6-A的四种花色）
    all_possible_cards = [(p, s) for p in range(6, 15) for s in range(4)]
    
    def try_all_replacements(remaining_jokers, current_cards):
        """递归尝试所有可能的癞子替换方案"""
        # 基础情况：所有癞子都已替换完
        if remaining_jokers == 0:
            return _check_pattern(current_cards)
        
        # 递归情况：尝试所有可能的替换
        max_multiplier = 0
        best_pattern = "不能胡牌"
        for card in all_possible_cards:
            multiplier, pattern = try_all_replacements(
                remaining_jokers - 1, 
                current_cards + [card]
            )
            if multiplier > max_multiplier:
                max_multiplier = multiplier
                best_pattern = pattern
                if multiplier == 100:  # 已经是最大倍数，可以提前返回
                    return multiplier, best_pattern
        return max_multiplier, best_pattern
    
    # 3. 开始计算最大胡牌倍数
    return try_all_replacements(joker_count, normal_cards)

def _check_pattern(cards):
    """检查具体牌型"""
    # 100倍牌型
    if _count_same_cards(cards, 14) >= 8:
        return 100, "独一无二"
    elif _count_same_cards(cards, 13) >= 8:
        return 100, "君临天下"
    elif _count_same_cards(cards, 10) >= 8:
        return 100, "十全十美"
    elif _count_same_cards(cards, 8) >= 8:
        return 100, "八方来财"
    
    # 50倍牌型：八方来贺（8张同花色或同点数）
    if _is_eight_same_suit(cards) or _is_eight_same_point(cards):
        return 50, "八方来贺"
    
    # 32倍牌型
    if _count_n_m_cards(cards, 13, 14) in [(6,2), (2,6)]:
        return 32, "顶峰相见"
    elif _count_n_m_cards(cards, 11, 12) in [(6,2), (2,6)]:
        return 32, "心心相连"
    elif _count_n_m_cards(cards, 9, 10) in [(6,2), (2,6)]:
        return 32, "十拿九稳"
    elif _count_n_m_cards(cards, 6, 7) in [(6,2), (2,6)]:
        return 32, "六事兴旺"
    
    # 16倍牌型
    if _is_six_two_adjacent(cards):
        return 16, "比翼为邻"
    elif _is_six_two_same_color(cards):
        return 16, "六朝金粉"
    
    # 8倍牌型
    if _is_six_two(cards):
        return 8, "六六大顺"
    elif _is_five_three_adjacent(cards):
        return 8, "永恒相随"
    elif _is_five_three_same_color(cards):
        return 8, "五谷丰登"
    
    # 4倍牌型
    if _is_five_three(cards):
        return 4, "五福临门"
    elif _is_four_four_adjacent(cards):
        return 4, "二龙腾飞"
    elif _is_four_four_same_color(cards):
        return 4, "四季发财"
    
    # 2倍牌型
    if _is_four_four(cards):
        return 2, "四季如春"
    
    # 1倍牌型
    if _is_three_three_two(cards):
        return 1, "平胡"
    
    return 0, "不能胡牌"

def _count_same_cards(cards, point):
    """统计指定点数的牌数量"""
    return sum(1 for card in cards if card[0] == point)

def _count_n_m_cards(cards, point1, point2):
    """统计两个点数的牌数量"""
    count1 = sum(1 for card in cards if card[0] == point1)
    count2 = sum(1 for card in cards if card[0] == point2)
    return count1, count2

def _is_eight_same_suit(cards):
    """判断是否8张同花色"""
    suits = [card[1] for card in cards]
    return len(set(suits)) == 1 and len(suits) == 8

def _is_eight_same_point(cards):
    """判断是否8张同点数"""
    points = [card[0] for card in cards]
    return len(set(points)) == 1 and len(points) == 8

def _is_same_color(cards):
    """判断所有牌是否同色(红色或黑色)"""
    suits = [card[1] for card in cards]
    return all(suit % 2 == suits[0] % 2 for suit in suits)

def _is_six_two_adjacent(cards):
    """判断是否是6+2相邻的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    for point in range(6, 14):
        if (point_counts.get(point, 0) == 6 and point_counts.get(point + 1, 0) == 2) or \
           (point_counts.get(point, 0) == 2 and point_counts.get(point + 1, 0) == 6):
            return True
    return False

def _is_six_two_same_color(cards):
    """判断是否是6+2同色的组合"""
    if not _is_same_color(cards):
        return False
    
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [2, 6]

def _is_six_two(cards):
    """判断是否是6+2的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [2, 6]

def _is_five_three_adjacent(cards):
    """判断是否是5+3相邻的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    for point in range(6, 14):
        if (point_counts.get(point, 0) == 5 and point_counts.get(point + 1, 0) == 3) or \
           (point_counts.get(point, 0) == 3 and point_counts.get(point + 1, 0) == 5):
            return True
    return False

def _is_five_three_same_color(cards):
    """判断是否是5+3同色的组合"""
    if not _is_same_color(cards):
        return False
    
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [3, 5]

def _is_five_three(cards):
    """判断是否是5+3的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [3, 5]

def _is_four_four_adjacent(cards):
    """判断是否是4+4相邻的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    for point in range(6, 14):
        if point_counts.get(point, 0) == 4 and point_counts.get(point + 1, 0) == 4:
            return True
    return False

def _is_four_four_same_color(cards):
    """判断是否是4+4同色的组合"""
    if not _is_same_color(cards):
        return False
    
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [4, 4]

def _is_four_four(cards):
    """判断是否是4+4的组合"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 2 and counts == [4, 4]

def _is_three_three_two(cards):
    """判断是否是3+3+2的组合(平胡)"""
    point_counts = {}
    for card in cards:
        point_counts[card[0]] = point_counts.get(card[0], 0) + 1
    
    counts = sorted(point_counts.values())
    return len(counts) == 3 and counts == [2, 3, 3]