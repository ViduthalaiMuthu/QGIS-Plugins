# QGIS_Transformer_Studio_V1
# Copyright (C) 2026 Viduthalai Muthu M
# Licensed under the GNU General Public License v2 or later.
# See LICENSE for details.

import json
import os
import traceback
from pathlib import Path

from qgis.PyQt.QtCore import Qt, QPointF, QRectF
from qgis.PyQt.QtGui import QAction, QBrush, QPen, QColor, QFont, QPainterPath
from qgis.PyQt.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QFileDialog, QMessageBox, QLabel, QLineEdit,
    QFormLayout, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QMenu, QCheckBox
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsProcessingContext, QgsProcessingFeedback, QgsApplication, QgsFeature
)
import processing

from .processing.provider import TransformerProvider


TYPE_COLORS = {
    "VECTOR": QColor("#2563eb"),
    "RASTER": QColor("#9333ea"),
    "TABLE": QColor("#d97706"),
    "FILE": QColor("#64748b"),
    "FOLDER": QColor("#0891b2"),
    "COLLECTION": QColor("#16a34a"),
    "ANY": QColor("#6b7280"),
    "POINT": QColor("#0ea5e9"),
    "LINE": QColor("#14b8a6"),
    "POLYGON": QColor("#f59e0b"),
}

TRANSFORMERS = {
    # Readers
    "Vector Reader": dict(category="Readers", inputs=[], outputs=["OUTPUT"], out_types={"OUTPUT":"VECTOR"}, kind="reader"),
    "Raster Reader": dict(category="Readers", inputs=[], outputs=["OUTPUT"], out_types={"OUTPUT":"RASTER"}, kind="reader"),
    "Table Reader": dict(category="Readers", inputs=[], outputs=["OUTPUT"], out_types={"OUTPUT":"TABLE"}, kind="reader"),
    "Database Reader": dict(category="Readers", inputs=[], outputs=["OUTPUT"], out_types={"OUTPUT":"VECTOR"}, kind="reader"),
    # Geometry
    "Buffer": dict(category="Geometry", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Clip": dict(category="Geometry", inputs=["INPUT","OVERLAY"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR","OVERLAY":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Dissolve": dict(category="Geometry", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Intersection": dict(category="Geometry", inputs=["INPUT","OVERLAY"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR","OVERLAY":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Difference": dict(category="Geometry", inputs=["INPUT","OVERLAY"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR","OVERLAY":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Centroid": dict(category="Geometry", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"POINT"}),
    "Fix Geometry": dict(category="Quality Control", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    # Attributes
    "Field Calculator": dict(category="Attributes", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Filter by Expression": dict(category="Attributes", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    "Merge Vector Layers": dict(category="Attributes", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    # CRS
    "Reproject": dict(category="CRS", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"VECTOR"}, out_types={"OUTPUT":"VECTOR"}),
    # Raster
    "Raster Calculator": dict(category="Raster", inputs=["INPUT"], outputs=["OUTPUT"], in_types={"INPUT":"RASTER"}, out_types={"OUTPUT":"RASTER"}),
    # Writers
    "Vector Writer": dict(category="Writers", inputs=["INPUT"], outputs=[], in_types={"INPUT":"VECTOR"}, out_types={}, kind="writer"),
    "Raster Writer": dict(category="Writers", inputs=["INPUT"], outputs=[], in_types={"INPUT":"RASTER"}, out_types={}, kind="writer"),
}


def compatible_types(source_type, target_type):
    if source_type == "ANY" or target_type == "ANY":
        return True
    if source_type == target_type:
        return True
    if target_type == "VECTOR" and source_type in {"POINT", "LINE", "POLYGON"}:
        return True
    return False


def port_type(node_name, direction, port):
    spec = TRANSFORMERS[node_name]
    if direction == "input":
        return spec.get("in_types", {}).get(port, "ANY")
    return spec.get("out_types", {}).get(port, "ANY")


class PortItem(QGraphicsEllipseItem):
    R = 6
    def __init__(self, node, port_name, kind, y):
        x = -self.R if kind == "input" else node.WIDTH - self.R
        super().__init__(x, y - self.R, self.R*2, self.R*2, node)
        self.node = node
        self.port_name = port_name
        self.port_kind = kind
        ptype = port_type(node.name, kind, port_name)
        self.ptype = ptype
        self.setBrush(QBrush(TYPE_COLORS.get(ptype, TYPE_COLORS["ANY"])))
        self.setPen(QPen(QColor("#ffffff"), 1.2))
        self.setZValue(10)
        self.setToolTip(f"{kind.title()}: {port_name} [{ptype}]")

    def center_scene(self):
        return self.sceneBoundingRect().center()


class NodeItem(QGraphicsRectItem):
    WIDTH = 230
    HEIGHT = 122

    def __init__(self, node_id, name, studio):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)
        self.node_id = node_id
        self.name = name
        self.studio = studio
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setBrush(QBrush(QColor("#f8fafc")))
        self.setPen(QPen(QColor("#64748b"), 1.4))
        self.title = QGraphicsTextItem(name, self)
        self.title.setDefaultTextColor(QColor("#0f172a"))
        self.title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title.setPos(12, 7)

        spec = TRANSFORMERS[name]
        cat = QGraphicsTextItem(spec["category"], self)
        cat.setDefaultTextColor(QColor("#64748b"))
        cat.setFont(QFont("Arial", 8))
        cat.setPos(12, 30)

        self.in_ports = {}
        self.out_ports = {}
        y = 61
        for port in spec["inputs"]:
            p = PortItem(self, port, "input", y)
            self.in_ports[port] = p
            lab = QGraphicsTextItem(f"{port} [{port_type(name,'input',port)}]", self)
            lab.setDefaultTextColor(TYPE_COLORS.get(port_type(name,'input',port), QColor("#475569")))
            lab.setFont(QFont("Arial", 7))
            lab.setPos(7, y - 8)
            y += 22

        y = 61
        for port in spec["outputs"]:
            p = PortItem(self, port, "output", y)
            self.out_ports[port] = p
            lab = QGraphicsTextItem(f"{port} [{port_type(name,'output',port)}]", self)
            lab.setDefaultTextColor(TYPE_COLORS.get(port_type(name,'output',port), QColor("#475569")))
            lab.setFont(QFont("Arial", 7))
            lab.setPos(self.WIDTH - 122, y - 8)
            y += 22

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.studio.update_edges()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        self.studio.configure_node(self)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        cfg = menu.addAction("Configure")
        dup = menu.addAction("Duplicate")
        prev = menu.addAction("Preview Output")
        menu.addSeparator()
        disable = menu.addAction("Disable / Enable")
        delete = menu.addAction("Delete")
        chosen = menu.exec(event.screenPos())
        if chosen == cfg:
            self.studio.configure_node(self)
        elif chosen == dup:
            self.studio.duplicate_node(self)
        elif chosen == prev:
            self.studio.preview_node(self)
        elif chosen == disable:
            self.studio.toggle_node(self)
        elif chosen == delete:
            self.studio.delete_node(self)

    def paint(self, painter, option, widget=None):
        if self.studio.disabled_nodes.get(self.node_id, False):
            self.setOpacity(0.45)
        else:
            self.setOpacity(1.0)
        super().paint(painter, option, widget)


class EdgeItem(QGraphicsPathItem):
    def __init__(self, source_port, target_port, studio):
        super().__init__()
        self.source_port = source_port
        self.target_port = target_port
        self.studio = studio
        self.setPen(QPen(QColor("#16a34a"), 2.2))
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setToolTip(f"{source_port.node.name}.{source_port.port_name} → {target_port.node.name}.{target_port.port_name}")
        self.update_path()

    def update_path(self):
        s = self.source_port.center_scene()
        t = self.target_port.center_scene()
        dx = max(60.0, abs(t.x() - s.x()) * 0.45)
        path = QPainterPath(s)
        path.cubicTo(QPointF(s.x()+dx, s.y()), QPointF(t.x()-dx, t.y()), t)
        self.setPath(path)

    def contextMenuEvent(self, event):
        m = QMenu()
        d = m.addAction("Delete connection")
        if m.exec(event.screenPos()) == d:
            self.studio.delete_connection(self)


class WorkflowScene(QGraphicsScene):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
    def mousePressEvent(self, event):
        if self.studio.handle_scene_press(event): return
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self.studio.handle_scene_move(event): return
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if self.studio.handle_scene_release(event): return
        super().mouseReleaseEvent(event)


class WorkflowView(QGraphicsView):
    def __init__(self, scene, studio, parent=None):
        super().__init__(scene, parent)
        self.studio = studio
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setInteractive(True)
    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.studio.delete_selected_items(); event.accept(); return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            self.studio.duplicate_selected_items(); event.accept(); return
        if event.key() == Qt.Key.Key_F:
            self.studio.fit_workflow(); event.accept(); return
        if event.key() == Qt.Key.Key_0:
            self.studio.reset_view(); event.accept(); return
        super().keyPressEvent(event)


class ConfigureDialog(QDialog):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self.setWindowTitle(f"Configure — {node.name}")
        self.resize(520, 310)
        root = QVBoxLayout(self)
        form = QFormLayout()
        cfg = node.studio.node_configs.setdefault(node.node_id, {})
        self.widgets = {}

        if node.name in ("Vector Reader", "Raster Reader", "Table Reader"):
            self.path = QLineEdit(cfg.get("path", ""))
            browse = QPushButton("Browse…")
            browse.clicked.connect(self.browse_file)
            row = QHBoxLayout()
            row.addWidget(self.path); row.addWidget(browse)
            w = QWidget(); w.setLayout(row)
            form.addRow("Source:", w)
            if node.name == "Table Reader":
                self.xfield = QLineEdit(cfg.get("xfield", ""))
                self.yfield = QLineEdit(cfg.get("yfield", ""))
                self.crs = QLineEdit(cfg.get("crs", "EPSG:4326"))
                self.as_points = QCheckBox("Create points from X/Y")
                self.as_points.setChecked(bool(cfg.get("as_points", False)))
                form.addRow("X field:", self.xfield)
                form.addRow("Y field:", self.yfield)
                form.addRow("Point CRS:", self.crs)
                form.addRow("", self.as_points)

        elif node.name == "Database Reader":
            self.info = QLabel("V0.2 provides the typed Database Reader node.\nConnection dialogs for PostGIS/SpatiaLite/MSSQL/Oracle are reserved for the next database milestone.")
            self.info.setWordWrap(True)
            form.addRow(self.info)

        elif node.name == "Buffer":
            self.distance = QDoubleSpinBox(); self.distance.setRange(-1e9,1e9); self.distance.setDecimals(6)
            self.distance.setValue(float(cfg.get("DISTANCE",10.0)))
            self.segments = QDoubleSpinBox(); self.segments.setRange(1,1000); self.segments.setDecimals(0)
            self.segments.setValue(float(cfg.get("SEGMENTS",8)))
            form.addRow("Distance:", self.distance); form.addRow("Segments:", self.segments)

        elif node.name == "Reproject":
            self.crs = QLineEdit(cfg.get("CRS","EPSG:4326"))
            form.addRow("Target CRS:", self.crs)

        elif node.name in ("Vector Writer","Raster Writer"):
            self.path = QLineEdit(cfg.get("path",""))
            browse = QPushButton("Browse…"); browse.clicked.connect(self.browse_writer)
            row = QHBoxLayout(); row.addWidget(self.path); row.addWidget(browse)
            w=QWidget(); w.setLayout(row); form.addRow("Output:", w)

        elif node.name == "Dissolve":
            self.field = QLineEdit(cfg.get("FIELD",""))
            form.addRow("Dissolve field:", self.field)

        elif node.name == "Field Calculator":
            self.field = QLineEdit(cfg.get("FIELD","new_field"))
            self.expression = QLineEdit(cfg.get("EXPRESSION",""))
            form.addRow("Field:", self.field); form.addRow("Expression:", self.expression)

        elif node.name == "Filter by Expression":
            self.expression = QLineEdit(cfg.get("EXPRESSION",""))
            form.addRow("Expression:", self.expression)

        elif node.name == "Raster Calculator":
            self.expression = QLineEdit(cfg.get("EXPRESSION",""))
            form.addRow("Expression:", self.expression)

        else:
            form.addRow(QLabel("No additional parameters required for this transformer."))

        root.addLayout(form); root.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def browse_file(self):
        filters = {
            "Vector Reader":"Vector data (*.gpkg *.shp *.geojson *.json *.gdb *.kml *.kmz *.dxf *.parquet *.gml *.sqlite *.db);;All files (*.*)",
            "Raster Reader":"Raster data (*.tif *.tiff *.img *.jp2 *.vrt *.ecw *.sid *.asc *.nc *.hdf *.jpg *.jpeg *.png);;All files (*.*)",
            "Table Reader":"Tables (*.csv *.dbf *.parquet *.xlsx *.ods);;All files (*.*)"
        }
        p,_=QFileDialog.getOpenFileName(self,"Choose source","",filters[self.node.name])
        if p: self.path.setText(p)

    def browse_writer(self):
        filt = "GeoPackage (*.gpkg);;Shapefile (*.shp);;GeoJSON (*.geojson);;All files (*.*)" if self.node.name=="Vector Writer" else "GeoTIFF (*.tif);;All files (*.*)"
        p,_=QFileDialog.getSaveFileName(self,"Choose output","",filt)
        if p: self.path.setText(p)

    def save(self):
        cfg=self.node.studio.node_configs.setdefault(self.node.node_id,{})
        if self.node.name in ("Vector Reader","Raster Reader","Table Reader"):
            cfg["path"]=self.path.text().strip()
            if self.node.name=="Table Reader":
                cfg["xfield"]=self.xfield.text().strip(); cfg["yfield"]=self.yfield.text().strip()
                cfg["crs"]=self.crs.text().strip(); cfg["as_points"]=self.as_points.isChecked()
        elif self.node.name=="Buffer":
            cfg["DISTANCE"]=self.distance.value(); cfg["SEGMENTS"]=int(self.segments.value())
        elif self.node.name=="Reproject": cfg["CRS"]=self.crs.text().strip()
        elif self.node.name in ("Vector Writer","Raster Writer"): cfg["path"]=self.path.text().strip()
        elif self.node.name=="Dissolve": cfg["FIELD"]=self.field.text().strip()
        elif self.node.name=="Field Calculator":
            cfg["FIELD"]=self.field.text().strip(); cfg["EXPRESSION"]=self.expression.text().strip()
        elif self.node.name in ("Filter by Expression","Raster Calculator"):
            cfg["EXPRESSION"]=self.expression.text().strip()


class TransformerStudioWindow(QMainWindow):
    # Standalone workflow editor window. It intentionally does not use a
    # QGIS QDockWidget so the workspace does not shrink the map canvas.
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QGIS_Transformer_Studio_V1")
        self.setObjectName("QGIS_Transformer_Studio_Window")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.iface=iface
        self.node_counter=0
        self.nodes={}
        self.node_configs={}
        self.connections=[]
        self.edge_items=[]
        self.disabled_nodes={}
        self.pending_wire=None
        self.drag_wire=None
        self.last_results={}
        self.setObjectName("GIS_Transformer_Studio_Dock")

        root=QWidget(); self.setCentralWidget(root)
        main=QHBoxLayout(root)

        left=QVBoxLayout()
        title=QLabel("TRANSFORMER LIBRARY"); title.setFont(QFont("Arial",11,QFont.Weight.Bold)); left.addWidget(title)
        self.search=QLineEdit(); self.search.setPlaceholderText("Search transformers…"); self.search.textChanged.connect(self.filter_list); left.addWidget(self.search)
        self.list=QListWidget(); self.populate_list(); self.list.itemDoubleClicked.connect(self.add_selected_transformer); left.addWidget(self.list,1)
        add=QPushButton("＋ Add to Canvas"); add.clicked.connect(self.add_selected_transformer); left.addWidget(add)
        main.addLayout(left,0)

        center=QVBoxLayout()
        bar=QHBoxLayout()
        for label,fn in [("New",self.new_workflow),("Open",self.open_workflow),("Save",self.save_workflow),("Validate",self.validate_workflow),("Run",self.run_workflow),("Fit",self.fit_workflow),("Reset View",self.reset_view),("Clear",self.clear_canvas)]:
            b=QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
        center.addLayout(bar)

        self.scene=WorkflowScene(self)
        self.scene.setSceneRect(0,0,4000,2400)
        self.view=WorkflowView(self.scene, self)
        center.addWidget(self.view,1)

        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(145); center.addWidget(self.log)
        self.status=QLabel("Ready — standalone workspace | drag from an output port to a compatible input port."); center.addWidget(self.status)
        guide_btn=QPushButton("User Guide")
        guide_btn.clicked.connect(self.show_user_guide)
        center.addWidget(guide_btn)
        main.addLayout(center,1)

        self.log_message("QGIS_Transformer_Studio_V1 V0.2.5 loaded — standalone workspace ready.")

    def populate_list(self):
        self.list.clear()
        for name,spec in TRANSFORMERS.items():
            item=QListWidgetItem(f"{spec['category']}  |  {name}")
            item.setData(Qt.ItemDataRole.UserRole,name); self.list.addItem(item)

    def filter_list(self,text):
        q=text.lower().strip()
        for i in range(self.list.count()):
            self.list.item(i).setHidden(q not in self.list.item(i).text().lower())

    def add_selected_transformer(self,item=None):
        if item is None: item=self.list.currentItem()
        if not item:return
        self.add_node(item.data(Qt.ItemDataRole.UserRole))

    def add_node(self,name,pos=None,node_id=None):
        if name not in TRANSFORMERS:
            self.log_message(f"❌ Unknown transformer: {name}")
            return None
        self.node_counter += 1
        nid = node_id or f"node_{self.node_counter}"
        node = NodeItem(nid, name, self)
        self.scene.addItem(node)
        if pos is None:
            center = self.view.mapToScene(self.view.viewport().rect().center())
            offset = len(self.nodes) * 28
            pos = QPointF(center.x() - node.WIDTH / 2 + offset, center.y() - node.HEIGHT / 2 + offset)
        node.setPos(pos)
        node.setVisible(True)
        node.setSelected(True)
        self.nodes[nid] = node
        self.node_configs.setdefault(nid,{})
        rect = self.scene.itemsBoundingRect().adjusted(-500,-500,500,500)
        self.scene.setSceneRect(rect.united(QRectF(0,0,4000,2400)))
        self.view.ensureVisible(node, 60, 60)
        self.view.centerOn(node)
        self.view.setFocus()
        self.log_message(f"Added {name} ({nid}) to canvas at ({node.x():.0f}, {node.y():.0f}).")
        return node

    def configure_node(self,node):
        dlg=ConfigureDialog(node,self)
        if dlg.exec()==QDialog.DialogCode.Accepted:
            dlg.save(); self.log_message(f"Configured {node.name} ({node.node_id}).")

    def scene_item_at_port(self,pos):
        item=self.scene.itemAt(pos, self.view.viewportTransform())
        return item if isinstance(item,PortItem) else None

    def handle_scene_press(self,event):
        port=self.scene_item_at_port(event.scenePos())
        if port and event.button()==Qt.MouseButton.LeftButton:
            if port.port_kind=="output":
                self.pending_wire=port
                self.status.setText(f"Dragging from {port.node.name}.{port.port_name} [{port.ptype}]…")
                return True
            if port.port_kind=="input" and self.pending_wire:
                self.finish_wire(port); return True
        return False

    def handle_scene_move(self,event):
        if self.pending_wire:
            self.update_edges(temp_pos=event.scenePos()); return True
        return False

    def handle_scene_release(self,event):
        if self.pending_wire:
            port=self.scene_item_at_port(event.scenePos())
            if port and port.port_kind=="input":
                self.finish_wire(port)
            else:
                self.pending_wire=None; self.update_edges(); self.status.setText("Connection cancelled.")
            return True
        return False

    def finish_wire(self,target):
        source=self.pending_wire
        self.pending_wire=None
        if source.node==target.node:
            self.status.setText("A node cannot connect to itself."); self.update_edges(); return
        if not compatible_types(source.ptype, target.ptype):
            QMessageBox.warning(self,"Incompatible connection",f"{source.ptype} output cannot connect to {target.ptype} input.")
            self.update_edges(); return
        # One connection per input port.
        self.connections=[c for c in self.connections if not (c["target"]==(target.node.node_id,target.port_name))]
        self.connections.append({"source":(source.node.node_id,source.port_name),"target":(target.node.node_id,target.port_name)})
        self.update_edges(); self.log_message(f"Connected {source.node.name}.{source.port_name} → {target.node.name}.{target.port_name}")

    def update_edges(self,temp_pos=None):
        for e in self.edge_items:
            self.scene.removeItem(e)
        self.edge_items=[]
        for c in self.connections:
            s=self.nodes.get(c["source"][0]); t=self.nodes.get(c["target"][0])
            if not s or not t: continue
            e=EdgeItem(s.out_ports[c["source"][1]],t.in_ports[c["target"][1]],self)
            self.scene.addItem(e); self.edge_items.append(e)
        if self.pending_wire and temp_pos:
            s=self.pending_wire.center_scene()
            path=QPainterPath(s)
            dx=max(60,abs(temp_pos.x()-s.x())*.45)
            path.cubicTo(QPointF(s.x()+dx,s.y()),QPointF(temp_pos.x()-dx,temp_pos.y()),temp_pos)
            e=QGraphicsPathItem(path); e.setPen(QPen(QColor("#94a3b8"),2,Qt.PenStyle.DashLine)); e.setZValue(-1)
            self.scene.addItem(e); self.edge_items.append(e)

    def delete_connection(self,edge):
        self.connections=[c for c in self.connections if not (
            c["source"]==(edge.source_port.node.node_id,edge.source_port.port_name) and
            c["target"]==(edge.target_port.node.node_id,edge.target_port.port_name)
        )]
        self.update_edges(); self.log_message("Connection deleted.")

    def delete_node(self,node):
        self.connections=[c for c in self.connections if c["source"][0]!=node.node_id and c["target"][0]!=node.node_id]
        self.nodes.pop(node.node_id,None); self.node_configs.pop(node.node_id,None); self.disabled_nodes.pop(node.node_id,None)
        self.scene.removeItem(node); self.update_edges(); self.log_message(f"Deleted {node.name}.")

    def duplicate_node(self,node):
        n=self.add_node(node.name,node.pos()+QPointF(35,35))
        self.node_configs[n.node_id]=dict(self.node_configs.get(node.node_id,{}))
        self.log_message(f"Duplicated {node.name}.")

    def toggle_node(self,node):
        self.disabled_nodes[node.node_id]=not self.disabled_nodes.get(node.node_id,False)
        self.log_message(f"{node.name}: {'disabled' if self.disabled_nodes[node.node_id] else 'enabled'}")
        self.scene.update()

    def delete_selected_items(self):
        for item in list(self.scene.selectedItems()):
            if isinstance(item,NodeItem): self.delete_node(item)
            elif isinstance(item,EdgeItem): self.delete_connection(item)
    def duplicate_selected_items(self):
        for item in list(self.scene.selectedItems()):
            if isinstance(item,NodeItem): self.duplicate_node(item)
    def fit_workflow(self):
        items=[i for i in self.scene.items() if isinstance(i,NodeItem)]
        if not items: self.reset_view(); return
        rect=self.scene.itemsBoundingRect().adjusted(-100,-100,100,100)
        self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.log_message("Canvas fitted to workflow.")
    def reset_view(self):
        self.view.resetTransform()
        self.view.centerOn(self.scene.sceneRect().center())
        self.log_message("Canvas view reset.")

    def new_workflow(self):
        if self.nodes and QMessageBox.question(self,"New workflow","Clear current workflow?")!=QMessageBox.StandardButton.Yes:return
        self.clear_canvas(); self.log_message("New workflow created.")

    def clear_canvas(self):
        self.scene.clear()
        self.nodes={}; self.node_configs={}; self.connections=[]; self.edge_items=[]
        self.disabled_nodes={}; self.pending_wire=None; self.node_counter=0; self.last_results={}
        self.scene.setSceneRect(0,0,4000,2400)
        self.reset_view()

    def save_workflow(self):
        path,_=QFileDialog.getSaveFileName(self,"Save workflow","","GIS Transformer Workflow (*.gtworkflow)")
        if not path:return
        if not path.lower().endswith(".gtworkflow"):path+=".gtworkflow"
        data={"format":"QGIS_Transformer_Studio_V1 Workflow","version":"0.2","qgis_major":4,"nodes":[],"connections":self.connections,"disabled":self.disabled_nodes}
        for nid,node in self.nodes.items():
            p=node.pos(); data["nodes"].append({"id":nid,"name":node.name,"x":p.x(),"y":p.y(),"config":self.node_configs.get(nid,{})})
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        self.log_message(f"Workflow saved: {path}")

    def open_workflow(self):
        path,_=QFileDialog.getOpenFileName(self,"Open workflow","","GIS Transformer Workflow (*.gtworkflow)")
        if not path:return
        try:
            with open(path,"r",encoding="utf-8") as f:data=json.load(f)
            self.clear_canvas()
            for n in data.get("nodes",[]):
                node=self.add_node(n["name"],QPointF(float(n.get("x",80)),float(n.get("y",80))),n["id"])
                self.node_configs[node.node_id]=n.get("config",{})
            self.connections=data.get("connections",[]); self.disabled_nodes=data.get("disabled",{})
            self.update_edges(); self.log_message(f"Workflow opened: {path}")
        except Exception as e:
            QMessageBox.critical(self,"Open workflow failed",str(e))

    def incoming(self,nid):
        return [c for c in self.connections if c["target"][0]==nid]

    def has_cycle(self):
        graph={n:[] for n in self.nodes}
        for c in self.connections: graph.setdefault(c["source"][0],[]).append(c["target"][0])
        visiting=set(); visited=set()
        def dfs(n):
            if n in visiting:return True
            if n in visited:return False
            visiting.add(n)
            for x in graph.get(n,[]):
                if dfs(x):return True
            visiting.remove(n); visited.add(n); return False
        return any(dfs(n) for n in graph)

    def topological_order(self):
        indeg={n:0 for n in self.nodes}; graph={n:[] for n in self.nodes}
        for c in self.connections:
            a,b=c["source"][0],c["target"][0]; graph[a].append(b); indeg[b]+=1
        q=[n for n,d in indeg.items() if d==0]; order=[]
        while q:
            n=q.pop(0); order.append(n)
            for b in graph[n]:
                indeg[b]-=1
                if indeg[b]==0:q.append(b)
        return order if len(order)==len(self.nodes) else []

    def validate_workflow(self,quiet=False):
        errors=[]
        if not self.nodes:errors.append("Workflow contains no transformers.")
        if self.has_cycle():errors.append("Workflow contains a cycle.")
        for nid,node in self.nodes.items():
            if self.disabled_nodes.get(nid):continue
            spec=TRANSFORMERS[node.name]; cfg=self.node_configs.get(nid,{})
            incoming={(c["target"][0],c["target"][1]):c for c in self.incoming(nid)}
            for port in spec["inputs"]:
                if (nid,port) not in incoming:errors.append(f"{node.name} ({nid}): input '{port}' is not connected.")
            if node.name in ("Vector Reader","Raster Reader","Table Reader") and not cfg.get("path"):
                errors.append(f"{node.name} ({nid}): source is not configured.")
            if node.name in ("Vector Reader","Raster Reader","Table Reader") and cfg.get("path") and not os.path.exists(cfg["path"]):
                errors.append(f"{node.name} ({nid}): source does not exist: {cfg['path']}")
            if node.name=="Reproject" and not cfg.get("CRS"):errors.append(f"Reproject ({nid}): target CRS is missing.")
            if node.name in ("Vector Writer","Raster Writer") and not cfg.get("path"):errors.append(f"{node.name} ({nid}): output is missing.")
            for c in self.incoming(nid):
                src=self.nodes.get(c["source"][0])
                if src:
                    st=port_type(src.name,"output",c["source"][1]); tt=port_type(node.name,"input",c["target"][1])
                    if st!="ANY" and tt!="ANY" and st!=tt:errors.append(f"Type mismatch: {src.name} [{st}] → {node.name} [{tt}].")
        if errors:
            self.log_message("Validation failed:")
            for e in errors:self.log_message("  ❌ "+e)
            if not quiet:QMessageBox.warning(self,"Workflow validation","\n".join(errors))
            return False
        self.log_message("✓ Workflow validation successful.")
        if not quiet:QMessageBox.information(self,"Workflow validation","Workflow is valid.")
        return True

    def run_workflow(self):
        if not self.validate_workflow(True):
            QMessageBox.warning(self,"Cannot run","Fix validation errors first."); return
        order=self.topological_order()
        if not order:
            QMessageBox.warning(self,"Cannot run","Workflow graph could not be ordered."); return
        context=QgsProcessingContext(); feedback=QgsProcessingFeedback(); results={}
        try:
            self.log_message("▶ Starting workflow execution…")
            for nid in order:
                node=self.nodes[nid]; name=node.name; cfg=self.node_configs.get(nid,{})
                if self.disabled_nodes.get(nid):
                    self.log_message(f"⏭ Skipping disabled node: {name}")
                    continue
                params={}
                for c in self.incoming(nid):
                    params[c["target"][1]]=results[c["source"][0]]
                self.log_message(f"▶ {name} ({nid})")
                if name=="Vector Reader":
                    layer=QgsVectorLayer(cfg["path"],Path(cfg["path"]).stem,"ogr")
                    if not layer.isValid():raise RuntimeError(f"Could not load vector: {cfg['path']}")
                    results[nid]=layer
                elif name=="Raster Reader":
                    layer=QgsRasterLayer(cfg["path"],Path(cfg["path"]).stem)
                    if not layer.isValid():raise RuntimeError(f"Could not load raster: {cfg['path']}")
                    results[nid]=layer
                elif name=="Table Reader":
                    layer=QgsVectorLayer(cfg["path"],Path(cfg["path"]).stem,"ogr")
                    if not layer.isValid():raise RuntimeError(f"Could not load table: {cfg['path']}")
                    if cfg.get("as_points") and cfg.get("xfield") and cfg.get("yfield"):
                        p={"INPUT":layer,"X_FIELD":cfg["xfield"],"Y_FIELD":cfg["yfield"],
                           "TARGET_CRS":QgsCoordinateReferenceSystem(cfg.get("crs","EPSG:4326")),
                           "OUTPUT":"TEMPORARY_OUTPUT"}
                        results[nid]=processing.run("native:createpointslayerfromtable",p,context=context,feedback=feedback)["OUTPUT"]
                    else: results[nid]=layer
                elif name=="Database Reader":
                    raise RuntimeError("Database Reader node is available in V0.2, but database connection execution is scheduled for the next milestone.")
                elif name=="Buffer":
                    results[nid]=processing.run("native:buffer",{"INPUT":params["INPUT"],"DISTANCE":cfg.get("DISTANCE",10.0),"SEGMENTS":cfg.get("SEGMENTS",8),"END_CAP_STYLE":0,"JOIN_STYLE":0,"MITER_LIMIT":2,"DISSOLVE":False,"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Clip":
                    results[nid]=processing.run("native:clip",{"INPUT":params["INPUT"],"OVERLAY":params["OVERLAY"],"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Dissolve":
                    f=cfg.get("FIELD","").strip(); results[nid]=processing.run("native:dissolve",{"INPUT":params["INPUT"],"FIELD":[f] if f else [],"SEPARATE_DISJOINT":False,"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Intersection":
                    results[nid]=processing.run("native:intersection",{"INPUT":params["INPUT"],"OVERLAY":params["OVERLAY"],"INPUT_FIELDS":[],"OVERLAY_FIELDS":[],"OVERLAY_FIELDS_PREFIX":"","GRID_SIZE":None,"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Difference":
                    results[nid]=processing.run("native:difference",{"INPUT":params["INPUT"],"OVERLAY":params["OVERLAY"],"GRID_SIZE":None,"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Centroid":
                    src_layer=params["INPUT"]
                    if not isinstance(src_layer,QgsVectorLayer): src_layer=QgsVectorLayer(str(src_layer),"Centroid input","ogr")
                    if not src_layer.isValid(): raise RuntimeError("Centroid input is not a valid vector layer.")
                    uri="Point" + (("?crs=" + src_layer.crs().authid()) if src_layer.crs().authid() else "")
                    out_layer=QgsVectorLayer(uri,f"{src_layer.name()}_centroids","memory")
                    if not out_layer.isValid(): raise RuntimeError("Could not create centroid point output layer.")
                    out_layer.dataProvider().addAttributes(list(src_layer.fields())); out_layer.updateFields()
                    provider=out_layer.dataProvider(); created=0; skipped=0
                    for feat in src_layer.getFeatures():
                        geom=feat.geometry()
                        if geom is None or geom.isNull() or geom.isEmpty(): skipped+=1; continue
                        centroid=geom.centroid()
                        if centroid.isNull() or centroid.isEmpty(): skipped+=1; continue
                        out_feat=QgsFeature(out_layer.fields()); out_feat.setAttributes(feat.attributes()); out_feat.setGeometry(centroid)
                        if not provider.addFeature(out_feat): raise RuntimeError(f"Could not add centroid feature for source feature {feat.id()}.")
                        created+=1
                    out_layer.updateExtents(); self.log_message(f"  Centroid created {created} point feature(s).")
                    if skipped: self.log_message(f"  Centroid skipped {skipped} null/empty feature(s).")
                    results[nid]=out_layer
                elif name=="Fix Geometry":
                    results[nid]=processing.run("native:fixgeometries",{"INPUT":params["INPUT"],"METHOD":1,"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Reproject":
                    crs=QgsCoordinateReferenceSystem(cfg["CRS"])
                    if not crs.isValid():raise RuntimeError(f"Invalid CRS: {cfg['CRS']}")
                    results[nid]=processing.run("native:reprojectlayer",{"INPUT":params["INPUT"],"TARGET_CRS":crs,"CONVERT_CURVED_GEOMETRIES":False,"OPERATION":"","OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Field Calculator":
                    results[nid]=processing.run("native:fieldcalculator",{"INPUT":params["INPUT"],"FIELD_NAME":cfg.get("FIELD","new_field"),"FIELD_TYPE":2,"FIELD_LENGTH":255,"FIELD_PRECISION":3,"FORMULA":cfg.get("EXPRESSION",""),"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Filter by Expression":
                    results[nid]=processing.run("native:extractbyexpression",{"INPUT":params["INPUT"],"EXPRESSION":cfg.get("EXPRESSION",""),"OUTPUT":"TEMPORARY_OUTPUT"},context=context,feedback=feedback)["OUTPUT"]
                elif name=="Merge Vector Layers":
                    results[nid]=processing.run("native:mergevectorlayers",{"LAYERS":[params["INPUT"]],"CRS":None,"OUTPUT":"TEMPORARY_OUTPUT"} ,context=context,feedback=feedback)["OUTPUT"]
                elif name=="Raster Calculator":
                    # Use GDAL's Processing raster calculator so the plugin does not
                    # depend on QgsRasterCalculator imports from qgis.core.
                    r = params["INPUT"]
                    formula = cfg.get("EXPRESSION", "A")
                    results[nid] = processing.run(
                        "gdal:rastercalculator",
                        {
                            "INPUT_A": r,
                            "BAND_A": 1,
                            "INPUT_B": None,
                            "BAND_B": None,
                            "INPUT_C": None,
                            "BAND_C": None,
                            "INPUT_D": None,
                            "BAND_D": None,
                            "INPUT_E": None,
                            "BAND_E": None,
                            "INPUT_F": None,
                            "BAND_F": None,
                            "FORMULA": formula,
                            "NO_DATA": None,
                            "RTYPE": 5,
                            "OPTIONS": "",
                            "EXTRA": "",
                            "OUTPUT": "TEMPORARY_OUTPUT"
                        },
                        context=context,
                        feedback=feedback
                    )["OUTPUT"]
                elif name=="Vector Writer":
                    out=processing.run("native:savefeatures",{"INPUT":params["INPUT"],"OUTPUT":cfg["path"],"LAYER_NAME":Path(cfg["path"]).stem,"DATASOURCE_OPTIONS":"","LAYER_OPTIONS":""},context=context,feedback=feedback)["OUTPUT"]; results[nid]=out
                elif name=="Raster Writer":
                    out=processing.run("gdal:translate",{"INPUT":params["INPUT"],"TARGET_CRS":None,"NODATA":None,"COPY_SUBDATASETS":False,"OPTIONS":"","EXTRA":"","DATA_TYPE":0,"OUTPUT":cfg["path"]},context=context,feedback=feedback)["OUTPUT"]; results[nid]=out
                self.log_message(f"✓ {name} complete.")
            self.last_results=results
            self.log_message("✓ Workflow completed successfully.")
            QMessageBox.information(self,"Workflow complete","Workflow completed successfully.")
        except Exception as e:
            self.log_message("❌ Workflow failed: "+str(e)); self.log_message(traceback.format_exc())
            QMessageBox.critical(self,"Workflow failed",str(e))

    def preview_node(self,node):
        if not self.validate_workflow(True):
            QMessageBox.warning(self,"Preview","Fix validation errors before preview."); return
        order=self.topological_order()
        if node.node_id not in order:return
        target_index=order.index(node.node_id)
        # Execute a truncated workflow by temporarily disabling downstream nodes.
        downstream=set(order[target_index+1:])
        old=dict(self.disabled_nodes)
        for n in downstream:self.disabled_nodes[n]=True
        try:
            self.run_workflow()
            result=self.last_results.get(node.node_id)
            if result and hasattr(result,"isValid"):
                if isinstance(result,QgsVectorLayer) or isinstance(result,QgsRasterLayer):
                    QgsProject.instance().addMapLayer(result)
                    self.log_message(f"Preview added to QGIS: {result.name()}")
        finally:
            self.disabled_nodes=old

    def log_message(self,msg):
        self.log.append(msg); self.status.setText(msg)

    def show_user_guide(self):
        """Open the bundled README as an in-plugin user manual."""
        guide = QTextBrowser(self)
        guide.setWindowTitle("QGIS_Transformer_Studio_V1 — User Guide")
        guide.setOpenExternalLinks(True)
        guide.setReadOnly(True)

        readme_path = Path(__file__).with_name("README.md")
        try:
            markdown = readme_path.read_text(encoding="utf-8")
            # QTextDocument in Qt 6 supports Markdown rendering.
            guide.document().setMarkdown(markdown)
        except Exception as exc:
            guide.setPlainText(
                "Unable to load the bundled user guide.\n\n"
                f"README path: {readme_path}\n"
                f"Error: {exc}"
            )

        guide.resize(1100, 800)
        guide.showMaximized()

        # Keep a reference so Qt does not destroy the modeless guide immediately.
        self._user_guide = guide


class GisTransformerStudio:
    def __init__(self, iface):
        self.iface = iface
        self.window = None
        self.provider = None
        self.action = None

    def initGui(self):
        self.action = QAction("QGIS_Transformer_Studio_V1", self.iface.mainWindow())
        self.action.triggered.connect(self.show_window)
        self.iface.addPluginToMenu("&QGIS_Transformer_Studio_V1", self.action)
        self.iface.addToolBarIcon(self.action)

        self.provider = TransformerProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&QGIS_Transformer_Studio_V1", self.action)
            self.iface.removeToolBarIcon(self.action)

        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider.id())
            self.provider = None

        if self.window:
            self.window.close()
            self.window.deleteLater()
            self.window = None

    def show_window(self):
        if self.window is None:
            self.window = TransformerStudioWindow(
                self.iface,
                self.iface.mainWindow()
            )

        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        # Maximized keeps the native title bar and its Minimize,
        # Maximize/Restore and Close buttons.
        self.window.showMaximized()
