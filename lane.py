import os
import sys
import time
import signal
import atexit
from multiprocessing import Process, Queue, shared_memory
from src.scenes import LF_threshold
from src.utils import getKey, log, CameraBroadcaster, CAMERA_INFO, Controller
from src.actions import Stop

# 全局清理标志
_cleanup_done = False

def cleanup_resources(camera_process=None, task_process=None, camera=None):
    """统一的资源清理函数"""
    global _cleanup_done
    if _cleanup_done:
        return
    
    _cleanup_done = True
    log.info("开始清理资源...")
    
    # 终止子进程
    if task_process and task_process.is_alive():
        log.info("终止车道保持进程")
        task_process.terminate()
    
    if camera_process and camera_process.is_alive():
        log.info("终止摄像头进程")
        if camera:
            camera.stop_sign.value = True
        camera_process.join(timeout=1.0)
        if camera_process.is_alive():
            camera_process.terminate()
    
    # 恢复终端设置
    os.system('stty sane')
    log.info("资源清理完成")

def handle_exit(signum, frame):
    """信号处理函数"""
    log.info(f"接收到信号 {signum}，开始安全退出")
    raise SystemExit(0)

def main():
    global _cleanup_done
    _cleanup_done = False
    
    # 注册退出处理
    atexit.register(cleanup_resources)
    signal.signal(signal.SIGINT, handle_exit)  # Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit) # kill命令

    log.info('车道保持程序启动')
    ctrl = Controller()
    msg_queue = Queue(maxsize=1)

    # 初始化摄像头广播器
    camera = CameraBroadcaster(CAMERA_INFO)
    camera_process = Process(target=camera.run)
    camera_process.start()

   # 等待摄像头初始化（改进后的逻辑）
    timeout = 30  # 秒
    start_time = time.time()
    shared_memory_name = None

    while (time.time() - start_time) < timeout:
        try:
            # 直接使用固定名称尝试连接
            temp_shm = shared_memory.SharedMemory(name='cycar_camera_frame', create=False)
            temp_shm.close()
            shared_memory_name = 'cycar_camera_frame'
            break
        except FileNotFoundError:
            time.sleep(0.1)
        except Exception as e:
            log.error(f"等待共享内存时出错: {str(e)}")
            time.sleep(0.1)

    if not shared_memory_name:
        log.error('摄像头初始化超时')
        cleanup_resources(camera_process=camera_process)
        sys.exit(1)

    log.info(f'使用共享内存: {shared_memory_name}')

    # 启动车道保持任务
    task = LF_threshold(shared_memory_name, CAMERA_INFO, msg_queue)
    task_process = Process(target=task.loop)
    task_process.start()
    log.info('车道保持进程已启动')

    try:
        log.info("主控制循环启动 (按ESC键退出)")
        while True:
            try:
                key = getKey()
                if key == 'esc':
                    log.info('正在安全停止...')
                    task.stop_sign.value = True
                    camera.stop_sign.value = True
                    break
                msg_queue.put(key)
            except Exception as e:
                log.error(f"键盘处理异常: {str(e)}")
                time.sleep(0.1)
                
    except SystemExit:
        pass  # 由信号处理器触发的正常退出
    except Exception as e:
        log.error(f"主循环异常: {str(e)}")
    finally:
        cleanup_resources(
            camera_process=camera_process,
            task_process=task_process,
            camera=camera
        )

if __name__ == '__main__':
    main()