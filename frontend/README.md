# Network Intelligence UI

A React + Cytoscape.js front end for a graph-based investigation tool
(Network / Analysis / Intelligence views), following the Flowsint-style
architecture: React for the shell, Cytoscape.js for the graph canvas, a
thin service layer where your Neo4j-backed REST API plugs in.

## Run it standalone

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Drop into an existing React app

1. Copy `src/components`, `src/data`, `src/styles`, and `src/App.jsx` into
   your project's `src/`.
2. Install the graph dependencies:
   ```bash
   npm install cytoscape cytoscape-cose-bilkent react-cytoscapejs lucide-react
   ```
3. Import `App.css` once in your app root, and render `<App />`.

## Where to wire in your backend

Everything currently runs on synthetic data in `src/data/mockNetwork.js`
and a couple of client-side stand-ins for real algorithms. Replace these
one at a time — nothing else in the component tree needs to change:

| File | What to replace |
|---|---|
| `src/data/mockNetwork.js` | `fetchNetwork(name)` → `GET /api/networks/{name}` returning `{ name, nodes, edges }` |
| `src/App.jsx` → `runAnalysis()` | POST the category/algorithm/param to your Python analysis microservice (NetworkX / PyTorch Geometric) instead of the local `connectedComponents()` stand-in |
| `src/App.jsx` → `handleToolbarAction()` | Wire `add` / `edit` / `delete` / `merge` / `exclude` to your graph-mutation endpoints (Neo4j Cypher writes) |
| `src/components/IntelligencePanel.jsx` | `hiddenLinksCount` / `anomaliesCount` props → live counts from your link-prediction / anomaly-detection service |

## Structure

```
src/
  App.jsx                  state + layout composition
  components/
    TabBar.jsx              Network / Analysis / Intelligence switcher
    GraphCanvas.jsx          cytoscape.js wrapper: zoom dock, coloring, n-hop dimming
    LayerPanel.jsx           left sidebar — node/edge type + label toggles
    DataPanel.jsx            right sidebar (Network tab) — load/save/export, stats
    Toolbar.jsx               middle rail — search + element actions
    AnalysisPanel.jsx        right sidebar (Analysis tab) — algorithm picker + results
    IntelligencePanel.jsx    Intelligence tab — sub-tabs, n-hop explorer, evidence trail
  data/mockNetwork.js       sample datasets + fetchNetwork()
  styles/App.css            design tokens + component styles
```

## Notes

- Node colors: teal = person, amber = location, purple = object,
  blue = event (edit the `TYPE_COLOR` map in `GraphCanvas.jsx`).
- Community Detection coloring reuses the same 6-color palette
  (`COMMUNITY_PALETTE`, also in `GraphCanvas.jsx`).
- The toolbar's destructive/CRUD actions (`edit`, `add`, `delete`, `merge`,
  `exclude`) currently just toast a placeholder — hook them to your API
  once the write endpoints exist.
