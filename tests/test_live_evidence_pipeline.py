"""Live Dash HTTP Integration Tests for the Case Evidence Pipeline.

Verifies via Flask test client on Dash server:
1. File selection banner update.
2. End-to-end evidence ingestion callback with a valid TXT file (Upload -> Validate -> Store -> Process -> Extract -> Analyze -> Link).
3. End-to-end evidence ingestion callback with a corrupted / empty file -> verifies error banner displays the REAL error without faking success.
4. End-to-end evidence ingestion callback with malformed JSON syntax -> verifies real JSON syntax error is displayed.
"""

import base64
import json
import os
import sys
import time

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.insert(0, path2root)

import visualizer.index as idx
from storage.case_data_service import CaseDataService


def test_live_evidence_pipeline():
    client = idx.app.visualizer_app.server.test_client()
    svc = CaseDataService()
    cases = svc.list_cases()
    test_case_id = cases[0]["id"]

    # 1. Test File Selection banner callback
    resp_banner = client.post('/_dash-update-component', json={
        'output': 'evidence-selected-file-banner.children',
        'outputs': {'id': 'evidence-selected-file-banner', 'property': 'children'},
        'inputs': [
            {'id': 'evidence-file-upload', 'property': 'filename', 'value': 'surveillance_log_march.txt'}
        ],
        'changedPropIds': ['evidence-file-upload.filename']
    })
    assert resp_banner.status_code == 200
    banner_res = resp_banner.json.get('response', {}).get('evidence-selected-file-banner', {}).get('children', {})
    assert 'SELECTED EXHIBIT' in str(banner_res)

    # 2. Find output spec for handle_evidence_ingestion_pipeline
    resp_deps = client.get('/_dash-dependencies')
    assert resp_deps.status_code == 200
    deps = resp_deps.json

    pipeline_output = None
    for d in deps:
        if 'evidence-pipeline-status-div.children' in d['output']:
            pipeline_output = d['output']
            break
    assert pipeline_output is not None, "handle_evidence_ingestion_pipeline callback must be registered in Dash dependencies"

    pipeline_outputs_spec = [
        {'id': 'evidence-pipeline-status-div', 'property': 'children'},
        {'id': 'dossier-evidence-registry-container', 'property': 'children'},
        {'id': 'case-refresh-trigger', 'property': 'data'},
        {'id': 'cytoscape', 'property': 'elements'},
        {'id': 'network-info', 'property': 'children'},
        {'id': 'node-interaction-table', 'property': 'children'},
        {'id': 'edge-interaction-table', 'property': 'children'},
        {'id': 'label-interaction-table', 'property': 'children'},
        {'id': 'evidence-file-upload', 'property': 'contents'},
    ]

    # Test Case A: Valid TXT Statement Ingestion
    txt_payload = (
        "During operation near Bhiwandi, informant confirmed Vikram Patel operating mobile 9820011223 "
        "drove vehicle MH04CD9999 to deliver contraband funds to Sunrise Traders."
    )
    b64_txt = "data:text/plain;base64," + base64.b64encode(txt_payload.encode('utf-8')).decode('utf-8')

    resp_valid = client.post('/_dash-update-component', json={
        'output': pipeline_output,
        'outputs': pipeline_outputs_spec,
        'inputs': [
            {'id': 'btn-process-evidence', 'property': 'n_clicks', 'value': 1}
        ],
        'state': [
            {'id': 'evidence-file-upload', 'property': 'contents', 'value': b64_txt},
            {'id': 'evidence-file-upload', 'property': 'filename', 'value': f'witness_memo_{int(time.time())}.txt'},
            {'id': 'evidence-type-select', 'property': 'value', 'value': 'TXT'},
            {'id': 'evidence-title-input', 'property': 'value', 'value': 'Witness Deposition Memo'},
            {'id': 'evidence-source-input', 'property': 'value', 'value': 'Bhiwandi Sub-Division'},
            {'id': 'evidence-desc-input', 'property': 'value', 'value': 'Recorded in presence of two panchas'},
            {'id': 'dossier-active-case-id-store', 'property': 'data', 'value': test_case_id},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 0}
        ],
        'changedPropIds': ['btn-process-evidence.n_clicks']
    })
    assert resp_valid.status_code == 200, f"Valid evidence ingestion failed with status {resp_valid.status_code}"
    res_data = resp_valid.json.get('response', {})
    status_div = res_data.get('evidence-pipeline-status-div', {}).get('children', {})
    assert "Evidence Successfully Processed" in str(status_div)
    assert "PROCESSED" in str(status_div)

    # Test Case B: Empty file validation error - verify real error displayed without faking success
    b64_empty = "data:text/plain;base64,"
    resp_empty = client.post('/_dash-update-component', json={
        'output': pipeline_output,
        'outputs': pipeline_outputs_spec,
        'inputs': [
            {'id': 'btn-process-evidence', 'property': 'n_clicks', 'value': 2}
        ],
        'state': [
            {'id': 'evidence-file-upload', 'property': 'contents', 'value': b64_empty},
            {'id': 'evidence-file-upload', 'property': 'filename', 'value': 'zero_byte_evidence.txt'},
            {'id': 'evidence-type-select', 'property': 'value', 'value': 'TXT'},
            {'id': 'evidence-title-input', 'property': 'value', 'value': 'Empty Exhibit'},
            {'id': 'evidence-source-input', 'property': 'value', 'value': 'Unknown'},
            {'id': 'evidence-desc-input', 'property': 'value', 'value': 'Testing empty file'},
            {'id': 'dossier-active-case-id-store', 'property': 'data', 'value': test_case_id},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 1}
        ],
        'changedPropIds': ['btn-process-evidence.n_clicks']
    })
    assert resp_empty.status_code == 200
    res_empty = resp_empty.json.get('response', {})
    status_empty = res_empty.get('evidence-pipeline-status-div', {}).get('children', {})
    assert "Evidence Processing Failed" in str(status_empty)
    assert "0 bytes" in str(status_empty)

    # Test Case C: Malformed JSON syntax error - verify real syntax error displayed
    bad_json = "{\n  \"case\": \"FIR-999\",\n  \"unclosed\": \n"
    b64_bad_json = "data:application/json;base64," + base64.b64encode(bad_json.encode('utf-8')).decode('utf-8')

    resp_bad = client.post('/_dash-update-component', json={
        'output': pipeline_output,
        'outputs': pipeline_outputs_spec,
        'inputs': [
            {'id': 'btn-process-evidence', 'property': 'n_clicks', 'value': 3}
        ],
        'state': [
            {'id': 'evidence-file-upload', 'property': 'contents', 'value': b64_bad_json},
            {'id': 'evidence-file-upload', 'property': 'filename', 'value': 'corrupt_report.json'},
            {'id': 'evidence-type-select', 'property': 'value', 'value': 'JSON'},
            {'id': 'evidence-title-input', 'property': 'value', 'value': 'Corrupted Intel'},
            {'id': 'evidence-source-input', 'property': 'value', 'value': 'Cyber Infiltration'},
            {'id': 'evidence-desc-input', 'property': 'value', 'value': 'Testing corrupt JSON'},
            {'id': 'dossier-active-case-id-store', 'property': 'data', 'value': test_case_id},
            {'id': 'case-refresh-trigger', 'property': 'data', 'value': 2}
        ],
        'changedPropIds': ['btn-process-evidence.n_clicks']
    })
    assert resp_bad.status_code == 200
    res_bad = resp_bad.json.get('response', {})
    status_bad = res_bad.get('evidence-pipeline-status-div', {}).get('children', {})
    assert "Evidence Processing Failed" in str(status_bad)
    assert "Invalid JSON syntax" in str(status_bad)

    print("ALL LIVE EVIDENCE PIPELINE INTEGRATION TESTS (VALID, EMPTY, CORRUPT) PASSED CLEANLY!")


if __name__ == '__main__':
    test_live_evidence_pipeline()
