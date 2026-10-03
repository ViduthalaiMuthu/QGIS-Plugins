
from qgis.core import QgsProcessingProvider, QgsApplication
from .workflow_algorithm import WorkflowAlgorithm

class TransformerProvider(QgsProcessingProvider):
    def id(self): return "qgis_transformer_studio"
    def name(self): return "QGIS Transformer Studio"
    def longName(self): return "QGIS Transformer Studio"
    def loadAlgorithms(self):
        self.addAlgorithm(WorkflowAlgorithm())

def provider_factory():
    return TransformerProvider()
