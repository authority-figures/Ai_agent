import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def plot_multiple_frames(poses, axis_length=1.0, show_labels=True):
    """
    在三维空间中显示多个坐标系相对于世界坐标系的姿态。

    参数：
        poses (list of tuples): 每个元素是一个 (R, t)，其中
            R 是 3x3 旋转矩阵，t 是 3x1 平移向量。
        axis_length (float): 每个坐标系坐标轴的长度。
        show_labels (bool): 是否显示坐标轴标签。
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # 画世界坐标系（参考坐标系）
    origin = np.array([0, 0, 0])
    I = np.eye(3)
    colors = ['r', 'g', 'b']
    labels = ['X', 'Y', 'Z']
    for i in range(3):
        ax.quiver(*origin, *I[:, i], color=colors[i], length=axis_length, linewidth=2, arrow_length_ratio=0.1)
        if show_labels:
            ax.text(*(I[:, i] * axis_length * 1.1), f'{labels[i]}0', color=colors[i])

    # 画多个姿态的坐标系
    for idx, (R, t) in enumerate(poses, start=1):
        for i in range(3):
            axis = R[:, i] * axis_length
            ax.quiver(*t, *axis, color=colors[i], linestyle='dashed', length=axis_length, linewidth=2, arrow_length_ratio=0.1)
            if show_labels:
                ax.text(*(t + axis * 1.1), f'{labels[i]}{idx}', color=colors[i])

    # 自动设置范围
    all_points = [origin] + [t for _, t in poses]
    all_points = np.array(all_points)
    max_range = np.max(np.ptp(all_points, axis=0)) * 1.2 + axis_length
    mid = np.mean(all_points, axis=0)
    ax.set_xlim(mid[0] - max_range/2, mid[0] + max_range/2)
    ax.set_ylim(mid[1] - max_range/2, mid[1] + max_range/2)
    ax.set_zlim(mid[2] - max_range/2, mid[2] + max_range/2)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Multiple Coordinate Frames")
    plt.grid()
    plt.show()


if __name__ == '__main__':
    # 45度绕Z轴旋转，平移到(1, 1, 0)
    T1 = np.array([
        [ 6.76547033e-01,  4.76871278e-02,  7.34853761e-01,  8.80531499e-04],
        [ 7.32743968e-01,  5.57125446e-02, -6.78220015e-01, -6.62753123e-02],
        [ -7.32829375e-02,  9.97307400e-01,  2.74970153e-03, -1.07519874e-03 ],
        [0,0,0,1]
    ])
    T2 = np.array([
        [ 0.70617056,  0.00795297,  0.7079971,   0.02044407],
        [ 0.70800497,  0.00226264, -0.70620383, -0.06433113],
        [-0.00721836,  0.99996581, -0.00403294, -0.01517148],
        [0.,          0.,          0.,          1.,],
    ])

    R1 = T1[:3, :3]
    t1 = T1[:3, 3]
    R2 = T2[:3, :3]
    t2 = T2[:3, 3]
    poses = [(R1, t1), (R2, t2)]
    plot_multiple_frames(poses)