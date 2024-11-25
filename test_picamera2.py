from picamera2 import Picamera2, Preview
import time

def main():
    # 初始化摄像头
    picamera = Picamera2()
    
    # 配置摄像头，设置预览模式
    picamera.configure(picamera.create_still_configuration())
    
    # 启动摄像头预览
    picamera.start_preview(Preview.QTGL)
    
    # 等待几秒钟，确保摄像头初始化完毕
    time.sleep(2)
    
    # 捕获一帧图像
    image = picamera.capture_array()
    
    # 保存图像到文件
    from PIL import Image
    img = Image.fromarray(image)
    img.save("test_image.jpg")
    
    print("Image captured and saved as 'test_image.jpg'")
    
    # 关闭摄像头
    picamera.close()

if __name__ == "__main__":
    main()


