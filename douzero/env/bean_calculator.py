from douzero.env.score_detector import get_negative_score
from douzero.env.hu_pattern_detector import get_hu_multiplier

def calculate_beans(game_env, position, card, is_self_draw, is_first_round):
    """计算胡牌时的豆子变化"""
    # 1. 获取基础信息
    hand_cards = game_env.info_sets[position].player_hand_cards
    gold_cards = game_env.gold_cards
    base_score = 450  # 底分
    
    # 2. 计算各种系数
    # 2.1 硬胡系数：检查手牌中是否有癞子
    has_joker = any(card[0] == 0 and card[1] == -1 for card in hand_cards)
    hard_hu_factor = 1 if has_joker else 2
    
    # 2.2 金牌系数：计算手牌中金牌的数量
    gold_count = sum(1 for card in hand_cards if card[0] in gold_cards)
    gold_factor = max(1, gold_count)
    
    # 2.3 自摸系数
    self_draw_factor = 3 if is_self_draw else 1
    
    # 2.4 海底系数：检查牌堆是否只剩1张
    is_last_card = len(game_env.remaining_cards) == 1
    last_card_factor = 4 if is_last_card and is_self_draw else 1
    
    # 2.5 地胡系数
    first_round_factor = 16 if is_first_round else 1
    
    # 3. 计算分数
    # 3.1 计算胡牌玩家的正分
    hu_cards = hand_cards + [card]
    hu_multiplier, _ = get_hu_multiplier(hu_cards)
    
    # 3.2 计算其他玩家的负分
    other_positions = [pos for pos in ['down', 'right', 'up', 'left'] 
                      if pos != position]
    result = {}
    
    # 计算基础赢豆上限(系统600万和玩家豆子数的较小值)
    base_limit = min(game_env.beans[position], 6000000)
    
    # 计算基础豆子(不含硬胡)
    base_beans = min(base_limit, 
                    base_score * hu_multiplier * gold_factor * 
                    self_draw_factor * last_card_factor * first_round_factor)
    
    # 加上硬胡倍数
    total_beans = base_beans * hard_hu_factor
    
    # 计算每个玩家应输的豆子
    for pos in other_positions:
        # 输家豆子不足则全输
        actual_lose = min(game_env.beans[pos], total_beans)
        result[pos] = -actual_lose
        result[position] = result.get(position, 0) + actual_lose
    
    return result