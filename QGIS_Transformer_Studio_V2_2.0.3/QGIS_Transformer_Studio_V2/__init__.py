def classFactory(iface):
    from .plugin import QGISTransformerStudioPlugin
    return QGISTransformerStudioPlugin(iface)
