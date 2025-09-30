from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsPolygonItem,
                             QGraphicsTextItem,QGraphicsLineItem,QGraphicsItem,QGraphicsEllipseItem,QGraphicsPathItem
                             )
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QLineF, QRectF, QPoint
from PyQt5.QtGui import QBrush, QPen, QColor, QFont, QPainter,QPainterPath, QPolygonF
import networkx as nx
import numpy as np

class GraphNode(QGraphicsRectItem):
    def __init__(self, node_id, name, pos, width=120, height=60):
        super().__init__(0, 0, width, height)
        self.node_id = node_id
        self.setPos(pos)
        self.setBrush(QBrush(QColor(200, 220, 255)))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)   # 可拖动
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # 文字
        self.text = QGraphicsTextItem(name, self)
        rect = self.text.boundingRect()
        self.text.setPos(width/2 - rect.width()/2, height/2 - rect.height()/2)

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
                    edge.update_position()
        return super().itemChange(change, value)


# ---------------- 边（带箭头） ----------------
class GraphEdge(QGraphicsPathItem):
    def __init__(self, start_node, end_node):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        pen = QPen(Qt.black, 1.5)
        pen.setCapStyle(Qt.FlatCap)
        self.setPen(pen)
        self.update_position()

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
        angle = line.angle()
        arrow_size = 8
        rad = np.radians(angle)
        delta = QPointF(arrow_size * np.cos(rad + 2.6),
                        arrow_size * np.sin(rad + 2.6))
        arrow_head = QPolygonF([inter_p2,
                                inter_p2 + delta,
                                inter_p2 + QPointF(arrow_size * np.cos(rad - 2.6),
                                                   arrow_size * np.sin(rad - 2.6))])
        if hasattr(self, 'arrow'):
            self.scene().removeItem(self.arrow)
        self.arrow = QGraphicsPolygonItem(arrow_head, parent=None)
        self.arrow.setBrush(QBrush(Qt.black))
        self.arrow.setPen(QPen(Qt.black))
        self.arrow.setZValue(-1)


# ---------------- 视图 ----------------
class GraphWidget(QGraphicsView):
    node_selected = pyqtSignal(str)

    def __init__(self, graph_structure):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene.setSceneRect(-500, -500, 1000, 1000)

        self.nodes, self.edges = {}, []
        self.create_graph(graph_structure)

    def create_graph(self, g):
        if not g: return
        # 用 networkx 计算布局
        G = nx.DiGraph()
        G.add_nodes_from([n['id'] for n in g['nodes']])
        G.add_edges_from([(e['from'], e['to']) for e in g['edges']])

        # 布局算法可选：spring, kamada_kawai, dot(需pygraphviz), planar...
        pos = nx.spring_layout(G, seed=42, k=2, iterations=50)

        # 创建节点
        for node in g['nodes']:
            p = QPointF(*pos[node['id']] * 200)  # 放大坐标
            n = GraphNode(node['id'], node['name'], p)
            self.nodes[node['id']] = n
            self.scene.addItem(n)

        # 创建边
        for e in g['edges']:
            if e['from'] in self.nodes and e['to'] in self.nodes:
                edge = GraphEdge(self.nodes[e['from']], self.nodes[e['to']])
                self.edges.append(edge)
                self.scene.addItem(edge)

        # 把 edges 引用挂到 scene，方便全局刷新
        self.scene.edges = self.edges

    def update_graph_state(self, state):
        cur = state.get('current_node')
        for nid, node in self.nodes.items():
            node.set_current(nid == cur)
        for edge in self.edges:
            edge.update_position()

    def mousePressEvent(self, ev):
        item = self.itemAt(ev.pos())
        if isinstance(item, GraphNode):
            self.node_selected.emit(item.node_id)
        super().mousePressEvent(ev)

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
            {"id": "start", "name": "开始"},
            {"id": "input", "name": "输入处理"},
            {"id": "decision", "name": "决策节点"},
            {"id": "action1", "name": "动作1"},
            {"id": "action2", "name": "动作2"},
            {"id": "end", "name": "结束"}
        ],
        "edges": [
            {"from": "start", "to": "input"},
            {"from": "input", "to": "decision"},
            {"from": "decision", "to": "action1"},
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
