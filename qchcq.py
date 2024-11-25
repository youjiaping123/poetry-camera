import serial
import time

def reset_printer():
    try:
        # 打开串口
        ser = serial.Serial('/dev/serial0', 9600, timeout=1)
        
        # 发送初始化命令
        ser.write(b'\x1B\x40')  # ESC @
        time.sleep(0.1)
        
        # 清除输入缓冲区
        ser.reset_input_buffer()
        
        # 清除输出缓冲区
        ser.reset_output_buffer()
        
        # 发送换行和切纸命令
        ser.write(b'\n\n\n\n')
        ser.write(b'\x1D\x56\x41\x10')  # 切纸命令
        
        print("打印机重置命令已发送")
        
    except Exception as e:
        print(f"重置打印机时发生错误: {str(e)}")
    
    finally:
        if 'ser' in locals():
            ser.close()
            print("串口已关闭")

if __name__ == "__main__":
    reset_printer()