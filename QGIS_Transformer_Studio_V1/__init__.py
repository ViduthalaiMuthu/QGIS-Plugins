# QGIS Transformer Studio
# Copyright (C) 2026 Viduthalai Muthu M
# Licensed under the GNU General Public License v2 or later.
# See LICENSE for details.

def classFactory(iface):
    from .gis_transformer_studio import GisTransformerStudio
    return GisTransformerStudio(iface)
