import serial
import time
from datetime import datetime

# 串口设置
SERIAL_PORT = '/dev/serial0'  # 使用树莓派的硬件串口
BAUD_RATE = 9600  # 根据您的打印机波特率进行调整

def init_printer():
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False
        )
        print("打印机初始化成功")
        return ser
    except Exception as e:
        print(f"打印机初始化失败: {str(e)}")
        return None

def print_test(ser, text):
    try:
        # 初始化打印机
        ser.write(b'\x1B\x40')  # ESC @
        
        # 打印文本
        ser.write(text.encode('gbk'))
        
        # 换行
        ser.write(b'\n\n')
        
        # 切纸命令
        ser.write(b'\x1D\x56\x41\x10')
        
        print("打印命令已发送")
        time.sleep(1)  # 等待打印完成
        
    except Exception as e:
        print(f"打印错误: {str(e)}")

def main():
    # 初始化打印机
    ser = init_printer()
    if not ser:
        return

    try:
        # 测试项目1：打印当前时间
        now = datetime.now()
        print_test(ser, f"打印机测试\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        time.sleep(2)

        # 测试项目2：打印基本文本
        print_test(ser, "基本文本测试\n这是一行测试文本\n")
        time.sleep(2)

        # 测试项目3：打印分隔线
        print_test(ser, "=" * 32 + "\n")
        time.sleep(2)

        # 测试项目4：打印中文
        print_test(ser, "中文打印测试\n你好，世界！\n")
        time.sleep(2)

        # 测试项目5：打印多行文本
        test_text = """多行文本测试
第一行
第二行
第三行
测试结束
"""
        print_test(ser, test_text)

    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
    finally:
        ser.close()
        print("测试完成，串口已关闭")

if __name__ == "__main__":
    main()
