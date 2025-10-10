from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QSizePolicy

app = QApplication([])

# 1. 父窗口一开始就很小 → 布局被迫压缩子控件
w = QWidget()
w.resize(220, 200)          # 关键：初始宽度 220
w.setMaximumWidth(220)

lab = QLabel("A" * 200)
lab.setWordWrap(True)
lab.setMaximumWidth(200)
lab.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

layout = QVBoxLayout(w)
layout.addWidget(lab)

w.show()
# 2. 等待一次事件循环，让布局完成压缩
app.processEvents()
# 3. 再计算高度
lab.adjustSize()
print("width :", lab.width())   # 应该 ≤ 200
print("height:", lab.height())  # 现在 > 15
app.exec_()
