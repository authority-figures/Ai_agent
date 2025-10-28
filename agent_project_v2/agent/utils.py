from colorama import init, Fore, Style, Back
from pathlib import Path

# 初始化colorama，autoreset=True确保颜色不会影响后续输出
init(autoreset=True)


class ColorPrinter:
    """彩色打印工具类，用于在控制台中打印有颜色和格式的文本"""

    # 颜色映射
    COLORS = {
        "black": Fore.BLACK,
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE
    }

    # 背景色映射
    BACKGROUNDS = {
        "black": Back.BLACK,
        "red": Back.RED,
        "green": Back.GREEN,
        "yellow": Back.YELLOW,
        "blue": Back.BLUE,
        "magenta": Back.MAGENTA,
        "cyan": Back.CYAN,
        "white": Back.WHITE
    }

    # 样式映射
    STYLES = {
        "normal": Style.NORMAL,
        "bright": Style.BRIGHT,
        "dim": Style.DIM
    }

    @classmethod
    def print(cls, text, color="white", style="normal", bg=None, prefix=None, width=100):
        """
        打印彩色文本到控制台，带有特定格式的前缀和底部分隔线

        参数:
            text (str): 要打印的文本
            color (str): 前景色，可选值: "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"
            style (str): 文本样式，可选值: "normal", "bright", "dim"
            bg (str): 背景色，可选值同color，默认None表示不设置背景色
            prefix (str): 文本前缀，默认None表示无前缀
            width (int): 分隔线的长度，默认30
        """
        # 构建格式化字符串
        format_str = ""

        # 添加样式
        if style in cls.STYLES:
            format_str += cls.STYLES[style]

        # 添加前景色
        if color in cls.COLORS:
            format_str += cls.COLORS[color]

        # 添加背景色
        if bg in cls.BACKGROUNDS:
            format_str += cls.BACKGROUNDS[bg]

        # 打印带格式的前缀栏
        if prefix:
            separator = "=" * ((width - len(prefix)) // 2)
            prefix_line = f"{separator}{prefix}{separator}"
            # 如果长度因为整除问题不匹配，加一个=号
            if len(prefix_line) < width:
                prefix_line += "="
            print(f"{format_str}{prefix_line}")
        else:
            print(f"{format_str}{'=' * width}")

        # 打印主要内容
        print(f"{format_str}{text}")

        # 打印底部分隔线
        print(f"{format_str}{'=' * width}")

    @classmethod
    def tool_name(cls, name):
        """打印工具名称"""
        cls.print(f"执行工具: {name}", "yellow", "bright", prefix="TOOL")

    @classmethod
    def llm_output(cls, text):
        """打印工具名称"""
        cls.print(f"{text}", "blue", "bright", prefix="LLM Output",width=200)

    @classmethod
    def tool_execute(cls, text):
        """打印工具名称"""
        cls.print(f"{text}", "green", "bright", prefix="TOOL Execute",width=200)

    @classmethod
    def tool_result(cls, result):
        """打印工具执行结果"""
        cls.print(f"执行结果: {result}", "green", prefix="RESULT")

    @classmethod
    def error(cls, error_msg):
        """打印错误信息"""
        cls.print(f"错误: {error_msg}", "red", "bright", prefix="ERROR")

    @classmethod
    def info(cls, message):
        """打印一般信息"""
        cls.print(message, "cyan", prefix="INFO")

    @classmethod
    def debug(cls, message):
        """打印调试信息"""
        cls.print(message, "blue", "dim", prefix="DEBUG")

    @classmethod
    def success(cls, message):
        """打印成功信息"""
        cls.print(message, "green", "bright", prefix="SUCCESS")


def truncate_path_to(path, target_dir_name):
    path = Path(path).resolve()
    for parent in path.parents:
        if parent.name == target_dir_name:
            return str(parent)
    return None  # 如果没找到
