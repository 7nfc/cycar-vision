from abc import ABC,abstractmethod
from ctypes import c_bool
from multiprocessing import shared_memory,Value
import time
from src.utils import Controller

class BaseScene(ABC):
    def __init__(self,memory_name,camera_info,msg_queue):
        max_retries = 3
        retry_delay = 0.5
        self.pause_sign = Value(c_bool,False) #暂停标志
        self.stop_sign = Value(c_bool,False) #停止标志
        self.ctrl = Controller() #控制器实例
        self.msg_queue = msg_queue #消息队列
        self.broadcaster = shared_memory.SharedMemory(name=memory_name) #共享内存
        self.camera_info = camera_info #摄像头信息
        self.height = self.camera_info.get('height',720) #图像高度
        self.width = self.camera_info.get('width',1280) #图像宽度
        self.fps = self.camera_info.get('fps',30) #帧率

        for attempt in range(max_retries):
            try:
                # 移除路径前的斜杠
                if memory_name.startswith('/'):
                    memory_name = memory_name[1:]
                    
                self.broadcaster = shared_memory.SharedMemory(name=memory_name)
                break
            except FileNotFoundError as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"无法访问共享内存 {memory_name}") from e
                time.sleep(retry_delay)
            except Exception as e:
                raise RuntimeError(f"共享内存初始化失败: {str(e)}") from e
    
    @abstractmethod
    def init_state(self):
        pass

    @abstractmethod
    def loop(self):
        pass