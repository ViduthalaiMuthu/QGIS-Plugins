# QGIS_Transformer_Studio_V1

**QGIS Transformer Studio** is a visual GIS ETL and workflow-building plugin for QGIS 4.x. It is designed around the idea of connecting reusable GIS **Readers → Transformers → Writers** on a visual canvas, similar in concept to transformer-based ETL tools such as FME, while using QGIS/PyQGIS and QGIS Processing underneath.

> **Current release:** 0.2.5  
> **QGIS target:** QGIS 4.2+  
> **Author:** Viduthalai Muthu M  
> **Email:** viduthalaimuthu5@gmail.com  
> **License:** GPL-2.0-or-later

---

# Table of Contents

1. [What is QGIS Transformer Studio?](#what-is-qgis-transformer-studio)
2. [What can you do with it?](#what-can-you-do-with-it)
3. [Installation](#installation)
4. [Opening the plugin](#opening-the-plugin)
5. [Understanding the interface](#understanding-the-interface)
6. [How a workflow works](#how-a-workflow-works)
7. [Adding a transformer](#adding-a-transformer)
8. [Moving, selecting, duplicating and deleting nodes](#moving-selecting-duplicating-and-deleting-nodes)
9. [Connecting transformers](#connecting-transformers)
10. [Port and data types](#port-and-data-types)
11. [Configuring transformers](#configuring-transformers)
12. [Readers](#readers)
13. [Vector Reader](#vector-reader)
14. [Raster Reader](#raster-reader)
15. [Table Reader](#table-reader)
16. [Database Reader](#database-reader)
17. [Geometry transformers](#geometry-transformers)
18. [Buffer](#buffer)
19. [Clip](#clip)
20. [Dissolve](#dissolve)
21. [Intersection](#intersection)
22. [Difference](#difference)
23. [Centroid](#centroid)
24. [Fix Geometry](#fix-geometry)
25. [Attribute transformers](#attribute-transformers)
26. [Field Calculator](#field-calculator)
27. [Filter by Expression](#filter-by-expression)
28. [Merge Vector Layers](#merge-vector-layers)
29. [CRS transformers](#crs-transformers)
30. [Reproject](#reproject)
31. [Raster transformers](#raster-transformers)
32. [Raster Calculator](#raster-calculator)
33. [Writers](#writers)
34. [Vector Writer](#vector-writer)
35. [Raster Writer](#raster-writer)
36. [Building your first workflow](#building-your-first-workflow)
37. [Example: Parcel workflow](#example-parcel-workflow)
38. [Example: Buffer and clip workflow](#example-buffer-and-clip-workflow)
39. [Example: Attribute calculation workflow](#example-attribute-calculation-workflow)
40. [Branching workflows](#branching-workflows)
41. [Validation](#validation)
42. [Running a workflow](#running-a-workflow)
43. [Execution messages and troubleshooting](#execution-messages-and-troubleshooting)
44. [Previewing a transformer](#previewing-a-transformer)
45. [Saving and opening workflows](#saving-and-opening-workflows)
46. [Standalone Processing algorithms](#standalone-processing-algorithms)
47. [Keyboard and mouse controls](#keyboard-and-mouse-controls)
48. [Important limitations in 0.2.5](#important-limitations-in-025)
49. [Recommended workflow practices](#recommended-workflow-practices)
50. [Troubleshooting](#troubleshooting)
51. [Reporting a bug](#reporting-a-bug)
52. [Development and contribution](#development-and-contribution)
53. [Roadmap](#roadmap)
54. [License](#license)
55. [Author and repository](#author-and-repository)

---

# What is QGIS Transformer Studio?

QGIS Transformer Studio provides a visual environment for building repeatable GIS processing workflows.

Instead of repeatedly performing:

```text
Open layer
    ↓
Buffer
    ↓
Clip
    ↓
Calculate fields
    ↓
Reproject
    ↓
Save
```

you can create a reusable workflow:

```text
┌──────────────┐
│ Vector Reader│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Buffer    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│     Clip     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Vector Writer│
└──────────────┘
```

The workflow can then be validated and executed as one graph.

## Core concepts

QGIS Transformer Studio has four major concepts:

### Reader

A Reader brings data into the workflow.

Examples:

- Vector Reader
- Raster Reader
- Table Reader
- Database Reader

### Transformer

A Transformer performs an operation on data.

Examples:

- Buffer
- Clip
- Dissolve
- Centroid
- Field Calculator
- Reproject

### Writer

A Writer saves workflow results.

Examples:

- Vector Writer
- Raster Writer

### Connection

A connection transfers the output of one transformer into the input of another.

```text
Reader OUTPUT ─────────→ Transformer INPUT
```

---

# What can you do with it?

The current release provides the foundation for:

- Visual GIS ETL workflows
- Vector data reading
- Raster data reading
- Table reading
- Geometry processing
- Attribute processing
- CRS transformation
- Raster calculation
- Vector output
- Raster output
- Branching workflows
- Typed connections
- Workflow validation
- Workflow execution
- Workflow save/load
- Basic transformer preview
- Standalone QGIS Processing algorithms

The project is intentionally modular so new transformers can be added without redesigning the complete workflow engine.

---

# Installation

## Install from ZIP

1. Download the QGIS Transformer Studio ZIP.
2. Open QGIS.
3. Go to:

```text
Plugins → Manage and Install Plugins
```

4. Select:

```text
Install from ZIP
```

5. Select:

```text
QGIS_Transformer_Studio_0.2.5_QGIS4.2.2.zip
```

6. Confirm the installation.
7. Restart QGIS if requested.
8. Enable **QGIS Transformer Studio** from the Installed Plugins list.

## Important

Do not extract the installation ZIP into the QGIS plugin directory manually unless you specifically need a development installation.

The ZIP should contain exactly one top-level plugin directory:

```text
QGIS_Transformer_Studio/
```

---

# Opening the plugin

QGIS Transformer Studio uses a **standalone workspace window**, not a QGIS dock panel.

Open it from:

```text
Plugins → QGIS Transformer Studio
```

or from the QGIS toolbar/menu entry created by the plugin.

The workspace opens maximized by default.

The window has normal operating-system controls:

- Minimize
- Maximize/Restore
- Close

QGIS remains available behind the Transformer Studio window.

This design is intentional because a visual workflow editor needs a large working area and should not permanently reduce the QGIS map canvas.

---

# Understanding the interface

The interface is divided into several functional areas.

```text
┌──────────────────────────────────────────────────────────────┐
│ QGIS Transformer Studio                                      │
├──────────────────────────────────────────────────────────────┤
│ Workflow controls                                            │
├─────────────────────┬────────────────────────────────────────┤
│ Transformer Library │                                        │
│                     │                                        │
│ Readers             │                                        │
│ Geometry            │          Workflow Canvas               │
│ Attributes          │                                        │
│ CRS                 │      [Reader] → [Transformer]          │
│ Raster              │                    ↓                   │
│ Writers             │                 [Writer]               │
│                     │                                        │
├─────────────────────┴────────────────────────────────────────┤
│ Execution / Messages                                         │
└──────────────────────────────────────────────────────────────┘
```

## Transformer Library

The library contains available transformer types.

Typical groups include:

- Readers
- Geometry
- Attributes
- CRS
- Raster
- Writers

Select a transformer and add it to the canvas.

## Workflow Canvas

The canvas is where the workflow graph is created.

Each transformer is represented by a node.

Nodes can be:

- Moved
- Selected
- Connected
- Configured
- Duplicated
- Deleted
- Enabled/disabled

## Execution / Messages

The message area records workflow events such as:

```text
Added Vector Reader
Configured Vector Reader
Connected Vector Reader.OUTPUT → Centroid.INPUT
Workflow validation successful
Starting workflow execution
Vector Reader complete
Centroid complete
Workflow completed
```

Errors include the QGIS Processing error and Python traceback when available.

---

# How a workflow works

A workflow is a directed graph.

For example:

```text
Vector Reader
      │
      ▼
   Buffer
      │
      ▼
    Clip
      │
      ▼
Vector Writer
```

When the workflow is executed, the plugin determines the dependency order and runs upstream transformers before downstream transformers.

For example:

```text
1. Vector Reader
2. Buffer
3. Clip
4. Vector Writer
```

A downstream transformer cannot execute successfully if its required input has not been produced.

---

# Adding a transformer

1. Select a transformer from the library.
2. Click **Add to Canvas**.
3. The node is placed in the workflow workspace.
4. Configure it if necessary.
5. Connect it to other nodes.

For example:

```text
Add Vector Reader
Add Buffer
Add Vector Writer
```

Then connect:

```text
Vector Reader OUTPUT
        ↓
Buffer INPUT
        ↓
Vector Writer INPUT
```

---

# Moving, selecting, duplicating and deleting nodes

## Move

Drag a node using its body/title area.

## Select

Click a node.

Multiple selection is supported by the canvas selection behavior.

## Duplicate

Use:

```text
Ctrl + D
```

when a node is selected.

The duplicate can then be moved and configured independently.

## Delete

Select a node and press:

```text
Delete
```

or:

```text
Backspace
```

Connections associated with the deleted node are removed as appropriate.

## Context menu

Right-clicking a node provides actions such as:

- Configure
- Duplicate
- Preview Output
- Disable/Enable
- Delete

---

# Connecting transformers

Connections are created by dragging from an output port to an input port.

Example:

```text
┌─────────────┐
│ Vector      │
│ Reader      │
│          ●──┼──────────●
└─────────────┘          │
                       INPUT
                         │
                   ┌─────▼─────┐
                   │  Buffer   │
                   └───────────┘
```

The output port is the source.

The input port is the destination.

## Connection rules

The plugin checks the declared data type of ports.

For example:

```text
VECTOR → VECTOR
```

is valid.

A raster output should not be connected directly to a vector-only input.

If the connection is incompatible, the plugin reports the problem instead of silently creating an invalid workflow.

## One connection per normal input

A normal single-value input accepts one incoming connection.

If a transformer requires multiple inputs, each input port should be connected separately.

---

# Port and data types

QGIS Transformer Studio uses typed ports to help prevent invalid workflows.

Current conceptual types include:

```text
VECTOR
POINT
LINE
POLYGON
RASTER
TABLE
FILE
FOLDER
COLLECTION
ANY
```

`POINT`, `LINE` and `POLYGON` are more specific vector geometry types.

For example:

```text
Vector Reader
      │
      ▼
   Centroid
      │
      ▼
    POINT
```

A Centroid operation produces point geometry.

A generic Vector input can accept compatible specific vector outputs.

---

# Configuring transformers

A transformer must normally be configured before execution.

Typical configuration values include:

- Input source
- Output location
- Field name
- Expression
- Distance
- CRS
- Raster expression
- Filter expression
- Output format

To configure:

1. Select the node.
2. Use **Configure**.
3. Enter the required values.
4. Confirm.
5. Validate the workflow.

---

# Readers

Readers are workflow entry points.

They load external data into the workflow.

Current reader foundations include:

- Vector Reader
- Raster Reader
- Table Reader
- Database Reader

---

# Vector Reader

## Purpose

Reads vector data into the workflow.

It is intended for common QGIS/GDAL/OGR vector sources.

Examples include:

- Shapefile
- GeoPackage
- GeoJSON
- File Geodatabase where supported
- KML/KMZ where supported
- DXF where supported
- Other OGR-supported vector sources

## Typical workflow

```text
Vector Reader
      ↓
Buffer
      ↓
Vector Writer
```

## Important

Format support depends on the QGIS/GDAL installation.

A file format supported by one QGIS build may not be available in another build.

---

# Raster Reader

## Purpose

Reads raster datasets into the workflow.

Common GDAL-supported examples include:

- GeoTIFF
- JPEG
- PNG
- JPEG 2000
- IMG
- VRT
- Other supported GDAL raster formats

Typical workflow:

```text
Raster Reader
      ↓
Raster Calculator
      ↓
Raster Writer
```

Raster data may have:

- CRS
- Width/height
- Bands
- Pixel size
- Data type
- NoData information

---

# Table Reader

## Purpose

Reads tabular information.

Examples:

- CSV
- DBF
- Other supported tabular sources

Depending on the source and configuration, tabular data can potentially be used as:

- Attribute table
- X/Y point data
- WKT geometry data

---

# Database Reader

The Database Reader represents the database-reader part of the workflow architecture.

The current release provides the typed workflow foundation for database sources.

Full database connection management and advanced table-selection functionality are planned for future versions.

Do not assume that every database type is fully implemented in 0.2.5.

---

# Geometry transformers

Current geometry transformer foundations include:

- Buffer
- Clip
- Dissolve
- Intersection
- Difference
- Centroid
- Fix Geometry

These transformers generally operate on vector layers.

---

# Buffer

## Purpose

Creates a buffer around input geometries.

Concept:

```text
Input geometry
      ↓
    Buffer
      ↓
Buffered geometry
```

Example:

```text
Roads
  ↓
Buffer 25 m
  ↓
Road_25m_Buffer
```

The distance and other options depend on the transformer configuration.

Be careful with CRS: distances should normally be calculated in an appropriate projected coordinate system.

---

# Clip

## Purpose

Extracts the portion of one vector dataset that falls within another geometry.

Typical workflow:

```text
Input Features ─────→ Clip
                       ↑
Clip Layer ────────────┘
```

Example:

```text
Parcels
   │
   └─────────────┐
                 ▼
              Clip
                 ▲
                 │
            Project Area
```

The exact input roles should be checked in the transformer configuration.

---

# Dissolve

## Purpose

Combines geometries based on dissolve rules.

Typical use:

```text
Parcels
   ↓
Dissolve
   ↓
Merged boundaries
```

Dissolve can be useful for:

- Administrative boundaries
- Parcel grouping
- Land-use grouping
- Buffer cleanup
- Removing internal boundaries

---

# Intersection

## Purpose

Returns the spatial overlap between two vector datasets.

Concept:

```text
Layer A ──────┐
              ▼
        Intersection
              ▲
Layer B ──────┘
```

The result contains geometry representing the intersection.

---

# Difference

## Purpose

Removes the portion of one dataset covered by another.

Concept:

```text
Input ─────────┐
               ▼
           Difference
               ▲
Overlay ───────┘
```

Example:

```text
Parcel
  minus
Road ROW
```

This can be useful in parcel and right-of-way workflows.

---

# Centroid

## Purpose

Creates a point representing the centroid of each input feature.

Example:

```text
Polygon
   ↓
Centroid
   ↓
Point
```

For polygon or multipart polygon input, the transformer creates a Point output.

Source attributes are carried to the centroid output.

Example:

```text
Parcel Polygon
     ↓
  Centroid
     ↓
Parcel Point
```

This is useful for:

- Label points
- Parcel representative points
- POI generation
- Point-based spatial joins
- Sampling workflows

---

# Fix Geometry

## Purpose

Attempts to repair invalid vector geometry using QGIS Processing functionality.

Typical workflow:

```text
Raw polygons
     ↓
Fix Geometry
     ↓
Valid/cleaned polygons
```

Geometry repair should still be checked against the requirements of the actual project.

---

# Attribute transformers

Current attribute transformer foundations include:

- Field Calculator
- Filter by Expression
- Merge Vector Layers

---

# Field Calculator

## Purpose

Creates or calculates attribute values using QGIS expressions.

Basic concept:

```text
Vector
  ↓
Field Calculator
  ↓
Vector with calculated attributes
```

Examples of QGIS expressions include:

### Area

```text
$area
```

### Area in hectares

```text
$area / 10000
```

### Perimeter

```text
$perimeter
```

### X coordinate

```text
$x
```

### Y coordinate

```text
$y
```

### Geometry centroid X

```text
x(centroid($geometry))
```

### Geometry centroid Y

```text
y(centroid($geometry))
```

### Attribute combination

```text
"OWNER" || ' - ' || "PARCEL_ID"
```

### Conditional value

```text
CASE
    WHEN $area > 10000 THEN 'Large'
    WHEN $area > 5000 THEN 'Medium'
    ELSE 'Small'
END
```

> The exact Field Calculator dialog/options available in a release depend on the implementation of that release. Use the fields shown by the current transformer configuration dialog rather than assuming future options are already available.

---

# Filter by Expression

## Purpose

Keeps features that satisfy a QGIS expression.

Example:

```text
"LAND_USE" = 'RESIDENTIAL'
```

or:

```text
$area > 1000
```

Workflow:

```text
Vector Reader
     ↓
Filter by Expression
     ↓
Vector Writer
```

---

# Merge Vector Layers

## Purpose

Combines compatible vector datasets into a merged vector result.

This transformer is currently a foundation and will be expanded for richer multi-input/collection workflows.

For production workflows, verify that the input schemas and geometry types are compatible.

---

# CRS transformers

---

# Reproject

## Purpose

Transforms vector data from one CRS to another.

Example:

```text
Input: EPSG:4326
       ↓
   Reproject
       ↓
Output: EPSG:27700
```

Typical uses:

- British National Grid
- Web Mercator
- Local projected CRS
- Converting geographic coordinates to projected coordinates

## Important

Choose a CRS appropriate for the operation.

For measurements such as area or distance, a suitable projected CRS is often preferable to a geographic CRS.

---

# Raster transformers

---

# Raster Calculator

## Purpose

Performs raster calculations using QGIS/GDAL Processing functionality.

Concept:

```text
Raster Reader
      ↓
Raster Calculator
      ↓
Raster Writer
```

A simple expression can use raster input `A`.

Example:

```text
A
```

More advanced raster expressions can be added as the transformer implementation evolves.

---

# Writers

Writers are workflow endpoints.

Current writers include:

- Vector Writer
- Raster Writer

---

# Vector Writer

## Purpose

Writes vector workflow output to a file.

Typical workflow:

```text
Vector Reader
      ↓
Buffer
      ↓
Vector Writer
```

Configure the destination path and output format supported by the current QGIS Processing implementation.

---

# Raster Writer

## Purpose

Writes raster workflow output.

Typical workflow:

```text
Raster Reader
      ↓
Raster Calculator
      ↓
Raster Writer
```

Raster output depends on the GDAL/QGIS installation and selected destination format.

---

# Building your first workflow

Let's create a simple workflow.

## Step 1 — Add Reader

Add:

```text
Vector Reader
```

Configure it with a vector dataset.

## Step 2 — Add transformer

Add:

```text
Buffer
```

Configure the buffer distance.

## Step 3 — Add Writer

Add:

```text
Vector Writer
```

Configure an output path.

## Step 4 — Connect

Connect:

```text
Vector Reader OUTPUT
        ↓
Buffer INPUT

Buffer OUTPUT
        ↓
Vector Writer INPUT
```

## Step 5 — Validate

Run:

```text
Validate
```

The workflow should report successful validation.

## Step 6 — Run

Run:

```text
Run Workflow
```

The execution log should show each transformer in dependency order.

---

# Example: Parcel workflow

A typical parcel-processing workflow can be:

```text
                 ┌───────────────┐
                 │ Parcel Reader │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Fix Geometry  │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   Reproject   │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │Field Calculator│
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Vector Writer │
                 └───────────────┘
```

For example, Field Calculator could calculate:

```text
Area_Ha = $area / 10000
```

---

# Example: Buffer and clip workflow

```text
Road Reader
     │
     ▼
  Buffer
     │
     │
     ├─────────────────┐
     │                 │
     ▼                 ▼
                  Project Boundary
     │                 │
     └───────┬─────────┘
             ▼
           Clip
             │
             ▼
       Vector Writer
```

This is an example of a workflow with multiple data dependencies.

---

# Example: Attribute calculation workflow

```text
Parcel Reader
      ↓
Field Calculator
      ↓
Filter by Expression
      ↓
Vector Writer
```

Example:

```text
Field:
Area_Ha

Expression:
$area / 10000
```

Then filter:

```text
"Area_Ha" > 1
```

The result contains only parcels larger than one hectare.

---

# Branching workflows

A workflow can branch.

For example:

```text
                  ┌──→ Field Calculator ──→ Writer A
                  │
Vector Reader ────┤
                  │
                  └──→ Centroid ──────────→ Writer B
```

The same Reader output can therefore feed more than one downstream operation.

This is useful when the same source dataset needs to produce several derived outputs.

---

# Validation

Always validate a workflow before running it.

Validation checks the workflow structure and reports problems such as:

- Missing inputs
- Missing required configuration
- Invalid connections
- Type mismatches
- Invalid workflow dependencies
- Invalid sources
- Output configuration problems
- Cyclic workflow dependencies where detected

A successful validation means the graph passed the plugin's structural checks.

It does **not** guarantee that every external dataset, driver, expression or Processing operation will succeed at runtime.

---

# Running a workflow

The normal sequence should be:

```text
Build
  ↓
Configure
  ↓
Connect
  ↓
Validate
  ↓
Run
```

During execution, the message panel reports the current transformer.

Example:

```text
▶ Starting workflow execution…

▶ Vector Reader
✓ Vector Reader complete.

▶ Buffer
✓ Buffer complete.

▶ Vector Writer
✓ Vector Writer complete.

✓ Workflow completed successfully.
```

If something fails, execution reports the failing transformer and error.

---

# Execution messages and troubleshooting

A workflow error normally contains three useful pieces:

1. Transformer name
2. QGIS Processing error
3. Python traceback, where available

Example:

```text
▶ Centroid

❌ Workflow failed:
Could not write feature...

Traceback...
```

The transformer named immediately before the error is usually the first place to investigate.

---

# Previewing a transformer

The transformer context menu can provide:

```text
Preview Output
```

The current implementation provides the foundation for intermediate-output preview.

Preview functionality is still being expanded and should not be treated as a complete interactive debugger in version 0.2.5.

---

# Saving and opening workflows

Workflows can be saved as:

```text
.gtworkflow
```

A workflow file stores the workflow structure/configuration so it can be reopened later.

Typical process:

```text
Build workflow
      ↓
Save
      ↓
MyParcelWorkflow.gtworkflow
```

Later:

```text
Open
 ↓
MyParcelWorkflow.gtworkflow
 ↓
Continue editing / execution
```

## Important

A workflow file should not be assumed to contain copies of all source datasets.

If your Reader references:

```text
C:\GIS\Data\Parcels.gpkg
```

the referenced data must still be accessible when the workflow is executed.

For portable workflows, keep the workflow and source data in a controlled project/data structure and use appropriate paths.

---

# Standalone Processing algorithms

Selected transformers are also exposed through the QGIS Processing framework.

The current provider includes transformer implementations such as:

- Buffer
- Reproject
- Dissolve
- Clip
- Fix Geometry

This means they can be used independently from the visual canvas where supported.

The visual workflow and Processing provider are two interfaces to the same general transformer architecture:

```text
                   QGIS Transformer Studio
                           │
             ┌─────────────┴─────────────┐
             │                           │
       Visual Workflow            Processing Toolbox
```

---

# Keyboard and mouse controls

## Mouse

| Action | Result |
|---|---|
| Left click | Select/interact with node |
| Drag node | Move node |
| Drag output → input | Create connection |
| Right click node | Context menu |
| Wheel | Zoom |
| Middle mouse drag | Pan |
| Selection drag | Select multiple nodes where supported |

## Keyboard

| Shortcut | Action |
|---|---|
| `Ctrl + D` | Duplicate selected node |
| `Delete` | Delete selected node |
| `Backspace` | Delete selected node |
| `F` | Fit workflow view where supported |
| `0` | Reset view where supported |

Exact behavior can vary slightly with focus and the operating system/QGIS Qt environment.

---

# Important limitations in 0.2.5

Version 0.2.5 is a **foundation release**, not the final 1.0 implementation.

The following areas are still being expanded:

## Database Reader

The current Database Reader is a typed workflow foundation. Advanced database connection management and table browsing are planned.

## Merge Vector Layers

The current implementation is a foundation for merging vector data and will be expanded for true collection/multi-input workflows.

## Raster Calculator

The current implementation provides a basic raster-calculation path. Multiple raster inputs and a richer expression builder are planned.

## Field Calculator

The current transformer provides basic QGIS expression calculation. A more advanced multi-calculation interface is planned.

## Preview

Preview is a foundation and will become a more complete intermediate-data inspection system.

## Geometry typing

The workflow engine is moving toward more detailed geometry-aware types such as:

```text
POINT
LINE
POLYGON
```

in addition to generic vector data.

## Advanced workflow features

Planned features include:

- Multiple input/output ports
- Collections
- Iterators
- Conditional routing
- Workflow parameters
- Batch execution
- Reusable templates
- Custom transformers
- Transformer packages
- More Readers
- More Writers
- Service/API readers
- Better debugging
- Feature counts
- Execution timing
- Intermediate data inspection

---

# Recommended workflow practices

## 1. Validate before execution

Always use:

```text
Validate → Run
```

rather than immediately executing a complex workflow.

## 2. Use appropriate CRS

Before distance/area operations, make sure the data uses a CRS appropriate for the measurement.

## 3. Fix geometry before complex overlays

A common workflow pattern is:

```text
Reader
 ↓
Fix Geometry
 ↓
Spatial operation
```

This can reduce failures caused by invalid geometries.

## 4. Keep workflows modular

Instead of creating one extremely large graph, separate logical stages.

For example:

```text
INPUT
 ↓
CLEAN
 ↓
TRANSFORM
 ↓
ATTRIBUTE
 ↓
OUTPUT
```

## 5. Give nodes meaningful configuration

When building larger workflows, use clear names/configuration values so another analyst can understand the workflow.

## 6. Keep source data accessible

Readers depend on their configured input data.

## 7. Save reusable workflows

If a process is repeated regularly, save the `.gtworkflow` rather than rebuilding it manually.

---

# Troubleshooting

## Plugin does not appear

Check:

1. The plugin is installed.
2. The plugin is enabled.
3. QGIS was restarted after installation.
4. The plugin directory contains:

```text
QGIS_Transformer_Studio/
```

5. `metadata.txt` and `__init__.py` exist.

## Plugin fails during startup

Open:

```text
View → Panels → Log Messages
```

and inspect the QGIS Python/Plugin messages.

Provide the complete traceback when reporting the issue.

## Transformer appears in the log but not on the canvas

First:

1. Confirm the standalone Transformer Studio window is active.
2. Use the canvas fit/reset controls.
3. Try adding a new transformer.
4. Restart the plugin if necessary.
5. Do not load an old workflow until basic node creation works.

## Connection cannot be created

Check the port types.

For example:

```text
RASTER → VECTOR INPUT
```

is normally invalid.

Use a transformer that converts or processes the required data type.

## Workflow validation fails

Read the validation message and check:

- Missing configuration
- Missing input connection
- Invalid source path
- Type mismatch
- Missing writer
- Invalid workflow dependency

## Workflow starts but fails during execution

This is different from validation failure.

Validation checks workflow structure.

Execution can still fail because of:

- Missing files
- Invalid geometries
- Unsupported format
- GDAL/OGR driver problems
- Invalid expression
- CRS problems
- Permission problems
- Invalid Processing parameters
- Data-specific errors

Copy the complete error and traceback when reporting it.

---

# Reporting a bug

Please report issues through:

https://github.com/ViduthalaiMuthu/QGIS-Plugins/issues

Include:

### QGIS information

```text
QGIS version:
Operating system:
Python version:
QGIS Transformer Studio version:
```

### Workflow

```text
Reader:
Transformer:
Writer:
```

### Error

Include the complete message and traceback.

### Data

If possible, provide:

- Small sample dataset
- Workflow file
- Screenshots
- Exact steps to reproduce

A good bug report looks like:

```text
QGIS: 4.2.2
OS: Windows 11
Plugin: 0.2.5

Steps:
1. Add Vector Reader
2. Configure polygon GeoPackage
3. Add Centroid
4. Connect Reader → Centroid
5. Add Vector Writer
6. Run

Error:
[paste complete traceback]
```

---

# Development and contribution

Source repository:

https://github.com/ViduthalaiMuthu/QGIS-Plugins

The project is written primarily in Python using:

- PyQGIS
- QGIS Processing
- Qt/PyQt supplied by QGIS
- GDAL functionality available through QGIS

No separate Python installation should be required for normal plugin use.

## Development installation

For development, place the plugin directory in the QGIS profile plugin directory:

```text
<QGIS profile>/python/plugins/QGIS_Transformer_Studio/
```

Restart QGIS and enable the plugin.

## Development principles

New transformers should:

1. Have a clearly defined purpose.
2. Declare their input/output types.
3. Use QGIS Processing/PyQGIS where appropriate.
4. Provide clear configuration.
5. Produce useful error messages.
6. Avoid unnecessary external dependencies.
7. Work independently where practical.
8. Be chainable with other transformers.
9. Be documented in the user guide.
10. Be tested with representative vector/raster/table data.

---

# Roadmap

## 0.3 — Transformer expansion

Planned:

- More geometry transformers
- More spatial transformers
- More attribute transformers
- More raster transformers
- More CRS tools
- Quality-control transformers
- Improved Readers and Writers

## 0.4 — Workflow engine

Planned:

- Multiple inputs
- Multiple outputs
- Collections
- Stronger type validation
- More advanced dependency handling
- Conditional routing

## 0.5 — Debugging

Planned:

- Intermediate output inspection
- Feature counts
- Execution timing
- Transformer-level logs
- Better error recovery
- Data previews

## 0.6 — Automation

Planned:

- Workflow parameters
- Templates
- Iterators
- Loops
- Batch processing
- Reusable workflow components

## 1.0 — Transformer platform

Long-term goals:

- Custom Transformer SDK
- Reusable transformer packages
- Transformer marketplace/repository possibilities
- Workflow execution from Processing
- Advanced visual workflow editing
- Rich data inspection
- FME-style reusable ETL architecture built on QGIS

---

# Project structure

```text
QGIS_Transformer_Studio/
├── __init__.py
├── metadata.txt
├── LICENSE
├── README.md
├── CHANGELOG.md
├── icon.svg
├── icon.png
├── gis_transformer_studio.py
└── processing/
    ├── __init__.py
    ├── algorithms.py
    └── provider.py
```

---

# Compatibility

The current plugin targets:

```text
QGIS 4.2+
```

and declares compatibility through:

```text
QGIS 4.x
```

The plugin uses the Python and Qt environment supplied by QGIS.

Individual data formats depend on the GDAL/OGR drivers available in the user's QGIS installation.

---

# License

QGIS Transformer Studio is free and open-source software released under:

**GNU General Public License v2 or later (GPL-2.0-or-later)**.

See the `LICENSE` file for the complete license.

Copyright (C) 2026 Viduthalai Muthu M.

---

# Author and repository

**Author:** Viduthalai Muthu M

**Email:** `viduthalaimuthu5@gmail.com`

**GitHub repository:**

https://github.com/ViduthalaiMuthu/QGIS-Plugins

**Issue tracker:**

https://github.com/ViduthalaiMuthu/QGIS-Plugins/issues

---

# Quick-start cheat sheet

If you only want the shortest possible instructions:

```text
1. Install plugin
        ↓
2. Open QGIS Transformer Studio
        ↓
3. Add a Reader
        ↓
4. Configure the Reader
        ↓
5. Add a Transformer
        ↓
6. Configure the Transformer
        ↓
7. Add a Writer
        ↓
8. Connect:
   Reader → Transformer → Writer
        ↓
9. Validate
        ↓
10. Run
        ↓
11. Check Execution / Messages
        ↓
12. Save the workflow as .gtworkflow
```

For a more complex workflow:

```text
                 ┌──────────────→ Transformer A ──→ Writer A
                 │
Reader ──────────┤
                 │
                 └──────────────→ Transformer B ──→ Writer B
```

The goal of QGIS Transformer Studio is to make repeated GIS processing tasks easier to build, understand, reuse and automate without having to manually repeat every Processing operation in QGIS.
