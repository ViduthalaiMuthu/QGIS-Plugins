
import json
from pathlib import Path
from qgis.core import (
    QgsProcessingAlgorithm,QgsProcessingParameterFile,QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,QgsProcessingException,QgsProcessing,QgsProcessingOutputString
)
from ..core.engine import run_workflow

class WorkflowAlgorithm(QgsProcessingAlgorithm):
    WORKFLOW="WORKFLOW"
    MESSAGE="MESSAGE"
    def name(self): return "run_workflow"
    def displayName(self): return "Run Transformer Studio Workflow"
    def group(self): return "QGIS Transformer Studio"
    def groupId(self): return "qgis_transformer_studio"
    def createInstance(self): return WorkflowAlgorithm()
    def shortHelpString(self):
        return "Executes a .gtworkflow file produced by QGIS Transformer Studio."
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterFile(self.WORKFLOW,"Workflow file",behavior=QgsProcessingParameterFile.File,fileFilter="Transformer workflow (*.gtworkflow)"))
        self.addParameter(QgsProcessingParameterString(self.MESSAGE,"Execution message",optional=True))
        self.addOutput(QgsProcessingOutputString(self.MESSAGE,"Execution message"))
    def processAlgorithm(self,parameters,context,feedback):
        path=self.parameterAsFile(parameters,self.WORKFLOW,context)
        try:data=json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:raise QgsProcessingException(f"Could not read workflow: {e}")
        nodes=[{"id":n["id"],"name":n["name"],"config":n.get("config",{})} for n in data.get("nodes",[])]
        res=run_workflow(nodes,data.get("connections",[]),feedback,lambda m:feedback.pushInfo(m))
        return {"MESSAGE":f"Executed {len(nodes)} transformer nodes."}
