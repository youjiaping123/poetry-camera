import time
import os
import httpx
import serial
import json
import replicate
import shutil
from picamera2 import Picamera2
from wraptext import wrap_text
from datetime import datetime
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
import RPi.GPIO as GPIO
import logging
import sys
import signal

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/pi/poetry-camera.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置GPIO模式和按钮引脚
GPIO.setmode(GPIO.BCM)
BUTTON_PIN = 21
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# 从.env文件加载API密钥和代理设置
load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
if not DEEPSEEK_API_KEY or not REPLICATE_API_TOKEN:
    logging.error("错误：未设置 DEEPSEEK_API_KEY 或 REPLICATE_API_TOKEN 环境变量")
    exit(1)

# 初始化HTTP客户端
http_client = httpx.Client(timeout=30)  # 增加超时时间到30秒

# 串口设置
SERIAL_PORT = '/dev/serial0'  # 使用树莓派的硬件串口
BAUD_RATE = 9600  # 根据您的打印机波特率进行调整

# 初始化串口
ser = serial.Serial(
    port=SERIAL_PORT,
    baudrate=BAUD_RATE,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    xonxoff=False,  # 禁用软件流控制
    rtscts=False    # 禁用硬件流控制
)

# 定义文件夹路径
UPLOADS_FOLDER = '/home/pi/poetry-camera-rpi/uploads'
IMAGES_FOLDER = '/home/pi/poetry-camera-rpi/images'
PROCESSED_FOLDER = os.path.join(UPLOADS_FOLDER, 'processed')

# 确保所需文件夹存在
os.makedirs(UPLOADS_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def initialize_printer():
    try:
        logging.info("开始初始化打印机...")
        logging.info(f"串口状态 - 是否打开: {ser.is_open}")
        
        # 确保串口已关闭
        if ser.is_open:
            logging.info("关闭已打开的串口...")
            ser.close()
        
        # 重新打开串口
        logging.info("打开串口...")
        ser.open()
        logging.info(f"串口配置: 波特率={ser.baudrate}, 数据位={ser.bytesize}, 校验位={ser.parity}")
        
        # 清空缓冲区
        logging.info("清空串口缓冲区...")
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        logging.info("等待打印机就绪...")
        time.sleep(0.5)
        
        # 发送初始化命令
        logging.info("发送打印机初始化命令...")
        ser.write(b'\x1B\x40')
        time.sleep(0.1)
        logging.info("发送打印取消命令...")
        ser.write(b'\x1B\x78')
        time.sleep(0.1)
        
        logging.info("打印机初始化完成")
    except Exception as e:
        logging.error(f"打印机初始化错误: {str(e)}", exc_info=True)

def print_using_serial(text):
    try:
        logging.info("准备打印文本...")
        logging.info(f"串口状态检查 - 是否打开: {ser.is_open}")
        
        # 记录要打印的文本（前50个字符）
        logging.info(f"打印文本预览: {text[:50]}...")
        
        # 初始化打印机
        logging.info("发送打印机初始化命令...")
        ser.write(b'\x1B\x40')
        
        # 记录发送的字节数
        encoded_text = text.encode('gbk')
        bytes_written = ser.write(encoded_text)
        logging.info(f"已发送 {bytes_written} 字节数据")
        
        # 切纸命令
        logging.info("发送切纸命令...")
        ser.write(b'\x1D\x56\x41\x10')
        
        # 确保数据发送完成
        logging.info("等待数据发送完成...")
        ser.flush()
        
        logging.info("打印命令执行完成")
    except Exception as e:
        logging.error(f"打印机错误: {str(e)}", exc_info=True)

# 初始化相机
try:
    picam2 = Picamera2()
    picam2.start()
    time.sleep(2)
    logging.info("相机初始化成功")
except Exception as e:
    logging.error(f"相机初始化错误: {str(e)}")
    exit(1)

# 提示词
system_prompt = """你是一位诗人。你擅长优雅且情感丰富的诗歌。
你善于使用微妙的表达,并以现代口语风格写作。
使用高中水平的中文,但研究生水平的技巧。
你的诗更具文学性,但易于理解和产生共鸣。
你专注于亲密和个人的真实,不能使用诸如真理、时间、沉默、生命、爱、和平、战争、仇恨、幸福等宏大词语,
而必须使用具体和具象的语言来展示,而非直接告诉这些想法。
仔细思考如何创作一首能满足这些要求的诗。
这非常重要,过于生硬或俗气的诗会造成巨大伤害。"""

prompt_base = """根据我下面描述的细节写一首诗。
使用指定的诗歌格式。对源材料的引用必须微妙但清晰。
专注于独特和优雅的诗,使用具体的想法和细节。
你必须保持词汇简单,并使用低调的视角。这一点非常重要。\n\n"""

poem_format = "8行自由诗"

def generate_prompt(image_description):
    prompt_format = "诗歌格式: " + poem_format + "\n\n"
    prompt_scene = "场景描述: " + image_description + "\n\n"
    prompt = prompt_base + prompt_format + prompt_scene
    prompt = prompt.replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("'", "")
    return prompt

def print_poem(poem):
    printable_poem = wrap_text(poem, 32)
    print_using_serial(printable_poem)
    time.sleep(1)

def print_header():
    now = datetime.now()
    date_string = now.strftime('%b %-d, %Y')
    time_string = now.strftime('%-I:%M %p')
    header_text = f'\n{date_string}\n{time_string}\n\n`\' . \' ` \' . \' ` \' . \' `\n   `     `     `     `     `\n'
    print_using_serial(header_text)
    time.sleep(1)

def print_footer():
    footer_text = "   .     .     .     .     .   \n_.` `._.` `._.` `._.` `._.` `._\n\n 这首诗由AI创作。\n在以下网址探索档案\nroefruit.com\n\n\n\n"
    print_using_serial(footer_text)
    time.sleep(1)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def call_deepseek_api(url, headers, data):
    response = http_client.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_image_caption(image_path):
    try:
        image_caption = replicate.run(
            "andreasjansson/blip-2:4b32258c42e9efd4288bb9910bc532a69727f9acd26aa08e175713a0a857a608",
            input={
                "image": open(image_path, "rb"),
                "caption": True,
            })
        logging.info(f'caption: {image_caption}')
        return image_caption
    except Exception as e:
        logging.error(f"生成图像描述错误: {str(e)}")
        return "一张未知场景的照片"

def get_latest_upload():
    uploads = [f for f in os.listdir(UPLOADS_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not uploads:
        return None
    return max([os.path.join(UPLOADS_FOLDER, f) for f in uploads], key=os.path.getmtime)

def move_to_processed(file_path):
    filename = os.path.basename(file_path)
    new_path = os.path.join(PROCESSED_FOLDER, filename)
    shutil.move(file_path, new_path)
    logging.info(f"已将处理过的图片移动到: {new_path}")

def take_photo_and_print_poem():
    try:
        # 打印前初始化
        ser.write(b'\x1B\x40')
        time.sleep(0.1)
        
        latest_upload = get_latest_upload()
        
        if latest_upload:
            logging.info(f"发现上传的图片: {latest_upload}")
            image_path = latest_upload
        else:
            logging.info("未发现上传的图片，正在拍摄新照片...")
            image_path = os.path.join(IMAGES_FOLDER, 'image.jpg')
            picam2.capture_file(image_path)
            logging.info(f'成功: 图像已保存到 {image_path}')

        print_header()
        
        # 生成图像描述
        image_caption = generate_image_caption(image_path)

        # 使用 DeepSeek API 生成诗歌
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": generate_prompt(image_caption)}
            ],
            "stream": False
        }

        try:
            logging.info("正在调用 DeepSeek API...")
            result = call_deepseek_api(url, headers, data)
            poem = result['choices'][0]['message']['content']
            logging.info("生成的诗:")
            logging.info(poem)
            print_poem(poem)
        except Exception as e:
            logging.error(f"API 调用或诗歌生成错误: {str(e)}")

        print_footer()

        if latest_upload:
            move_to_processed(latest_upload)

        # 打印后清理
        ser.write(b'\x1B\x78')  # 取消打印
        time.sleep(0.1)
        ser.flush()
    except Exception as e:
        logging.error(f"打印过程错误: {str(e)}")

def wait_for_button_press():
    logging.info("等待按钮按下...")
    button_press_time = None
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            if button_press_time is None:
                button_press_time = time.time()
            elif time.time() - button_press_time >= 2:
                logging.info("检测到长按，正在关闭程序...")
                return "SHUTDOWN"
        else:
            if button_press_time is not None:
                if time.time() - button_press_time < 2:
                    logging.info("按钮被短按！")
                    return "NORMAL"
                button_press_time = None
        time.sleep(0.1)

def shutdown():
    logging.info("开始执行关闭程序流程...")
    try:
        logging.info(f"当前串口状态 - 是否打开: {ser.is_open}")
        
        # 发送复位命令
        logging.info("发送打印机复位命令...")
        ser.write(b'\x1B\x40')
        time.sleep(0.2)
        
        logging.info("发送打印取消命令...")
        ser.write(b'\x1B\x78')
        time.sleep(0.2)
        
        # 清理缓冲区
        logging.info("清空串口缓冲区...")
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # 等待数据发送完成
        logging.info("等待所有数据发送完成...")
        ser.flush()
        time.sleep(0.5)
        
        # 关闭串口
        if ser.is_open:
            logging.info("关闭串口连接...")
            ser.close()
            logging.info("串口已关闭")
            
    except Exception as e:
        logging.error(f"关闭打印机时出错: {str(e)}", exc_info=True)
    finally:
        logging.info("清理GPIO资源...")
        GPIO.cleanup()
        logging.info("发送终止信号...")
        os.kill(os.getpid(), signal.SIGTERM)

def signal_handler(signum, frame):
    logging.info(f"收到系统信号: {signum}")
    logging.info(f"当前进程状态: PID={os.getpid()}")
    shutdown()

def main():
    logging.info("程序启动...")
    logging.info(f"Python版本: {sys.version}")
    logging.info(f"当前工作目录: {os.getcwd()}")
    
    # 注册信号处理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logging.info("信号处理器已注册")
    
    try:
        initialize_printer()
        
        while True:
            logging.info("等待按钮输入...")
            button_action = wait_for_button_press()
            
            if button_action == "SHUTDOWN":
                logging.info("收到关机命令")
                shutdown()
                break
            elif button_action == "NORMAL":
                logging.info("开始拍照打印流程")
                take_photo_and_print_poem()
                time.sleep(1)
                logging.info("拍照打印流程完成")
                
    except KeyboardInterrupt:
        logging.info("程序被键盘中断")
    except Exception as e:
        logging.error(f"主程序发生错误: {str(e)}", exc_info=True)
    finally:
        logging.info("开始最终清理流程...")
        try:
            logging.info("发送打印机复位命令...")
            ser.write(b'\x1B\x40')
            time.sleep(0.1)
            
            logging.info("清空串口缓冲区...")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            if ser.is_open:
                logging.info("关闭串口连接...")
                ser.close()
                
        except Exception as e:
            logging.error(f"最终清理时出错: {str(e)}", exc_info=True)
            
        logging.info("清理GPIO资源...")
        GPIO.cleanup()
        logging.info("程序正常结束")

if __name__ == "__main__":
    main()