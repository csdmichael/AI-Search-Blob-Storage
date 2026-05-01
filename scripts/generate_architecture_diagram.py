"""
Generate an architecture diagram for the AI Search + Blob Storage + Foundry Agent solution.

Uses matplotlib to create a professional diagram with Azure-styled components.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DOCS_DIR = config.DOCS_DIR
_res = config.azure_resources()
_doc_cfg = config.document_config()
_diagram_cfg = _doc_cfg["architecture_diagram"]

DIAGRAM_FILENAME = _diagram_cfg["output_filename"]
DIAGRAM_DPI = _diagram_cfg["dpi"]


def draw_azure_icon_box(ax, x, y, width, height, label, sublabel, color, icon_text):
    """Draw an Azure-style resource box with icon."""
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor="#333333",
        linewidth=1.5, alpha=0.9,
    )
    ax.add_patch(box)

    # Icon circle
    icon_circle = plt.Circle(
        (x + 0.3, y + height - 0.25), 0.18,
        facecolor="white", edgecolor="#333333", linewidth=1, alpha=0.9,
    )
    ax.add_patch(icon_circle)
    ax.text(x + 0.3, y + height - 0.25, icon_text,
            ha="center", va="center", fontsize=10, fontweight="bold", color="#333333")

    # Labels
    ax.text(x + width / 2, y + height - 0.25, label,
            ha="center", va="center", fontsize=9, fontweight="bold", color="white")
    ax.text(x + width / 2, y + 0.18, sublabel,
            ha="center", va="center", fontsize=7, color="white", style="italic")


def draw_arrow(ax, start, end, label="", color="#555555"):
    """Draw a connection arrow between components."""
    ax.annotate(
        "", xy=end, xytext=start,
        arrowprops=dict(
            arrowstyle="->", color=color,
            lw=2, connectionstyle="arc3,rad=0.1",
        ),
    )
    if label:
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        ax.text(mid_x, mid_y + 0.12, label,
                ha="center", va="center", fontsize=6.5,
                color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor=color, alpha=0.8))


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Gather info for both use cases
    uc_infos = []
    for uc in config.VALID_USE_CASES:
        uc_doc = config.uc_document_config(uc)
        uc_search = config.uc_search_config(uc)
        uc_ag = config.uc_agent_config(uc)["agent"]
        uc_infos.append({
            "key": uc,
            "domain": uc_doc["domain"],
            "container": config.container_name(uc),
            "index": uc_search["standard_index"]["name"],
            "agent": uc_ag["name"],
        })

    fig, ax = plt.subplots(1, 1, figsize=(18, 12))
    ax.set_xlim(-0.5, 14.5)
    ax.set_ylim(-0.5, 10.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    ax.text(7, 10.0, "AI Search & Foundry Agent — Multi Use-Case Architecture",
            ha="center", va="center", fontsize=15, fontweight="bold", color="#0078D4")
    ax.text(7, 9.6, "Private VNET · Managed Identity · Dual Agents",
            ha="center", va="center", fontsize=10, color="#555555")

    # ── Private VNET boundary ──
    vnet_box = FancyBboxPatch(
        (0.3, 0.3), 10.4, 8.8,
        boxstyle="round,pad=0.15",
        facecolor="#F0F7FF", edgecolor="#0078D4",
        linewidth=2.5, linestyle="--", alpha=0.4,
    )
    ax.add_patch(vnet_box)
    ax.text(5.5, 8.85, "Private VNET", fontsize=11, fontweight="bold",
            color="#0078D4", style="italic")

    # ── Use Case 1: Engineering Docs (left column) ──
    uc0 = uc_infos[0]
    # Blob
    draw_azure_icon_box(ax, 0.8, 5.8, 3.2, 1.0,
                        "Blob Storage", f"{_res['storage']['account_name']} / {uc0['container']}",
                        "#0078D4", "BS")
    # Index
    draw_azure_icon_box(ax, 0.8, 4.0, 3.2, 1.0,
                        "AI Search Index", uc0["index"],
                        "#6B2FA0", "AS")
    # Agent
    draw_azure_icon_box(ax, 0.8, 2.2, 3.2, 1.0,
                        "Foundry Agent", uc0["agent"],
                        "#107C10", "FA")
    # Label
    ax.text(2.4, 7.1, f"Use Case 1: {uc0['domain']}", ha="center", va="center",
            fontsize=9, fontweight="bold", color="#333333",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#E8F0FE", edgecolor="#0078D4", alpha=0.9))

    # Arrows UC1
    draw_arrow(ax, (2.4, 5.8), (2.4, 5.0), "Indexer", "#6B2FA0")
    draw_arrow(ax, (2.4, 3.2), (2.4, 4.0), "Search Tool", "#107C10")

    # ── Use Case 2: Filter Design (right column) ──
    uc1 = uc_infos[1]
    draw_azure_icon_box(ax, 5.8, 5.8, 3.2, 1.0,
                        "Blob Storage", f"{_res['storage']['account_name']} / {uc1['container']}",
                        "#0078D4", "BS")
    draw_azure_icon_box(ax, 5.8, 4.0, 3.2, 1.0,
                        "AI Search Index", uc1["index"],
                        "#6B2FA0", "AS")
    draw_azure_icon_box(ax, 5.8, 2.2, 3.2, 1.0,
                        "Foundry Agent", uc1["agent"],
                        "#107C10", "FA")
    ax.text(7.4, 7.1, f"Use Case 2: {uc1['domain']}", ha="center", va="center",
            fontsize=9, fontweight="bold", color="#333333",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#E8F0FE", edgecolor="#0078D4", alpha=0.9))

    draw_arrow(ax, (7.4, 5.8), (7.4, 5.0), "Indexer", "#6B2FA0")
    draw_arrow(ax, (7.4, 3.2), (7.4, 4.0), "Search Tool", "#107C10")

    # ── Shared Private Endpoints row ──
    for x_pos, label in [(1.5, "PE: Blob"), (4.3, "PE: AI Search"), (7.0, "PE: Blob"), (9.0, "PE: AI Search")]:
        pe = FancyBboxPatch(
            (x_pos - 0.6, 7.5), 1.2, 0.5,
            boxstyle="round,pad=0.03",
            facecolor="#50B0E0", edgecolor="#0078D4",
            linewidth=1, alpha=0.8,
        )
        ax.add_patch(pe)
        ax.text(x_pos, 7.75, label, ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="white")

    # ── Managed Identity (shared) ──
    mi_box = FancyBboxPatch(
        (3.6, 0.6), 2.8, 0.8,
        boxstyle="round,pad=0.05",
        facecolor="#FF8C00", edgecolor="#CC7000",
        linewidth=1.2, alpha=0.85,
    )
    ax.add_patch(mi_box)
    ax.text(5.0, 1.05, "Managed Identity", ha="center", va="center",
            fontsize=8, fontweight="bold", color="white")
    ax.text(5.0, 0.8, "DefaultAzureCredential", ha="center", va="center",
            fontsize=6.5, color="white")

    # Dashed auth lines from MI to agents
    for target_x in [2.4, 7.4]:
        ax.annotate(
            "", xy=(target_x, 2.2), xytext=(5.0, 1.4),
            arrowprops=dict(arrowstyle="->", color="#FF8C00", lw=1.2, linestyle="--"),
        )

    # ── User / Client (outside VNET) ──
    user_box = FancyBboxPatch(
        (11.5, 5.5), 2.5, 1.8,
        boxstyle="round,pad=0.08",
        facecolor="#2D2D2D", edgecolor="#555555",
        linewidth=1.5, alpha=0.9,
    )
    ax.add_patch(user_box)
    ax.text(12.75, 6.9, "Users / Engineers", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(12.75, 6.4, "Semantic & Keyword", ha="center", va="center",
            fontsize=7, color="#AAAAAA")
    ax.text(12.75, 6.05, "Search Queries", ha="center", va="center",
            fontsize=7, color="#AAAAAA")
    ax.text(12.75, 5.7, "Feedback Loop", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    draw_arrow(ax, (11.5, 6.5), (9.0, 3.2), "Query", "#107C10")
    draw_arrow(ax, (11.5, 6.0), (4.0, 3.0), "Query", "#107C10")

    # ── GitHub Actions (outside VNET) ──
    gh_box = FancyBboxPatch(
        (11.5, 3.5), 2.5, 1.2,
        boxstyle="round,pad=0.08",
        facecolor="#24292E", edgecolor="#555555",
        linewidth=1.5, alpha=0.9,
    )
    ax.add_patch(gh_box)
    ax.text(12.75, 4.35, "GitHub Actions", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(12.75, 3.9, "CI/CD Pipeline", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    draw_arrow(ax, (11.5, 4.1), (9.0, 5.8), "Deploy", "#24292E")

    # ── Schedule indicator ──
    sched_box = FancyBboxPatch(
        (11.5, 1.5), 2.5, 0.8,
        boxstyle="round,pad=0.05",
        facecolor="#E8E8E8", edgecolor="#999999",
        linewidth=1, alpha=0.85,
    )
    ax.add_patch(sched_box)
    ax.text(12.75, 1.95, "Indexer Schedule", ha="center", va="center",
            fontsize=8, fontweight="bold", color="#333333")
    ax.text(12.75, 1.7, "Daily 8:00 AM PST", ha="center", va="center",
            fontsize=7, color="#555555")

    draw_arrow(ax, (11.5, 1.9), (9.0, 4.0), "", "#999999")

    # ── Ranking / Feedback box ──
    fb_box = FancyBboxPatch(
        (11.5, 8.0), 2.5, 1.0,
        boxstyle="round,pad=0.05",
        facecolor="#D4E6F1", edgecolor="#2980B9",
        linewidth=1.2, alpha=0.85,
    )
    ax.add_patch(fb_box)
    ax.text(12.75, 8.55, "Ranking & Feedback", ha="center", va="center",
            fontsize=8, fontweight="bold", color="#2C3E50")
    ax.text(12.75, 8.2, "95% accuracy target", ha="center", va="center",
            fontsize=7, color="#555555")

    draw_arrow(ax, (11.5, 8.5), (9.0, 6.8), "", "#2980B9")

    # ── Legend ──
    legend_items = [
        mpatches.Patch(facecolor="#0078D4", edgecolor="#333", label="Azure Blob Storage"),
        mpatches.Patch(facecolor="#6B2FA0", edgecolor="#333", label="Azure AI Search"),
        mpatches.Patch(facecolor="#107C10", edgecolor="#333", label="AI Foundry Agent"),
        mpatches.Patch(facecolor="#FF8C00", edgecolor="#333", label="Managed Identity"),
        mpatches.Patch(facecolor="#50B0E0", edgecolor="#0078D4", label="Private Endpoint"),
        mpatches.Patch(facecolor="#F0F7FF", edgecolor="#0078D4", label="Private VNET", linestyle="--"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#CCCCCC")

    output_path = os.path.join(DOCS_DIR, DIAGRAM_FILENAME)
    plt.savefig(output_path, dpi=DIAGRAM_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()

    print(f"Architecture diagram saved to: {output_path}")

    # Generate per-use-case diagrams
    for uc in config.VALID_USE_CASES:
        _generate_single_uc_diagram(uc)


def _generate_single_uc_diagram(use_case: str):
    """Generate a standalone architecture diagram for a single use case."""
    uc_doc = config.uc_document_config(use_case)
    uc_search = config.uc_search_config(use_case)
    uc_ag = config.uc_agent_config(use_case)["agent"]
    container = config.container_name(use_case)
    domain = uc_doc["domain"]
    index_name = uc_search["standard_index"]["name"]
    agent_name = uc_ag["name"]

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(-0.5, 8.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    ax.text(6, 8.1, f"{domain} — AI Search & Foundry Agent",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#0078D4")
    ax.text(6, 7.75, "Private VNET · Managed Identity · Azure AI Search",
            ha="center", va="center", fontsize=10, color="#555555")

    # Private VNET boundary
    vnet_box = FancyBboxPatch(
        (0.3, 0.3), 8.4, 7.0,
        boxstyle="round,pad=0.15",
        facecolor="#F0F7FF", edgecolor="#0078D4",
        linewidth=2.5, linestyle="--", alpha=0.4,
    )
    ax.add_patch(vnet_box)
    ax.text(4.5, 7.05, "Private VNET", fontsize=11, fontweight="bold",
            color="#0078D4", style="italic")

    # Blob Storage (or Cosmos DB for cosmosdb use cases)
    is_cosmosdb = config.is_cosmosdb_use_case(use_case)
    if is_cosmosdb:
        cosmosdb_cfg = config.cosmosdb_config()
        draw_azure_icon_box(ax, 0.8, 4.5, 3.2, 1.2,
                            "Azure Cosmos DB",
                            f"{cosmosdb_cfg['account_name']} / {cosmosdb_cfg['database_name']}",
                            "#00A4EF", "CD")
    else:
        draw_azure_icon_box(ax, 0.8, 4.5, 3.2, 1.2,
                            "Azure Blob Storage",
                            f"{_res['storage']['account_name']} / {container}",
                            "#0078D4", "BS")

    # Private Endpoint: Blob / Cosmos DB
    pe_label = "PE: Cosmos DB" if is_cosmosdb else "Private Endpoint"
    pe1 = FancyBboxPatch((1.5, 3.3), 1.8, 0.6, boxstyle="round,pad=0.04",
                         facecolor="#50B0E0", edgecolor="#0078D4", linewidth=1, alpha=0.85)
    ax.add_patch(pe1)
    ax.text(2.4, 3.6, pe_label, ha="center", va="center",
            fontsize=7, fontweight="bold", color="white")

    draw_arrow(ax, (2.4, 3.9), (2.4, 4.5), "Private Link", "#0078D4")

    # AI Search
    draw_azure_icon_box(ax, 4.5, 4.5, 3.2, 1.2,
                        "Azure AI Search", index_name,
                        "#6B2FA0", "AS")

    draw_arrow(ax, (4.5, 5.1), (4.0, 5.1), "CosmosDB Indexer" if is_cosmosdb else "Indexer", "#6B2FA0")

    # Private Endpoint: Search
    pe2 = FancyBboxPatch((5.2, 3.3), 1.8, 0.6, boxstyle="round,pad=0.04",
                         facecolor="#8B5EC0", edgecolor="#6B2FA0", linewidth=1, alpha=0.85)
    ax.add_patch(pe2)
    ax.text(6.1, 3.6, "Private Endpoint", ha="center", va="center",
            fontsize=7, fontweight="bold", color="white")

    draw_arrow(ax, (6.1, 3.9), (6.1, 4.5), "Private Link", "#6B2FA0")

    # Foundry Agent
    draw_azure_icon_box(ax, 4.5, 6.0, 3.2, 1.0,
                        "AI Foundry Agent", agent_name,
                        "#107C10", "FA")

    draw_arrow(ax, (6.1, 6.0), (6.1, 5.7), "Search Tool", "#107C10")

    # Managed Identity
    mi = FancyBboxPatch((1.0, 0.6), 2.5, 0.8, boxstyle="round,pad=0.05",
                        facecolor="#FF8C00", edgecolor="#CC7000", linewidth=1.2, alpha=0.85)
    ax.add_patch(mi)
    ax.text(2.25, 1.05, "Managed Identity", ha="center", va="center",
            fontsize=8, fontweight="bold", color="white")
    ax.text(2.25, 0.8, "DefaultAzureCredential", ha="center", va="center",
            fontsize=6.5, color="white")

    for tx, ty in [(2.4, 3.3), (6.1, 3.3)]:
        ax.annotate("", xy=(tx, ty), xytext=(2.25, 1.4),
                    arrowprops=dict(arrowstyle="->", color="#FF8C00", lw=1.2, linestyle="--"))

    # Schedule
    sched = FancyBboxPatch((4.5, 0.6), 3.2, 0.8, boxstyle="round,pad=0.05",
                           facecolor="#E8E8E8", edgecolor="#999999", linewidth=1, alpha=0.85)
    ax.add_patch(sched)
    ax.text(6.1, 1.05, "Indexer Schedule", ha="center", va="center",
            fontsize=8, fontweight="bold", color="#333333")
    ax.text(6.1, 0.8, "Daily 8:00 AM PST", ha="center", va="center",
            fontsize=7, color="#555555")

    draw_arrow(ax, (6.1, 1.4), (6.1, 3.3), "", "#999999")

    # User
    user = FancyBboxPatch((9.5, 5.5), 2.5, 1.5, boxstyle="round,pad=0.08",
                          facecolor="#2D2D2D", edgecolor="#555555", linewidth=1.5, alpha=0.9)
    ax.add_patch(user)
    ax.text(10.75, 6.55, "Users / Engineers", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(10.75, 6.15, "Semantic & Keyword", ha="center", va="center",
            fontsize=7, color="#AAAAAA")
    ax.text(10.75, 5.85, "Search Queries", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    draw_arrow(ax, (9.5, 6.3), (7.7, 6.5), "Query Agent", "#107C10")

    # GitHub Actions
    gh = FancyBboxPatch((9.5, 3.5), 2.5, 1.2, boxstyle="round,pad=0.08",
                        facecolor="#24292E", edgecolor="#555555", linewidth=1.5, alpha=0.9)
    ax.add_patch(gh)
    ax.text(10.75, 4.35, "GitHub Actions", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(10.75, 3.9, "CI/CD Pipeline", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    draw_arrow(ax, (9.5, 4.1), (7.7, 5.1), "Deploy", "#24292E")

    # Use-case-specific extras
    if use_case == "filter_design":
        fb = FancyBboxPatch((9.5, 1.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                            facecolor="#D4E6F1", edgecolor="#2980B9", linewidth=1.2, alpha=0.85)
        ax.add_patch(fb)
        ax.text(10.75, 2.05, "Ranking & Feedback", ha="center", va="center",
                fontsize=8, fontweight="bold", color="#2C3E50")
        ax.text(10.75, 1.75, "90% → 95% accuracy", ha="center", va="center",
                fontsize=7, color="#555555")
        draw_arrow(ax, (9.5, 2.0), (7.7, 5.0), "Boost scores", "#2980B9")
    elif use_case in ("tax_pdf_forms", "eng_design_ppt"):
        cb = FancyBboxPatch((9.5, 1.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                            facecolor="#FFF3E0", edgecolor="#E65100", linewidth=1.2, alpha=0.85)
        ax.add_patch(cb)
        ax.text(10.75, 2.05, "Cosmos DB Pipeline", ha="center", va="center",
                fontsize=8, fontweight="bold", color="#BF360C")
        doc_count = "388 PDFs" if use_case == "tax_pdf_forms" else "100 PPTXs"
        ax.text(10.75, 1.75, f"Chunk & Index ({doc_count})", ha="center", va="center",
                fontsize=7, color="#555555")
        draw_arrow(ax, (9.5, 2.0), (7.7, 5.0), "Section chunks", "#E65100")
    else:
        ft = FancyBboxPatch((9.5, 1.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                            facecolor="#E8F5E9", edgecolor="#388E3C", linewidth=1.2, alpha=0.85)
        ax.add_patch(ft)
        ax.text(10.75, 2.05, "Fine-Tuning Pipeline", ha="center", va="center",
                fontsize=8, fontweight="bold", color="#1B5E20")
        ax.text(10.75, 1.75, "539 Q&A pairs → 90% cite acc.", ha="center", va="center",
                fontsize=7, color="#555555")
        draw_arrow(ax, (9.5, 2.0), (7.7, 6.0), "Improved model", "#388E3C")

    # Legend
    legend_items = [
        mpatches.Patch(facecolor="#0078D4", edgecolor="#333", label="Azure Blob Storage"),
        mpatches.Patch(facecolor="#00A4EF", edgecolor="#333", label="Azure Cosmos DB"),
        mpatches.Patch(facecolor="#6B2FA0", edgecolor="#333", label="Azure AI Search"),
        mpatches.Patch(facecolor="#107C10", edgecolor="#333", label="AI Foundry Agent"),
        mpatches.Patch(facecolor="#FF8C00", edgecolor="#333", label="Managed Identity"),
        mpatches.Patch(facecolor="#F0F7FF", edgecolor="#0078D4", label="Private VNET", linestyle="--"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#CCCCCC")

    # Determine output path
    folder_map = {
        "engineering_docs": "engineering-docs",
        "filter_design": "filter-design",
        "tax_pdf_forms": "tax-pdf-forms",
        "eng_design_ppt": "eng-design-ppt",
    }
    uc_folder = os.path.join(config.PROJECT_ROOT, "use-cases", folder_map[use_case])
    os.makedirs(uc_folder, exist_ok=True)

    output_path = os.path.join(uc_folder, "architecture.png")
    plt.savefig(output_path, dpi=DIAGRAM_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"  {domain} diagram saved to: {output_path}")


if __name__ == "__main__":
    main()
