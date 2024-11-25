import usb.core
import usb.util
import sys

# 打印机的 Vendor ID 和 Product ID
VENDOR_ID = 0x28e9
PRODUCT_ID = 0x0289

def print_using_usb():
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

    if dev is None:
        raise ValueError('Device not found')

    if dev.is_kernel_driver_active(0):
        try:
            dev.detach_kernel_driver(0)
        except usb.core.USBError as e:
            print(f"Could not detach kernel driver: {str(e)}")

    try:
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]

        ep = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT
        )

        assert ep is not None

        # 初始化打印机
        ep.write(b'\x1B\x40')  # ESC @

        # 英文测试
        ep.write("Hello, this is a test print!\n".encode('ascii'))

        # 方法1：尝试 GBK 编码
        chinese_text = "如果您看到这行中文，说明打印成功。\n"
        ep.write(chinese_text.encode('gbk'))

        # 方法2：使用打印机指令切换到中文模式（适用于某些型号的打印机）
        ep.write(b'\x1C\x26')  # 切换到中文模式
        ep.write(chinese_text.encode('gbk'))
        ep.write(b'\x1C\x2E')  # 切换回ASCII模式

        # 切纸命令
        ep.write(b'\x1D\x56\x41\x10')

        print("USB 方法：打印命令已发送。")
    except usb.core.USBError as e:
        print(f"USB 错误: {str(e)}")
    finally:
        try:
            dev.attach_kernel_driver(0)
        except:
            pass

def print_using_device_file():
    try:
        with open('/dev/usb/lp0', 'wb') as printer:
            # 初始化打印机
            printer.write(b'\x1B\x40')  # ESC @

            # 英文测试
            printer.write("Hello, this is a test print!\n".encode('ascii'))

            # 方法1：尝试 GBK 编码
            chinese_text = "如果您看到这行中文，说明打印成功。\n"
            printer.write(chinese_text.encode('gbk'))

            # 方法2：使用打印机指令切换到中文模式
            printer.write(b'\x1C\x26')  # 切换到中文模式
            printer.write(chinese_text.encode('gbk'))
            printer.write(b'\x1C\x2E')  # 切换回ASCII模式

            # 切纸命令
            printer.write(b'\x1D\x56\x41\x10')

        print("设备文件方法：打印命令已发送。")
    except IOError as e:
        print(f"设备文件错误: {str(e)}")

if __name__ == "__main__":
    print("尝试使用 USB 方法打印...")
    try:
        print_using_usb()
    except Exception as e:
        print(f"USB 方法失败: {str(e)}")
        print("尝试使用设备文件方法打印...")
        print_using_device_file()