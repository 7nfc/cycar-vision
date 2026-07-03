# -*- coding:UTF-8 -*-
from src.actions.base_action import Advance,Stop,BackUp,Sleep
from src.utils import Controller

class Advance_Backup():
    def __init__(self):
        self.force = True
        self.update_controller_speed = True
        self.action_seq = [
            Advance(speed=30),    # 前进
            Sleep(sleep_time=8),       
            Stop(),
            Sleep(sleep_time=1),
            BackUp(speed=30),     # 后退速度与前进一致
            Sleep(sleep_time=6),
            Stop()
        ]

ctrl = Controller()
ctrl.execute(Advance_Backup())
