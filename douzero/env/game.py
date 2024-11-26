from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener

EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                    8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q',
                    13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}


class GameEnv(object):

    def __init__(self, players, recharge_positions):

        self.card_play_action_seq = []
        self.game_over = False
        self.acting_player_position = None
        self.player_utility_dict = None
        self.players = players

        self.last_move_dict = {'first': [],
                              'first_up': [],
                              'first_down': [],
                              'first_across': []}

        self.played_cards = {'first': [],
                            'first_up': [],
                            'first_down': [],
                            'first_across': []}

        self.num_scores = {'landlord': 0,
                           'farmer': 0}
        
        self.info_sets = {'first': InfoSet('first'),
                         'first_up': InfoSet('first_up'),
                         'first_down': InfoSet('first_down'),
                         'first_across': InfoSet('first_across')}

        # 添加豆子相关属性
        self.min_beans = 150000  # 最低豆子数(15万)
        self.max_beans = 1000000000  # 最高豆子数(10亿) 
        self.entry_fee = 60000  # 入场费(6万)
        
        # 随机初始化每个玩家的豆子数量(15万到10亿之间)
        self.beans = {
            pos: random.randint(self.min_beans, self.max_beans)
            for pos in ['first', 'first_up', 'first_across', 'first_down']
        }
        
        self.active_players = ['first', 'first_up', 'first_across', 'first_down']
        
        # 扣除入场费
        for pos in self.active_players:
            self.beans[pos] -= self.entry_fee

        # 接收从外部传入的可充值位置列表
        self.can_recharge = {
            pos: (pos in recharge_positions)
            for pos in ['first', 'first_up', 'first_across', 'first_down']
        }
        self.recharge_probability = 0.7  # 有资格的玩家充值概率

        # 添加自动胡牌相关属性
        self.auto_hu_players = set()  # 记录已经胡过牌的玩家
        
        # 添加换牌方向的定义
        self.EXCHANGE_UP = 'up'      # 和上家换
        self.EXCHANGE_ACROSS = 'across'  # 和对家换
        self.EXCHANGE_DOWN = 'down'   # 和下家换

        # 添加补胡相关属性
        self.bu_hu_state = False  # 是否处于补胡状态
        self.bu_hu_starter = None  # 记录补胡开始时的玩家位置
        
        # 添加每个玩家的胡牌序列
        self.hu_sequences = {
            'first': [],
            'first_up': [],
            'first_down': [],
            'first_across': []
        }

    def calculate_hu_value(self, position, card):
        """计算胡某张牌的价值（赢豆数/硬胡系数）"""
        hand_cards = self.info_sets[position].player_hand_cards
        has_joker = any(c[0] == 0 and c[1] == -1 for c in hand_cards)
        hard_hu_factor = 1 if has_joker else 2
        beans = calculate_beans(self, position, card, False, False)
        total_win = sum(v for v in beans.values() if v > 0)
        return total_win / hard_hu_factor
        
    def handle_auto_hu(self, position, is_bu_hu=False):
        """处理自动胡牌的玩家行动
        Args:
            position: 玩家位置
            is_bu_hu: 是否是补胡状态
        """
        # 1. 检查公共牌区是否有能胡的牌
        best_value = -1
        best_card = None
        best_index = -1
        
        for i, card in enumerate(self.public_cards):
            if card is None:
                continue
            if self.can_hu(position, card):
                value = self.calculate_hu_value(position, card)
                if value >= best_value:
                    best_value = value
                    best_card = card
                    best_index = i
                    
        if best_card:
            self.hu_sequences[position].append(best_card)
            self.hu_card(position, best_card, card_index=best_index, is_bu_hu=is_bu_hu)
            return
            
        # 如果是补胡状态，到这里就结束了（不需要摸牌）
        if is_bu_hu:
            return
            
        # 2. 摸牌
        card = self.draw_card()
        if not card:
            return  # 牌堆空了
            
        if self.can_hu(position, card):
            self.hu_sequences[position].append(card)
            self.hu_card(position, card)
        elif card[0] == -1:  # 问号牌的点数是-1
            # 从牌堆顶部4张牌中选择价值最高的
            values = []
            for i, possible_card in enumerate(self.remaining_cards[:4]):
                if self.can_hu(position, possible_card):
                    values.append((i, possible_card, 
                                 self.calculate_hu_value(position, possible_card)))
                else:
                    values.append((i, possible_card, -1))
            
            # 选择价值最高的牌的索引
            best_index, best_card, best_value = max(values, key=lambda x: x[2])
            
            # 选择这张牌并从牌堆中移除
            self.select_from_top_four(position, best_index)
            
            # 如果可以胡，就胡掉
            if best_value > -1:
                self.hu_sequences[position].append(best_card)
                self.hu_card(position, best_card)
            else:
                # 否则打出去
                self.play_card(position, best_card)
        else:
            # 直接打出
            self.play_card(position, card)

    def card_play_init(self, card_play_data):
        self.info_sets['first'].player_hand_cards = \
            card_play_data['first'][:7]
        self.info_sets['first_up'].player_hand_cards = \
            card_play_data['first_up'][:7]
        self.info_sets['first_down'].player_hand_cards = \
            card_play_data['first_down'][:7]
        self.info_sets['first_across'].player_hand_cards = \
            card_play_data['first_across'][:7]
        
        
        # 执行换牌
        self.exchange_cards()
        
        # 发一张牌到公共牌区最左边
        self.public_cards = [None] * 4
        self.public_cards[0] = card_play_data['first_public_card']
        
        # ... 原有代码保持不变 ...
        self.get_acting_player_position()
        self.game_infoset = self.get_infoset()

        
    def exchange_cards(self):
        """执行换牌操作"""
        # 1. 随机决定换牌方向
        exchange_direction = random.choice([
            self.EXCHANGE_UP,
            self.EXCHANGE_ACROSS,
            self.EXCHANGE_DOWN
        ])
        
        # 2. 每个玩家选择两张牌换出去
        exchange_cards = {}
        for position in ['first', 'first_up', 'first_across', 'first_down']:
            hand_cards = self.info_sets[position].player_hand_cards
            cards_to_exchange = random.sample(hand_cards, 2)
            exchange_cards[position] = cards_to_exchange
            for card in cards_to_exchange:
                hand_cards.remove(card)
        
        # 3. 执行换牌
        for position in ['first', 'first_up', 'first_across', 'first_down']:
            # 使用get_relative_position获取目标位置
            # 比如 position 是 'first'，exchange_direction 是 'up'
            # 那么 target_position 就会是 'first_up'
            target_position = self.get_relative_position(position, exchange_direction)
            self.info_sets[target_position].player_hand_cards.extend(
                exchange_cards[position]
            )

    def game_done(self):
        if len(self.info_sets['landlord'].player_hand_cards) == 0 or \
                len(self.info_sets['landlord_up'].player_hand_cards) == 0 or \
                len(self.info_sets['landlord_down'].player_hand_cards) == 0:
            # if one of the three players discards his hand,
            # then game is over.
            self.compute_player_utility()
            self.update_num_wins_scores()

            self.game_over = True

    def compute_player_utility(self):

        if len(self.info_sets['landlord'].player_hand_cards) == 0:
            self.player_utility_dict = {'landlord': 2,
                                        'farmer': -1}
        else:
            self.player_utility_dict = {'landlord': -2,
                                        'farmer': 1}

    def update_num_wins_scores(self):
        for pos, utility in self.player_utility_dict.items():
            base_score = 2 if pos == 'landlord' else 1
            if utility > 0:
                self.num_wins[pos] += 1
                self.winner = pos
                self.num_scores[pos] += base_score * (2 ** self.bomb_num)
            else:
                self.num_scores[pos] -= base_score * (2 ** self.bomb_num)


    def step(self):
        """游戏的一步"""
        current_player = self.acting_player_position
        
        # 检查是否需要进入补胡状态
        if len(self.remaining_cards) == 0 and not self.bu_hu_state:
            self.bu_hu_state = True
            self.bu_hu_starter = current_player
            
        # 补胡状态的处理
        if self.bu_hu_state:
            self.handle_auto_hu(current_player, is_bu_hu=True)
            
            # 找下一个活跃玩家
            next_player = self.get_relative_position(current_player, self.EXCHANGE_DOWN)
            while next_player not in self.active_players:
                next_player = self.get_relative_position(next_player, self.EXCHANGE_DOWN)
            self.acting_player_position = next_player
            
            # 如果回到了开始补胡的玩家，结束补胡
            if next_player == self.bu_hu_starter:
                self.bu_hu_state = False
                self.game_over = True
            return
            
        # 正常游戏流程
        if current_player in self.auto_hu_players:
            self.handle_auto_hu(current_player)
        else:
            # 原有的step逻辑
            action = self.players[current_player].act(self.game_infoset)
            if action[1] == 'hu':
                self.auto_hu_players.add(current_player)

    def bu_hu_step(self):
        """处理补胡阶段"""
        # 直接让当前玩家尝试胡牌
        self.handle_auto_hu(self.acting_player_position)
        
        # 找下一个活跃玩家
        next_player = self.get_relative_position(self.acting_player_position, self.EXCHANGE_DOWN)
        while next_player not in self.active_players:
            next_player = self.get_relative_position(next_player, self.EXCHANGE_DOWN)
        self.acting_player_position = next_player
        
        # 如果回到了开始补胡的玩家，结束补胡
        if self.acting_player_position == self.bu_hu_starter:
            self.bu_hu_state = False
            self.game_over = True
                # ... 原有代码继续 ...

    def bu_hu_step(self):
        """处理补胡阶段"""
        # 直接让当前玩家尝试胡牌（传入is_bu_hu=True）
        self.handle_auto_hu(self.acting_player_position, is_bu_hu=True)
        
        # 找下一个活跃玩家
        next_player = self.get_relative_position(self.acting_player_position, self.EXCHANGE_DOWN)
        while next_player not in self.active_players:
            next_player = self.get_relative_position(next_player, self.EXCHANGE_DOWN)
        self.acting_player_position = next_player
        
        # 如果回到了开始补胡的玩家，结束补胡
        if self.acting_player_position == self.bu_hu_starter:
            self.bu_hu_state = False
            self.game_over = True


    def get_relative_position(self, position, relation):
        """获取玩家的相对位置
        Args:
            position: 玩家当前位置 ('first', 'first_up', 'first_across', 'first_down')
            relation: 相对关系 (self.EXCHANGE_UP/ACROSS/DOWN)
        Returns:
            相对位置的玩家
        """
        position_order = ['first', 'first_up', 'first_across', 'first_down']
        current_index = position_order.index(position)
        
        if relation == self.EXCHANGE_UP:  # 上家
            return position_order[(current_index - 1) % 4]
        elif relation == self.EXCHANGE_ACROSS:  # 对家
            return position_order[(current_index + 2) % 4]
        elif relation == self.EXCHANGE_DOWN:  # 下家
            return position_order[(current_index + 1) % 4]
        else:
            raise ValueError(f"Unknown relation: {relation}")

    def get_acting_player_position(self):
        """获取当前出牌玩家位置，并更新到下一个玩家
        在游戏流程中被调用，用于：
        1. card_play_init 初始化时确定第一个出牌玩家
        2. 每次行动后更新到下一个玩家
        3. get_infoset 获取当前玩家信息
        Returns:
            当前玩家位置 ('first', 'first_up', 'first_across', 'first_down')
        """
        if self.acting_player_position is None:
            self.acting_player_position = 'first'
        else:
            # 使用相对位置函数获取下家，使用类定义的常量
            self.acting_player_position = self.get_relative_position(
                self.acting_player_position, 
                self.EXCHANGE_DOWN
            )
        
        return self.acting_player_position


    def update_acting_player_hand_cards(self, action):
        if action != []:
            for card in action:
                self.info_sets[
                    self.acting_player_position].player_hand_cards.remove(card)
            self.info_sets[self.acting_player_position].player_hand_cards.sort()



    def reset(self):
        self.card_play_action_seq = []

        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.last_move_dict = {'first': [],
                               'first_up': [],
                               'first_down': [],
                               'first_across': []}

        self.played_cards = {'first': [],
                             'first_up': [],
                             'first_down': [],
                             'first_across': []}

        self.last_move = []
        self.last_two_moves = []

        self.info_sets = {'first': InfoSet('first'),
                         'first_up': InfoSet('first_up'),
                         'first_down': InfoSet('first_down'),
                         'first_across': InfoSet('first_across')}

        # 重置胡牌序列
        self.hu_sequences = {
            'first': [],
            'first_up': [],
            'first_down': [],
            'first_across': []
        }



    def get_infoset(self):


        self.info_sets[
            self.acting_player_position].legal_actions = \
            self.get_legal_card_play_actions()

        self.info_sets[
            self.acting_player_position].bomb_num = self.bomb_num

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()

        self.info_sets[
            self.acting_player_position].last_two_moves = self.get_last_two_moves()

        self.info_sets[
            self.acting_player_position].last_move_dict = self.last_move_dict

        self.info_sets[self.acting_player_position].num_cards_left_dict = \
            {pos: len(self.info_sets[pos].player_hand_cards)
             for pos in ['first', 'first_up', 'first_down', 'first_across']}

        self.info_sets[self.acting_player_position].other_hand_cards = []
        for pos in ['first', 'first_up', 'first_down', 'first_across']:
            if pos != self.acting_player_position:
                self.info_sets[
                    self.acting_player_position].other_hand_cards += \
                    self.info_sets[pos].player_hand_cards

        self.info_sets[self.acting_player_position].played_cards = \
            self.played_cards

        self.info_sets[self.acting_player_position].card_play_action_seq = \
            self.card_play_action_seq

        self.info_sets[
            self.acting_player_position].all_handcards = \
            {pos: self.info_sets[pos].player_hand_cards
             for pos in ['first', 'first_up', 'first_down', 'first_across']}

        return deepcopy(self.info_sets[self.acting_player_position])

    def draw_card(self, position):
        """从牌堆摸一张牌
        1. 从牌堆顶部摸一张牌加入手牌
        2. 公共牌区的牌右移一位
        3. 最右边的牌进入废牌区
        """
        # 1. 摸牌
        card = self.remaining_cards[0]  # 获取牌堆顶部的牌
        self.remaining_cards = self.remaining_cards[1:]  # 移除牌堆顶部的牌
        self.info_sets[position].player_hand_cards.append(card)  # 将摸到的牌加入玩家手牌

        # 2. 公共牌区右移
        # 保存最右边的牌（如果有的话）
        rightmost_card = self.public_cards[3]
        # 右移操作
        for i in range(3, 0, -1):  # 从右往左移动
            self.public_cards[i] = self.public_cards[i-1]
        # 最左边设为空
        self.public_cards[0] = None

        # 3. 最右边的牌进入废牌区（如果有的话）
        if rightmost_card is not None:
            self.discard_cards.append(rightmost_card)

    def eat_card(self, position, card_index):
        """从公共牌区吃牌
        Args:
            position: 玩家位置
            card_index: 要吃的牌在公共牌区的位置(0-3)
        
        1. 将指定位置的牌加入手牌
        2. 该位置左边的牌右移一位
        3. 该位置右边的牌保持不动
        """
        # 1. 将指定位置的牌加入手牌
        eaten_card = self.public_cards[card_index]  # 获取指定位置的牌
        self.info_sets[position].player_hand_cards.append(eaten_card)  # 加入手牌

        # 2. 该位置左边的牌右移
        for i in range(card_index, 0, -1):  # 从被吃牌的位置向左遍历
            self.public_cards[i] = self.public_cards[i-1]
        # 最左边设为空
        self.public_cards[0] = None

        # 3. 该位置右边的牌保持不动
        # (不需要额外操作)

    def hu_card(self, position, card, card_index=None, is_bu_hu=False):
        """胡牌
        Args:
            position: 玩家位置
            card: 要胡的牌
            card_index: 胡的牌在公共牌区的位置(0-3)，补胡时需要
            is_bu_hu: 是否是补胡状态
        """
        # 将玩家加入自动胡牌集合
        self.auto_hu_players.add(position)
        
        if is_bu_hu and card_index is not None:
            # 补胡时，和吃牌一样：左边的牌右移，右边的牌不动
            for i in range(card_index, 0, -1):
                self.public_cards[i] = self.public_cards[i-1]
            self.public_cards[0] = None
        elif len(self.remaining_cards) > 0:
            # 非补胡时，摸新牌到最左边
            self.public_cards[0] = self.remaining_cards[0]
            self.remaining_cards = self.remaining_cards[1:]
        
        # 检查是否游戏结束
        if len(self.auto_hu_players) == len(self.active_players):
            self.game_over = True

    def play_card(self, position, card):
        """打出一张牌
        Args:
            position: 玩家位置
            card: 要打出的牌
            
        1. 从玩家手牌中移除这张牌
        2. 将这张牌放到公共牌区最左边
        3. 如果是问号，返回True表示需要进行问号的选牌
        """
        # 1. 从玩家手牌中移除打出的牌
        self.info_sets[position].player_hand_cards.remove(card)
        
        # 2. 将打出的牌放到公共牌区最左边
        self.public_cards[0] = card
        
        # 3. 如果是问号，返回True
        return card == (1, -1)  # 问号的表示是(1, -1)
            
    def select_from_top_four(self, position, card_choice):
    """     
   在游戏流程中：
    result = env.play_card(position, card)
    if result == "question_mark":
        # 玩家选择一张牌（0-3）
        chosen_card = env.handle_question_mark(position, card_choice)
        # 玩家选择胡牌或出牌
        if want_to_hu:
            env.hu_card(position, chosen_card)
        else:
            env.play_card(position, chosen_card) 
        """
        """问号的选牌流程：从牌堆顶部4张牌中选择一张
        Args:
            position: 玩家位置
            card_choice: 选择的牌的索引(0-3)
        """
        # 获取牌堆顶部4张牌，选择一张加入手牌
        chosen_card = self.remaining_cards[card_choice]
        self.info_sets[position].player_hand_cards.append(chosen_card)
        
        # 从牌堆中移除被选中的牌，其他牌保持原顺序
        self.remaining_cards = (self.remaining_cards[:card_choice] + 
                              self.remaining_cards[card_choice + 1:])

    def get_relative_position(self, position, relation):
        """获取玩家的相对位置
        Args:
            position: 玩家当前位置 ('first', 'first_up', 'first_across', 'first_down')
            relation: 相对关系 ('up'-上家, 'across'-对家, 'down'-下家)
        Returns:
            相对位置的玩家
        """
        position_order = ['first', 'first_up', 'first_across', 'first_down']
        current_index = position_order.index(position)
        
        if relation == 'up':  # 上家
            return position_order[(current_index - 1) % 4]
        elif relation == 'across':  # 对家
            return position_order[(current_index + 2) % 4]
        elif relation == 'down':  # 下家
            return position_order[(current_index + 1) % 4]
        else:
            raise ValueError(f"Unknown relation: {relation}")

class InfoSet(object):
    """
    The game state is described as infoset, which
    includes all the information in the current situation,
    such as the hand cards of the three players, the
    historical moves, etc.
    """
    def __init__(self, player_position):
        # The player position, i.e., landlord, landlord_down, or landlord_up
        self.player_position = player_position
        # The hand cands of the current player. A list.
        self.player_hand_cards = None
        # The number of cards left for each player. It is a dict with str-->int 
        self.num_cards_left_dict = None
        # The historical moves. It is a list of list
        self.card_play_action_seq = None
        # The union of the hand cards of the other two players for the current player 
        self.other_hand_cards = None
        # The legal actions for the current move. It is a list of list
        self.legal_actions = None
        # The most recent valid move
        self.last_move = None
        # The most recent two moves
        self.last_two_moves = None
        # The last moves for all the postions
        self.last_move_dict = None
        # The played cands so far. It is a list.
        self.played_cards = None
        # The hand cards of all the players. It is a dict. 
        self.all_handcards = None
        # The number of bombs played so far
        self.bomb_num = None

        self.bomb_num = None

        # The number of bombs played so far
        self.bomb_num = None
