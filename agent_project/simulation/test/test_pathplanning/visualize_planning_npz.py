import os
import glob
import argparse
import numpy as np
import matplotlib.pyplot as plt

def safe_item(x):
    """np.array(dict, dtype=object) -> dict"""
    try:
        return x.item()
    except Exception:
        return x

def infer_status(data):
    """
    返回 status 数组：shape (N,), 取值 {'exact','approx','fail'}
    优先使用 data['status']；否则用 success + 时间/路径等做降级推断（不完美）。
    """
    if "status" in data.files:
        status = data["status"].astype(object)
        # 兼容 bytes
        status = np.array([s.decode() if isinstance(s, (bytes, np.bytes_)) else str(s) for s in status], dtype=object)
        return status

    # 降级：如果没存 status，就用 success 当 exact，其余当 fail（approx 无法可靠区分）
    success = data["success"].astype(bool) if "success" in data.files else None
    if success is None:
        raise ValueError("npz里既没有 status 也没有 success，无法判定成功/失败。")

    status = np.where(success, "exact", "fail").astype(object)
    return status

def load_npz(npz_path):
    data = np.load(npz_path, allow_pickle=True)
    name = os.path.splitext(os.path.basename(npz_path))[0]

    success = data["success"].astype(bool) if "success" in data.files else None
    solved_time = data["solved_time"].astype(float) if "solved_time" in data.files else None
    total_states = data["total_states"].astype(float) if "total_states" in data.files else None  # int也行
    status = infer_status(data)

    summary = safe_item(data["summary"]) if "summary" in data.files else {}
    meta = safe_item(data["meta"]) if "meta" in data.files else {}

    return {
        "name": name,
        "success": success,
        "solved_time": solved_time,
        "total_states": total_states,
        "status": status,
        "summary": summary if isinstance(summary, dict) else {},
        "meta": meta if isinstance(meta, dict) else {},
    }

def boxplot_by_planner(planners, values_by_name, title, ylabel, out_path=None, logy=False):
    names = [p["name"] for p in planners]
    data = [values_by_name[n] for n in names]

    plt.figure()
    plt.boxplot(data, labels=names, showfliers=True)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
    plt.grid(True, axis="y", linestyle="--", alpha=0.4)
    if logy:
        plt.yscale("log")
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=200)
    plt.show()

def stacked_rate_bar(planners, out_path=None):
    names = [p["name"] for p in planners]

    exact_rates = []
    approx_rates = []
    fail_rates = []

    for p in planners:
        status = p["status"]
        n = len(status)
        exact_rates.append(np.mean(status == "exact"))
        approx_rates.append(np.mean(status == "approx"))
        fail_rates.append(np.mean((status != "exact") & (status != "approx")))

    x = np.arange(len(names))

    plt.figure()
    b1 = plt.bar(x, exact_rates)
    b2 = plt.bar(x, approx_rates, bottom=exact_rates)
    b3 = plt.bar(x, fail_rates, bottom=np.array(exact_rates) + np.array(approx_rates))

    plt.xticks(x, names, rotation=30, ha="right")
    plt.ylim(0, 1.0)
    plt.ylabel("Rate")
    plt.title("Exact / Approx / Fail rate per planner")
    plt.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.legend([b1, b2, b3], ["Exact", "Approx", "Fail"], loc="upper right")
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=200)
    plt.show()

def main():
    dir = r"/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/datas/20260114"
    log_time = True
    npz_files = sorted(glob.glob(os.path.join(dir, "*.npz")))
    if not npz_files:
        raise FileNotFoundError(f"在目录 {dir} 下没找到 .npz 文件")

    planners = [load_npz(f) for f in npz_files]

    out_dir = r"/home/lwh/Project/python_project/Ai_agent/agent_project/simulation/test/test_pathplanning/figs"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # 1) 比例图
    stacked_rate_bar(planners, out_path=(os.path.join(out_dir, "rate_stacked.png") if out_dir else None))

    # 2) Exact 的 solved_time（只看成功/可用解）
    exact_time = {}
    for p in planners:
        t = p["solved_time"]
        s = p["status"]
        if t is None:
            exact_time[p["name"]] = np.array([])
        else:
            exact_time[p["name"]] = t[s == "exact"]

    boxplot_by_planner(
        planners,
        exact_time,
        title="Solved time (Exact only)",
        ylabel="Time (s)",
        out_path=(os.path.join(out_dir, "time_exact_box.png") if out_dir else None),
        logy=log_time,
    )

    # 3) All trial 的 solved_time（包含失败，更反映算法代价）
    all_time = {}
    for p in planners:
        t = p["solved_time"]
        all_time[p["name"]] = t if t is not None else np.array([])

    boxplot_by_planner(
        planners,
        all_time,
        title="Solved time (All trials)",
        ylabel="Time (s)",
        out_path=(os.path.join(out_dir, "time_all_box.png") if out_dir else None),
        logy=log_time,
    )

    # 4) total_states（all trials）
    all_states = {}
    for p in planners:
        st = p["total_states"]
        all_states[p["name"]] = st if st is not None else np.array([])

    boxplot_by_planner(
        planners,
        all_states,
        title="Total states / vertices (All trials)",
        ylabel="States",
        out_path=(os.path.join(out_dir, "states_all_box.png") if out_dir else None),
        logy=False,
    )

    # 控制台输出一个快速汇总
    print("\n=== Quick summary ===")
    for p in planners:
        status = p["status"]
        exact = np.mean(status == "exact")
        approx = np.mean(status == "approx")
        fail = np.mean((status != "exact") & (status != "approx"))

        t = p["solved_time"]
        if t is not None:
            t_exact = t[status == "exact"]
            t_all_mean = float(np.mean(t))
            t_exact_mean = float(np.mean(t_exact)) if len(t_exact) else float("nan")
        else:
            t_all_mean = float("nan")
            t_exact_mean = float("nan")

        st = p["total_states"]
        st_mean = float(np.mean(st)) if st is not None else float("nan")

        print(f"{p['name']:<12} exact={exact:.2f} approx={approx:.2f} fail={fail:.2f} "
              f"time_exact_mean={t_exact_mean:.3f}s time_all_mean={t_all_mean:.3f}s states_mean={st_mean:.1f}")

if __name__ == "__main__":
    main()
