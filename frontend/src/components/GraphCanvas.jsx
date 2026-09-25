import React, { forwardRef, useImperativeHandle, useRef, useState, useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import { Maximize2, Minus, Plus, Crosshair } from "lucide-react";

cytoscape.use(coseBilkent);

const TYPE_COLOR = {
  person: "#10b7a6",
  location: "#f5a623",
  object: "#7c5cbf",
  event: "#2454ff",
};

export const COMMUNITY_PALETTE = ["#f5a623", "#e8622c", "#7c5cbf", "#10b7a6", "#2454ff", "#16a34a"];

const LAYOUT = {
  name: "cose-bilkent",
  animate: false,
  nodeRepulsion: 6000,
  idealEdgeLength: 90,
  fit: true,
  padding: 40,
};

const GraphCanvas = forwardRef(function GraphCanvas(
  { nodes, edges, colorMode, communityOf, focusId, nHopIds, dimOthers, onSelect, visibleTypes, showLabels = true },
  ref
) {
  const cyRef = useRef(null);
  const [zoomPct, setZoomPct] = useState(100);

  useImperativeHandle(ref, () => ({
    fit: () => cyRef.current?.fit(undefined, 40),
    zoomBy: (f) => {
      const cy = cyRef.current;
      if (!cy) return;
      cy.zoom(cy.zoom() * f);
      cy.center();
    },
    center: (id) => {
      const cy = cyRef.current;
      if (!cy) return;
      const el = id ? cy.getElementById(id) : cy.elements();
      cy.animate({ center: { eles: el }, zoom: id ? 1.4 : cy.zoom() }, { duration: 250 });
    },
    getCy: () => cyRef.current,
  }));

  const elements = useMemo(() => {
    const visNodes = nodes.filter((n) => visibleTypes[n.type] !== false);
    const visIds = new Set(visNodes.map((n) => n.id));
    const nodeEls = visNodes.map((n) => ({
      data: { id: n.id, label: n.label, type: n.type, ...n },
      classes: n.type,
    }));
    const edgeEls = edges
      .filter((e) => visIds.has(e.source) && visIds.has(e.target))
      .map((e) => ({
        data: { id: `${e.source}__${e.target}`, source: e.source, target: e.target, label: e.label },
      }));
    return [...nodeEls, ...edgeEls];
  }, [nodes, edges, visibleTypes]);

  const stylesheet = useMemo(() => {
    const base = [
      {
        selector: "node",
        style: {
          width: 26,
          height: 26,
          "background-color": (el) =>
            colorMode === "community" && communityOf?.[el.id()] != null
              ? COMMUNITY_PALETTE[communityOf[el.id()] % COMMUNITY_PALETTE.length]
              : TYPE_COLOR[el.data("type")] || "#10b7a6",
          label: showLabels ? "data(label)" : "",
          "font-size": 9,
          color: "#374151",
          "text-valign": "bottom",
          "text-margin-y": 4,
          "border-width": 0,
          opacity: 1,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.1,
          "line-color": "#c7cad1",
          "target-arrow-color": "#c7cad1",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.7,
          "curve-style": "bezier",
          opacity: 0.9,
        },
      },
      {
        selector: ".dimmed",
        style: { opacity: 0.12 },
      },
      {
        selector: ".focus",
        style: {
          "border-width": 3,
          "border-color": "#e43d3d",
          width: 32,
          height: 32,
          "z-index": 999,
        },
      },
      {
        selector: ".selected",
        style: { "border-width": 3, "border-color": "#2454ff" },
      },
    ];
    return base;
  }, [colorMode, communityOf, showLabels]);

  const applyEmphasis = (cy) => {
    if (!cy) return;
    cy.elements().removeClass("dimmed focus selected");
    if (focusId) cy.getElementById(focusId).addClass("focus");
    if (nHopIds && nHopIds.size > 0) {
      cy.nodes().forEach((n) => {
        if (!nHopIds.has(n.id()) && n.id() !== focusId) n.addClass("dimmed");
      });
      cy.edges().forEach((e) => {
        if (!nHopIds.has(e.data("source")) || !nHopIds.has(e.data("target"))) {
          if (!(e.data("source") === focusId || e.data("target") === focusId)) e.addClass("dimmed");
        }
      });
    } else if (dimOthers) {
      cy.elements().not(`#${dimOthers}`).addClass("dimmed");
    }
  };

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <CytoscapeComponent
        elements={elements}
        stylesheet={stylesheet}
        layout={LAYOUT}
        style={{ width: "100%", height: "100%" }}
        cy={(cy) => {
          cyRef.current = cy;
          cy.off("tap zoom");
          cy.on("tap", "node", (evt) => onSelect?.(evt.target.id()));
          cy.on("tap", (evt) => {
            if (evt.target === cy) onSelect?.(null);
          });
          cy.on("zoom", () => setZoomPct(Math.round(cy.zoom() * 100)));
          applyEmphasis(cy);
        }}
      />
      {/* re-apply emphasis whenever inputs change, without re-mounting cytoscape */}
      {cyRef.current && applyEmphasis(cyRef.current)}

      <div className="zoom-dock">
        <button onClick={() => ref.current?.zoomBy(0.8)} title="Zoom out"><Minus size={14} /></button>
        <span className="pct">{zoomPct}%</span>
        <button onClick={() => ref.current?.zoomBy(1.25)} title="Zoom in"><Plus size={14} /></button>
        <button onClick={() => ref.current?.fit()} title="Fit to screen"><Maximize2 size={13} /></button>
        <button onClick={() => ref.current?.center(focusId)} title="Center"><Crosshair size={13} /></button>
      </div>
    </div>
  );
});

export default GraphCanvas;
