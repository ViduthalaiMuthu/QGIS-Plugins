
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMessageBox

class QGISTransformerStudioPlugin:
    def __init__(self, iface):
        self.iface=iface
        self.action=None
        self.window=None
        self.provider=None
    def initGui(self):
        from .processing.provider import TransformerProvider
        self.provider=TransformerProvider()
        from qgis.core import QgsApplication
        QgsApplication.processingRegistry().addProvider(self.provider)
        self.action=QAction("QGIS_Transformer_Studio_V2", self.iface.mainWindow())
        self.action.triggered.connect(self.show)
        self.iface.addPluginToMenu("&QGIS Transformer Studio", self.action)
    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&QGIS Transformer Studio", self.action)
            self.action.deleteLater()
        if self.provider:
            from qgis.core import QgsApplication
            try: QgsApplication.processingRegistry().removeProvider(self.provider)
            except Exception: pass
            self.provider=None
        if self.window:
            self.window.close()
            self.window.deleteLater()
            self.window=None
        self.provider=None
    def show(self):
        if self.window is None:
            from .ui.studio import Studio
            self.window=Studio(self.iface)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
