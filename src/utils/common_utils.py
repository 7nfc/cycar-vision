import threading
import os
import sys
import tty
import termios

class SingleTonType(type):
    _instance_lock = threading.Lock()# 线程锁，确保多线程安全

    def __call__(cls, *args, **kwargs):
        # 检查类是否已创建实例
        if not hasattr(cls,'_instance'):
            # 加锁，防止多线程同时创建实例
            with SingleTonType._instance_lock:
                # 二次检查（避免锁释放后重复创建）第一次检查避免不必要的加锁，第二次检查确保锁内只有一个实例被创建。
                if not hasattr(cls,'_instance'):
                    # 调用父类的__call__方法创建实例
                    cls._instance = super(SingleTonType,cls).__call__(*args,**kwargs)
        # 返回唯一实例
        return cls._instance

def getKey():
    # 保存终端原始设置
    old_settings = termios.tcgetattr(sys.stdin)
    # 设置终端为cbreak模式（无缓冲，无需回车即可读取输入）
    tty.setcbreak(sys.stdin.fileno())
    try:
        while True:
            # 读取最多3个字节的输入（处理特殊按键，如方向键）
            b = os.read(sys.stdin.fileno(),3).decode()
            # 解析按键：特殊按键（如方向键）通常是3字节，普通按键是1字节
            if len(b) == 3:
                # 取第3个字节作为键值（特殊按键的标识）
                k =ord(b[2])
            else:
                # 普通按键直接取ASCII值
                k = ord(b)
            # 按键映射：将ASCII值/特殊键值映射为可读字符串
            key_mapping = {
                127:'backspace',
                10:'return',
                32:'space',
                9:'tab',
                27:'esc',
                65:'up',
                66:'down',
                67:'right',
                68:'left'
            }
            # 返回映射后的键名，若未在映射表中，则返回字符本身（如'a'、'w'等）
            return key_mapping.get(k,chr(k))
        
    except TypeError:
        pass # 忽略类型错误
    finally:
        # 恢复终端原始设置（无论是否出错，确保终端正常）
        termios.tcsetattr(sys.stdin,termios.TCSADRAIN,old_settings)
        sys.stdout.flush() # 刷新输出缓冲区