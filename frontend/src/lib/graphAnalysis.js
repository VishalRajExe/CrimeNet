/**
 * graphAnalysis.js — Network analysis algorithms for NetIntel.
 * Implements: Degree Centrality, PageRank, Betweenness Centrality, Closeness Centrality,
 * Community Detection (Label Propagation, Louvain, Modularity),
 * Link Prediction (Jaccard, Resource Allocation, Adamic Adar),
 * Shortest Path (BFS), Anomaly Detection,
 * Spring Layout (Fruchterman-Reingold with Collision Repulsion).
 */

export function buildAdj(nodes, edges) {
  const adj = {};
  nodes.forEach((n) => (adj[n.id] = []));
  edges.forEach((e) => {
    adj[e.source]?.push(e.target);
    adj[e.target]?.push(e.source);
  });
  return adj;
}

export function degreeMap(nodes, edges) {
  const m = {};
  nodes.forEach((n) => (m[n.id] = 0));
  edges.forEach((e) => {
    m[e.source] = (m[e.source] || 0) + 1;
    m[e.target] = (m[e.target] || 0) + 1;
  });
  return m;
}

export function degreeCentrality(nodes, edges) {
  const adj = buildAdj(nodes, edges);
  const n = nodes.length;
  const scores = {};
  if (n <= 1) {
    nodes.forEach((nd) => (scores[nd.id] = 0));
    return scores;
  }
  nodes.forEach((nd) => {
    scores[nd.id] = +((adj[nd.id]?.length || 0) / (n - 1)).toFixed(3);
  });
  return scores;
}

export function pageRank(nodes, edges, { damping = 0.85, maxIter = 40, tol = 1e-4 } = {}) {
  const n = nodes.length;
  if (!n) return {};
  const adj = buildAdj(nodes, edges);
  const deg = {};
  nodes.forEach((nd) => (deg[nd.id] = adj[nd.id]?.length || 0));

  let rank = {};
  nodes.forEach((nd) => (rank[nd.id] = 1 / n));

  for (let iter = 0; iter < maxIter; iter++) {
    const next = {};
    let diff = 0;

    nodes.forEach((u) => {
      let sum = 0;
      (adj[u.id] || []).forEach((v) => {
        if (deg[v] > 0) sum += rank[v] / deg[v];
      });
      next[u.id] = (1 - damping) / n + damping * sum;
      diff += Math.abs(next[u.id] - rank[u.id]);
    });

    rank = next;
    if (diff < tol) break;
  }

  const max = Math.max(...Object.values(rank)) || 1;
  const out = {};
  nodes.forEach((nd) => (out[nd.id] = +(rank[nd.id] / max).toFixed(3)));
  return out;
}

export function betweennessCentrality(nodes, edges) {
  const n = nodes.length;
  const cb = {};
  nodes.forEach((nd) => (cb[nd.id] = 0));
  if (n <= 2) return cb;

  const adj = buildAdj(nodes, edges);

  nodes.forEach((s) => {
    const S = [];
    const P = {};
    const sigma = {};
    const d = {};
    nodes.forEach((w) => {
      P[w.id] = [];
      sigma[w.id] = 0;
      d[w.id] = -1;
    });

    sigma[s.id] = 1;
    d[s.id] = 0;
    const Q = [s.id];

    while (Q.length) {
      const v = Q.shift();
      S.push(v);
      (adj[v] || []).forEach((w) => {
        if (d[w] < 0) {
          Q.push(w);
          d[w] = d[v] + 1;
        }
        if (d[w] === d[v] + 1) {
          sigma[w] += sigma[v];
          P[w].push(v);
        }
      });
    }

    const delta = {};
    nodes.forEach((w) => (delta[w.id] = 0));
    while (S.length) {
      const w = S.pop();
      P[w].forEach((v) => {
        delta[v] += (sigma[v] / (sigma[w] || 1)) * (1 + delta[w]);
      });
      if (w !== s.id) cb[w] += delta[w];
    }
  });

  const factor = 2 / ((n - 1) * (n - 2));
  const max = Math.max(...Object.values(cb).map((v) => v * factor)) || 1;
  const out = {};
  nodes.forEach((nd) => (out[nd.id] = +((cb[nd.id] * factor) / max).toFixed(3)));
  return out;
}

export function closenessCentrality(nodes, edges) {
  const adj = buildAdj(nodes, edges);
  const n = nodes.length;
  const scores = {};

  nodes.forEach((s) => {
    const queue = [s.id];
    const dist = { [s.id]: 0 };

    while (queue.length) {
      const u = queue.shift();
      (adj[u] || []).forEach((v) => {
        if (dist[v] === undefined) {
          dist[v] = dist[u] + 1;
          queue.push(v);
        }
      });
    }

    const reachable = Object.keys(dist).length - 1;
    if (reachable <= 0) {
      scores[s.id] = 0;
      return;
    }

    const sumDist = Object.values(dist).reduce((a, b) => a + b, 0);
    scores[s.id] = +((reachable / (n - 1)) * (reachable / sumDist)).toFixed(3);
  });

  return scores;
}

export function communityDetection(nodes, edges, maxIter = 25) {
  const adj = buildAdj(nodes, edges);
  const labels = {};
  nodes.forEach((n, i) => (labels[n.id] = i));

  for (let iter = 0; iter < maxIter; iter++) {
    let changed = false;
    const shuffled = [...nodes].sort(() => Math.random() - 0.5);

    shuffled.forEach((node) => {
      const neighbors = adj[node.id] || [];
      if (!neighbors.length) return;

      const counts = {};
      neighbors.forEach((nb) => {
        const l = labels[nb];
        counts[l] = (counts[l] || 0) + 1;
      });

      let best = labels[node.id];
      let bestCount = 0;
      Object.entries(counts).forEach(([l, c]) => {
        if (c > bestCount) {
          best = Number(l);
          bestCount = c;
        }
      });
      if (best !== labels[node.id]) {
        labels[node.id] = best;
        changed = true;
      }
    });

    if (!changed) break;
  }

  const idMap = {};
  let nextId = 0;
  const communityOf = {};
  nodes.forEach((n) => {
    const l = labels[n.id];
    if (!(l in idMap)) idMap[l] = nextId++;
    communityOf[n.id] = idMap[l];
  });

  return { communityOf, groups: nextId };
}

// ─── Link Prediction (Jaccard, Resource Allocation, Adamic-Adar) ──────────────

export function linkPrediction(nodes, edges, method = "jaccard") {
  const adj = buildAdj(nodes, edges);
  const connectedPairs = new Set();
  edges.forEach((e) => {
    connectedPairs.add(e.source + '__' + e.target);
    connectedPairs.add(e.target + '__' + e.source);
  });

  const deg = {};
  nodes.forEach((n) => (deg[n.id] = (adj[n.id] || []).length));

  const results = [];

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const u = nodes[i];
      const v = nodes[j];
      if (connectedPairs.has(u.id + '__' + v.id)) continue;

      const uNeighbors = new Set(adj[u.id] || []);
      const vNeighbors = adj[v.id] || [];
      const common = vNeighbors.filter((w) => uNeighbors.has(w));

      if (!common.length) continue;

      let score = 0;
      if (method === "jaccard") {
        const unionSize = new Set([...adj[u.id], ...adj[v.id]]).size;
        score = unionSize > 0 ? common.length / unionSize : 0;
      } else if (method === "resource_allocation") {
        score = common.reduce((acc, w) => acc + (deg[w] > 0 ? 1 / deg[w] : 0), 0);
      } else if (method === "adamic_adar") {
        score = common.reduce((acc, w) => acc + (deg[w] > 1 ? 1 / Math.log(deg[w]) : 0), 0);
      }

      if (score > 0) {
        results.push({
          source: u.id,
          sourceLabel: u.label,
          target: v.id,
          targetLabel: v.label,
          commonCount: common.length,
          score: +score.toFixed(3),
        });
      }
    }
  }

  return results.sort((a, b) => b.score - a.score).slice(0, 15);
}

export function shortestPath(nodes, edges, sourceId, targetId) {
  if (sourceId === targetId) return [sourceId];
  const adj = buildAdj(nodes, edges);
  const parent = { [sourceId]: null };
  const queue = [sourceId];

  outer: while (queue.length) {
    const v = queue.shift();
    for (const w of adj[v] || []) {
      if (!(w in parent)) {
        parent[w] = v;
        if (w === targetId) break outer;
        queue.push(w);
      }
    }
  }

  if (!(targetId in parent)) return null;
  const path = [];
  let cur = targetId;
  while (cur !== null) {
    path.unshift(cur);
    cur = parent[cur];
  }
  return path;
}

export function anomalyDetection(nodes, edges, threshold = 1.8) {
  const adj = buildAdj(nodes, edges);
  const degrees = nodes.map((n) => (adj[n.id] || []).length);
  const mean = degrees.reduce((a, b) => a + b, 0) / (degrees.length || 1);
  const std = Math.sqrt(
    degrees.reduce((a, d) => a + (d - mean) ** 2, 0) / (degrees.length || 1)
  );

  return nodes
    .map((n, i) => {
      const z = std > 0 ? Math.abs(degrees[i] - mean) / std : 0;
      return { id: n.id, label: n.label, type: n.type, degree: degrees[i], zScore: +z.toFixed(2) };
    })
    .filter((r) => r.zScore >= threshold)
    .sort((a, b) => b.zScore - a.zScore);
}

import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCollide,
  forceCenter,
  forceX,
  forceY,
} from 'd3-force';

export function springLayout(
  nodes,
  edges,
  { width = 1100, height = 750, iterations = 300 } = {}
) {
  if (!nodes.length) return {};
  if (nodes.length === 1) return { [nodes[0].id]: { x: width / 2, y: height / 2 } };

  const nodeMap = new Map(
    nodes.map((n) => [
      n.id,
      {
        id: n.id,
        x: width / 2 + (Math.random() - 0.5) * 200,
        y: height / 2 + (Math.random() - 0.5) * 200,
      },
    ])
  );

  const linkList = [];
  const edgeSet = new Set();
  edges.forEach((e) => {
    const key = [e.source, e.target].sort().join('__');
    if (!edgeSet.has(key) && nodeMap.has(e.source) && nodeMap.has(e.target)) {
      edgeSet.add(key);
      linkList.push({ source: e.source, target: e.target });
    }
  });

  const simNodes = Array.from(nodeMap.values());
  const sim = forceSimulation(simNodes)
    .force(
      'link',
      forceLink(linkList)
        .id((d) => d.id)
        .distance(75)
        .strength(0.7)
    )
    .force('charge', forceManyBody().strength(-350).distanceMax(600))
    .force('collide', forceCollide().radius(38).iterations(4))
    .force('center', forceCenter(width / 2, height / 2))
    .force('x', forceX(width / 2).strength(0.05))
    .force('y', forceY(height / 2).strength(0.06))
    .stop();

  const iters = nodes.length > 250 ? 120 : iterations;
  sim.tick(iters);

  const pos = {};
  simNodes.forEach((n) => {
    pos[n.id] = { x: n.x, y: n.y };
  });
  return pos;
}

export function topN(scoreMap, nodes, n = 10) {
  return nodes
    .map((node) => ({ id: node.id, label: node.label, type: node.type, score: scoreMap[node.id] ?? 0 }))
    .sort((a, b) => b.score - a.score)
    .slice(0, n);
}

export function directionalLayout(
  nodes,
  edges,
  direction = 'LR',
  { width = 1100, height = 750, iterations = 300 } = {}
) {
  if (!nodes.length) return {};
  if (nodes.length === 1) return { [nodes[0].id]: { x: width / 2, y: height / 2 } };

  // 1. Compute topological / BFS ranks
  const adj = {};
  const inDeg = {};
  nodes.forEach((n) => {
    adj[n.id] = [];
    inDeg[n.id] = 0;
  });
  edges.forEach((e) => {
    adj[e.source]?.push(e.target);
    inDeg[e.target] = (inDeg[e.target] || 0) + 1;
  });

  const rank = {};
  const visited = new Set();
  const sorted = [...nodes].sort((a, b) => (inDeg[a.id] || 0) - (inDeg[b.id] || 0));
  let queue = sorted.slice(0, Math.max(3, Math.ceil(nodes.length * 0.15))).map((n) => n.id);
  queue.forEach((id) => {
    rank[id] = 0;
    visited.add(id);
  });

  let curRank = 0;
  while (queue.length < nodes.length) {
    const nextQueue = [];
    queue.forEach((u) => {
      (adj[u] || []).forEach((v) => {
        if (!visited.has(v)) {
          visited.add(v);
          rank[v] = (rank[u] || 0) + 1;
          nextQueue.push(v);
        }
      });
    });
    if (nextQueue.length === 0) {
      const unvisited = nodes.find((n) => !visited.has(n.id));
      if (!unvisited) break;
      visited.add(unvisited.id);
      rank[unvisited.id] = curRank + 1;
      nextQueue.push(unvisited.id);
    }
    queue = nextQueue;
    curRank++;
  }

  const maxR = Math.max(1, ...Object.values(rank));
  const norm = {};
  nodes.forEach((n) => (norm[n.id] = (rank[n.id] || 0) / maxR));

  const nodeMap = new Map(
    nodes.map((n) => [
      n.id,
      {
        id: n.id,
        x: direction === 'LR' ? 80 + norm[n.id] * (width - 160) : width / 2,
        y: direction === 'TB' ? 80 + norm[n.id] * (height - 160) : height / 2,
      },
    ])
  );

  const linkList = [];
  const edgeSet = new Set();
  edges.forEach((e) => {
    const key = [e.source, e.target].sort().join('__');
    if (!edgeSet.has(key) && nodeMap.has(e.source) && nodeMap.has(e.target)) {
      edgeSet.add(key);
      linkList.push({ source: e.source, target: e.target });
    }
  });

  const simNodes = Array.from(nodeMap.values());
  const sim = forceSimulation(simNodes)
    .force(
      'link',
      forceLink(linkList)
        .id((d) => d.id)
        .distance(65)
        .strength(0.6)
    )
    .force('charge', forceManyBody().strength(-280).distanceMax(500))
    .force('collide', forceCollide().radius(38).iterations(4))
    .force(
      'x',
      direction === 'LR'
        ? forceX((d) => 80 + norm[d.id] * (width - 160)).strength(0.4)
        : forceX(width / 2).strength(0.06)
    )
    .force(
      'y',
      direction === 'TB'
        ? forceY((d) => 80 + norm[d.id] * (height - 160)).strength(0.4)
        : forceY(height / 2).strength(0.06)
    )
    .stop();

  const iters = nodes.length > 250 ? 120 : iterations;
  sim.tick(iters);

  const pos = {};
  simNodes.forEach((n) => {
    pos[n.id] = { x: n.x, y: n.y };
  });
  return pos;
}
