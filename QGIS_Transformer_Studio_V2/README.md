# QGIS_Transformer_Studio_V2 — 2.0.4

Visual GIS ETL workflow builder for QGIS 4.2+.

## What this release is

This release expands the original Transformer Studio into a **100+ transformer architecture**.

The Transformer Library contains **129 entries**:

- Common Readers
- Geometry transformers
- Vector overlay transformers
- Attribute transformers
- Spatial transformers
- Selection/QC transformers
- CRS transformers
- Raster/GDAL transformers
- Writers
- HTTP Caller
- ArcGIS FeatureServer Parcel Downloader

### Important implementation rule

The Processing-backed transformers are **not dummy/no-op placeholders**. Each one points to a real QGIS Processing algorithm ID and is executed through QGIS `processing.run()`.

At runtime the plugin checks whether the algorithm exists in the current QGIS installation. If an algorithm is not available in a particular build, validation reports it instead of pretending that it worked.

## QGIS compatibility

- Minimum: QGIS 4.2
- Maximum: QGIS 4.99
- Python: the Python version bundled with QGIS
- External Python packages are not required for the core Processing transformers.

## Source repository

The source for this plugin is maintained here:

https://github.com/ViduthalaiMuthu/QGIS-Plugins/tree/main/QGIS_Transformer_Studio_V2

The same path is stored in `metadata.txt` as the homepage and repository URL so a reviewer can go directly to the plugin source.

## Main architecture

```text
QGIS_Transformer_Studio_V2/
├── __init__.py
├── plugin.py
├── metadata.txt
├── README.md
├── CHANGELOG.md
├── LICENSE
├── icon.svg
├── core/
│   ├── __init__.py
│   ├── catalog.py
│   └── engine.py
├── ui/
│   ├── __init__.py
│   └── studio.py
└── processing/
    ├── __init__.py
    ├── provider.py
    └── workflow_algorithm.py
```

## How the visual workflow works

1. Open **Plugins → QGIS Transformer Studio**.
2. Search the Transformer Library.
3. Double-click a transformer or select it and click **Add to Canvas**.
4. Double-click a node to configure it.
5. Drag from an output port to a compatible input port.
6. Click **Validate**.
7. Click **Run**.
8. Final unconnected outputs are added to the QGIS project.

Workflows are directed dependency graphs. The engine calculates a topological execution order and executes upstream nodes before downstream nodes.

## Configuration model

Processing-backed transformers use the actual QGIS Processing algorithm metadata.

The Configure dialog exposes a JSON parameter editor. The plugin starts it with the Processing algorithm's default parameter values where QGIS supplies them.

Connected layer ports override the corresponding Processing parameters at execution time.

This means the transformer is a visual wrapper around the actual QGIS Processing engine rather than a second, incomplete implementation of every GIS algorithm.

## Transformer catalog

The library contains 129 transformer entries in this release. Examples include:

### Geometry

Buffer, Centroids, Dissolve, Multipart to Singleparts, Promote to Multipart, Collect Geometries, Merge Lines, Lines to Polygons, Polygons to Lines, Polygonize, Extract Vertices, Remove Duplicate Vertices, Boundary, Bounding Boxes, Convex Hull, Concave Hull, Delaunay Triangulation, Voronoi Polygons, Minimum Bounding Geometry, Point on Surface, Geometry by Expression, Affine Transform, Convert Geometry Type, Densify, Simplify, Smooth, Snap Geometries to Layer, Offset Lines, Reverse Line Direction, Rotate, Translate, Set Z, Set M, Force 2D and more.

### Overlay / spatial

Clip, Difference, Intersection, Symmetrical Difference, Union, Split with Lines, Join Attributes by Location, Join by Location Summary, Join by Nearest, Distance Matrix, Line Intersections, nearest-neighbour analysis and more.

### Attributes

Field Calculator, Join Attributes by Field Value, Aggregate, Statistics by Categories, Basic Statistics, Add Field, Delete Fields, Refactor Fields, Retain Fields, Sort, duplicate handling and more.

### Selection / QC

Extract by Expression, Extract by Attribute, Extract by Location, Extract Within Distance, Select by Expression, Select by Location, Select by Attribute, Fix Geometries, Check Validity, Delete Duplicate Geometries, Remove Null Geometries, Remove Parts by Area/Length and more.

### CRS

Reproject Layer, Assign Projection and Extract Projection.

### Raster / GDAL

Raster Calculator, Warp/Reproject, Clip Raster by Extent, Clip Raster by Mask Layer, Translate, Build Virtual Raster, Merge, Sieve, Polygonize, Rasterize, Contour, Aspect, Slope, Hillshade, Proximity and Fill NoData.

### Web/API

**HTTP Caller**

Supports GET, POST, PUT, PATCH and DELETE, custom headers, query JSON, request body and configurable timeout. The response is written to a temporary file so it can be inspected or used by later workflow components.

### ArcGIS FeatureServer

**Parcel Downloader**

The Parcel Downloader is specifically intended for large ArcGIS FeatureServer datasets.

It supports:

- FeatureServer query URL
- WHERE filter
- outFields
- output SRID
- optional geometry/bounding-box filter
- configurable batch size
- timeout
- automatic pagination using `resultOffset` and `resultRecordCount`
- GeoJSON response
- QGIS vector output

It does not require GeoPandas.

Typical workflow:

```text
Parcel Downloader
        ↓
Fix Geometries
        ↓
Filter by Expression
        ↓
Reproject Layer
        ↓
GeoPackage Writer
```

## Readers

Built-in readers include:

- Vector Reader
- Raster Reader
- Table Reader
- CSV Reader
- GeoJSON Reader
- GeoPackage Reader
- Shapefile Reader
- Database Reader

## Writers

Built-in writers include:

- Vector Writer
- Raster Writer
- GeoPackage Writer
- GeoJSON Writer
- CSV Writer

## Workflow files

Use **Save** to create:

```text
my_workflow.gtworkflow
```

The file contains:

- transformer names
- node IDs
- node positions
- transformer configuration
- connections

Use **Open** to restore the graph.

## Processing provider

The plugin also registers:

**QGIS Transformer Studio → Run Transformer Studio Workflow**

This accepts a `.gtworkflow` file and executes it using the same engine as the visual application.

## Validation

Validation checks:

- Processing algorithm availability
- incompatible data connections
- workflow cycles

The plugin does not silently execute a transformer whose Processing algorithm is missing.

## Important limitation

QGIS Processing has a large and evolving algorithm surface. The catalog is deliberately backed by Processing IDs instead of copying every algorithm's implementation into this plugin.

This keeps the plugin maintainable and lets QGIS remain the actual GIS execution engine.

Some algorithms have many advanced parameters. Those parameters are exposed through the JSON configuration editor so that the wrapper does not hide QGIS functionality.

## Parcel Downloader

The Parcel Downloader accepts either an ArcGIS FeatureServer layer URL (for example `.../FeatureServer/0`) or its `/query` endpoint. It supports `WHERE`, output fields, output SRID, optional geometry filtering, batch size, timeout, output layer name, and output format. GeoPackage is the default. If an output filename has no extension, the plugin adds the correct extension automatically. During execution the progress dialog reports connection, batch, feature-count and output-writing status and supports cancellation.

For large datasets, GeoPackage is recommended. The downloader uses the Python standard library for HTTP and native PyQGIS/OGR output handling; it does not require GeoPandas, Pandas or NumPy.

## Development principle

The project follows these rules:

1. No fake transformer implementations.
2. No success message when an underlying algorithm failed.
3. QGIS Processing is the execution engine wherever a native algorithm exists.
4. Custom code is used only where the workflow needs behavior that is not a normal Processing algorithm, such as HTTP Caller and Parcel Downloader.
5. New transformers should be added to `core/catalog.py` with a real implementation.
6. Every public release should be tested in the target QGIS version before upload.

## Installation from ZIP

The ZIP should contain exactly one top-level directory:

```text
QGIS_Transformer_Studio_V2/
```

Install through:

**Plugins → Manage and Install Plugins → Install from ZIP**

## Author

Viduthalai M Muthu  
viduthalaimuthu5@gmail.com

## Repository

https://github.com/ViduthalaiMuthu/QGIS-Plugins

## License

GPL-2.0-or-later
