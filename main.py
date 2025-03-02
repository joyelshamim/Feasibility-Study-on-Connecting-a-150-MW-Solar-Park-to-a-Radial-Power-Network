#!/usr/bin/env python3
import os
import sys
import subprocess
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import HTMLExporter
import tempfile

# Define the available topology notebooks
TOPOLOGY_NOTEBOOKS = [
    {
        "num": 1,
        "name": "Transformer Station Near Aalamoen (22KV)",
        "path": "CSS/SLD_Transformer_Station_Near_Aalamoen_22KV.ipynb",
        "description": "Analysis of transformer station near Aalamoen with 22KV collection system"
    },
    {
        "num": 2,
        "name": "Transformer Station Near Aalamoen (33KV)",
        "path": "CSS/SLD_Transformer_Station_Near_Aalamoen_33KV.ipynb",
        "description": "Analysis of transformer station near Aalamoen with 33KV collection system"
    },
    {
        "num": 3,
        "name": "Transformer Station Near Aalamoen with BESS (33KV)",
        "path": "CSS/SLD_Transformer_Station_Near_Aalamoen_33KV_with_BESS_extra_bus_in_solar_plant.ipynb",
        "description": "Analysis of transformer station near Aalamoen with 33KV collection system and Battery Energy Storage"
    },
    {
        "num": 4,
        "name": "Transformer Station Near Solar Plant (22KV)",
        "path": "CSS/SLD_Transformer_Station_Near_the_Solar_Plant_22KV.ipynb",
        "description": "Analysis of transformer station near the solar plant with 22KV collection system"
    },
    {
        "num": 5,
        "name": "Transformer Station Near Solar Plant (33KV)",
        "path": "CSS/SLD_Transformer_Station_Near_the_Solar_Plant_33KV.ipynb",
        "description": "Analysis of transformer station near the solar plant with 33KV collection system"
    }
]

def ensure_dir(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def list_topologies():
    """Print the list of available topology notebooks"""
    print("\n===== Available Network Topologies =====")
    for topo in TOPOLOGY_NOTEBOOKS:
        print(f"{topo['num']}. {topo['name']}")
        print(f"   {topo['description']}")
        print()

def run_notebook(notebook_path, output_dir="SLD diagram"):
    """Run a Jupyter notebook and capture its output"""
    print(f"\nRunning notebook: {notebook_path}")
    
    # Create the output directory
    ensure_dir(output_dir)
    
    # Modify notebook to save SVGs to the output_dir
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = nbformat.read(f, as_version=4)
    
    # Insert a cell at the beginning to import os and create output dir
    setup_cell = nbformat.v4.new_code_cell(
        f'''
import os

# Create SLD diagram directory if it doesn't exist
os.makedirs("{output_dir}", exist_ok=True)
'''
    )
    notebook.cells.insert(0, setup_cell)
    
    # Find all references to SVG output paths and modify them
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            if 'write_matrix_multi_substation_single_line_diagram_svg' in cell.source:
                # This is a heuristic approach - it might need refinement for specific notebooks
                cell.source = cell.source.replace(
                    ".svg',",
                    f".svg',  # Original path"
                )
                cell.source = cell.source.replace(
                    "parameters=param",
                    f"parameters=param\n)\n\n# Save to output directory\nnetwork.write_matrix_multi_substation_single_line_diagram_svg(\n    layout,\n    os.path.join('{output_dir}', filename),\n    parameters=param"
                )
    
    # Execute the notebook
    print("Executing notebook...")
    try:
        # Create a temporary notebook with our modifications
        with tempfile.NamedTemporaryFile(suffix='.ipynb', delete=False) as temp_notebook:
            nbformat.write(notebook, temp_notebook)
            temp_notebook_path = temp_notebook.name
        
        # Run the notebook in a jupyter environment
        # This approach uses subprocess instead of ExecutePreprocessor for better compatibility
        cmd = [
            sys.executable, "-m", "jupyter", "nbconvert", 
            "--execute", "--to", "notebook", 
            "--output", temp_notebook_path + ".out",
            temp_notebook_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error executing notebook:")
            print(result.stderr)
            return False
        
        # Convert to HTML for display
        html_exporter = HTMLExporter()
        html_exporter.exclude_input = True  # Show only outputs
        
        with open(temp_notebook_path + ".out", 'r', encoding='utf-8') as f:
            executed_nb = nbformat.read(f, as_version=4)
            
        (body, resources) = html_exporter.from_notebook_node(executed_nb)
        
        # Clean up temp files
        os.unlink(temp_notebook_path)
        try:
            os.unlink(temp_notebook_path + ".out")
        except:
            pass
            
        print("\nNotebook executed successfully.")
        
        # List generated SVG files
        svg_files = [f for f in os.listdir(output_dir) if f.endswith('.svg')]
        if svg_files:
            print(f"\nGenerated SLD diagrams in '{output_dir}' directory:")
            for svg in svg_files:
                print(f"  - {svg}")
        else:
            print(f"\nNo SVG files were generated in '{output_dir}' directory.")
            
        return True
        
    except Exception as e:
        print(f"Error executing notebook: {str(e)}")
        return False

def run_in_jupyter(notebook_path):
    """Open the notebook in Jupyter"""
    print(f"\nOpening notebook in Jupyter: {notebook_path}")
    subprocess.run(["jupyter", "notebook", notebook_path])

def list_sld_diagrams(output_dir="SLD diagram"):
    """List available SLD diagrams"""
    if not os.path.exists(output_dir):
        print(f"No SLD diagrams found (directory '{output_dir}' does not exist)")
        return
    
    files = [f for f in os.listdir(output_dir) if f.endswith('.svg')]
    
    if not files:
        print(f"No SLD diagrams found in '{output_dir}' directory")
        return
    
    # Group files by topology
    file_groups = {}
    for f in files:
        # Extract topology name from filename
        if '_22KV' in f:
            key = '22KV'
        elif '_33KV_with_BESS' in f or '_33KV_extraSG' in f:
            key = '33KV with BESS'
        elif '_33KV' in f:
            key = '33KV'
        else:
            key = 'Other'
        
        if key not in file_groups:
            file_groups[key] = []
        file_groups[key].append(f)
    
    print("\nGenerated SLD Diagrams:")
    for group, files in file_groups.items():
        print(f"\n{group} Topology:")
        for f in sorted(files):
            print(f"  - {f}")

def main():
    """Main function"""
    print("===== Power Flow Analysis Tool =====")
    print("This tool runs power flow analysis and generates SLD diagrams.")
    
    # Create SLD diagram directory
    ensure_dir("SLD diagram")
    
    while True:
        print("\nOptions:")
        print("1. List available network topologies")
        print("2. Run a topology analysis")
        print("3. Open a topology notebook in Jupyter")
        print("4. List generated SLD diagrams")
        print("0. Exit")
        
        try:
            choice = int(input("\nEnter your choice (0-4): "))
            
            if choice == 0:
                print("Exiting. Thank you for using the Power Flow Analysis Tool.")
                break
                
            elif choice == 1:
                list_topologies()
                
            elif choice == 2:
                list_topologies()
                selection = int(input("\nSelect a topology to run (1-5): "))
                
                if 1 <= selection <= len(TOPOLOGY_NOTEBOOKS):
                    selected = next((t for t in TOPOLOGY_NOTEBOOKS if t["num"] == selection), None)
                    run_notebook(selected["path"])
                else:
                    print("Invalid selection.")
                    
            elif choice == 3:
                list_topologies()
                selection = int(input("\nSelect a topology to open in Jupyter (1-5): "))
                
                if 1 <= selection <= len(TOPOLOGY_NOTEBOOKS):
                    selected = next((t for t in TOPOLOGY_NOTEBOOKS if t["num"] == selection), None)
                    run_in_jupyter(selected["path"])
                else:
                    print("Invalid selection.")
                    
            elif choice == 4:
                list_sld_diagrams()
                
            else:
                print("Invalid choice. Please enter a number between 0 and 4.")
                
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            break

if __name__ == "__main__":
    main()