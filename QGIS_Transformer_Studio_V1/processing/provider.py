# QGIS Transformer Studio
# Copyright (C) 2026 Viduthalai Muthu M
# Licensed under the GNU General Public License v2 or later.
# See LICENSE for details.

from qgis.core import QgsProcessingProvider
from .algorithms import (
    BufferTransformer, ReprojectTransformer, DissolveTransformer,
    ClipTransformer, FixGeometryTransformer
)

class TransformerProvider(QgsProcessingProvider):
    def id(self):
        return "gistransformerstudio"

    def name(self):
        return "QGIS Transformer Studio"

    def longName(self):
        return "QGIS Transformer Studio — Standalone Transformers"

    def loadAlgorithms(self):
        for alg in (
            BufferTransformer(),
            ReprojectTransformer(),
            DissolveTransformer(),
            ClipTransformer(),
            FixGeometryTransformer(),
        ):
            self.addAlgorithm(alg)
