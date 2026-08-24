import { useEffect, useRef } from "react";
import { Canvas, FabricImage, Rect } from "fabric";
import { loadZones, saveZone } from "../lib/supabase";
import type { ZoneDef } from "../types";

interface Props {
  frameUrl: string;
}

// Epic 3 Day 1: user draws rectangular zones on a store frame; polygons persist to Supabase
export default function ZoneCanvas({ frameUrl }: Props) {
  const canvasEl = useRef<HTMLCanvasElement | null>(null);
  const canvasRef = useRef<Canvas | null>(null);
  const [zones, setZones] = useState<ZoneDef[]>([]);
  const [zoneName, setZoneName] = useState("");

  useEffect(() => {
    if (!canvasEl.current) return;
    const canvas = new Canvas(canvasEl.current, { selection: false });
    canvasRef.current = canvas;

    let drawingRect: Rect | null = null;
    let origin = { x: 0, y: 0 };

    canvas.on("mouse:down", (opt) => {
      origin = { x: opt.scenePoint.x, y: opt.scenePoint.y };
      drawingRect = new Rect({ left: origin.x, top: origin.y, width: 1, height: 1, fill: "rgba(56,189,248,0.2)", stroke: "#38bdf8" });
      canvas.add(drawingRect);
    });
    canvas.on("mouse:move", (opt) => {
      if (!drawingRect) return;
      drawingRect.set({
        width: Math.abs(opt.scenePoint.x - origin.x),
        height: Math.abs(opt.scenePoint.y - origin.y),
        left: Math.min(origin.x, opt.scenePoint.x),
        top: Math.min(origin.y, opt.scenePoint.y),
      });
      canvas.requestRenderAll();
    });
    canvas.on("mouse:up", () => {
      // TODO(epic-3 day 1): prompt for zone name, convert rect -> polygon points,
      // push into zones state and enable save; also allow edit/delete of existing zones
      drawingRect = null;
    });

    FabricImage.fromURL(frameUrl, { crossOrigin: "anonymous" }).then((img) => {
      canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas));
      canvas.requestRenderAll();
    });

    loadZones()
      .then(setZones)
      .catch(() => setZones([]));

    return () => {
      canvas.dispose();
      canvasRef.current = null;
    };
  }, [frameUrl]);

  const handleSave = async () => {
    // TODO(epic-3 day 2): take the last drawn rectangle's corners as the polygon and call saveZone
  };

  return (
    <div>
      <canvas ref={canvasEl} width={640} height={480} />
      <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} placeholder="Zone name" />
      <button onClick={handleSave}>Save zones</button>
      <ul>
        {zones.map((z) => (
          <li key={z.id ?? z.name}>{z.name}</li>
        ))}
      </ul>
    </div>
  );
}
