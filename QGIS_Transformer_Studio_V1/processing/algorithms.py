# QGIS Transformer Studio
# Copyright (C) 2026 Viduthalai Muthu M
# Licensed under the GNU General Public License v2 or later.
# See LICENSE for details.

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterDistance,
    QgsProcessingParameterCrs, QgsProcessingParameterField
)
import processing

class BaseTransformer(QgsProcessingAlgorithm):
    def tr(self, string):
        return string
    def createInstance(self):
        return type(self)()
    def group(self):
        return "Transformers"

class BufferTransformer(BaseTransformer):
    def name(self): return "buffer_transformer"
    def displayName(self): return "Buffer Transformer"
    def groupId(self): return "geometry"
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input layer"))
        self.addParameter(QgsProcessingParameterDistance("DISTANCE", "Distance", defaultValue=10.0, parentParameterName="INPUT"))
        self.addParameter(QgsProcessingParameterFeatureSink("OUTPUT", "Output"))
    def processAlgorithm(self, parameters, context, feedback):
        return processing.run("native:buffer", {
            "INPUT": parameters["INPUT"], "DISTANCE": parameters["DISTANCE"],
            "SEGMENTS": 8, "END_CAP_STYLE": 0, "JOIN_STYLE": 0,
            "MITER_LIMIT": 2, "DISSOLVE": False, "OUTPUT": parameters["OUTPUT"]
        }, context=context, feedback=feedback)

class ReprojectTransformer(BaseTransformer):
    def name(self): return "reproject_transformer"
    def displayName(self): return "Reproject Transformer"
    def groupId(self): return "crs"
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input layer"))
        self.addParameter(QgsProcessingParameterCrs("TARGET_CRS", "Target CRS"))
        self.addParameter(QgsProcessingParameterFeatureSink("OUTPUT", "Output"))
    def processAlgorithm(self, parameters, context, feedback):
        return processing.run("native:reprojectlayer", {
            "INPUT": parameters["INPUT"], "TARGET_CRS": parameters["TARGET_CRS"],
            "CONVERT_CURVED_GEOMETRIES": False, "OPERATION": "",
            "OUTPUT": parameters["OUTPUT"]
        }, context=context, feedback=feedback)

class DissolveTransformer(BaseTransformer):
    def name(self): return "dissolve_transformer"
    def displayName(self): return "Dissolve Transformer"
    def groupId(self): return "geometry"
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input layer"))
        self.addParameter(QgsProcessingParameterField("FIELD", "Dissolve field", parentLayerParameterName="INPUT", optional=True))
        self.addParameter(QgsProcessingParameterFeatureSink("OUTPUT", "Output"))
    def processAlgorithm(self, parameters, context, feedback):
        field = parameters.get("FIELD")
        return processing.run("native:dissolve", {
            "INPUT": parameters["INPUT"], "FIELD": [field] if field else [],
            "SEPARATE_DISJOINT": False, "OUTPUT": parameters["OUTPUT"]
        }, context=context, feedback=feedback)

class ClipTransformer(BaseTransformer):
    def name(self): return "clip_transformer"
    def displayName(self): return "Clip Transformer"
    def groupId(self): return "geometry"
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input layer"))
        self.addParameter(QgsProcessingParameterFeatureSource("OVERLAY", "Overlay layer"))
        self.addParameter(QgsProcessingParameterFeatureSink("OUTPUT", "Output"))
    def processAlgorithm(self, parameters, context, feedback):
        return processing.run("native:clip", {
            "INPUT": parameters["INPUT"], "OVERLAY": parameters["OVERLAY"],
            "OUTPUT": parameters["OUTPUT"]
        }, context=context, feedback=feedback)

class FixGeometryTransformer(BaseTransformer):
    def name(self): return "fix_geometry_transformer"
    def displayName(self): return "Fix Geometry Transformer"
    def groupId(self): return "quality_control"
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input layer"))
        self.addParameter(QgsProcessingParameterFeatureSink("OUTPUT", "Output"))
    def processAlgorithm(self, parameters, context, feedback):
        return processing.run("native:fixgeometries", {
            "INPUT": parameters["INPUT"], "METHOD": 1,
            "OUTPUT": parameters["OUTPUT"]
        }, context=context, feedback=feedback)
