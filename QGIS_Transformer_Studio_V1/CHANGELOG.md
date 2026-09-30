## 0.2.5 - 2026-09-27

- Public plugin name updated to `QGIS_Transformer_Studio_V1` without changing author, email, repository, license or workflow functionality.
- Added an in-plugin **User Guide** window that displays the bundled README documentation.

- Expanded README into a complete end-user guide covering installation, interface, workflow construction, connections, data types, readers, transformers, writers, examples, validation, execution, troubleshooting and limitations.

- Replaced the QGIS dock-panel UI with a standalone QMainWindow workspace.
- Plugin opens maximized by default for a full workflow-editing workspace.
- Added native Minimize, Maximize/Restore and Close controls.
- The workflow editor no longer occupies or resizes the QGIS map canvas.
- QGIS remains available behind the Transformer Studio window.
- Preserved the 0.2.4 canvas, typed ports and Centroid fixes.

## 0.2.4 - 2026-09-27

- Rebuilt the canvas event handling using dedicated QGraphicsScene/QGraphicsView subclasses.
- Fixed transformers being reported as added while not reliably appearing in the visible canvas.
- New transformers are now placed at the current visible canvas center and automatically brought into view.
- Added Fit and Reset View controls plus keyboard shortcuts F and 0.
- Moved Delete and Ctrl+D handling into the canvas view so keyboard focus works correctly.
- Added geometry-aware port typing for POINT/LINE/POLYGON outputs.
- Fixed Centroid to always emit a real Point layer and preserve source attributes.
- Added safer canvas scene sizing and selection behavior.

# Changelog

## 0.2.3 - 2026-09-27

- Fixed the Centroid transformer for multipart polygon inputs.
- Centroid now creates a dedicated Point memory layer and copies source attributes.
- Avoided the temporary-output geometry mismatch that could produce:
  `Could not add feature with geometry type MultiPolygon to layer of type Point`.
- Added clear execution logging for created and skipped centroid features.

## 0.2.2 - 2026-09-27

- Renamed the public plugin to QGIS Transformer Studio.
- Updated author to Viduthalai Muthu M.
- Updated contact email to viduthalaimuthu5@gmail.com.
- Added QGIS plugin repository-ready metadata.
- Added repository, homepage and issue tracker links.
- Added GPL-2.0-or-later license.
- Added project README and changelog.
- Added dedicated plugin logo resources.
- Kept QGIS 4.2+ compatibility metadata.
- Preserved the V0.2 workflow canvas, typed ports, readers, transformers, validation and Processing provider foundation.

## 0.2.1

- Replaced the unsupported `QgsRasterCalculator` import path with the QGIS Processing GDAL raster calculator algorithm.
- Maintained QGIS 4.2 compatibility.

## 0.2

- Added typed Readers and Writers.
- Added workflow validation, branching, save/load and execution foundation.
- Added core geometry, attribute, CRS and raster transformer foundations.
