import torch
import numpy as np

from douzero.env.env import get_obs

def _load_model(position, model_path):
    from douzero.dmc.models import model_dict
    model = model_dict[position]()
    model_state_dict = model.state_dict()
    if torch.cuda.is_available():
        pretrained = torch.load(model_path, map_location='cuda:0')
    else:
        pretrained = torch.load(model_path, map_location='cpu')
    pretrained = {k: v for k, v in pretrained.items() if k in model_state_dict}
    model_state_dict.update(pretrained)
    model.load_state_dict(model_state_dict)
    if torch.cuda.is_available():
        model.cuda()
    model.eval()
    return model

class DeepAgent:

    def __init__(self, position, model_path):
        self.model = _load_model(position, model_path)
        self.position = position
        
        # 随机分队（在创建agents时完成）
        self.team = None  # 'team1' or 'team2'
        self.teammates = []  # 队友的位置列表

    def act(self, infoset):
        if len(infoset.legal_actions) == 1:
            return infoset.legal_actions[0]

        # 获取队友的信息（如果有）
        team_info = self.get_team_info(infoset)

        obs = get_obs(infoset) 

        z_batch = torch.from_numpy(obs['z_batch']).float()
        x_batch = torch.from_numpy(obs['x_batch']).float()
        if torch.cuda.is_available():
            z_batch, x_batch = z_batch.cuda(), x_batch.cuda()
        y_pred = self.model.forward(z_batch, x_batch, return_value=True)['values']
        y_pred = y_pred.detach().cpu().numpy()

        best_action_index = np.argmax(y_pred, axis=0)[0]
        best_action = infoset.legal_actions[best_action_index]

        return best_action
        
    def get_team_info(self, infoset):
        """获取队友的信息"""
        if not self.teammates:
            return None
            
        team_info = {}
        for teammate in self.teammates:
            team_info[teammate] = {
                'hand_cards': infoset.all_handcards[teammate],
                # 其他需要共享的信息...
            }
        return team_info
