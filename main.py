import sys
import os
from parser import parse_csv
from graph_builder import build_graph
from xlsx_exporter import export_xlsx
from html_exporter import export_html

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input.csv> [output_dir]")
        sys.exit(1)

    csv_path   = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(csv_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    print(f"Reading {csv_path}...")
    people, parse_warnings = parse_csv(csv_path)
    for w in parse_warnings:
        print(f"  [PARSE] {w}")

    print("Building call graph...")
    graph_warnings = build_graph(people)
    for w in graph_warnings:
        print(f"  [GRAPH] {w}")

    xlsx_path = os.path.join(output_dir, "recall_assignments.xlsx")
    html_path = os.path.join(output_dir, "recall_chart.html")

    print(f"Writing spreadsheet → {xlsx_path}")
    export_xlsx(people, xlsx_path)

    print(f"Writing HTML chart  → {html_path}")
    export_html(people, html_path)

    print("\nDone ✓")

if __name__ == "__main__":
    main()
