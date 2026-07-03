# cycar-vision

这是我在小学期实践中完成的智能小车道路识别项目，主要用于整理和归档当时的实验代码。

项目基于 Python 和 OpenCV，实现了摄像头画面采集、黄色车道线识别、模板匹配、手动控制，以及通过串口向 STM32 下发小车控制指令等功能。

> 该项目偏课程实践和实验记录，代码以当时完成任务和调试验证为主，并非完整工程化产品。

## 项目结构

```text
.
├── src/
│   ├── actions/        # 小车动作定义
│   ├── scenes/         # 场景逻辑：手动控制、车道跟随、模板匹配等
│   └── utils/          # 摄像头、控制器、日志等工具
├── ctr_*.py            # 控制与测试脚本
├── lane.py             # 车道相关脚本
└── test_camera.py      # 摄像头测试脚本
```

## 环境依赖

建议使用 Python 3.10+。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

在 Linux / 小车端运行时，串口设备默认使用 `/dev/ttyACM0`，摄像头默认使用 OpenCV 的 `VideoCapture(0)`。

## 主要功能

- 串口下发 STM32 控制指令
- 摄像头帧采集与共享内存广播
- 手动键盘控制小车移动与舵机角度
- 基于 HSV 阈值和霍夫变换的车道线跟随
- 基于模板图片的场景识别

## 注意事项

- `.idea/`、日志和运行时截图不会提交到 Git。
- 运行控制程序前，请确认摄像头、串口和硬件连接正常。
- 如果你的串口设备不是 `/dev/ttyACM0`，需要在 `src/utils/controller.py` 中调整设备路径。
