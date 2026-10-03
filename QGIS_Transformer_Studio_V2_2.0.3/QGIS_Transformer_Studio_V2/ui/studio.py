
import json
from pathlib import Path

from qgis.PyQt.QtCore import Qt, QPointF
from qgis.PyQt.QtGui import QBrush, QPen, QColor, QFont, QPainterPath
from qgis.PyQt.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QListWidget,QListWidgetItem,
    QGraphicsView,QGraphicsScene,QGraphicsItem,QGraphicsRectItem,QGraphicsTextItem,
    QGraphicsEllipseItem,QGraphicsPathItem,QLineEdit,QDialog,QDialogButtonBox,QFormLayout,
    QTextEdit,QMessageBox,QFileDialog,QLabel,QComboBox,QDoubleSpinBox,QCheckBox,QSpinBox,QProgressDialog,QApplication,QMenu
)
from qgis.core import QgsApplication, QgsProject, QgsProcessingFeedback, QgsProcessingException

from ..core.catalog import TRANSFORMER_CATALOG
from ..core.engine import CATALOG, default_parameters, algorithm_available, run_workflow

TYPE_COLORS={
    "VECTOR":QColor("#2563eb"),"RASTER":QColor("#9333ea"),"TABLE":QColor("#d97706"),
    "FILE":QColor("#64748b"),"COLLECTION":QColor("#16a34a"),"ANY":QColor("#6b7280"),
}

def port_type(name, direction, port):
    s=CATALOG[name]
    if direction=="output":
        return s.get("out_types",{}).get(port,"ANY")
    if name in ("Raster Reader", "Raster Writer") or (s.get("category")=="Raster" and port.startswith("INPUT")):
        return "RASTER"
    if name=="HTTP Caller": return "FILE"
    if name in ("Table Reader","CSV Reader"): return "TABLE"
    if name=="Parcel Downloader": return "VECTOR"
    return "VECTOR"

class Port(QGraphicsEllipseItem):
    def __init__(self,node,name,direction,y):
        super().__init__(-6 if direction=="input" else node.W-6,y-6,12,12,node)
        self.node=node; self.name=name; self.direction=direction
        self.ptype=port_type(node.name,direction,name)
        self.setBrush(QBrush(TYPE_COLORS.get(self.ptype,TYPE_COLORS["ANY"])))
        self.setPen(QPen(Qt.GlobalColor.white,1.2)); self.setZValue(10)
    def center(self): return self.sceneBoundingRect().center()

class Node(QGraphicsRectItem):
    W,H=260,130
    def __init__(self,studio,nid,name):
        super().__init__(0,0,self.W,self.H)
        self.studio=studio; self.node_id=nid; self.name=name
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemIsSelectable|QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor("#f8fafc"))); self.setPen(QPen(QColor("#475569"),1.4))
        title=QGraphicsTextItem(name,self); title.setFont(QFont("Arial",10,QFont.Weight.Bold)); title.setDefaultTextColor(QColor("#0f172a")); title.setPos(10,7)
        cat=QGraphicsTextItem(CATALOG[name]["category"],self); cat.setFont(QFont("Arial",8)); cat.setDefaultTextColor(QColor("#64748b")); cat.setPos(10,30)
        self.inputs={}; self.outputs={}
        y=62
        for p in CATALOG[name]["inputs"]:
            self.inputs[p]=Port(self,p,"input",y)
            lab=QGraphicsTextItem(f"{p} [{port_type(name,'input',p)}]",self); lab.setDefaultTextColor(TYPE_COLORS.get(port_type(name,'input',p),QColor("#475569"))); lab.setFont(QFont("Arial",7)); lab.setPos(8,y-8); y+=22
        y=62
        for p in CATALOG[name]["outputs"]:
            self.outputs[p]=Port(self,p,"output",y)
            lab=QGraphicsTextItem(f"{p} [{port_type(name,'output',p)}]",self); lab.setDefaultTextColor(TYPE_COLORS.get(port_type(name,'output',p),QColor("#475569"))); lab.setFont(QFont("Arial",7)); lab.setPos(self.W-125,y-8); y+=22
    def itemChange(self,change,value):
        if change==QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.studio.update_edges()
        return super().itemChange(change,value)
    def mouseDoubleClickEvent(self,e):
        self.studio.configure(self)
        e.accept()
    def contextMenuEvent(self,e):
        menu = QMenu()
        edit = menu.addAction("Configure")
        menu.addSeparator()
        delete = menu.addAction("Delete transformer")
        act = menu.exec(e.screenPos())
        if act is edit:
            self.studio.configure(self)
        elif act is delete:
            self.studio.remove_node(self.node_id)
        e.accept()
    def keyPressEvent(self,e):
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.studio.remove_node(self.node_id)
            e.accept(); return
        super().keyPressEvent(e)

class Edge(QGraphicsPathItem):
    def __init__(self,studio,conn):
        super().__init__(); self.studio=studio; self.conn=conn
        self.setPen(QPen(QColor("#16a34a"),2.3)); self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.update_path()
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.RightButton:
            menu=QMenu(); delete=menu.addAction("Delete connection")
            act=menu.exec(e.screenPos())
            if act is delete:
                self.studio.remove_connection(self.conn)
            e.accept(); return
        if e.button()==Qt.MouseButton.LeftButton:
            self.setSelected(True)
            self.setPen(QPen(QColor("#dc2626"),3.0))
            e.accept(); return
        super().mousePressEvent(e)
    def update_path(self):
        s=self.studio.nodes[self.conn["source"][0]].outputs[self.conn["source"][1]].center()
        t=self.studio.nodes[self.conn["target"][0]].inputs[self.conn["target"][1]].center()
        dx=max(60,abs(t.x()-s.x())*.45); p=QPainterPath(s); p.cubicTo(QPointF(s.x()+dx,s.y()),QPointF(t.x()-dx,t.y()),t); self.setPath(p)

class Canvas(QGraphicsScene):
    pass

class WorkflowView(QGraphicsView):
    def __init__(self, scene, studio):
        super().__init__(scene)
        self.studio=studio
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    def wheelEvent(self,e):
        f=1.15 if e.angleDelta().y()>0 else 1/1.15
        self.scale(f,f); e.accept()
    def mousePressEvent(self,e):
        p=self.studio._port_at(self.mapToScene(e.position().toPoint()))
        if p and e.button()==Qt.MouseButton.LeftButton:
            if p.direction=="output":
                self.studio.pending=p; self.studio.status.setText(f"Connecting {p.node.name}.{p.name} [{p.ptype}]…"); e.accept(); return
            if p.direction=="input" and self.studio.pending:
                self.studio._finish(p); e.accept(); return
        super().mousePressEvent(e)
    def mouseReleaseEvent(self,e):
        if self.studio.pending:
            p=self.studio._port_at(self.mapToScene(e.position().toPoint()))
            if p and p.direction=="input": self.studio._finish(p)
            else:
                self.studio.pending=None; self.studio.status.setText("Connection cancelled.")
            e.accept(); return
        super().mouseReleaseEvent(e)
    def keyPressEvent(self,e):
        if e.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected=list(self.scene().selectedItems())
            removed=False
            for item in selected:
                if isinstance(item, Node):
                    self.studio.remove_node(item.node_id); removed=True
                elif isinstance(item, Edge):
                    self.studio.remove_connection(item.conn); removed=True
            if removed:
                e.accept(); return
        super().keyPressEvent(e)

class ConfigDialog(QDialog):
    def __init__(self,node,parent=None):
        super().__init__(parent); self.node=node; self.setWindowTitle(f"Configure — {node.name}"); self.resize(760,560)
        root=QVBoxLayout(self); form=QFormLayout()
        self.info=QLabel(); self.info.setWordWrap(True)
        spec=CATALOG[node.name]
        aid=spec.get("algorithm") or "Built-in custom transformer"
        avail="Available" if (aid=="Built-in custom transformer" or algorithm_available(aid)) else "NOT AVAILABLE in this QGIS installation"
        self.info.setText(f"<b>{node.name}</b><br>Category: {spec['category']}<br>Engine: {aid}<br>Status: {avail}")
        root.addWidget(self.info)
        self.fields={}
        cfg=node.studio.configs.setdefault(node.node_id,{})
        if node.name in ("Vector Reader","GeoJSON Reader","GeoPackage Reader","Shapefile Reader","Raster Reader","Table Reader","CSV Reader"):
            self.path=QLineEdit(cfg.get("path","")); b=QPushButton("Browse…"); b.clicked.connect(self.browse)
            row=QHBoxLayout(); row.addWidget(self.path); row.addWidget(b); w=QWidget(); w.setLayout(row); form.addRow("Source:",w)
        elif node.name=="Database Reader":
            self.uri=QLineEdit(cfg.get("uri","")); form.addRow("Provider URI:",self.uri)
        elif node.name=="Parcel Downloader":
            self.fields = {}
            for key,label,default in [("url","FeatureServer URL (layer or /query)",""),("where","WHERE","1=1"),("out_fields","Out fields","*"),("out_sr","Output SRID","4326"),("geometry","Geometry JSON / bbox (optional)",""),("geometry_type","Geometry type","esriGeometryEnvelope"),("spatial_rel","Spatial relationship","esriSpatialRelIntersects"),("batch_size","Batch size","2000"),("timeout","Timeout (sec)","60"),("layer_name","Output layer name","parcels")]:
                w=QLineEdit(str(cfg.get(key,default))); self.fields[key]=w; form.addRow(label,w)
            self.output_format=QComboBox(); self.output_format.addItems(["GeoPackage","Shapefile","GeoJSON","CSV"]); self.output_format.setCurrentText(cfg.get("output_format","GeoPackage"))
            self.output=QLineEdit(str(cfg.get("output",""))); bout=QPushButton("Browse…"); bout.clicked.connect(self.browse_parcel_output)
            row=QHBoxLayout(); row.addWidget(self.output); row.addWidget(bout); w=QWidget(); w.setLayout(row)
            form.addRow("Output file/folder:",w); form.addRow("Output format:",self.output_format)
            note=QLabel("Leave output empty for a temporary file. A missing extension is added automatically. Existing output layers are overwritten safely.")
            note.setWordWrap(True); note.setStyleSheet("color:#64748b;"); form.addRow(note)
        elif node.name=="HTTP Caller":
            self.method=QComboBox(); self.method.addItems(["GET","POST","PUT","PATCH","DELETE"]); self.method.setCurrentText(cfg.get("method","GET"))
            self.url=QLineEdit(cfg.get("url","")); self.headers=QLineEdit(cfg.get("headers","{}")); self.query=QLineEdit(cfg.get("query","{}")); self.body=QTextEdit(cfg.get("body","")); self.timeout=QSpinBox(); self.timeout.setRange(1,3600); self.timeout.setValue(int(cfg.get("timeout",60)))
            form.addRow("Method:",self.method); form.addRow("URL:",self.url); form.addRow("Headers JSON:",self.headers); form.addRow("Query JSON:",self.query); form.addRow("Body:",self.body); form.addRow("Timeout:",self.timeout)
        elif spec.get("kind")=="writer":
            self.path=QLineEdit(cfg.get("path","")); b=QPushButton("Browse…"); b.clicked.connect(self.browse_writer); row=QHBoxLayout(); row.addWidget(self.path); row.addWidget(b); w=QWidget(); w.setLayout(row); form.addRow("Output:",w)
        else:
            params=cfg.get("params")
            if params is None:
                params=default_parameters(spec["algorithm"]) if spec.get("algorithm") else {}
            self.json_edit=QTextEdit(json.dumps(params,indent=2,default=str)); form.addRow("Processing parameters JSON:",self.json_edit)
            helpb=QPushButton("Show QGIS algorithm help")
            helpb.clicked.connect(self.show_help); root.addWidget(helpb)
        root.addLayout(form); root.addStretch()
        bb=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); root.addWidget(bb)
    def browse(self):
        p,_=QFileDialog.getOpenFileName(self,"Choose source",""); 
        if p:self.path.setText(p)
    def browse_writer(self):
        p,_=QFileDialog.getSaveFileName(self,"Choose output",""); 
        if p:self.path.setText(p)
    def browse_parcel_output(self):
        fmt=self.output_format.currentText() if hasattr(self,"output_format") else "GeoPackage"
        filters={"GeoPackage":"GeoPackage (*.gpkg)","Shapefile":"ESRI Shapefile (*.shp)","GeoJSON":"GeoJSON (*.geojson *.json)","CSV":"CSV (*.csv)"}
        p,_=QFileDialog.getSaveFileName(self,"Choose parcel output","",filters.get(fmt,"All files (*.*)"))
        if p:self.output.setText(p)
    def show_help(self):
        aid=CATALOG[self.node.name].get("algorithm")
        if aid:
            try: QMessageBox.information(self,"QGIS Processing Help",QgsApplication.processingRegistry().algorithmById(aid).shortHelpString())
            except Exception as e: QMessageBox.warning(self,"Help",str(e))
    def save(self):
        cfg=self.node.studio.configs.setdefault(self.node.node_id,{})
        if hasattr(self,"path"): cfg["path"]=self.path.text().strip()
        if hasattr(self,"uri"): cfg["uri"]=self.uri.text().strip()
        if self.node.name=="Parcel Downloader":
            for k,w in self.fields.items():
                cfg[k]=int(w.text()) if k in ("batch_size","timeout") else w.text().strip()
            cfg["output_format"]=self.output_format.currentText()
            cfg["output"]=self.output.text().strip()
        elif self.node.name=="HTTP Caller":
            cfg.update({"method":self.method.currentText(),"url":self.url.text().strip(),"headers":self.headers.text().strip(),"query":self.query.text().strip(),"body":self.body.toPlainText(),"timeout":self.timeout.value()})
        elif hasattr(self,"json_edit"):
            try: cfg["params"]=json.loads(self.json_edit.toPlainText() or "{}")
            except Exception as e: raise ValueError(f"Invalid JSON: {e}")

class Studio(QMainWindow):
    def __init__(self,iface,parent=None):
        super().__init__(parent); self.iface=iface; self.setWindowTitle("QGIS_Transformer_Studio_V2"); self.resize(1500,900); self.showMaximized()
        self.nodes={}; self.configs={}; self.connections=[]; self.edges=[]; self.counter=0; self.pending=None
        root=QWidget(); self.setCentralWidget(root); main=QHBoxLayout(root)
        left=QVBoxLayout(); left.addWidget(QLabel("TRANSFORMER LIBRARY"))
        self.search=QLineEdit(); self.search.setPlaceholderText("Search 100+ transformers…"); self.search.textChanged.connect(self.filter); left.addWidget(self.search)
        self.list=QListWidget(); self.populate(); self.list.itemDoubleClicked.connect(self.add_selected); left.addWidget(self.list,1)
        b=QPushButton("＋ Add to Canvas"); b.clicked.connect(self.add_selected); left.addWidget(b)
        main.addLayout(left,0)
        center=QVBoxLayout(); bar=QHBoxLayout()
        for txt,fn in [("New",self.new),("Open",self.open),("Save",self.save),("Validate",self.validate),("Audit Library",self.audit),("Run",self.run),("Fit",self.fit),("Clear",self.clear),("User Guide",self.guide)]:
            x=QPushButton(txt); x.clicked.connect(fn); bar.addWidget(x)
        center.addLayout(bar); self.scene=Canvas(self); self.scene.setSceneRect(0,0,5000,3000)
        self.view=WorkflowView(self.scene,self); self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag); self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse); center.addWidget(self.view,1)
        self.log=QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(150); center.addWidget(self.log); main.addLayout(center,1)
        self.status=QLabel("Ready — 100+ real QGIS Processing transformers + Web/API + Parcel Downloader."); center.addWidget(self.status)
        self.log.append("QGIS Transformer Studio V2.0.3 loaded.")
    def populate(self):
        self.list.clear()
        for s in TRANSFORMER_CATALOG:
            item=QListWidgetItem(f"{s['category']}  |  {s['name']}"); item.setData(Qt.ItemDataRole.UserRole,s["name"]); self.list.addItem(item)
    def filter(self,t):
        q=t.lower().strip()
        for i in range(self.list.count()): self.list.item(i).setHidden(q not in self.list.item(i).text().lower())
    def add_selected(self,*args):
        item=self.list.currentItem() if not args or not isinstance(args[0],QListWidgetItem) else args[0]
        if not item:return
        self.add_node(item.data(Qt.ItemDataRole.UserRole))
    def add_node(self,name,pos=None,nid=None):
        self.counter+=1; nid=nid or f"node_{self.counter}"; n=Node(self,nid,name); self.scene.addItem(n)
        if pos is None:
            c=self.view.mapToScene(self.view.viewport().rect().center()); pos=QPointF(c.x()-n.W/2+(len(self.nodes)%5)*40,c.y()-n.H/2+(len(self.nodes)//5)*40)
        n.setPos(pos); self.nodes[nid]=n; self.configs.setdefault(nid,{})
        self.view.centerOn(n); return n
    def remove_connection(self,conn):
        self.connections=[c for c in self.connections if c != conn]
        self.update_edges()
        self.status.setText("Connection removed.")
    def remove_node(self,nid):
        if nid not in self.nodes: return
        self.connections=[c for c in self.connections if c["source"][0] != nid and c["target"][0] != nid]
        n=self.nodes.pop(nid)
        self.configs.pop(nid,None)
        self.scene.removeItem(n)
        self.update_edges()
        self.status.setText("Transformer removed.")
    def configure(self,node):
        try:
            d=ConfigDialog(node,self)
            if d.exec()==QDialog.DialogCode.Accepted:
                d.save(); self.log.append(f"Configured {node.name}")
        except Exception as e: QMessageBox.critical(self,"Configuration error",str(e))
    def mousePressEvent(self,event):
        super().mousePressEvent(event)
    def _port_at(self,scene_pos):
        item=self.scene.itemAt(scene_pos,self.view.viewportTransform()); return item if isinstance(item,Port) else None
    def _scene_press(self,event):
        p=self._port_at(event.scenePos())
        if p and p.direction=="output": self.pending=p; return
    def _finish(self,p):
        if not self.pending:return
        s=self.pending; self.pending=None
        if p.direction!="input" or s.node==p.node:return
        if s.ptype!="ANY" and p.ptype!="ANY" and s.ptype!=p.ptype:
            if not (s.ptype in ("POINT","LINE","POLYGON") and p.ptype=="VECTOR"):
                QMessageBox.warning(self,"Incompatible connection",f"{s.ptype} → {p.ptype} is not compatible."); return
        self.connections=[c for c in self.connections if c["target"]!=(p.node.node_id,p.name)]
        self.connections.append({"source":(s.node.node_id,s.name),"target":(p.node.node_id,p.name)}); self.update_edges()
    def update_edges(self):
        for e in self.edges:self.scene.removeItem(e)
        self.edges=[]
        for c in self.connections:
            if c["source"][0] in self.nodes and c["target"][0] in self.nodes:
                e=Edge(self,c); self.scene.addItem(e); self.edges.append(e)
    def eventFilter(self,obj,event):
        return super().eventFilter(obj,event)
    def validate(self):
        try:
            self.audit()
            # Validate graph connectivity and required inputs without executing.
            for nid,n in self.nodes.items():
                spec=CATALOG[n.name]
                incoming=[c for c in self.connections if c["target"][0]==nid]
                connected={c["target"][1] for c in incoming}
                missing=[p for p in spec.get("inputs",[]) if p not in connected]
                if missing: self.log.append(f"⚠ {n.name}: unconnected inputs: {', '.join(missing)}")
            self.log.append("✓ Canvas validation completed. Run will perform a final Processing-parameter validation before execution.")
        except Exception as e: QMessageBox.critical(self,"Validation error",str(e))
    def audit(self):
        """Audit catalog entries against the exact Processing registry in this QGIS session."""
        missing=[]; adapted=[]; bad_inputs=[]; checked=0
        alias_groups={
            "OVERLAY":{"OVERLAY","LINES","JOIN","TARGET","POLYGONS","INTERSECT"},
            "INPUT_2":{"INPUT_2","JOIN","TARGET","OVERLAY","INTERSECT","DESTINATION"},
            "INPUT":{"INPUT","INPUT_LAYER","SOURCE"},
            "LAYERS":{"LAYERS","INPUT"},
        }
        for spec in TRANSFORMER_CATALOG:
            aid=spec.get("algorithm")
            if not aid: continue
            checked += 1
            alg=QgsApplication.processingRegistry().algorithmById(aid)
            if not alg:
                missing.append(f"{spec['name']} → {aid}")
                continue
            defined={p.name() for p in alg.parameterDefinitions()}
            for port in spec.get("inputs",[]):
                if port in defined: continue
                if port in alias_groups and defined.intersection(alias_groups[port]):
                    adapted.append(f"{spec['name']}: {port} → {sorted(defined.intersection(alias_groups[port]))[0]}")
                else:
                    bad_inputs.append(f"{spec['name']}: {port} not in {aid}")
        self.log.append(f"Library audit: checked {checked} Processing-backed transformers.")
        if missing: self.log.append("⚠ Unavailable in this QGIS build: " + " | ".join(missing))
        if adapted: self.log.append("✓ Parameter mappings adapted to this QGIS build: " + " | ".join(adapted))
        if bad_inputs: self.log.append("⚠ Unresolved catalog/input mismatches: " + " | ".join(bad_inputs))
        if not missing and not bad_inputs: self.log.append("✓ No unavailable algorithms or unresolved catalog input mismatches detected.")
        QMessageBox.information(self,"Transformer Library Audit",f"Checked {checked} Processing-backed transformers.\n\nUnavailable: {len(missing)}\nAdapted parameter mappings: {len(adapted)}\nUnresolved input mismatches: {len(bad_inputs)}\n\nSee the execution log for details.")

    def run(self):
        nodes=[]
        for nid,n in self.nodes.items(): nodes.append({"id":nid,"name":n.name,"config":self.configs.get(nid,{})})
        if not nodes:
            QMessageBox.information(self,"Run workflow","Add at least one transformer to the canvas.")
            return
        progress=QProgressDialog("Preparing workflow…","Cancel",0,100,self)
        progress.setWindowTitle("QGIS Transformer Studio — Running")
        progress.setAutoClose(False); progress.setAutoReset(False); progress.setMinimumDuration(0); progress.show()
        QApplication.processEvents()

        class StudioFeedback(QgsProcessingFeedback):
            def __init__(self, dialog, log):
                super().__init__(); self.dialog=dialog; self.log=log
            def setProgress(self, progress):
                super().setProgress(progress); self.dialog.setValue(max(0,min(100,int(progress)))); QApplication.processEvents()
            def setProgressText(self, text):
                super().setProgressText(text); self.dialog.setLabelText(str(text)); self.log.append(str(text)); QApplication.processEvents()
            def pushInfo(self, info):
                super().pushInfo(info); self.log.append(str(info)); QApplication.processEvents()
            def reportError(self, error, fatalError=False):
                super().reportError(error,fatalError); self.log.append("✗ "+str(error)); QApplication.processEvents()

        fb=StudioFeedback(progress,self.log)
        progress.canceled.connect(fb.cancel)
        try:
            res=run_workflow(nodes,self.connections,fb,lambda m:self.log.append(m))
            used=set()
            for nid,r in res.items():
                val=r.get("OUTPUT")
                if hasattr(val,"isValid") and val.isValid():
                    outgoing=any(c["source"][0]==nid for c in self.connections)
                    if not outgoing and val not in used:
                        QgsProject.instance().addMapLayer(val); used.add(val)
            progress.setValue(100); progress.setLabelText("✓ Workflow completed")
            self.log.append("✓ Workflow completed successfully.")
        except Exception as e:
            self.log.append("✗ "+str(e))
            QMessageBox.critical(self,"Workflow error",str(e))
        finally:
            QApplication.processEvents()
            progress.close()
    def new(self):
        self.clear()
    def clear(self):
        self.scene.clear(); self.nodes={}; self.configs={}; self.connections=[]; self.edges=[]; self.counter=0; self.log.append("Canvas cleared.")
    def fit(self):
        if self.nodes:self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-100,-100,100,100),Qt.AspectRatioMode.KeepAspectRatio)
    def save(self):
        p,_=QFileDialog.getSaveFileName(self,"Save workflow","","QGIS Transformer Workflow (*.gtworkflow)")
        if not p:return
        data={"format":"QGIS Transformer Studio","version":"2.0","nodes":[{"id":nid,"name":n.name,"x":n.x(),"y":n.y(),"config":self.configs.get(nid,{})} for nid,n in self.nodes.items()],"connections":self.connections}
        Path(p).write_text(json.dumps(data,indent=2),encoding="utf-8"); self.log.append("Workflow saved: "+p)
    def open(self):
        p,_=QFileDialog.getOpenFileName(self,"Open workflow","","QGIS Transformer Workflow (*.gtworkflow)")
        if not p:return
        data=json.loads(Path(p).read_text(encoding="utf-8")); self.clear()
        for d in data.get("nodes",[]): self.add_node(d["name"],QPointF(d["x"],d["y"]),d["id"]); self.configs[d["id"]]=d.get("config",{})
        self.connections=data.get("connections",[]); self.update_edges(); self.fit()
    def guide(self):
        d=QDialog(self); d.setWindowTitle("QGIS Transformer Studio V2 — User Guide"); d.resize(900,700)
        l=QVBoxLayout(d); t=QTextEdit(); t.setReadOnly(True)
        t.setPlainText(Path(self._guide_path()).read_text(encoding="utf-8") if Path(self._guide_path()).exists() else "See README.md in the plugin package.")
        l.addWidget(t); b=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); b.rejected.connect(d.reject); b.accepted.connect(d.accept); l.addWidget(b); d.exec()
    def _guide_path(self):
        return str(Path(__file__).resolve().parent.parent/"README.md")

    # Mouse wiring for the graphics view.
    def event(self,e):
        return super().event(e)
