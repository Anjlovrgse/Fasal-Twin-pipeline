"""
Fasal Twin - Regional Network Graph Model
Constructs a directed graph using NetworkX representing the logistics network
(FPOs, Mandis, Storage facilities, Processors).
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import networkx as nx
import pandas as pd

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader


def load_network(district: Optional[str] = None, loader: Optional[DataLoader] = None) -> nx.DiGraph:
    """
    Constructs a directed graph from network_capacity.csv and network_edges.csv.
    Each node holds capacity_tonnes, current_occupancy (starts at 0.0), and spatial metadata.
    """
    if loader is None:
        loader = DataLoader()

    df_nodes = loader.load_network_capacity()
    df_edges = loader.load_network_edges()

    if district:
        # Filter nodes by district or connected nodes
        matching_node_ids = set(df_nodes[df_nodes["district"].str.lower() == district.lower()]["node_id"])
        # Include connected destination nodes if edge exists
        edge_dest_ids = set(df_edges[df_edges["from_node_id"].isin(matching_node_ids)]["to_node_id"])
        edge_src_ids = set(df_edges[df_edges["to_node_id"].isin(matching_node_ids)]["from_node_id"])
        allowed_node_ids = matching_node_ids | edge_dest_ids | edge_src_ids
        df_nodes = df_nodes[df_nodes["node_id"].isin(allowed_node_ids)]

    G = nx.DiGraph()

    for _, row in df_nodes.iterrows():
        G.add_node(
            str(row["node_id"]),
            node_name=str(row["node_name"]),
            node_type=str(row["node_type"]),
            district=str(row["district"]),
            capacity_tonnes=float(row["capacity_tonnes"]),
            current_occupancy=0.0,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
        )

    for _, row in df_edges.iterrows():
        u = str(row["from_node_id"])
        v = str(row["to_node_id"])
        if G.has_node(u) and G.has_node(v):
            G.add_edge(
                u,
                v,
                distance_km=float(row["distance_km"]),
                transit_hours=float(row["transit_hours"]),
                transport_cost_per_tonne=float(row["transport_cost_per_tonne"]),
            )

    return G


def reset_occupancy(graph: nx.DiGraph) -> None:
    """Resets current occupancy of all nodes to 0.0."""
    for n in graph.nodes:
        graph.nodes[n]["current_occupancy"] = 0.0


def update_occupancy(graph: nx.DiGraph, node_id: str, delta_tonnes: float) -> float:
    """
    Adds delta_tonnes to node's occupancy.
    Returns new occupancy.
    """
    if not graph.has_node(node_id):
        raise KeyError(f"Node '{node_id}' does not exist in network graph.")
    curr = graph.nodes[node_id]["current_occupancy"]
    new_occ = max(0.0, curr + delta_tonnes)
    graph.nodes[node_id]["current_occupancy"] = new_occ
    return new_occ


def node_utilization(graph: nx.DiGraph) -> Dict[str, Dict[str, Any]]:
    """
    Calculates utilization metrics for all nodes in the graph.
    Returns: {node_id: {node_name, node_type, district, capacity, occupancy, utilization_ratio, is_overshoot}}
    """
    utilization: Dict[str, Dict[str, Any]] = {}
    for node_id, data in graph.nodes(data=True):
        cap = data.get("capacity_tonnes", 1.0)
        occ = data.get("current_occupancy", 0.0)
        ratio = round(occ / cap, 4) if cap > 0 else 0.0
        utilization[node_id] = {
            "node_id": node_id,
            "node_name": data.get("node_name"),
            "node_type": data.get("node_type"),
            "district": data.get("district"),
            "capacity_tonnes": cap,
            "current_occupancy": occ,
            "utilization_ratio": ratio,
            "utilization_pct": round(ratio * 100.0, 2),
            "is_overshoot": occ > cap,
            "overshoot_tonnes": max(0.0, round(occ - cap, 2)),
        }
    return utilization


def get_nodes_by_type(graph: nx.DiGraph, node_type: str) -> List[str]:
    """Returns list of node_ids matching the given node_type (fpo, mandi, storage, processor)."""
    return [n for n, d in graph.nodes(data=True) if d.get("node_type") == node_type]


if __name__ == "__main__":
    g = load_network(district="Alappuzha")
    print(f"Network loaded: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    update_occupancy(g, "M1", 1350)
    utils = node_utilization(g)
    for nid, u in utils.items():
        if u["current_occupancy"] > 0:
            print(f"Node {nid} ({u['node_name']}): {u['current_occupancy']}/{u['capacity_tonnes']} tonnes ({u['utilization_pct']}%) - Overshoot: {u['is_overshoot']}")
