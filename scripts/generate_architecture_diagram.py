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

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")


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

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(-0.5, 12.5)
    ax.set_ylim(-0.5, 8.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title
    ax.text(6, 8.1, "KLA Engineering Docs - AI Search & Foundry Agent Architecture",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#0078D4")
    ax.text(6, 7.75, "Private VNET with Managed Identity Authentication",
            ha="center", va="center", fontsize=10, color="#555555")

    # ── Private VNET boundary ──
    vnet_box = FancyBboxPatch(
        (0.3, 0.3), 8.4, 6.8,
        boxstyle="round,pad=0.15",
        facecolor="#F0F7FF", edgecolor="#0078D4",
        linewidth=2.5, linestyle="--", alpha=0.4,
    )
    ax.add_patch(vnet_box)
    ax.text(4.5, 6.85, "Private VNET", fontsize=11, fontweight="bold",
            color="#0078D4", style="italic")

    # ── Azure Blob Storage ──
    draw_azure_icon_box(ax, 0.8, 4.0, 2.8, 1.2,
                        "Azure Blob Storage", "aistoragemyaacoub / engineering-docs",
                        "#0078D4", "BS")

    # ── Private Endpoint for Blob ──
    pe_blob = FancyBboxPatch(
        (1.2, 2.5), 2.0, 0.7,
        boxstyle="round,pad=0.05",
        facecolor="#50B0E0", edgecolor="#0078D4",
        linewidth=1.2, alpha=0.85,
    )
    ax.add_patch(pe_blob)
    ax.text(2.2, 2.85, "Private Endpoint", ha="center", va="center",
            fontsize=7.5, fontweight="bold", color="white")
    ax.text(2.2, 2.65, "(Blob Storage)", ha="center", va="center",
            fontsize=6.5, color="white")

    # Arrow: PE -> Blob
    draw_arrow(ax, (2.2, 3.2), (2.2, 4.0), "Private Link", "#0078D4")

    # ── Azure AI Search ──
    draw_azure_icon_box(ax, 4.2, 4.0, 2.8, 1.2,
                        "Azure AI Search", "ai-search-my / engineering-docs-index",
                        "#6B2FA0", "AS")

    # Arrow: AI Search -> Blob (indexer pulls data)
    draw_arrow(ax, (4.2, 4.6), (3.6, 4.6), "Indexer", "#6B2FA0")

    # ── Private Endpoint for AI Search ──
    pe_search = FancyBboxPatch(
        (4.6, 2.5), 2.0, 0.7,
        boxstyle="round,pad=0.05",
        facecolor="#8B5EC0", edgecolor="#6B2FA0",
        linewidth=1.2, alpha=0.85,
    )
    ax.add_patch(pe_search)
    ax.text(5.6, 2.85, "Private Endpoint", ha="center", va="center",
            fontsize=7.5, fontweight="bold", color="white")
    ax.text(5.6, 2.65, "(AI Search)", ha="center", va="center",
            fontsize=6.5, color="white")

    # Arrow: PE -> AI Search
    draw_arrow(ax, (5.6, 3.2), (5.6, 4.0), "Private Link", "#6B2FA0")

    # ── Azure AI Foundry Agent ──
    draw_azure_icon_box(ax, 4.2, 5.8, 2.8, 1.0,
                        "AI Foundry Agent", "Eng-Docs-Search-Agent",
                        "#107C10", "FA")

    # Arrow: Foundry Agent -> AI Search (tool call)
    draw_arrow(ax, (5.6, 5.8), (5.6, 5.2), "AI Search Tool", "#107C10")

    # ── Managed Identity ──
    mi_box = FancyBboxPatch(
        (1.0, 0.6), 2.2, 0.8,
        boxstyle="round,pad=0.05",
        facecolor="#FF8C00", edgecolor="#CC7000",
        linewidth=1.2, alpha=0.85,
    )
    ax.add_patch(mi_box)
    ax.text(2.1, 1.05, "Managed Identity", ha="center", va="center",
            fontsize=8, fontweight="bold", color="white")
    ax.text(2.1, 0.8, "DefaultAzureCredential", ha="center", va="center",
            fontsize=6.5, color="white")

    # Dashed lines from MI to services
    for target_x, target_y in [(2.2, 2.5), (5.6, 2.5)]:
        ax.annotate(
            "", xy=(target_x, target_y), xytext=(2.1, 1.4),
            arrowprops=dict(arrowstyle="->", color="#FF8C00", lw=1.5, linestyle="--"),
        )

    # ── User / Client (outside VNET) ──
    user_box = FancyBboxPatch(
        (9.5, 5.5), 2.5, 1.5,
        boxstyle="round,pad=0.08",
        facecolor="#2D2D2D", edgecolor="#555555",
        linewidth=1.5, alpha=0.9,
    )
    ax.add_patch(user_box)
    ax.text(10.75, 6.55, "User / Engineer", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(10.75, 6.15, "Semantic & Keyword", ha="center", va="center",
            fontsize=7, color="#AAAAAA")
    ax.text(10.75, 5.85, "Search Queries", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    # Arrow: User -> Agent
    draw_arrow(ax, (9.5, 6.3), (7.0, 6.3), "Query Agent", "#107C10")

    # ── GitHub Actions (outside VNET) ──
    gh_box = FancyBboxPatch(
        (9.5, 3.5), 2.5, 1.2,
        boxstyle="round,pad=0.08",
        facecolor="#24292E", edgecolor="#555555",
        linewidth=1.5, alpha=0.9,
    )
    ax.add_patch(gh_box)
    ax.text(10.75, 4.35, "GitHub Actions", ha="center", va="center",
            fontsize=9, fontweight="bold", color="white")
    ax.text(10.75, 3.9, "CI/CD Pipeline", ha="center", va="center",
            fontsize=7, color="#AAAAAA")

    # Arrow: GitHub Actions -> VNET
    draw_arrow(ax, (9.5, 4.1), (7.0, 4.6), "Deploy", "#24292E")

    # ── Schedule indicator ──
    sched_box = FancyBboxPatch(
        (4.2, 1.0), 2.8, 0.7,
        boxstyle="round,pad=0.05",
        facecolor="#E8E8E8", edgecolor="#999999",
        linewidth=1, alpha=0.85,
    )
    ax.add_patch(sched_box)
    ax.text(5.6, 1.35, "⏰ Indexer Schedule: Daily 8:00 AM PST",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#333333")

    # Arrow: Schedule -> AI Search
    draw_arrow(ax, (5.6, 1.7), (5.6, 2.5), "", "#999999")

    # ── Legend ──
    legend_items = [
        mpatches.Patch(facecolor="#0078D4", edgecolor="#333", label="Azure Storage"),
        mpatches.Patch(facecolor="#6B2FA0", edgecolor="#333", label="Azure AI Search"),
        mpatches.Patch(facecolor="#107C10", edgecolor="#333", label="AI Foundry Agent"),
        mpatches.Patch(facecolor="#FF8C00", edgecolor="#333", label="Managed Identity"),
        mpatches.Patch(facecolor="#F0F7FF", edgecolor="#0078D4", label="Private VNET", linestyle="--"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8,
              framealpha=0.9, edgecolor="#CCCCCC")

    output_path = os.path.join(DOCS_DIR, "architecture.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()

    print(f"Architecture diagram saved to: {output_path}")


if __name__ == "__main__":
    main()
