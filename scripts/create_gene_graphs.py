import sys
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import json
import numpy as np
from app.db.studies_db import StudiesDBClient

# if we do this, install, pip install networkx, matplotlib, pandas, scipy

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)


def convert_to_serializable(obj):
    if isinstance(obj, np.float32):
        return float(obj)
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


# Connect to database and load data
studies_db = StudiesDBClient()
studies = studies_db.get_all_colocs_to_dataframe()
# Print number of rows in studies
print(f"Number of rows in studies: {len(studies)}")
# Print first 5 rows of studies
print("\nFirst 5 rows of studies:")
print(studies.head())
# Print column names
print("\nColumn names in studies:")
print(studies.columns.tolist())

# Create graph
G = nx.Graph()

# Add edges between genes that share coloc_group_id
for coloc_group, group in studies.groupby("coloc_group_id"):
    genes = group["gene"].unique()
    genes = [gene for gene in genes if gene is not None]
    if len(genes) > 1:  # Only add edges if there are multiple genes in the group
        # Add all pairwise connections between genes in this coloc group
        for i in range(len(genes)):
            for j in range(i + 1, len(genes)):
                # Get the maximum posterior probability for this gene pair
                gene_pair_data = group[(group["gene"].isin([genes[i], genes[j]]))]
                max_prob = gene_pair_data["posterior_prob"].max()
                # Add edge with weight based on posterior probability
                G.add_edge(
                    genes[i],
                    genes[j],
                    coloc_group=coloc_group,
                    weight=max_prob,
                    snp=group["snp_id"].iloc[0],
                )  # Store the SNP ID for reference

# Now you can analyze the graph for your target gene
target_gene = "IKBKE"  # You can change this to any gene you're interested in
depth = 3  # Change this to control how many layers of neighbors to show (1 = immediate neighbors only, 2 = neighbors of neighbors, etc.)
neighbors = list(G.neighbors(target_gene))
print(f"\nNeighbors of {target_gene}: {neighbors}")

# Draw the subgraph around your target gene
subgraph = G.subgraph(list(nx.ego_graph(G, target_gene, radius=depth).nodes()))
pos = nx.spring_layout(subgraph)

# Create D3.js compatible JSON
d3_data = {"nodes": [], "links": []}

# Add nodes
for node in subgraph.nodes():
    d3_data["nodes"].append(
        {
            "id": node,
            "group": 1,  # You can modify this to group nodes differently
            "isTarget": node == target_gene,
        }
    )

# Add links
for source, target in subgraph.edges():
    d3_data["links"].append(
        {
            "source": source,
            "target": target,
            "value": G[source][target]["weight"],
            "coloc_group": G[source][target]["coloc_group"],
            "snp": G[source][target]["snp"],
        }
    )

# Save the D3.js data
output_file = f"gene_coloc_network_{target_gene}_d3.json"
with open(output_file, "w") as f:
    json.dump(convert_to_serializable(d3_data), f, indent=2)
print(f"\nD3.js data saved to {output_file}")

# Create a simple HTML template for D3.js visualization
html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Gene Co-localization Network - {target_gene}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .node {{
            stroke: #fff;
            stroke-width: 1.5px;
        }}
        .link {{
            stroke: #999;
            stroke-opacity: 0.6;
        }}
        .node text {{
            pointer-events: none;
            font: 10px sans-serif;
        }}
        .tooltip {{
            position: absolute;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            pointer-events: none;
        }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <script>
        // Load the graph data
        d3.json("{output_file}").then(function(graph) {{
            const width = 800;
            const height = 600;
            
            // Create SVG
            const svg = d3.select("#graph")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Create tooltip
            const tooltip = d3.select("body")
                .append("div")
                .attr("class", "tooltip")
                .style("opacity", 0);
            
            // Create force simulation
            const simulation = d3.forceSimulation(graph.nodes)
                .force("link", d3.forceLink(graph.links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            // Create links
            const link = svg.append("g")
                .selectAll("line")
                .data(graph.links)
                .enter().append("line")
                .attr("class", "link")
                .style("stroke-width", d => Math.sqrt(d.value) * 2);
            
            // Create nodes
            const node = svg.append("g")
                .selectAll("circle")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", d => d.isTarget ? 10 : 5)
                .style("fill", d => d.isTarget ? "#ff0000" : "#1f77b4")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // Add labels
            const label = svg.append("g")
                .selectAll("text")
                .data(graph.nodes)
                .enter().append("text")
                .text(d => d.id)
                .attr("x", 8)
                .attr("y", "0.31em");
            
            // Add tooltips
            node.on("mouseover", function(event, d) {{
                tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                tooltip.html(`Gene: ${{d.id}}<br/>Target: ${{d.isTarget ? 'Yes' : 'No'}}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function(d) {{
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            }});
            
            // Update positions on each tick
            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                label
                    .attr("x", d => d.x + 8)
                    .attr("y", d => d.y + 3);
            }});
            
            // Drag functions
            function dragstarted(event, d) {{
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }}
            
            function dragged(event, d) {{
                d.fx = event.x;
                d.fy = event.y;
            }}
            
            function dragended(event, d) {{
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }}
        }});
    </script>
</body>
</html>
"""

# Save the HTML template
html_file = f"gene_coloc_network_{target_gene}.html"
with open(html_file, "w") as f:
    f.write(html_template)
print(f"Interactive visualization saved to {html_file}")

exit()
# Create the static visualization (keeping the existing matplotlib code)
plt.figure(figsize=(15, 10))
# Draw nodes
nx.draw_networkx_nodes(subgraph, pos, node_size=1000, node_color="skyblue", alpha=0.7)

# Draw edges with varying thickness based on weight
edge_weights = [G[u][v]["weight"] * 2 for u, v in subgraph.edges()]
nx.draw_networkx_edges(subgraph, pos, width=edge_weights, alpha=0.5)

# Draw labels
nx.draw_networkx_labels(subgraph, pos, font_size=10, font_weight="bold")

# Add edge labels showing the coloc group ID
edge_labels = {(u, v): f"Group: {G[u][v]['coloc_group']}\nSNP: {G[u][v]['snp']}" for u, v in subgraph.edges()}
nx.draw_networkx_edge_labels(subgraph, pos, edge_labels=edge_labels, font_size=8)

plt.title(f"Gene Co-localization Network for {target_gene}\nEdge thickness represents posterior probability")
plt.axis("off")
plt.tight_layout()
plt.savefig(f"gene_coloc_network_{target_gene}.png", dpi=300, bbox_inches="tight")
plt.show()
