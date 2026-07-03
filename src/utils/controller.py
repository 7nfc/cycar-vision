import atexit
import os
import pickle
import shutil
import time

import serial
from filelock import FileLock

from src.actions.base_action import BaseAction
from src.utils.common_utils import SingleTonType
from src.utils.logger import logger_instance as log
from src.utils.constant import STM32_NAME
from src.actions import SetServo  

class Controller(metaclass=SingleTonType): #表示该类使用单例模式，确保只有一个Controller
        
    def __init__(self) ->None:
        #获取当前用户的home目录
        home = os.path.expanduser('~')
        #新建临时文件夹 保存控制器的状态（如电机速度、舵机角度），实现多进程间的状态同步。
        self._temp_path = os.path.join(home,'temp','controller')
        if not os.path.exists(self._temp_path):
            os.makedirs(self._temp_path,exist_ok=True)

        #设置序列化文件保存路径，文件锁路径，全局引用计数路径
        self._ser_path = os.path.join(self._temp_path,'controller.pickle') # 保存控制器状态的序列化文件
        self._lock_path = os.path.join(self._temp_path,'controller.lock') # 文件锁路径（用于多进程同步）
        self._count_path = os.path.join(self._temp_path,'controller.count') # 全局引用计数文件（记录使用控制器的进程数）

        #创建文件锁（确保多进程操作时状态一致）
        self._lock = FileLock(self._lock_path)

        # 初始化与 STM32 的串口连接（设备路径、波特率 115200、超时时间 0.01s）
        self._ser = serial.Serial("/dev/ttyACM0",115200,timeout=0.01)

        # 校验值（用于指令完整性检查，固定为 0x3039）
        self._check_val = 0x3039

        # 控制器维护的核心状态（需持久化的信息）
        self.last_modify_time = 0 # 最后一次成功下发指令的时间戳
        self .state = [0,0,0,0,0,0,0x39,0x30] # 电机+舵机的状态（4 个电机速度+2 个舵机角度+校验值）
        self.speed = 0 # 当前小车速度
        self.servo_angle = [0,0] # 当前舵机角度（水平+垂直）

        # 初始化并同步全局状态
        self._set_global_unique()
        
        # 注册程序退出时的清理函数（确保资源释放）
        atexit.register(self._deinit)
    
    def _set_global_unique(self):#确保控制器状态在多进程环境下的一致性
        with self._lock:  # 加锁确保多进程安全
            if not os.path.exists(self._ser_path):
                # 若序列化文件不存在，初始化状态并保存
                self.reset()
                self._save()
            else:
                try:
                    # 从序列化文件加载最新状态
                    self._update()
                except EOFError:
                    # 若文件损坏，重置状态并重新保存
                    self.reset()
                    self._save()
            self._inc_count() # 增加全局引用计数

    #重置电机与舵机状态 通常在程序启动、退出或异常时调用。
    def reset(self):
        self.speed = 0
        self.servo_angle = [100, 60]  # 默认舵机角度
        state = [0, 0, 0, 0] + self.servo_angle + [0x39, 0x30]
        self.send_to_device(state)
    
    #执行动作序列 负责解析并执行动作（单个动作或动作序列），并同步设备状态。
    def execute(self,action):
        with self._lock: # 加锁确保状态同步
            self._update() #从序列化文件更新当前控制器的相关参数

            # 提取动作的属性（如是否强制执行、动作序列、是否更新速度等）
            attr_dict = action.__dict__
            force = attr_dict.get('force',None) # 是否强制执行
            send_time = attr_dict.get('send_time',None)  # 动作下发时间
            action_seq = attr_dict.get('action_seq',None) # 动作序列（复杂动作）
            update_controller_speed = attr_dict.get('update_controller_speed',True) # 是否更新控制器记录的速度
            log.info(f'update_controller_speed:{update_controller_speed}')
            log.info(f'self.speed:{self.speed}')

            # 确保 `SetServo` 能正确更新舵机
            if isinstance(action, SetServo):
                self.servo_angle = action.servo_angle  # 确保直接更新
                log.info(f"Servo angle updated to {self.servo_angle}")
                update_controller_speed = False  # 舵机调整不影响速度
                action.update_servo = True       # 强制更新舵机

            # 动作过滤：若不是强制执行，且动作下发时间早于最后一次执行时间，则丢弃该动作
            if force is None or not force:
                if send_time is not None and isinstance(send_time,float) and self.last_modify_time > send_time:
                    return -1
                
            # 处理动作序列：若为单个动作，包装为列表；若为序列，直接使用
            if action_seq is None and isinstance(action,BaseAction):
                action_seq = [action]

            #执行动作序列
            for action in action_seq:
                # 调用动作的 __call__ 方法，生成设备状态（电机速度+舵机角度）
                state = action(self.speed,self.servo_angle)
                #如果当前动作不需要下发指令至STM32,跳过后续步骤
                if state is None:
                    continue

                state += [0x39,0x30] # 追加校验值
                # 发送指令到 STM32，并获取执行结果和时间戳
                ret,modify_time = self.send_to_device(state)
                log.info(f'action {action.__class__.__name__}execute {ret}')

                # 更新控制器状态
                self.state = state # 记录当前状态
                self.last_modify_time = modify_time # 记录最后执行时间
                # 若需要更新速度，同步动作中的速度到控制器
                if update_controller_speed and action.speed != -1:
                    self.speed = action.speed
                # 若动作包含舵机角度，同步到控制器
                if action.servo_angle != [-1,-1]:
                    self.servo_angle = action.servo_angle
                
            self._save()# 保存更新后的状态到序列化文件
            return 0# 执行成功
            
    def send_to_device(self,state):
        #发送指令到STM32
        start = time.time()
        # 将状态列表编码为字节流（每个数值转为 2 字节小端有符号整数）
        msg = b''.join([num.to_bytes(2,byteorder='little',signed=True)for num in state])

        # 发送指令到 STM32（串口通信）
        try:
            self._ser.write(msg)
        except Exception:
            # 若发送失败，重新初始化串口并重试
            self._ser = serial.Serial("/dev/ttyACM0",115200,timeout=0.01,bytesize=8,stopbits=1,parity='N')
            self._ser.write(msg)
        log.info(f'{state}')

        # 接收 STM32 的反馈（如成功/失败信号）
        try:
            ret = self.recv_from_device().strip().decode()
        except:
            ret = "Invalid data received"
        log.debug(f'{ret}')

        # 若反馈为避障信号，记录警告
        if ret =='FALL':
            log.warn(f'Ultrasonic obstacle avoidance is activated.Please move the car to a safe position.')
        end = time.time()
        log.debug(f'action execute cost:{end-start}s')
        return ret,time.time() # 返回反馈结果和执行时间戳
            
    def recv_from_device(self):
        return self._ser.readline()  # 从串口读取一行反馈数据
            
    #从序列化文件中获取参数并更新当前控制器的相关参数
    def _update(self):
        # 从序列化文件加载状态（反序列化）
        with open(self._ser_path,'rb')as f:
            attr_dict = pickle.load(f)
            for k,v in attr_dict.items():
                setattr(self,k,v)  # 更新控制器的属性

    #保存当前控制器的相关参数至序列化文件
    def _save(self):
        with open(self._ser_path,'wb')as f:
            pickle.dump(self.get_public_var(),f)# 只保存公共属性

    def _inc_count(self):
        # 增加引用计数：新进程使用控制器时调用
        count = 1  # 文件不存在或为空时的默认值
        if os.path.exists(self._count_path):
            try:
                with open(self._count_path, 'r') as f:
                    content = f.readline().strip()
                    if content:  # 仅当内容不为空时才转换为整数
                        count = int(content) + 1
            except (ValueError, IOError):
                pass  # 若文件损坏或无法读取，则回退到默认计数1

        with open(self._count_path, 'w') as f:
            f.write(str(count))


    def _dec_count(self):
        # 减少引用计数：进程退出时调用
        count=0
        if os.path.exists(self._count_path):
            with open(self._count_path,'r')as f:
                count = int(f.readline())-1

            if count >0:
                with open(self._count_path,'w')as f:
                    f.write(str(count))
                    return False # 仍有进程使用，不清理资源
            else:
                return True # 计数为0，可清理资源
        else:
            raise RuntimeError('Cannot find the processes count file.')
                
    #过滤出需要保存的参数
    def get_public_var(self):
        dic = self.__dict__
        # 过滤出公共属性（不含私有属性，即不以_开头的属性）
        public_var ={key:value for key,value in dic.items() if not key.startswith('_')}
        return public_var
            
    #在__del__方法被调用前执行的去初始化方法
    def _deinit(self):
        with self._lock:
            finalize = self._dec_count() # 减少引用计数
        # 若所有进程都已退出（计数为0），清理资源
        if finalize:
            self.reset()# 发送停止指令，确保设备安全
            shutil.rmtree(self._temp_path)# 删除临时文件夹（含序列化文件、锁文件等）