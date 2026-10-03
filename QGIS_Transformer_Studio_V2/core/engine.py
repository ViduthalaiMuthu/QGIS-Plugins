
import json
import os
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
import shutil
from collections import defaultdict, deque

import processing
from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsProcessingContext, QgsProcessingFeedback, QgsVectorFileWriter
)

from .catalog import TRANSFORMER_CATALOG

CATALOG = {x["name"]: x for x in TRANSFORMER_CATALOG}

def algorithm_available(algorithm_id):
    try:
        return bool(algorithm_id and QgsApplication.processingRegistry().algorithmById(algorithm_id))
    except Exception:
        return False

def default_parameters(algorithm_id):
    """Build a conservative parameter dictionary from QGIS Processing metadata."""
    alg = QgsApplication.processingRegistry().algorithmById(algorithm_id)
    if not alg:
        return {}
    out = {}
    for p in alg.parameterDefinitions():
        if p.name() in ("INPUT", "OUTPUT"):
            continue
        try:
            v = p.defaultValue()
            if v is not None:
                out[p.name()] = v
        except Exception:
            pass
    return out

def _layer_uri(layer):
    if hasattr(layer, "source"):
        return layer.source()
    return layer

def read_source(path, kind="vector", name=None):
    if not path:
        raise ValueError("Source path is empty.")
    name = name or os.path.basename(path)
    if kind == "raster":
        lyr = QgsRasterLayer(path, name)
    else:
        lyr = QgsVectorLayer(path, name, "ogr")
    if not lyr.isValid():
        raise ValueError(f"Could not open source: {path}")
    return lyr

def _write_json_temp(payload, suffix=".json"):
    fd, path = tempfile.mkstemp(prefix="qts_", suffix=suffix)
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def _feedback(feedback, text=None, progress=None):
    if feedback:
        if text:
            feedback.setProgressText(str(text))
            feedback.pushInfo(str(text))
        if progress is not None:
            feedback.setProgress(max(0, min(100, int(progress))))
        try:
            from qgis.PyQt.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception:
            pass


def _normalise_output_path(path, fmt, layer_name="parcels"):
    """Return a concrete filename so OGR can always select a driver."""
    path = (path or "").strip()
    ext_map = {
        "GeoPackage": ".gpkg",
        "Shapefile": ".shp",
        "GeoJSON": ".geojson",
        "CSV": ".csv",
    }
    ext = ext_map.get(fmt, ".gpkg")
    if not path:
        fd, path = tempfile.mkstemp(prefix="qts_parcels_", suffix=ext)
        os.close(fd)
        try: os.remove(path)
        except OSError: pass
        return path
    if os.path.isdir(path):
        path = os.path.join(path, layer_name or "parcels")
    root, current_ext = os.path.splitext(path)
    if current_ext.lower() != ext:
        # If the user supplied another extension, replace it rather than letting
        # OGR guess a driver from an unsupported/empty suffix.
        path = root + ext if current_ext else path + ext
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    return path


def _release_output_layer(path):
    """Remove a project layer that is currently using the target datasource.

    On Windows an open GeoPackage can remain locked by QGIS. Releasing the
    project reference before replacing the file prevents the common
    'Opening of data source in update mode failed' error.
    """
    try:
        target = os.path.normcase(os.path.abspath(path))
        project = QgsProject.instance()
        for lyr in list(project.mapLayers().values()):
            try:
                src = lyr.source() if hasattr(lyr, "source") else ""
                if src and os.path.normcase(os.path.abspath(src.split("|", 1)[0])) == target:
                    project.removeMapLayer(lyr.id())
            except Exception:
                continue
    except Exception:
        pass

def _write_vector(layer, path, fmt, layer_name, feedback=None):
    """Write a vector layer with deterministic driver selection and safer GPKG replacement.

    For GeoPackage, write to a sibling temporary file first. This prevents a
    late failure from destroying an existing output and avoids opening an
    existing datasource in update mode during the main write.
    """
    driver = {
        "GeoPackage": "GPKG",
        "Shapefile": "ESRI Shapefile",
        "GeoJSON": "GeoJSON",
        "CSV": "CSV",
    }.get(fmt, "GPKG")
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)

    if driver == "GPKG":
        _release_output_layer(path)
        temp = os.path.join(parent, f".{os.path.basename(path)}.qts_tmp_{os.getpid()}_{int(time.time()*1000)}.gpkg")
        try:
            try:
                if os.path.exists(temp): os.remove(temp)
            except OSError:
                pass
            opts = QgsVectorFileWriter.SaveVectorOptions()
            opts.driverName = "GPKG"
            opts.fileEncoding = "UTF-8"
            opts.layerName = layer_name or "parcels"
            opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
            opts.feedback = None
            result = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer, temp, QgsProject.instance().transformContext(), opts
            )
            err = result[0] if isinstance(result, tuple) else result
            if err != QgsVectorFileWriter.NoError:
                msg = result[1] if isinstance(result, tuple) and len(result)>1 else str(err)
                raise ValueError(f"Could not create temporary GeoPackage: {msg}")
            if not os.path.exists(temp) or os.path.getsize(temp) == 0:
                raise ValueError("QGIS reported a successful GeoPackage write, but the temporary file was not created.")
            _release_output_layer(path)
            try:
                if os.path.exists(path): os.remove(path)
                os.replace(temp, path)
            except OSError as exc:
                # Preserve the successfully written file rather than losing the data.
                fallback = _unique_sibling(path)
                os.replace(temp, fallback)
                raise ValueError(f"Target GeoPackage is locked or unavailable: {path}. A safe copy was written to {fallback}. ({exc})")
            return path
        finally:
            try:
                if os.path.exists(temp): os.remove(temp)
            except OSError:
                pass

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = driver
    opts.fileEncoding = "UTF-8"
    opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    if driver == "GeoJSON":
        opts.layerName = layer_name or "parcels"
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, QgsProject.instance().transformContext(), opts
    )
    err = result[0] if isinstance(result, tuple) else result
    if err != QgsVectorFileWriter.NoError:
        msg = result[1] if isinstance(result, tuple) and len(result)>1 else str(err)
        raise ValueError(f"Could not write output '{path}': {msg}")
    return path

def _unique_sibling(path):
    root, ext = os.path.splitext(path)
    for i in range(1, 10000):
        candidate = f"{root}_qts_{i:03d}{ext}"
        if not os.path.exists(candidate):
            return candidate
    raise ValueError(f"Could not find a free output filename beside: {path}")

def _arcgis_query_url(url):
    url = url.rstrip("/")
    if not url.lower().endswith("/query"):
        url += "/query"
    return url


def _http_json(url, params, timeout, feedback=None):
    qurl = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(qurl, headers={"User-Agent": "QGIS-Transformer-Studio/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1000]
        raise ValueError(f"FeatureServer HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise ValueError(f"FeatureServer connection failed: {e.reason}")
    except TimeoutError:
        raise ValueError("FeatureServer request timed out.")


def parcel_download(cfg, feedback=None):
    url = _arcgis_query_url(cfg.get("url", "").strip())
    if not url:
        raise ValueError("Parcel Downloader: FeatureServer URL is required.")
    batch = max(1, int(cfg.get("batch_size", 2000)))
    timeout = max(5, int(cfg.get("timeout", 60)))
    where = cfg.get("where", "1=1") or "1=1"
    out_fields = cfg.get("out_fields", "*") or "*"
    out_sr = str(cfg.get("out_sr", "4326") or "4326")
    geometry = cfg.get("geometry", "") or ""
    geometry_type = cfg.get("geometry_type", "esriGeometryEnvelope")
    spatial_rel = cfg.get("spatial_rel", "esriSpatialRelIntersects")
    layer_name = cfg.get("layer_name", "parcels") or "parcels"
    output_format = cfg.get("output_format", "GeoPackage") or "GeoPackage"
    output_path = _normalise_output_path(cfg.get("output", ""), output_format, layer_name)

    _feedback(feedback, "Connecting to ArcGIS FeatureServer…", 0)
    count_params = {
        "where": where, "returnCountOnly": "true", "f": "json"
    }
    if geometry:
        count_params.update({"geometry": geometry, "geometryType": geometry_type, "spatialRel": spatial_rel})
    total = None
    try:
        count_data = _http_json(url, count_params, timeout, feedback)
        if "error" in count_data:
            raise ValueError(str(count_data["error"]))
        total = int(count_data.get("count")) if count_data.get("count") is not None else None
    except Exception as e:
        _feedback(feedback, f"Feature count unavailable; continuing with paged download ({e})")

    all_features = []
    offset = 0
    batch_no = 0
    while True:
        if feedback and feedback.isCanceled():
            raise ValueError("Parcel download cancelled by user.")
        batch_no += 1
        params = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true",
            "f": "geojson",
            "resultOffset": str(offset),
            "resultRecordCount": str(batch),
            "outSR": out_sr,
        }
        if geometry:
            params.update({"geometry": geometry, "geometryType": geometry_type, "spatialRel": spatial_rel})
        _feedback(feedback, f"Downloading batch {batch_no} — {offset:,} features received…",
                  (offset / total * 100) if total else min(95, batch_no % 95))
        data = _http_json(url, params, timeout, feedback)
        if "error" in data:
            raise ValueError(f"ArcGIS FeatureServer error: {data['error']}")
        feats = data.get("features", []) or []
        if not feats:
            break
        all_features.extend(feats)
        offset += len(feats)
        exceeded = bool(data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit"))
        if total:
            _feedback(feedback, f"Downloaded {offset:,} / {total:,} features",
                      min(99, offset / total * 100))
        else:
            _feedback(feedback, f"Downloaded {offset:,} features")
        if feedback and feedback.isCanceled():
            raise ValueError("Parcel download cancelled by user.")
        if len(feats) < batch and not exceeded:
            break
        # Some services ignore resultOffset and return the same first page.
        if len(all_features) > batch and len(feats) == batch and offset == batch:
            pass

    if not all_features:
        raise ValueError("FeatureServer returned 0 features for the current WHERE/geometry filter.")

    _feedback(feedback, f"Building {len(all_features):,} downloaded features…", 99)
    fc = {"type": "FeatureCollection", "features": all_features}
    temp_geojson = _write_json_temp(fc, ".geojson")
    lyr = QgsVectorLayer(temp_geojson, layer_name, "ogr")
    if not lyr.isValid():
        raise ValueError("ArcGIS FeatureServer returned data, but QGIS could not open the GeoJSON result.")
    if feedback and feedback.isCanceled():
        raise ValueError("Parcel download cancelled by user.")
    _feedback(feedback, f"Writing {output_format} output: {output_path}", 99)
    try:
        _write_vector(lyr, output_path, output_format, layer_name, feedback)
    except Exception as first_error:
        # Never discard a completed download. Write to a unique sibling.
        fallback = _unique_sibling(output_path)
        _feedback(feedback, f"⚠ Requested output could not be finalized: {first_error}")
        _feedback(feedback, f"Writing a safe fallback copy: {fallback}", 99)
        try:
            _write_vector(lyr, fallback, output_format, layer_name, feedback)
            output_path = fallback
        except Exception as second_error:
            raise ValueError(
                f"Could not write the downloaded parcels.\n\n"
                f"Requested output: {output_path}\n"
                f"First error: {first_error}\n"
                f"Fallback error: {second_error}\n\n"
                f"The downloaded GeoJSON has been retained at: {temp_geojson}"
            )
    out_layer = QgsVectorLayer(output_path, layer_name, "ogr")
    if not out_layer.isValid():
        raise ValueError(f"Output was written but QGIS could not reopen it: {output_path}")
    _feedback(feedback, f"✓ Parcel download complete — {len(all_features):,} features → {output_path}", 100)
    try: os.remove(temp_geojson)
    except OSError: pass
    return out_layer, output_path, len(all_features)

def http_call(cfg):
    url = cfg.get("url","").strip()
    if not url:
        raise ValueError("HTTP Caller: URL is required.")
    method = cfg.get("method","GET").upper()
    headers = cfg.get("headers",{})
    if isinstance(headers, str):
        headers = json.loads(headers or "{}")
    query = cfg.get("query",{})
    if isinstance(query, str):
        query = json.loads(query or "{}")
    if query:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode(query)
    body = cfg.get("body","")
    if isinstance(body, (dict,list)):
        body = json.dumps(body)
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=int(cfg.get("timeout",60))) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type","")
        text = raw.decode("utf-8", errors="replace")
        suffix = ".json" if "json" in ctype.lower() else ".txt"
        path = _write_json_temp(json.loads(text), suffix) if "json" in ctype.lower() else _write_json_temp({"status":resp.status,"content":text}, suffix)
        return path, resp.status, ctype

def _resolve_processing_inputs(spec, alg, input_values):
    """Map Studio logical ports to the actual parameter names exposed by this QGIS build."""
    defined = {p.name(): p for p in alg.parameterDefinitions()}
    params = {}
    # Exact matches always win.
    for key, value in input_values.items():
        if key in defined:
            params[key] = value
    # Common semantic aliases used by older catalog entries.
    aliases = {
        "OVERLAY": ["OVERLAY", "LINES", "JOIN", "TARGET", "POLYGONS", "INTERSECT"],
        "INPUT_2": ["INPUT_2", "JOIN", "TARGET", "OVERLAY", "INTERSECT"],
        "OVERLAY_2": ["OVERLAY_2", "JOIN", "TARGET"],
        "INPUT": ["INPUT", "INPUT_LAYER", "SOURCE"],
        "INPUT_2": ["INPUT_2", "JOIN", "TARGET", "DESTINATION"],
    }
    used = set(params)
    for logical, value in input_values.items():
        if logical in defined or logical in used:
            continue
        for candidate in aliases.get(logical, []):
            if candidate in defined and candidate not in used:
                params[candidate] = value; used.add(candidate); break
    return params

def execute_node(node, input_values, feedback=None):
    name = node["name"]
    cfg = node.get("config",{})
    spec = CATALOG[name]
    kind = spec.get("kind")
    if name == "Centroids":
        inp = input_values.get("INPUT")
        if inp is None:
            raise ValueError("Centroids: INPUT is not connected.")
        from qgis.core import QgsFeature, QgsGeometry, QgsWkbTypes
        fields = inp.fields()
        out = QgsVectorLayer("Point?crs=" + inp.crs().authid(), "Centroids", "memory")
        out.dataProvider().addAttributes(list(fields)); out.updateFields()
        total = inp.featureCount()
        for i, feat in enumerate(inp.getFeatures()):
            if feedback and feedback.isCanceled(): raise ValueError("Centroids cancelled by user.")
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                nf = QgsFeature(out.fields()); nf.setAttributes(feat.attributes()); nf.setGeometry(geom.centroid()); out.dataProvider().addFeature(nf)
            if total and i % 100 == 0: _feedback(feedback, f"Centroids: {i:,}/{total:,}", i/total*100)
        out.updateExtents()
        return {"OUTPUT": out}
    if kind == "custom":
        if name in ("Vector Reader","GeoJSON Reader","GeoPackage Reader","Shapefile Reader"):
            return {"OUTPUT": read_source(cfg.get("path",""), "vector", name)}
        if name == "Raster Reader":
            return {"OUTPUT": read_source(cfg.get("path",""), "raster", name)}
        if name == "Table Reader":
            path=cfg.get("path","")
            lyr=QgsVectorLayer(path, name, "ogr")
            if not lyr.isValid():
                raise ValueError(f"Could not open table: {path}")
            return {"OUTPUT":lyr}
        if name == "CSV Reader":
            lyr=QgsVectorLayer(cfg.get("path",""), name, "delimitedtext")
            if not lyr.isValid():
                raise ValueError(f"Could not open CSV: {cfg.get('path','')}")
            return {"OUTPUT":lyr}
        if name == "Database Reader":
            lyr=QgsVectorLayer(cfg.get("uri",""), name, "ogr")
            if not lyr.isValid():
                raise ValueError("Could not open database source URI.")
            return {"OUTPUT":lyr}
        if name == "HTTP Caller":
            path,status,ctype=http_call(cfg)
            return {"OUTPUT":path,"STATUS":status,"CONTENT_TYPE":ctype}
        if name == "Parcel Downloader":
            lyr,path,count=parcel_download(cfg, feedback)
            return {"OUTPUT":lyr,"SOURCE_FILE":path,"FEATURE_COUNT":count}
    if kind == "writer":
        inp=input_values.get("INPUT")
        if inp is None:
            raise ValueError(f"{name}: INPUT is not connected.")
        path=cfg.get("path","").strip()
        if not path:
            raise ValueError(f"{name}: output path is required.")
        ext = os.path.splitext(path)[1].lower()
        if not ext:
            ext = ".tif" if name == "Raster Writer" else ".gpkg"
            path += ext
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if name == "Raster Writer":
            res=processing.run("gdal:translate", {"INPUT":inp,"OUTPUT":path}, feedback=feedback)
        else:
            res=processing.run("native:savefeatures", {"INPUT":inp,"OUTPUT":path}, feedback=feedback)
        return {"OUTPUT":res.get("OUTPUT",path)}
    alg_id=spec["algorithm"]
    if not algorithm_available(alg_id):
        raise ValueError(f"{name}: QGIS Processing algorithm '{alg_id}' is not available in this QGIS installation.")
    params=dict(cfg.get("params",{}))
    alg=QgsApplication.processingRegistry().algorithmById(alg_id)
    params.update(_resolve_processing_inputs(spec, alg, input_values))
    # Set first output to a temporary layer unless explicitly overridden.
    output_names=[o.name() for o in alg.outputDefinitions()]
    if "OUTPUT" in output_names and "OUTPUT" not in params:
        params["OUTPUT"]="TEMPORARY_OUTPUT"
    result=processing.run(alg_id, params, feedback=feedback)
    return result


def validate_node(node, input_values=None):
    """Validate a node against the installed Processing provider before execution."""
    name = node["name"]
    spec = CATALOG.get(name)
    if not spec:
        raise ValueError(f"Unknown transformer: {name}")
    if spec.get("kind") in ("custom", "writer"):
        return
    aid = spec.get("algorithm")
    alg = QgsApplication.processingRegistry().algorithmById(aid) if aid else None
    if not alg:
        raise ValueError(f"{name}: QGIS algorithm '{aid}' is not available in this QGIS installation.")
    defined = {p.name() for p in alg.parameterDefinitions()}
    supplied = set((node.get("config") or {}).get("params", {}).keys())
    supplied.update((input_values or {}).keys())
    aliases = {
        "OVERLAY": {"OVERLAY","LINES","JOIN","TARGET","POLYGONS","INTERSECT"},
        "INPUT_2": {"INPUT_2","JOIN","TARGET","OVERLAY","INTERSECT","DESTINATION"},
        "INPUT": {"INPUT","INPUT_LAYER","SOURCE"},
        "LAYERS": {"LAYERS","INPUT"},
    }
    for port in spec.get("inputs", []):
        if port not in defined and not (port in aliases and any(a in defined for a in aliases[port])):
            raise ValueError(f"{name}: catalog input '{port}' is not supported by QGIS algorithm '{aid}'. Available inputs: {', '.join(sorted(defined))}")
    for p in alg.parameterDefinitions():
        if p.flags() & p.Flag.FlagOptional:
            continue
        if p.name() in supplied or p.name() == "OUTPUT":
            continue
        # Some catalog aliases may be supplied under a semantic name.
        alias_for = {
            "FIELD_NAME": {"FIELD_NAME"},
            "FIELD_TYPE": {"FIELD_TYPE"},
            "FIELD_LENGTH": {"FIELD_LENGTH"},
            "FIELD_PRECISION": {"FIELD_PRECISION"},
            "NEW_FIELD": {"NEW_FIELD"},
            "FORMULA": {"FORMULA"},
            "FIELD": {"FIELD"},
        }
        if p.name() in alias_for and any(a in supplied for a in alias_for[p.name()]):
            continue
        try:
            if p.defaultValue() is not None:
                continue
        except Exception:
            pass
        # Some QGIS parameters are optional at runtime despite their flag metadata.
        if p.name() not in spec.get("inputs", []):
            raise ValueError(f"{name}: required parameter '{p.name()}' is not configured. Open the transformer and set it in Processing parameters JSON.")

def topo_order(nodes, connections):
    ids=[n["id"] for n in nodes]
    indeg={i:0 for i in ids}
    adj=defaultdict(list)
    for c in connections:
        s,t=c["source"][0],c["target"][0]
        if s in indeg and t in indeg:
            adj[s].append(t); indeg[t]+=1
    q=deque([i for i in ids if indeg[i]==0])
    order=[]
    while q:
        u=q.popleft(); order.append(u)
        for v in adj[u]:
            indeg[v]-=1
            if indeg[v]==0:q.append(v)
    if len(order)!=len(ids):
        raise ValueError("Workflow contains a cycle.")
    return order

def run_workflow(nodes, connections, feedback=None, logger=None):
    order=topo_order(nodes, connections)
    byid={n["id"]:n for n in nodes}
    incoming=defaultdict(list)
    for c in connections:
        incoming[c["target"][0]].append(c)
    results={}
    for idx,nid in enumerate(order):
        node=byid[nid]
        vals={}
        for c in incoming.get(nid,[]):
            src_id,src_port=c["source"]
            tgt_port=c["target"][1]
            src_result=results[src_id]
            vals[tgt_port]=src_result.get(src_port)
        if feedback and feedback.isCanceled():
            raise ValueError("Workflow cancelled by user.")
        validate_node(node, vals)
        if logger: logger(f"[{idx+1}/{len(order)}] {node['name']}")
        if feedback:
            _feedback(feedback, f"Running {node['name']} ({idx+1}/{len(order)})…", idx/ max(len(order),1)*100)
        res=execute_node(node, vals, feedback)
        results[nid]=res
        if logger: logger(f"    ✓ {node['name']} completed")
    return results
