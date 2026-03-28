"""PyCharm 调试用：向数字孪生机床轴监听 TCP 服务发送 ACXYZ 测试数据。

监听端默认: 127.0.0.1:9101
支持发送格式:
1. JSON 数组: [A, C, X, Y, Z]
2. JSON 对象: {"A": ..., "C": ..., "X": ..., "Y": ..., "Z": ...}
3. CSV 字符串: A,C,X,Y,Z

输入状态单位:
    [deg, deg, mm, mm, mm]

发送前自动转换为:
    [rad, rad, m, m, m]
"""

from __future__ import annotations

import json
import math
import socket
import time
from typing import List


AXIS_LABELS = ["A", "C", "X", "Y", "Z"]


# =========================
# PyCharm 调试参数区
# =========================
HOST = "127.0.0.1"
PORT = 9101
TIMEOUT = 3.0
INTERVAL = 0.01
FORMAT = "json-object"   # 可选: "json-object" / "json-array" / "csv"

# ['A:-0.3559', 'C:-0.9584', 'X:0.4537', 'Y:0.3362', 'Z:-0.1682', 'N:16.0000']
START_STATE = [0.0, 0.0, 0.0, 0.0, 0.0]          # [A, C, X, Y, Z] -> [deg, deg, mm, mm, mm]
END_STATE = [-20.3916, -54.912, 453.71000,336.2, -168.2] # [A, C, X, Y, Z] -> [deg, deg, mm, mm, mm]
N = 100                                          # 插值分段数，最终生成 N + 1 个点


def convert_units(axis_values: List[float]) -> List[float]:
    """将 [A, C, X, Y, Z] 从 [deg, deg, mm, mm, mm] 转为 [rad, rad, m, m, m]。"""
    if len(axis_values) != 5:
        raise ValueError("ACXYZ 必须恰好包含 5 个数值")

    a_deg, c_deg, x_mm, y_mm, z_mm = axis_values
    return [
        math.radians(a_deg),
        math.radians(c_deg),
        x_mm / 1000.0,
        y_mm / 1000.0,
        z_mm / 1000.0,
    ]


def interpolate_states(
    start_state: List[float],
    end_state: List[float],
    n: int,
) -> List[List[float]]:
    """对起始状态和终止状态做线性插值。

    参数:
        start_state: [A, C, X, Y, Z]，单位 [deg, deg, mm, mm, mm]
        end_state:   [A, C, X, Y, Z]，单位 [deg, deg, mm, mm, mm]
        n: 插值分段数。返回总数为 n + 1，包含起点和终点。

    返回:
        插值后的状态列表，单位仍为 [deg, deg, mm, mm, mm]
    """
    if len(start_state) != 5 or len(end_state) != 5:
        raise ValueError("start_state 和 end_state 都必须恰好包含 5 个数值")
    if n <= 0:
        raise ValueError("n 必须是正整数")

    result = []
    for i in range(n + 1):
        t = i / n
        interpolated = [
            s + (e - s) * t
            for s, e in zip(start_state, end_state)
        ]
        result.append(interpolated)

    return result


def encode_payload(axis_values: List[float], fmt: str) -> str:
    """将轴值编码为指定格式。输入单位应为 [rad, rad, m, m, m]。"""
    if len(axis_values) != 5:
        raise ValueError("ACXYZ 必须恰好包含 5 个数值")

    if fmt == "json-object":
        return json.dumps(dict(zip(AXIS_LABELS, axis_values)), ensure_ascii=False)
    if fmt == "json-array":
        return json.dumps(axis_values, ensure_ascii=False)
    if fmt == "csv":
        return ",".join(str(value) for value in axis_values)

    raise ValueError(f"不支持的消息格式: {fmt}")


def send_payload(host: str, port: int, payload: str, timeout: float) -> str:
    """发送一条消息，并尝试接收服务端响应。"""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall((payload + "\n").encode("utf-8"))

        chunks = []
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break

            if not chunk:
                break

            chunks.append(chunk)

            if b"\n" in chunk:
                break

    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def run_debug() -> None:
    """PyCharm 中直接运行/调试这个函数。"""
    raw_states = interpolate_states(START_STATE, END_STATE, N)
    total = len(raw_states)

    print("========== 调试发送开始 ==========")
    print(f"HOST={HOST}, PORT={PORT}, FORMAT={FORMAT}, TIMEOUT={TIMEOUT}, INTERVAL={INTERVAL}")
    print(f"START_STATE={START_STATE}")
    print(f"END_STATE={END_STATE}")
    print(f"N={N}, total_points={total}")
    print("=================================")

    for index, raw_axis_values in enumerate(raw_states, start=1):
        converted_axis_values = convert_units(raw_axis_values)
        payload = encode_payload(converted_axis_values, FORMAT)

        print(f"[{index}/{total}] input(deg,deg,mm,mm,mm) -> {raw_axis_values}")
        print(f"[{index}/{total}] send(rad,rad,m,m,m) -> {payload}")

        try:
            response = send_payload(HOST, PORT, payload, TIMEOUT)
        except OSError as exc:
            print(f"[{index}/{total}] 发送失败: {exc}")
            return

        if response:
            print(f"[{index}/{total}] recv <- {response}")
        else:
            print(f"[{index}/{total}] recv <- <empty>")

        if index < total and INTERVAL > 0:
            time.sleep(INTERVAL)

    print("发送完成。")


if __name__ == "__main__":
    run_debug()