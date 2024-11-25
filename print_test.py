import serial
import time

SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 9600

def send_and_log(data, description):
    print(f"发送 {description}: {data}")
    bytes_written = ser.write(data)
    print(f"写入 {bytes_written} 字节")
    time.sleep(0.5)

def test_print(init_commands, text, encoding):
    print(f"\n测试 - 编码: {encoding}, 初始化命令: {init_commands}")
    for cmd in init_commands:
        send_and_log(cmd, "初始化命令")
    
    encoded_text = text.encode(encoding, errors='ignore')
    send_and_log(encoded_text, "文本")
    send_and_log(b'\n\n', "换行")

try:
    print(f"尝试打开串口 {SERIAL_PORT} 波特率 {BAUD_RATE}")
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )
    print("串口已成功打开")

    # 测试不同的初始化命令和编码
    init_commands_list = [
        [b'\x1B\x40'],  # ESC @
        [b'\x1B\x40', b'\x1C\x26'],  # ESC @ + FS &
        [b'\x1B\x40', b'\x1B\x74\x15'],  # ESC @ + ESC t 15
    ]

    encodings = ['gbk', 'utf-8', 'gb2312']
    test_text = "测试打印 - 你好，世界！"

    for init_commands in init_commands_list:
        for encoding in encodings:
            test_print(init_commands, test_text, encoding)

    # 打印ASCII测试
    print("\nASCII 测试")
    send_and_log(b'\x1B\x40', "初始化命令")
    send_and_log(b"ASCII Test: Hello, World!", "ASCII文本")
    send_and_log(b'\n\n', "换行")

    # 发送切纸命令
    print("发送切纸命令")
    send_and_log(b'\x1D\x56\x41\x10', "切纸命令")

    print("测试完成")

except Exception as e:
    print(f"发生错误: {str(e)}")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("串口已关闭")
    else:
        print("串口未能成功打开")