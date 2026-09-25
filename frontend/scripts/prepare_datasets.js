import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const datasetsMeta = [
  { id: 'unbound_case_2026', name: 'UNBOUND — Indian Criminal Network 2026', file: 'unbound_case_2026.json', description: 'Synthetic syndicate case with phones, persons, organizations, locations, and bank accounts' },
  { id: '911_hijackers', name: '911 Hijackers', file: '911_hijackers.json', description: 'Covert terrorist network responsible for 9/11 attacks' },
  { id: 'montreal_gangs', name: 'Montreal Street Gangs', file: 'montreal_gangs.json', description: 'Street gangs in Montreal with co-offending ties' },
  { id: 'madoff', name: 'Madoff Frauds', file: 'madoff.json', description: 'Bernard Madoff Ponzi scheme financial and familial network' },
  { id: 'rhodes_bombing', name: 'Rhodes Bombing', file: 'rhodes_bombing.json', description: 'Rhodes bombing covert network' },
  { id: 'moreno_crime', name: 'Moreno Crime Network', file: 'moreno_crime.json', description: 'Co-offending network of criminal actors and associates' },
  { id: 'noordintop', name: 'Noordin Top Network', file: 'noordintop.json', description: 'Noordin Top terrorist network with organizational and familial ties' },
  { id: 'bbc_islam_groups', name: 'BBC Islam Groups', file: 'bbc_islam_groups.json', description: 'Religious and political covert network' },
  { id: 'israel_lea_case1', name: 'Israel LEA Case 1', file: 'israel_lea_case1_speakers.json', description: 'Law enforcement intercepted communication case 1' },
  { id: 'israel_lea_case2', name: 'Israel LEA Case 2', file: 'israel_lea_case2_speakers.json', description: 'Law enforcement intercepted communication case 2' },
  { id: 'csi_s01e07', name: 'CSI (s01e07)', file: 'csi_indiap_s01e07.json', description: 'CSI investigation episode 7 forensic evidence network' },
  { id: 'csi_s01e08', name: 'CSI (s01e08)', file: 'csi_indiap_s01e08.json', description: 'CSI investigation episode 8 forensic evidence network' },
  { id: 'baseball_steroid_use', name: 'Baseball Steroid Use', file: 'baseball_steroid_use.json', description: 'Mitchell Report performance enhancing substance distribution network' },
  { id: 'nist_c1', name: 'NIST C1', file: 'nist_c1.json', description: 'NIST benchmark intelligence case 1' },
  { id: 'nist_c2', name: 'NIST C2', file: 'nist_c2.json', description: 'NIST benchmark intelligence case 2' }
];

const srcDir = path.join(rootDir, 'CrimeNet', 'datasets', 'preprocessed');
const destDir = path.join(rootDir, 'src', 'data', 'datasets');

if (!fs.existsSync(destDir)) {
  fs.mkdirSync(destDir, { recursive: true });
}

function parseDatasetFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split(/\r?\n/);
  const nodes = [];
  const edges = [];
  const nodeSet = new Set();

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    try {
      const obj = JSON.parse(trimmed);
      if (obj.type === 'node' && obj.id) {
        const id = String(obj.id);
        if (!nodeSet.has(id)) {
          nodeSet.add(id);
          const props = obj.properties || {};
          const label = props.name || props.label || props.number || props.title || id;
          const nodeType = (props.type || 'person').toLowerCase();
          nodes.push({
            id,
            label: String(label),
            type: nodeType,
            properties: props
          });
        }
      } else if (obj.type === 'edge' && obj.source && obj.target) {
        const src = String(obj.source);
        const tgt = String(obj.target);
        const props = obj.properties || {};
        const edgeType = props.type || 'connected_to';
        const weight = Number(props.weight != null ? props.weight : 1);
        edges.push({
          id: `e_${src}_${tgt}_${edges.length}`,
          source: src,
          target: tgt,
          label: props.type || 'connected_to',
          type: edgeType,
          weight: isNaN(weight) ? 1 : weight,
          properties: props
        });
      }
    } catch (e) {
      // skip invalid lines
    }
  }

  // Ensure any edge sources/targets not explicitly listed as nodes are added
  for (const edge of edges) {
    if (!nodeSet.has(edge.source)) {
      nodeSet.add(edge.source);
      nodes.push({
        id: edge.source,
        label: edge.source,
        type: 'entity',
        properties: { name: edge.source, type: 'entity' }
      });
    }
    if (!nodeSet.has(edge.target)) {
      nodeSet.add(edge.target);
      nodes.push({
        id: edge.target,
        label: edge.target,
        type: 'entity',
        properties: { name: edge.target, type: 'entity' }
      });
    }
  }

  return { nodes, edges };
}

const summary = [];

for (const ds of datasetsMeta) {
  const srcPath = path.join(srcDir, ds.file);
  if (fs.existsSync(srcPath)) {
    const { nodes, edges } = parseDatasetFile(srcPath);
    const parsedData = {
      id: ds.id,
      name: ds.name,
      description: ds.description,
      numNodes: nodes.length,
      numEdges: edges.length,
      nodes,
      edges
    };
    const destPath = path.join(destDir, `${ds.id}.json`);
    fs.writeFileSync(destPath, JSON.stringify(parsedData, null, 2), 'utf-8');
    summary.push({ id: ds.id, name: ds.name, nodes: nodes.length, edges: edges.length });
    console.log(`Processed ${ds.id}: ${nodes.length} nodes, ${edges.length} edges`);
  } else {
    console.warn(`File not found: ${srcPath}`);
  }
}

// Generate src/data/crimeNetDatasets.js
const indexContent = `// CrimeNet benchmark datasets catalog and loaders
${datasetsMeta.map(d => `import ${d.id.replace(/-/g, '_')} from './datasets/${d.id}.json';`).join('\n')}

export const DATASETS_CATALOG = [
${datasetsMeta.map(d => `  {
    id: '${d.id}',
    name: '${d.name.replace(/'/g, "\\'")}',
    description: '${d.description.replace(/'/g, "\\'")}',
    data: ${d.id.replace(/-/g, '_')}
  },`).join('\n')}
];

export function getDatasetById(id) {
  const found = DATASETS_CATALOG.find(d => d.id === id);
  return found ? found.data : DATASETS_CATALOG[0].data;
}

export default DATASETS_CATALOG;
`;

fs.writeFileSync(path.join(rootDir, 'src', 'data', 'crimeNetDatasets.js'), indexContent, 'utf-8');
console.log(`Successfully generated crimeNetDatasets.js with ${summary.length} datasets!`);
