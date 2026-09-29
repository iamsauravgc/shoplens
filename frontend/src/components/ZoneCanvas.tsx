import { useEffect, useRef, useState } from "react";
import { Canvas, FabricImage, Rect, Text } from "fabric";
import { deleteZone, listZones, saveZone, zoneFrameUrl } from "../api/client";
import type { ZoneDef } from "../types";

interface RectGeom {
  left: number;
  top: number;
  width: number;
  height: number;
}

const COLORS = ["#38bdf8", "#f472b6", "#4ade80", "#facc15", "#a78bfa", "#fb923c"];
const MIN_DRAG = 10;

export default function ZoneCanvas() {
  const containerEl = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<Canvas | null>(null);
  const previewRef = useRef<Rect | null>(null);
  const overlaysRef = useRef<Rect[]>([]);
  const labelsRef = useRef<Text[]>([]);
  const [zones, setZones] = useState<ZoneDef[]>([]);
  const [zoneName, setZoneName] = useState("");
  const [pending, setPending] = useState<RectGeom | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    listZones()
      .then(setZones)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));

  useEffect(() => {
    const container = containerEl.current;
    if (!container) return;
    // Fabric moves the canvas into its own wrapper div; creating it imperatively
    // keeps React from reconciling a node it no longer owns (insertBefore crash)
    const el = document.createElement("canvas");
    container.appendChild(el);
    const canvas = new Canvas(el, { selection: false });
    canvasRef.current = canvas;

    let origin = { x: 0, y: 0 };

    canvas.on("mouse:down", (opt) => {
      // drop any earlier preview so rects never leak
      if (previewRef.current) {
        canvas.remove(previewRef.current);
        previewRef.current = null;
      }
      origin = { x: opt.scenePoint.x, y: opt.scenePoint.y };
      const rect = new Rect({
        left: origin.x,
        top: origin.y,
        width: 1,
        height: 1,
        fill: "rgba(56,189,248,0.2)",
        stroke: "#38bdf8",
        strokeWidth: 2,
        selectable: false,
        evented: false,
      });
      previewRef.current = rect;
      canvas.add(rect);
    });

    canvas.on("mouse:move", (opt) => {
      const rect = previewRef.current;
      if (!rect) return;
      rect.set({
        width: Math.abs(opt.scenePoint.x - origin.x),
        height: Math.abs(opt.scenePoint.y - origin.y),
        left: Math.min(origin.x, opt.scenePoint.x),
        top: Math.min(origin.y, opt.scenePoint.y),
      });
      canvas.requestRenderAll();
    });

    canvas.on("mouse:up", () => {
      const rect = previewRef.current;
      if (!rect) return;
      const geom: RectGeom = {
        left: Math.round(rect.left ?? 0),
        top: Math.round(rect.top ?? 0),
        width: Math.round(rect.width ?? 0),
        height: Math.round(rect.height ?? 0),
      };
      if (geom.width < MIN_DRAG || geom.height < MIN_DRAG) {
        canvas.remove(rect);
        previewRef.current = null;
        canvas.requestRenderAll();
        return;
      }
      setPending(geom);
    });

    // StrictMode (and any fast unmount) disposes this canvas while the image is
    // still in flight; ignore that promise instead of touching a dead canvas
    let disposed = false;

    FabricImage.fromURL(zoneFrameUrl())
      .then((img) => {
        if (disposed) return;
        // setWidth/setHeight are gone in Fabric v6+; setDimensions is the API
        canvas.setDimensions({
          width: img.width ?? 640,
          height: img.height ?? 480,
        });
        canvas.backgroundImage = img;
        canvas.requestRenderAll();
      })
      .catch((err: unknown) => {
        if (disposed) return;
        console.error("zone frame failed", err);
        setError(err instanceof Error ? err.message : "Could not load the reference frame");
      });

    refresh();

    return () => {
      disposed = true;
      canvas.dispose();
      container.replaceChildren();
      canvasRef.current = null;
      previewRef.current = null;
      overlaysRef.current = [];
      labelsRef.current = [];
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    overlaysRef.current.forEach((o) => canvas.remove(o));
    labelsRef.current.forEach((t) => canvas.remove(t));
    overlaysRef.current = [];
    labelsRef.current = [];

    zones.forEach((z, i) => {
      if (!z.polygon.length) return;
      const xs = z.polygon.map((p) => p.x);
      const ys = z.polygon.map((p) => p.y);
      const left = Math.min(...xs);
      const top = Math.min(...ys);
      const color = COLORS[i % COLORS.length];
      const box = new Rect({
        left,
        top,
        width: Math.max(...xs) - left,
        height: Math.max(...ys) - top,
        fill: `${color}26`,
        stroke: color,
        strokeWidth: 2,
        selectable: false,
        evented: false,
      });
      const label = new Text(z.name, {
        left: left + 4,
        top: top + 4,
        fontSize: 14,
        fill: color,
        selectable: false,
        evented: false,
      });
      overlaysRef.current.push(box);
      labelsRef.current.push(label);
      canvas.add(box, label);
    });
    canvas.requestRenderAll();
  }, [zones]);

  const clearPreview = () => {
    const canvas = canvasRef.current;
    if (canvas && previewRef.current) canvas.remove(previewRef.current);
    previewRef.current = null;
    setPending(null);
    canvas?.requestRenderAll();
  };

  const handleSave = async () => {
    if (!pending) {
      setError("Drag a rectangle on the frame first");
      return;
    }
    const name = zoneName.trim();
    if (!name) {
      setError("Give the zone a name");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await saveZone({
        name,
        polygon: [
          { x: pending.left, y: pending.top },
          { x: pending.left + pending.width, y: pending.top },
          { x: pending.left + pending.width, y: pending.top + pending.height },
          { x: pending.left, y: pending.top + pending.height },
        ],
      });
      setZoneName("");
      clearPreview();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id?: string) => {
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      await deleteZone(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="zone-editor">
      <p className="hint">
        Drag a rectangle over an area of the store floor, name it, and save. Zones are drawn once and
        reused for every video.
      </p>
      <div className="zone-toolbar">
        <input
          type="text"
          value={zoneName}
          onChange={(e) => setZoneName(e.target.value)}
          placeholder="Zone name (e.g. Entrance)"
        />
        <button onClick={handleSave} disabled={busy || !pending}>
          Save zone
        </button>
        <button className="secondary" onClick={clearPreview} disabled={busy || !pending}>
          Cancel
        </button>
      </div>
      {error && <div className="status status-error">{error}</div>}
      <div ref={containerEl} className="zone-canvas" />
      <h3>Saved zones ({zones.length})</h3>
      {zones.length === 0 ? (
        <p className="hint">No zones yet — draw the first one above.</p>
      ) : (
        <ul className="zone-list">
          {zones.map((z, i) => (
            <li key={z.id ?? z.name}>
              <span className="zone-swatch" style={{ background: COLORS[i % COLORS.length] }} />
              {z.name}
              <button className="danger" onClick={() => handleDelete(z.id)} disabled={busy}>
                delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}