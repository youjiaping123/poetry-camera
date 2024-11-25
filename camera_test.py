from picamera2 import Picamera2
import time

picam2 = Picamera2()
picam2.start()
time.sleep(2)  # 预热期
picam2.capture_file('/home/pi/test.jpg')
picam2.stop()

print("图片已捕获并保存到 /home/pi/test.jpg")

