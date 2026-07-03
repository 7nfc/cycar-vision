import cv2

for index in [0, 1]:
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        print(f"摄像头 /dev/video{index} 已打开")
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"test_{index}.jpg", frame)
            print(f"图像已保存为 test_{index}.jpg")
        cap.release()
    else:
        print(f"无法打开 /dev/video{index}")