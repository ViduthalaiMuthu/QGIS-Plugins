# Changelog


## 2.0.3
- Hardened workflow execution and Processing parameter validation for QGIS 4.2+.
- Improved transformer deletion and connection deletion handling.
- Improved GeoPackage output handling for Parcel Downloader.
- Added safer output-path and file-finalization handling.
- Improved compatibility with QGIS Processing parameter variations.
- Updated documentation and release metadata for the 2.0.3 stable release.


## 2.0.2
- Hardened GeoPackage output using a sibling temporary GeoPackage before final replacement.
- Preserves completed Parcel Downloader data when the requested output is locked.
- Added safe unique fallback outputs and retained temporary GeoJSON on final write failure.
- Corrected QGIS 4.2 parameter mappings for Split with Lines, Join by Location, Distance Matrix, Basic Statistics, Merge Vector Layers, Package Layers and Minimum Enclosing Circles.
- Improved Processing audit reporting to distinguish unavailable algorithms, adapted mappings and unresolved mismatches.
- Removed generated Python bytecode from the release package.
- Updated workflow format and all V2 release strings.


## 2.0.1
- Hardened Parcel Downloader output writing, especially GeoPackage files that already exist or are locked by QGIS/another process.
- Attempts to release an existing output layer before writing.
- If the requested GeoPackage cannot be replaced, automatically writes a timestamped fallback file instead of losing the downloaded dataset.
- Preserves the downloaded temporary GeoJSON long enough to retry output creation.
- Corrected the runtime banner to report QGIS Transformer Studio V2.0.1.
- Improved Processing audit reporting for unavailable algorithms and parameter mismatches.


## 1.1.0
- Audited the 100+ transformer catalog against the installed QGIS Processing registry at runtime.
- Added pre-execution validation for algorithm availability, input-port names, required parameters and workflow cancellation.
- Added an **Audit Library** command and stronger canvas validation.
- Added a real QGIS/PyQGIS Centroids implementation to avoid geometry-type/provider issues.
- Corrected raster/vector output typing for raster-to-vector and vector-to-raster transformers.
- Added visible run progress, status messages, cancellation and structured error reporting.
- Hardened vector writer output paths so extension-less paths no longer cause `OGR driver for '' not found`.
- Rebuilt Parcel Downloader: accepts a FeatureServer layer URL or `/query`, obtains feature count when supported, downloads in batches, reports progress, supports cancellation/timeouts, handles ArcGIS errors, and writes GeoPackage/Shapefile/GeoJSON/CSV with automatic extensions.
- Parcel Downloader defaults to GeoPackage and safely handles folder paths and extension-less filenames.
- No GeoPandas/Pandas/NumPy dependency is used by the plugin.

## 1.0.0
- Expanded visual transformer catalog to 100+ QGIS Processing-backed transformers.
- Added HTTP Caller and ArcGIS FeatureServer Parcel Downloader.
- Added workflow save/load and Processing provider.
