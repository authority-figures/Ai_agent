from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem,
                             QGraphicsTextItem,QGraphicsLineItem,QGraphicsItem,QGraphicsEllipseItem,QGraphicsPathItem
                             )
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QLineF, QRectF, QPoint, QTimer
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter,QPainterPath, QPolygonF, QFontMetrics
import networkx as nx
import numpy as np
from networkx.drawing.nx_agraph import graphviz_layout

class GraphNode(QGraphicsRectItem):
    '''
    用于显示langgraph的图结构的节点
    '''
    def __init__(self, node_id, name, pos, node_type='normal', width=120, height=60):
        super().__init__(0, 0, width, height)
        self.node_id = node_id
        self.node_type = node_type
        # self.setPos(pos)
        center_pos = (pos.x() + width / 2, pos.y() + height / 2)
        self.setPos(QPointF(center_pos[0] - width / 2, center_pos[1] - height / 2))

        # 不同类型节点颜色
        color_map = {
            "__start__": QColor(180, 255, 180),
            "__end__": QColor(255, 180, 180),
            "action": QColor(200, 200, 255),
            "decision": QColor(255, 255, 180),
            "normal": QColor(200, 220, 255)
        }
        self.setBrush(QBrush(color_map.get(node_type, QColor(200, 220, 255))))
        self.setPen(QPen(Qt.black, 2))

        # self.setBrush(QBrush(QColor(200, 220, 255)))
        # self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)   # 可拖动
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # 文字
        self.text = QGraphicsTextItem(name, self)
        font = QFont("Arial", 15)
        self.text.setFont(font)
        # 2. 计算文字实际宽高
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(name) + 20  # 左右各留 10 px 边距
        text_h = fm.height() + 10  # 上下各留 5 px 边距

        # 3. 取最大值，避免过窄
        new_width = max(text_w, width)  # 你原来的最小 120
        new_height = max(text_h, height)  # 最小 60
        self.setRect(0, 0, new_width, new_height)
        self.text.setParentItem(self)
        rect = self.text.boundingRect()
        self.text.setPos(new_width/2 - rect.width()/2, new_height/2 - rect.height()/2)
        # 更新位置，保持中心点不变
        delta_x = (new_width - width) / 2
        delta_y = (new_height - height) / 2
        if delta_x >= 0 or delta_y >= 0:
            self.moveBy(-delta_x, -delta_y)



        # 状态灯
        self.light = QGraphicsEllipseItem(5, 5, 10, 10, self)
        self.light.setBrush(QBrush(Qt.gray))

    def set_current(self, yes):
        self.setBrush(QBrush(QColor(255, 200, 200)) if yes else QBrush(QColor(200, 220, 255)))
        self.light.setBrush(QBrush(Qt.green if yes else Qt.gray))

    def itemChange(self, change, value):
        """节点移动后让边重绘"""
        if change == QGraphicsItem.ItemPositionChange:
            for edge in self.scene().edges:
                if edge.start_node is self or edge.end_node is self:
                    edge.update_position_v2()
        return super().itemChange(change, value)


# ---------------- 边（带箭头） ----------------
class GraphEdge(QGraphicsPathItem):
    '''
    用于显示langgraph的图结构的边
    '''
    def __init__(self, start_node, end_node, edge_type='normal',data=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.edge_type = edge_type
        self.edge_data = data

        # 文字标签
        self.label = QGraphicsTextItem(self)  # 以边为父项，会跟随移动
        self.label.setZValue(self.zValue() + 2)  # 比箭头再高一层
        self.label.setDefaultTextColor(Qt.black)
        font = QFont("Arial", 8)
        self.label.setFont(font)
        self.label_bg = QGraphicsRectItem(self)  # 底纹
        self.label_bg.setZValue(self.label.zValue() - 1)  # 背景在文字下方
        # 透明边框 + 淡色填充
        self.label_bg.setBrush(QBrush(QColor(200, 200, 200, 200)))  # 米黄半透明
        self.label_bg.setPen(QPen(Qt.NoPen))


        pen = QPen(Qt.black, 1.5)
        if edge_type == 'condition':
            pen.setStyle(Qt.DashLine)
            pen.setColor(QColor(200, 50, 50))
        else:
            pen.setCapStyle(Qt.FlatCap)
        self.setPen(pen)
        # 注册到场景自建列表


        self.update_position_v2()


    def update_position(self):
        r1 = self.start_node.sceneBoundingRect()
        r2 = self.end_node.sceneBoundingRect()
        p1 = r1.center()
        p2 = r2.center()
        line = QLineF(p1, p2)

        # 辅助：求线段与矩形边框的交点
        def intersect_rect(rect, line):
            poly = [rect.topLeft(), rect.topRight(),
                    rect.bottomRight(), rect.bottomLeft()]
            for i in range(4):
                edge = QLineF(poly[i], poly[(i + 1) % 4])
                intersect_pt = QPointF()
                typ = line.intersect(edge, intersect_pt)
                if typ == QLineF.BoundedIntersection:
                    return intersect_pt
            return line.p1() if line.p1() != rect.center() else line.p2()

        inter_p1 = intersect_rect(r1, line)
        inter_p2 = intersect_rect(r2, line)

        # 画线
        path = QPainterPath(inter_p1)
        path.lineTo(inter_p2)
        self.setPath(path)

        # 画箭头
        angle = -line.angle()
        arrow_size = 8
        rad = np.radians(angle)
        delta = QPointF(arrow_size * np.cos(rad + 2.6),
                        arrow_size * np.sin(rad + 2.6))
        arrow_head = QPolygonF([inter_p2,
                                inter_p2 + delta,
                                inter_p2 + QPointF(arrow_size * np.cos(rad - 2.6),
                                                   arrow_size * np.sin(rad - 2.6))])
        if hasattr(self, 'arrow'):
            # 只有当旧箭头的归属场景是当前场景时，才删除（避免scene不匹配）
            if self.arrow.scene() == self.scene():
                self.scene().removeItem(self.arrow)
            # （可选）删除旧箭头的引用，避免内存泄漏
            delattr(self, 'arrow')
        self.arrow = QGraphicsPolygonItem(arrow_head, parent=None)
        self.arrow.setBrush(QBrush(Qt.black))
        self.arrow.setPen(QPen(Qt.black))
        self.arrow.setZValue(-1)

        if self.scene() is not None:
            self.scene().addItem(self.arrow)

    def _draw_arrow(self, tip: QPointF, angle: float):
        """绘制与线条同颜色、同样式、z 值更高的箭头"""
        rad = np.radians(angle)
        arrow_size = 8
        p1 = tip + QPointF(arrow_size * np.cos(rad - 2.6),
                           arrow_size * np.sin(rad - 2.6))
        p2 = tip + QPointF(arrow_size * np.cos(rad + 2.6),
                           arrow_size * np.sin(rad + 2.6))
        head = QPolygonF([tip, p1, p2])

        # 1. 颜色/样式跟随线条
        line_pen = self.pen()  # 当前线条的 QPen
        arrow_brush = QBrush(line_pen.color())  # 填充色 = 线条色
        arrow_pen = QPen(line_pen.color())  # 画笔复制线条
        arrow_pen.setStyle(Qt.SolidLine)
        arrow_pen.setJoinStyle(Qt.MiterJoin)

        # 2. 删除旧箭头
        if hasattr(self, 'arrow') and self.arrow.scene() == self.scene():
            self.scene().removeItem(self.arrow)

        # 3. 创建新箭头
        self.arrow = QGraphicsPolygonItem(head)
        self.arrow.setBrush(arrow_brush)
        self.arrow.setPen(arrow_pen)
        # 关键：z 值高于线条
        self.arrow.setZValue(self.zValue() + 1)
        self.scene().addItem(self.arrow)

    def update_position_v2(self):
        scene = self.scene()
        if scene is None:
            return

        # 1. 注册到 scene.edges（仅一次）
        if not hasattr(scene, 'edges'):
            scene.edges = []
        if self not in scene.edges:
            scene.edges.append(self)

        # 2. 同一束边计数（无序 key）
        edge_key = tuple(sorted([self.start_node.node_id, self.end_node.node_id]))
        same_edges = [e for e in scene.edges
                      if tuple(sorted([e.start_node.node_id, e.end_node.node_id])) == edge_key]
        index = same_edges.index(self)
        total = len(same_edges)
        median = (total - 1) / 2.0
        base_offset = 50 * (index - median)
        # 方向符号：A->B 正，B->A 负
        if self.start_node.node_id < self.end_node.node_id:
            offset = base_offset
        else:
            offset = -base_offset

        # 3. 矩形边框交点（照搬你旧代码）
        def intersect_rect(rect: QRectF, line: QLineF):
            poly = [rect.topLeft(), rect.topRight(),
                    rect.bottomRight(), rect.bottomLeft()]
            for i in range(4):
                edge = QLineF(poly[i], poly[(i + 1) % 4])
                intersect_pt = QPointF()
                typ = line.intersect(edge, intersect_pt)
                if typ == QLineF.BoundedIntersection:
                    return intersect_pt
            # 保底
            return line.p1() if line.p1() != rect.center() else line.p2()

        r1 = self.start_node.sceneBoundingRect()
        r2 = self.end_node.sceneBoundingRect()
        center_line = QLineF(r1.center(), r2.center())
        inter_p1 = intersect_rect(r1, center_line)
        inter_p2 = intersect_rect(r2, center_line)

        # 4. 构造带偏移的二次贝塞尔
        mid = center_line.pointAt(0.5)
        normal = QPointF(-center_line.dy(), center_line.dx())
        if normal.isNull():
            normal = QPointF(1, 0)
        normal *= offset / (normal.x() ** 2 + normal.y() ** 2) ** 0.5
        mid += normal

        path = QPainterPath(inter_p1)
        path.quadTo(mid, inter_p2)
        self.setPath(path)

        # 5. 箭头方向沿末端切线
        angle = -path.angleAtPercent(1.0)
        self._draw_arrow(inter_p2, angle)

        # 6. 虚线样式
        pen = self.pen()
        if self.edge_type == 'condition':
            pen.setStyle(Qt.DashLine)
            pen.setColor(QColor(200, 50, 50))
        else:
            pen.setStyle(Qt.SolidLine)
        self.setPen(pen)

        # ---------- 7. 显示文字描述 ----------
        if self.edge_data:
            self.label.setPlainText(str(self.edge_data))
            mid_pt = path.pointAtPercent(0.5)
            normal = QPointF(-center_line.dy(), center_line.dx())
            normal /= (normal.x() ** 2 + normal.y() ** 2) ** 0.5
            label_offset = 15
            label_pos = mid_pt + normal * label_offset
            self.label.setPos(label_pos)

            # 背景矩形：比文字大 4 像素
            rect = self.label.boundingRect()
            rect.adjust(-4, -4, 4, 4)  # 四周留 4px 边距
            self.label_bg.setRect(rect)
            self.label_bg.setPos(label_pos)

            self.label.setVisible(True)
            self.label_bg.setVisible(True)
        else:
            self.label.setVisible(False)
            self.label_bg.setVisible(False)


# ---------------- 视图 ----------------
class GraphWidget(QGraphicsView):
    '''
    用于显示langgraph的图结构
    '''
    node_selected = pyqtSignal(str)

    def __init__(self, graph_structure):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene.setSceneRect(0, 0, 1000, 1000)

        self.nodes, self.edges = {}, []
        self.create_graph(graph_structure)

        self.ctrl_pressed = False  # Ctrl键状态
        self.is_panning = False

        # 刷新图布局
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_position)
        self.timer.start(100)  # 每5秒刷新一次布局

    def create_graph(self, g):
        if not g: return
        # 用 networkx 计算布局
        G = nx.DiGraph()
        G.add_nodes_from([n['id'] for n in g['nodes']])
        G.add_edges_from([(e['from'], e['to']) for e in g['edges']])

        # 布局算法可选：spring, kamada_kawai, dot(需pygraphviz), planar...
        # pos = nx.spring_layout(G, seed=42, k=2, iterations=50)
        pos = graphviz_layout(G, prog='dot')
        transformed_pos = self.transform_graphviz_layout_to_scene(
            pos, self.scene.sceneRect() , scale_factor=0.5, flip_y=True)
        # 创建节点
        for node in g['nodes']:
            # p = QPointF(*pos[node['id']] * 200)  # 放大坐标
            # coords = [coord * 2 for coord in pos[node['id']]]  # 缩放
            # coords[1] = -coords[1]  # y轴反转
            # p = QPointF(*coords)
            p = transformed_pos.get(node['id'])  # 使用转换后的坐标

            n = GraphNode(node['id'], node['name'], p, node_type=node.get('node_type', 'normal'))
            self.nodes[node['id']] = n
            self.scene.addItem(n)

        # 创建边
        for e in g['edges']:
            if e['from'] in self.nodes and e['to'] in self.nodes:
                edge = GraphEdge(self.nodes[e['from']], self.nodes[e['to']], edge_type=e.get('type', 'normal'),data=e.get('data', None))
                self.edges.append(edge)
                self.scene.addItem(edge)

        # 把 edges 引用挂到 scene，方便全局刷新
        self.scene.edges = self.edges

    import networkx as nx
    from PyQt5.QtCore import QRectF, QPointF

    def transform_graphviz_layout_to_scene(self, pos, scene_rect, scale_factor=0.8, flip_y=True):
        """
        将 graphviz_layout 生成的坐标转换为 QGraphicsScene 中的居中坐标（修复Y轴反转问题）

        参数:
            pos: dict，graphviz_layout 返回的节点坐标字典，格式 {node_id: (x, y)}
            scene_rect: QRectF，画布范围（如 QRectF(0, 0, 1000, 1000)）
            scale_factor: float，图占画布的比例（0.8 表示留 20% 边距）
            flip_y: bool，是否反转 y 轴（基于图的中心反转，避免跑出窗口）

        返回:
            transformed_pos: dict，转换后的节点坐标字典，格式 {node_id: QPointF(x, y)}
        """
        if not pos:  # 处理空图情况
            return {}

        # -------------------------- 步骤1：计算图的原始边界和中心（关键：翻转的基准）
        all_coords = list(pos.values())
        all_x = [x for x, y in all_coords]
        all_y = [y for x, y in all_coords]

        # 图的原始边界（left/right：X方向；top/bottom：Y方向）
        graph_left, graph_right = min(all_x), max(all_x)
        graph_top, graph_bottom = min(all_y), max(all_y)
        # 图的原始中心（翻转Y轴的基准点）
        graph_center_x = (graph_left + graph_right) / 2
        graph_center_y = (graph_top + graph_bottom) / 2  # 重点：基于这个中心翻转Y轴
        # 图的原始宽高（用于计算缩放比例）
        graph_width = graph_right - graph_left
        graph_height = graph_bottom - graph_top

        # 处理单节点场景（避免除以0）
        graph_width = graph_width if graph_width != 0 else 1.0
        graph_height = graph_height if graph_height != 0 else 1.0

        # -------------------------- 步骤2：对每个节点先做「基于图中心的Y轴反转」
        flipped_pos = {}  # 存储翻转后的原始坐标
        for node_id, (x, y) in pos.items():
            if flip_y:
                # 核心公式：基于图的Y中心翻转 → 新Y = 2*图中心Y - 原始Y
                # 原理：以图中心为对称轴，上下对称翻转（比如中心Y=100，原始Y=120 → 翻转后Y=80）
                flipped_y = 2 * graph_center_y - y
                flipped_pos[node_id] = (x, flipped_y)
            else:
                flipped_pos[node_id] = (x, y)  # 不翻转则直接保留原始坐标

        # -------------------------- 步骤3：缩放（基于翻转后的坐标）
        # 计算缩放比例（确保图不超过画布的 scale_factor 比例）
        scale_x = (scene_rect.width() * scale_factor) / graph_width
        scale_y = (scene_rect.height() * scale_factor) / graph_height
        scale = min(scale_x, scale_y)  # 取最小比例，避免图超出画布

        # 重新提取翻转后的坐标，计算缩放后的图中心（用于后续偏移）
        flipped_coords = list(flipped_pos.values())
        flipped_all_x = [x for x, y in flipped_coords]
        flipped_all_y = [y for x, y in flipped_coords]
        # 缩放后的图中心（因缩放是均匀的，也可直接用 原始中心 * 缩放比例，结果一致）
        scaled_graph_center_x = (min(flipped_all_x) + max(flipped_all_x)) / 2 * scale
        scaled_graph_center_y = (min(flipped_all_y) + max(flipped_all_y)) / 2 * scale

        # -------------------------- 步骤4：居中偏移（基于画布中心）
        canvas_center_x = scene_rect.center().x()
        canvas_center_y = scene_rect.center().y()
        # 偏移量：画布中心 - 缩放后的图中心（确保图整体居中）
        offset_x = canvas_center_x - scaled_graph_center_x
        offset_y = canvas_center_y - scaled_graph_center_y

        # -------------------------- 步骤5：计算最终坐标（缩放 + 偏移）
        transformed_pos = {}
        for node_id, (x, y) in flipped_pos.items():
            final_x = x * scale + offset_x
            final_y = y * scale + offset_y
            transformed_pos[node_id] = QPointF(final_x, final_y)

        return transformed_pos

    def update_graph_state(self, state):
        cur = state.get('current_node')
        for nid, node in self.nodes.items():
            node.set_current(nid == cur)
        self.refresh_position()



    def refresh_position(self):
        # 刷新所有边的位置
        for edge in self.edges:
            edge.update_position_v2()

    # 2. 监听 Ctrl 按键按下/松开，更新 ctrl_pressed 状态
    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Control:
            self.ctrl_pressed = True
        super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        if ev.key() == Qt.Key_Control:
            self.ctrl_pressed = False
            # Ctrl松开时，若处于平移状态，恢复拖拽模式
            if self.is_panning:
                self.setDragMode(QGraphicsView.NoDrag)
                self.is_panning = False
        super().keyReleaseEvent(ev)

    def mousePressEvent(self, ev):
        # 情况1：Ctrl + 鼠标左键 → 启用平移模式
        if self.ctrl_pressed and ev.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.is_panning = True  # 标记进入平移状态
            # 手动触发父类的鼠标按下事件，确保平移生效
            super().mousePressEvent(ev)

        # 情况2：未按Ctrl + 左键点击节点 → 触发节点选择
        elif not self.ctrl_pressed and ev.button() == Qt.LeftButton:
            item = self.itemAt(ev.pos())
            if isinstance(item, GraphNode):
                self.node_selected.emit(item.node_id)
            # 未点击节点时，不触发平移（拖拽模式仍为NoDrag）
            # super().mousePressEvent(ev) # 可选：若想允许节点拖动，可启用此行
        # 其他情况（如右键、中键）：按默认逻辑处理
        else:
            super().mousePressEvent(ev)



    # 4. 鼠标松开时恢复初始拖拽模式
    def mouseReleaseEvent(self, ev):
        # 若处于平移状态，松开左键后恢复NoDrag
        if self.is_panning and ev.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.is_panning = False
        super().mouseReleaseEvent(ev)

    # 5. 鼠标移动时：确保平移状态下正常响应
    def mouseMoveEvent(self, ev):
        # 只有处于平移状态时，才触发父类的移动事件（保证平移流畅）
        if self.is_panning:
            super().mouseMoveEvent(ev)
        else:
            # 非平移状态下，可按需处理（如节点hover效果）
            super().mouseMoveEvent(ev)

    def wheelEvent(self, ev):
        factor = 1.15 if ev.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor)


# 测试入口
if __name__ == "__main__":

    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
    import sys
    from PyQt5.QtCore import QTimer

    # 创建Qt应用实例
    app = QApplication(sys.argv)

    # 创建主测试窗口
    main_window = QWidget()
    main_window.setWindowTitle("GraphWidget 测试")
    main_window.resize(1000, 600)

    # 创建布局
    layout = QVBoxLayout(main_window)

    # 创建状态显示标签
    status_label = QLabel("当前选中的节点: 无")
    layout.addWidget(status_label)

    # 创建示例图结构
    test_graph = {
        "nodes": [
            {"id": "start", "name": "开始", "type": "start"},
            {"id": "input", "name": "输入处理"},
            {"id": "decision", "name": "决策节点"},
            {"id": "action1", "name": "动作1"},
            {"id": "action2", "name": "动作2"},
            {"id": "end", "name": "结束", "type": "end"}
        ],
        "edges": [
            {"from": "start", "to": "input"},
            {"from": "input", "to": "decision"},
            {"from": "decision", "to": "action1", "type": "condition"},
            {"from": "decision", "to": "action2"},
            {"from": "action1", "to": "end"},
            {"from": "action2", "to": "end"}
        ]
    }

    # 创建图形组件
    graph_widget = GraphWidget(test_graph)
    layout.addWidget(graph_widget)


    # 连接节点选择信号
    def on_node_selected(node_id):
        status_label.setText(f"当前选中的节点: {node_id}")


    graph_widget.node_selected.connect(on_node_selected)

    # 添加控制按钮
    control_layout = QVBoxLayout()
    cycle_button = QPushButton("开始节点循环")
    reset_button = QPushButton("重置状态")

    control_layout.addWidget(cycle_button)
    control_layout.addWidget(reset_button)
    layout.addLayout(control_layout)

    # 节点循环展示功能
    node_ids = [node["id"] for node in test_graph["nodes"]]
    current_index = 0
    timer = QTimer()


    def cycle_nodes():
        global current_index
        current_node_id = node_ids[current_index]
        graph_widget.update_graph_state({"current_node": current_node_id})
        current_index = (current_index + 1) % len(node_ids)


    def start_cycle():
        if not timer.isActive():
            timer.timeout.connect(cycle_nodes)
            timer.start(1000)  # 每秒切换一个节点
            cycle_button.setText("停止节点循环")
        else:
            timer.stop()
            cycle_button.setText("开始节点循环")


    def reset_graph():
        timer.stop()
        cycle_button.setText("开始节点循环")
        graph_widget.update_graph_state({"current_node": None})
        status_label.setText("当前选中的节点: 无")


    cycle_button.clicked.connect(start_cycle)
    reset_button.clicked.connect(reset_graph)

    # 显示窗口
    main_window.show()

    # 启动应用事件循环
    sys.exit(app.exec_())
