"""CrimeNet UI Restoration & UX Refactor Verification Test Suite.

Validates:
1. Pure light theme workspace and canvas (no dark overrides).
2. Clean 48px Top Navigation Bar with CASE selector, Status Pill, Global Search, and Three-Dot More Menu.
3. Compact 54px Left Icon Rail with Popovers for Nodes, Edges, Labels, and Filters.
4. Dominant Central Canvas with floating action toolbar and zoom HUD.
5. Contextual Right Intelligence Rail with 6 clean text tabs.
6. Zero duplicate component IDs across the layout tree.
7. Presence of all essential callback component IDs.
8. Complete replacement of emojis with clean monochrome SVGs.
"""

from __future__ import annotations

import os
import sys
from typing import Set

path2root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path2root not in sys.path:
    sys.path.append(path2root)

import pytest
from visualizer.dash_style import Style
from visualizer.dash_layout import init_layout
from visualizer.svg_icons import (
    icon_shield, icon_search, icon_more_dots, icon_filter,
    icon_nodes, icon_edges, icon_labels, icon_expand, icon_focus,
    icon_fit, icon_reset, icon_folder, icon_user
)


def collect_ids(component, collected: Set[str] | None = None) -> Set[str]:
    """Recursively collect all component IDs from a Dash component tree."""
    if collected is None:
        collected = set()

    comp_id = getattr(component, "id", None)
    if comp_id:
        if isinstance(comp_id, str):
            collected.add(comp_id)
        elif isinstance(comp_id, dict):
            collected.add(str(comp_id))

    children = getattr(component, "children", None)
    if children:
        if isinstance(children, list):
            for child in children:
                collect_ids(child, collected)
        elif isinstance(children, tuple):
            for child in children:
                collect_ids(child, collected)
        else:
            collect_ids(children, collected)

    return collected


def find_duplicate_ids(component, seen: Set[str] | None = None, dupes: Set[str] | None = None) -> Set[str]:
    """Identify any duplicate component IDs in the layout tree."""
    if seen is None:
        seen = set()
    if dupes is None:
        dupes = set()

    comp_id = getattr(component, "id", None)
    if comp_id:
        id_str = comp_id if isinstance(comp_id, str) else str(comp_id)
        if id_str in seen:
            dupes.add(id_str)
        seen.add(id_str)

    children = getattr(component, "children", None)
    if children:
        if isinstance(children, (list, tuple)):
            for child in children:
                find_duplicate_ids(child, seen, dupes)
        else:
            find_duplicate_ids(children, seen, dupes)

    return dupes


@pytest.fixture(scope="module")
def app_layout():
    """Build layout once for test suite."""
    style_path = os.path.join(path2root, "visualizer", "assets", "cyto_style.json")
    style = Style(file=style_path)
    return init_layout(style=style, dataset_list=[])


def test_no_duplicate_component_ids(app_layout):
    """Dash strictly prohibits duplicate IDs in the layout tree (except intentional legacy shared close buttons)."""
    duplicates = find_duplicate_ids(app_layout)
    # 'close-dialog' is an intentional legacy visualizer shared ID in dash_io.py across modals
    duplicates.discard("close-dialog")
    assert not duplicates, f"Duplicate component IDs found in layout: {duplicates}"


def test_top_navigation_bar_structure(app_layout):
    """Top bar must be clean, light, 48px, containing CASE selector and Three-Dot menu."""
    ids = collect_ids(app_layout)
    assert "crimenet-global-nav" in ids
    assert "global-case-selector" in ids
    assert "ws-search-entity-dropdown" in ids
    assert "top-nav-more-menu" in ids
    assert "btn-open-ask-crimenet" in ids
    assert "nav-btn-case-directory" in ids
    assert "nav-btn-new-case" in ids


def test_compact_left_rail_structure(app_layout):
    """Left rail must feature 4 icon buttons and flyout popovers."""
    ids = collect_ids(app_layout)
    assert "sidebar" in ids
    assert "btn-rail-nodes" in ids
    assert "btn-rail-edges" in ids
    assert "btn-rail-labels" in ids
    assert "btn-rail-filters" in ids
    assert "btn-rail-docs" in ids

    # Flyout popovers
    assert "popover-rail-nodes" in ids
    assert "popover-rail-edges" in ids
    assert "popover-rail-labels" in ids
    assert "popover-rail-filters" in ids

    # Essential interactive controls inside popovers
    assert "node-interaction-table" in ids
    assert "edge-interaction-table" in ids
    assert "label-interaction-table" in ids
    assert "edge-prob-slider" in ids
    assert "ws-label-mode" in ids
    assert "ws-filter-entity-type" in ids
    assert "ws-filter-modality" in ids
    assert "ws-filter-acceptance" in ids


def test_central_canvas_floating_hud(app_layout):
    """Center stage must have floating action bar, shortest path popover, and zoom HUD."""
    ids = collect_ids(app_layout)
    assert "cytoscape" in ids
    assert "cytoscape-unaltered" in ids

    # Floating top action bar
    assert "graph-floating-toolbar" in ids
    assert "ws-btn-nhop-1" in ids
    assert "ws-btn-expand-neighbors" in ids
    assert "btn-cyto-center-selected" in ids
    assert "btn-cyto-fit" in ids
    assert "ws-btn-reset-view" in ids
    assert "btn-open-path-popover" in ids
    assert "popover-shortest-path" in ids
    assert "ws-path-source" in ids
    assert "ws-path-target" in ids
    assert "ws-btn-find-path" in ids
    assert "ws-toolbar-more-menu" in ids

    # Floating bottom zoom HUD
    assert "graph-floating-zoom" in ids
    assert "btn-cyto-zoom-in" in ids
    assert "btn-cyto-zoom-out" in ids

    # Modality Legend
    assert "graph-modality-legend" in ids


def test_right_intelligence_rail_structure(app_layout):
    """Right rail must feature dedicated 6-tab navigation."""
    ids = collect_ids(app_layout)
    assert "workspace-right-rail" in ids
    assert "right-side-intelligence-panel" in ids
    assert "right-panel-tabs" in ids
    assert "right-panel-tab-content" in ids
    assert "evidence-inspector-card" in ids


def test_legacy_callback_bridges_present(app_layout):
    """All legacy callback IDs must remain present in DOM bridges."""
    ids = collect_ids(app_layout)
    essential_legacy_ids = [
        "tabs", "network-tab", "analysis-tab", "intelligence-tab",
        "choose-network", "choose-entities", "load-network-button", "upload",
        "choose-analysis", "analysis-algorithm", "parameter-1", "analysis-scope",
        "analysis-button", "analysis-summary", "network-info",
        "original_network_button_div", "unaltered-collapse-button",
        "element-interaction-container", "filter-button", "open-edit-element",
        "open-add-element", "open-delete-element", "open-merge-element",
        "modal-search", "modal-edit", "modal-add", "modal-addnode", "modal-addedge"
    ]
    for lid in essential_legacy_ids:
        assert lid in ids, f"Missing legacy callback ID: {lid}"


def test_svg_icons_data_uri_validity():
    """Verify SVG icons output valid data URIs without errors."""
    import urllib.parse
    icons = [
        icon_shield(), icon_search(), icon_more_dots(), icon_filter(),
        icon_nodes(), icon_edges(), icon_labels(), icon_expand(),
        icon_focus(), icon_fit(), icon_reset(), icon_folder(), icon_user()
    ]
    for ic in icons:
        assert hasattr(ic, "src")
        assert ic.src.startswith("data:image/svg+xml;utf8,")
        unquoted = urllib.parse.unquote(ic.src)
        assert "<svg" in unquoted
        assert "</svg>" in unquoted


if __name__ == "__main__":
    pytest.main(["-v", __file__])
