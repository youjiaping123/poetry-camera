from gpiozero import Button
from signal import pause

def button_pressed():
    print("按钮被按下！")

def button_released():
    print("按钮被释放！")

button = Button(21)  # 使用GPIO 21

button.when_pressed = button_pressed
button.when_released = button_released

print("等待按钮事件。按 Ctrl+C 退出。")

try:
    pause()
except KeyboardInterrupt:
    print("\n程序已退出")