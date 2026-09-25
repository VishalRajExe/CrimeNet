import json
import os
import sys
import time

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.insert(0, path2root)

import visualizer.index as idx

def test_live_dash_endpoints():
    client = idx.app.visualizer_app.server.test_client()

    # 1. Verify GET /
    resp = client.get('/')
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"

    # 2. Verify GET /_dash-dependencies
    resp_deps = client.get('/_dash-dependencies')
    assert resp_deps.status_code == 200
    deps = resp_deps.json
    assert len(deps) >= 7, f"Expected at least 7 callbacks, found {len(deps)}"

    # 3. Test Filter Cases callback via POST /_dash-update-component
    resp_filter = client.post('/_dash-update-component', json={
        'output': 'dashboard-cases-grid.children',
        'outputs': {'id': 'dashboard-cases-grid', 'property': 'children'},
        'inputs': [
            {'id': 'dashboard-search-input', 'property': 'value', 'value': 'Blackhawk'},
            {'id': 'dashboard-priority-filter', 'property': 'value', 'value': 'CRITICAL'},
            {'id': 'dashboard-status-filter', 'property': 'value', 'value': 'ALL'},
            {'id': 'btn-refresh-dashboard', 'property': 'n_clicks', 'value': 0},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 0}
        ],
        'changedPropIds': ['dashboard-search-input.value']
    })
    assert resp_filter.status_code == 200, f"Filter callback failed with status {resp_filter.status_code}"
    filter_data = resp_filter.json
    cards = filter_data.get('response', {}).get('dashboard-cases-grid', {}).get('children', [])
    assert len(cards) == 1, f"Expected 1 matching card for Blackhawk, got {len(cards)}"

    # 4. Test Filter with non-matching search
    resp_empty = client.post('/_dash-update-component', json={
        'output': 'dashboard-cases-grid.children',
        'outputs': {'id': 'dashboard-cases-grid', 'property': 'children'},
        'inputs': [
            {'id': 'dashboard-search-input', 'property': 'value', 'value': 'NonExistentCaseXYZ'},
            {'id': 'dashboard-priority-filter', 'property': 'value', 'value': 'ALL'},
            {'id': 'dashboard-status-filter', 'property': 'value', 'value': 'ALL'},
            {'id': 'btn-refresh-dashboard', 'property': 'n_clicks', 'value': 0},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 0}
        ],
        'changedPropIds': ['dashboard-search-input.value']
    })
    assert resp_empty.status_code == 200
    empty_children = resp_empty.json.get('response', {}).get('dashboard-cases-grid', {}).get('children', [])
    assert len(empty_children) == 1

    # 5. Test Case Creation callback via POST /_dash-update-component
    create_output = '..modal-create-case.is_open...create-case-alert-div.children...case-refresh-trigger.data..'
    resp_create = client.post('/_dash-update-component', json={
        'output': create_output,
        'outputs': [
            {'id': 'modal-create-case', 'property': 'is_open'},
            {'id': 'create-case-alert-div', 'property': 'children'},
            {'id': 'case-refresh-trigger', 'property': 'data'}
        ],
        'inputs': [
            {'id': 'btn-open-create-case-modal', 'property': 'n_clicks', 'value': 0},
            {'id': 'nav-btn-new-case', 'property': 'n_clicks', 'value': 0},
            {'id': 'btn-cancel-create-case', 'property': 'n_clicks', 'value': 0},
            {'id': 'btn-submit-create-case', 'property': 'n_clicks', 'value': 1}
        ],
        'state': [
            {'id': 'new-case-title', 'property': 'value', 'value': 'Integration Test: Project Sentinel'},
            {'id': 'new-case-number', 'property': 'value', 'value': f'FIR-TEST-{int(time.time()*1000)}'},
            {'id': 'new-case-crime-type', 'property': 'value', 'value': 'NARCOTICS'},
            {'id': 'new-case-priority', 'property': 'value', 'value': 'HIGH'},
            {'id': 'new-case-status', 'property': 'value', 'value': 'ACTIVE'},
            {'id': 'new-case-location', 'property': 'value', 'value': 'Goa Maritime Coast'},
            {'id': 'new-case-officer', 'property': 'value', 'value': 'Inspector Desai'},
            {'id': 'new-case-description', 'property': 'value', 'value': 'Contraband landing intercepted at Betul port.'},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 0}
        ],
        'changedPropIds': ['btn-submit-create-case.n_clicks']
    })
    assert resp_create.status_code == 200, f"Create callback failed with status {resp_create.status_code}"
    create_res = resp_create.json.get('response', {})
    assert create_res.get('modal-create-case', {}).get('is_open') is False
    assert create_res.get('case-refresh-trigger', {}).get('data') == 1

    # 6. Test Case Dossier Modal callback via POST /_dash-update-component
    dossier_output = '..modal-case-dossier.is_open...modal-dossier-header.children...modal-dossier-body.children...dossier-active-case-id-store.data..'
    resp_dossier = client.post('/_dash-update-component', json={
        'output': dossier_output,
        'outputs': [
            {'id': 'modal-case-dossier', 'property': 'is_open'},
            {'id': 'modal-dossier-header', 'property': 'children'},
            {'id': 'modal-dossier-body', 'property': 'children'},
            {'id': 'dossier-active-case-id-store', 'property': 'data'}
        ],
        'inputs': [
            {'id': '{"index":"case-sih-001","type":"btn-dossier-case"}', 'property': 'n_clicks', 'value': 1},
            {'id': 'btn-close-dossier', 'property': 'n_clicks', 'value': 0},
            {'id': 'btn-dossier-launch-workspace', 'property': 'n_clicks', 'value': 0}
        ],
        'changedPropIds': ['{"index":"case-sih-001","type":"btn-dossier-case"}.n_clicks']
    })
    assert resp_dossier.status_code == 200, f"Dossier callback failed with status {resp_dossier.status_code}"
    dossier_res = resp_dossier.json.get('response', {})
    assert dossier_res.get('modal-case-dossier', {}).get('is_open') is True
    assert dossier_res.get('dossier-active-case-id-store', {}).get('data') == 'case-sih-001'

    # 7. Test Entering Workspace for Case callback
    for d in deps:
        if 'case-dashboard-view.style' in d['output']:
            workspace_output = d['output']
            break

    ws_outputs_spec = [
        {'id': 'case-dashboard-view', 'property': 'style'},
        {'id': 'workspace-view', 'property': 'style'},
        {'id': 'active-case-store', 'property': 'data'},
        {'id': 'active-case-header-display', 'property': 'children'},
        {'id': 'cytoscape', 'property': 'elements'},
        {'id': 'network-info', 'property': 'children'},
        {'id': 'node-interaction-table', 'property': 'children'},
        {'id': 'edge-interaction-table', 'property': 'children'},
        {'id': 'label-interaction-table', 'property': 'children'},
        {'id': 'nav-btn-dashboard', 'property': 'style'},
        {'id': 'nav-btn-workspace', 'property': 'style'},
    ]

    resp_ws = client.post('/_dash-update-component', json={
        'output': workspace_output,
        'outputs': ws_outputs_spec,
        'inputs': [
            {'id': '{"index":"case-sih-001","type":"btn-open-case"}', 'property': 'n_clicks', 'value': 1},
            {'id': 'btn-dossier-launch-workspace', 'property': 'n_clicks', 'value': 0},
            {'id': 'nav-btn-dashboard', 'property': 'n_clicks', 'value': 0},
            {'id': 'nav-btn-workspace', 'property': 'n_clicks', 'value': 0},
            {'id': 'btn-switch-to-workspace-direct', 'property': 'n_clicks', 'value': 0}
        ],
        'state': [
            {'id': 'dossier-active-case-id-store', 'property': 'data', 'value': 'case-sih-001'},
            {'id': 'active-case-store', 'property': 'data', 'value': None}
        ],
        'changedPropIds': ['{"index":"case-sih-001","type":"btn-open-case"}.n_clicks']
    })
    assert resp_ws.status_code == 200, f"Workspace launch callback failed with status {resp_ws.status_code}"
    ws_res = resp_ws.json.get('response', {})
    assert ws_res.get('case-dashboard-view', {}).get('style', {}).get('display') == 'none'
    assert ws_res.get('workspace-view', {}).get('style', {}).get('display') == 'block'
    assert len(ws_res.get('cytoscape', {}).get('elements', [])) >= 35, "Expected at least 35 elements loaded into Cytoscape for case-sih-001"

    print("ALL LIVE DASH HTTP INTEGRATION TESTS (FILTER, CREATE, DOSSIER, WORKSPACE LAUNCH) PASSED CLEANLY!")

if __name__ == '__main__':
    test_live_dash_endpoints()
