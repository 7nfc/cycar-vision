from abc import ABC
from src.actions.base_action import Advance,Sleep
from src.actions.base_action import SpinAntiClockwise,Stop,SpinClockwise,CustomAction,ShiftLeft,TurnRight

class ComplexAction(ABC):
    def __init__(self):
        self.force = True #默认强制执行
        self.update_controller_speed = False  # 默认不更新控制器记录的速度
        self.action_seq = []  # 动作序列
        self.send_time = None  # 动作发送时间

class Start(ComplexAction):
    def __init__(self):
        super().__init__()
        self.update_controller_speed = True  # 更新控制器记录的速度
        # 定义动作序列：先以35速度前进0.2秒，然后降速到25
        self.action_seq = [
            Advance(speed=35),
            Sleep(sleep_time=0.1),
            Advance(speed=25)
        ]
    
class TurnLeftInPlace(ComplexAction):
    def __init__(self):
        super().__init__()
        self.action_seq = [
            Advance(speed=25),            # 向前移动3.5秒
            Sleep(sleep_time=3),
            SpinAntiClockwise(speed=20),  # 逆时针旋转4秒
            Sleep(sleep_time=4),
            Advance(speed=25)             # 转向后自动直行
        ]

class TurnRightInPlace(ComplexAction):
    def __init__(self):
        super().__init__()
        self.action_seq = [
            Advance(speed=25),        # 向前移动2.5秒
            Sleep(sleep_time=3),
            SpinClockwise(speed=20),  # 顺时针旋转2.6秒
            Sleep(sleep_time=4),
            Advance(speed=25)         # 转向后自动直行
        ]

class TurnAround(ComplexAction):
    def __init__(self):
        super().__init__()
        self.action_seq = [
            Advance(speed=25),  # 向前移动3.5秒
            Sleep(sleep_time=3),
            SpinAntiClockwise(speed=20),  # 逆时针旋转90度
            Sleep(sleep_time=4),
            Advance(speed=25),  # 向前移动一点
            Sleep(sleep_time=4.3),
            SpinAntiClockwise(speed=20),  # 逆时针旋转90度
            Sleep(sleep_time=4),
            Advance(speed=25),  # 转向后自动直行
        ]