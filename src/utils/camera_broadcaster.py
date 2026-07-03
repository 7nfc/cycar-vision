import cv2
import numpy as np
from multiprocessing import shared_memory, Value
from ctypes import Array, c_bool, c_char
import logging
import time
import os

class CameraBroadcaster:
    def __init__(self, camera_info):
        """
        初始化摄像头广播器。
        
        参数:
            camera_info (dict): 包含摄像头配置的字典，键为 'height', 'width', 'fps'。
        """
        self.height = camera_info.get('height', 720)
        self.width = camera_info.get('width', 1280)
        self.fps = camera_info.get('fps', 60)
        self.stop_sign = Value(c_bool, False)  # 进程间共享的停止标志
        self.frame = None                      # 共享内存对象
        self.cap = None                        # OpenCV 摄像头对象
        self.memory_name = None
        self.log = logging.getLogger('CameraBroadcaster')
        self.log.info("CameraBroadcaster已初始化")


    def run(self):
        """
        主运行循环：捕获摄像头帧并写入共享内存。
        """
        try:
            # 1. 创建共享内存
            self._init_shared_memory()
            
            # 2. 初始化摄像头
            self._init_camera()
            
            # 3. 主循环：捕获帧并写入共享内存
            self._capture_loop()
            
        except Exception as e:
            self.log.error(f"运行时发生错误: {str(e)}", exc_info=True)
        finally:
            self._cleanup()  # 确保资源释放

    def _init_shared_memory(self):
        """初始化共享内存"""
        try:
            # 使用固定名称并确保清理旧内存
            shm_name = 'cycar_camera_frame'  # 使用固定名称
            try:
                existing_shm = shared_memory.SharedMemory(name=shm_name, create=False)
                existing_shm.close()
                existing_shm.unlink()
                self.log.info(f"清理了已存在的共享内存: {shm_name}")
            except FileNotFoundError:
                pass

            # 创建新的共享内存
            self.frame = shared_memory.SharedMemory(
                name=shm_name,  # 使用固定名称
                create=True,
                size=np.zeros((self.height, self.width, 3), dtype=np.uint8).nbytes
            )
            self.memory_name = self.frame.name
            self.log.info(f"共享内存已创建: {self.memory_name}")
        except Exception as e:
            self.log.error(f"共享内存初始化失败: {str(e)}")
            raise

    def _init_camera(self):
        """初始化摄像头设备"""
        max_retries = 5  # 增加重试次数
        for attempt in range(max_retries):
            try:
                self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # 直接使用索引0
                if not self.cap.isOpened():
                    raise RuntimeError("无法打开默认摄像头设备")
                    
                # 设置摄像头参数
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.log.info("摄像头初始化成功")
                return
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log.error("摄像头初始化彻底失败")
                    raise
                self.log.warning(f"摄像头初始化失败，尝试 {attempt + 1}/{max_retries}...")
                time.sleep(1)
    
    def _hard_reset_camera(self):
        """尝试硬件复位摄像头（需要sudo权限）"""
        try:
            os.system("sudo rmmod uvcvideo && sudo modprobe uvcvideo")
            self.log.info("已尝试硬件复位摄像头")
        except Exception as e:
            self.log.warning("硬件复位摄像头失败")

    def _capture_loop(self):
        """主捕获循环"""
        sender = np.ndarray(
            (self.height, self.width, 3), 
            dtype=np.uint8, 
            buffer=self.frame.buf
        )
        
        while not self.stop_sign.value:
            ret, frame = self.cap.read()
            if not ret:
                self.log.error("摄像头读取失败，尝试重新初始化...")
                self._reinit_camera()
                continue
            
            # 调整帧大小（确保与共享内存尺寸匹配）
            if frame.shape[0] != self.height or frame.shape[1] != self.width:
                frame = cv2.resize(frame, (self.width, self.height))
            
            # 写入共享内存
            sender[:] = frame[:]
            self.log.debug("帧已更新到共享内存")

    def _reinit_camera(self):
        """重新初始化摄像头"""
        if self.cap:
            self.cap.release()
        self._init_camera()
        time.sleep(0.5)  # 等待摄像头稳定

    def _cleanup(self):
        """清理资源。"""
        if hasattr(self, 'log'):
            self.log.info("正在清理资源...")
        
        # 关闭摄像头（如果存在）
        if hasattr(self, 'cap') and self.cap is not None:
            if self.cap.isOpened():
                self.cap.release()
            self.cap = None
        
        # 关闭共享内存（如果存在）
        if hasattr(self, 'frame') and self.frame is not None:
            try:
                self.frame.close()
                try:
                    self.frame.unlink()
                except FileNotFoundError:
                    pass
            except Exception as e:
                if hasattr(self, 'log'):
                    self.log.error(f"关闭共享内存时出错: {str(e)}")
            finally:
                self.frame = None
                self.memory_name = None
        
        if hasattr(self, 'log'):
            self.log.info("资源清理完成")

    def __del__(self):
        """作为最后手段的析构函数。"""
        self._cleanup()