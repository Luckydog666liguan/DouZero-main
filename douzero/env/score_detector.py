"""
负分检测器模块。
用于计算玩家手牌中未能组成有效牌型的牌的负分总和。

主要功能：
1. 计算手牌的最小负分值
2. 考虑所有可能的牌型组合（同花顺或同点数）
3. 处理癞子和问号牌的特殊情况

计分规则：
- 问号牌 = 0分
- 6-10 = 10分
- J-K = 20分
- A = 30分

注意事项：
1. 输入为7张牌（与胡牌检测的8张不同）
2. 癞子可以变成任意牌
3. 有效牌型（不计负分）：
   - 同花顺（3张及以上）
   - 同点数（3张及以上）
4. 会尝试所有可能的组合方式，返回最小的负分值
"""
def get_negative_score(input_cards):
    """计算7张牌的最小负分
    Args:
        input_cards: 玩家手牌列表(7张)，每张牌是一个元组(点数,花色)
                    点数：6-10=6-10, J=11, Q=12, K=13, A=14, 问号=0
                    花色：黑桃=0, 红桃=1, 梅花=2, 方片=3, 癞子=-1
    Returns:
        int: 最小负分值
    """
    # 1. 分离普通牌、问号和癞子
    normal_cards = []
    question_marks = []
    joker_count = 0
    for card in input_cards:
        if card[1] == -1:  # 癞子
            joker_count += 1
        elif card[0] == 0:  # 问号
            question_marks.append(card)
        else:  # 普通牌
            normal_cards.append(card)
    
    # 2. 生成所有可能的牌（6-A的四种花色）
    all_possible_cards = [(p, s) for p in range(6, 15) for s in range(4)]
    
    def try_all_replacements(remaining_jokers, current_cards):
        """递归尝试所有可能的癞子替换方案
        Args:
            remaining_jokers: 剩余待替换的癞子数量
            current_cards: 当前已经替换的牌组
        Returns:
            int: 当前替换方案下的最小负分
        """
        # 基础情况：所有癞子都已替换完
        if remaining_jokers == 0:
            combinations = []
            _find_all_combinations(current_cards, [], set(), combinations)
            
            # 计算最小负分
            min_score = float('inf')
            for used_groups in combinations:
                used_cards = set()
                for group in used_groups:
                    used_cards.update(group)
                unused_cards = set(current_cards) - used_cards
                score = sum(_get_card_score(card) for card in unused_cards)
                if score == 0:  # 找到负分为0的组合就直接返回
                    return 0
                min_score = min(min_score, score)
            return min_score
        
        # 递归情况：尝试所有可能的替换
        min_score = float('inf')
        for card in all_possible_cards:
            score = try_all_replacements(remaining_jokers - 1, current_cards + [card])
            if score == 0:  # 找到负分为0的组合就直接返回
                return 0
            min_score = min(min_score, score)
        return min_score
    
    # 3. 开始计算最小负分
    min_score = try_all_replacements(joker_count, normal_cards)
    return min_score if min_score != float('inf') else sum(_get_card_score(card) for card in normal_cards)

def _find_all_combinations(input_cards, current_groups, used_cards, result):
    """找出所有可能的有效牌型组合（同花顺或同点数）
    Args:
        input_cards: 输入的牌组
        current_groups: 当前已找到的组合
        used_cards: 当前已使用的牌
        result: 存储所有找到的组合
    """
    # 把当前组合加入结果
    if current_groups:
        result.append(current_groups[:])
    
    # 找出所有可能的同点数和同花顺组合
    point_groups = _find_point_groups(input_cards, used_cards)
    straight_groups = _find_straight_groups(input_cards, used_cards)
    
    # 尝试添加每个可能的组合
    for group in point_groups + straight_groups:
        if not (set(group) & used_cards):  # 确保没有重复使用的牌
            current_groups.append(group)
            new_used = used_cards | set(group)
            _find_all_combinations(input_cards, current_groups, new_used, result)
            current_groups.pop()

def _find_point_groups(input_cards, used_cards):
    """找出所有可能的同点数组合（3张及以上）
    Args:
        input_cards: 输入的牌组
        used_cards: 已使用的牌
    Returns:
        list: 所有可能的同点数组合列表
    """
    result = []
    # 按点数分组
    point_groups = {}
    for card in input_cards:
        if card not in used_cards:
            point_groups.setdefault(card[0], []).append(card)
    
    # 对每个点数，找出所有可能的组合（3-7张）
    for _, same_cards in point_groups.items():
        for i in range(len(same_cards)):
            for j in range(i + 2, len(same_cards) + 1):
                group = same_cards[i:j]
                if len(group) >= 3:
                    result.append(tuple(sorted(group)))
    return result

def _find_straight_groups(input_cards, used_cards):
    """找出所有可能的同花顺组合（3张及以上）
    Args:
        input_cards: 输入的牌组
        used_cards: 已使用的牌
    Returns:
        list: 所有可能的同花顺组合列表
    """
    result = []
    # 按花色分组
    suit_groups = {}
    for card in input_cards:
        if card not in used_cards:
            suit_groups.setdefault(card[1], []).append(card)
    
    # 对每种花色找顺子
    for _, suited_cards in suit_groups.items():
        suited_cards.sort(key=lambda x: x[0])
        # 对每个可能的起始位置
        for i in range(len(suited_cards)):
            straight = [suited_cards[i]]
            # 尝试构建顺子
            for j in range(i + 1, len(suited_cards)):
                if suited_cards[j][0] == straight[-1][0] + 1:
                    straight.append(suited_cards[j])
                    if len(straight) >= 3:
                        result.append(tuple(straight))
                elif suited_cards[j][0] > straight[-1][0] + 1:
                    break
    return result

def _get_card_score(card):
    """获取单张牌的负分值
    Args:
        card: (点数,花色)元组
    Returns:
        int: 负分值
             问号=0分
             6-10=10分
             J-K=20分
             A=30分
    """
    point = card[0]
    if point == 0:  # 问号
        return 0
    elif 6 <= point <= 10:  # 6-10
        return 10
    elif 11 <= point <= 13:  # J-Q-K
        return 20
    elif point == 14:  # A
        return 30
    return 0
