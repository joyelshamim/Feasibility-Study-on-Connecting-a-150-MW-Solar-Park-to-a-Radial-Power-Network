import os
import sys
import glob
import subprocess
import tempfile
import time
import shutil

# Create the required folder structure if it doesn't exist
os.makedirs('CSS', exist_ok=True)
os.makedirs('SLD diagram', exist_ok=True)

def list_available_notebooks():
    """Display available notebooks in the CSS folder"""
    if not os.path.exists('CSS'):
        print("CSS folder not found. Please ensure your folder structure is correct.")
        return {}

    notebook_files = glob.glob('CSS/*.ipynb')
    
    if not notebook_files:
        print("No notebook files found in the CSS folder.")
        return {}
    
    # Create a dictionary mapping numbers to file paths
    notebooks = {}
    print("\nAvailable analysis configurations:")
    print("----------------------------------")
    for i, filepath in enumerate(sorted(notebook_files), 1):
        filename = os.path.basename(filepath)
        # Format filename for display
        display_name = filename.replace('SLD_', '').replace('.ipynb', '').replace('_', ' ')
        
        notebooks[i] = {
            'path': filepath,
            'name': display_name
        }
        print(f"{i}. {display_name}")
    print("----------------------------------")
    
    return notebooks

def run_notebook_with_subprocess(notebook_path, output_file=None):
    """Run a notebook using nbconvert via subprocess"""
    try:
        # Create a temporary file for output if none provided
        if output_file is None:
            fd, output_file = tempfile.mkstemp(suffix='.ipynb')
            os.close(fd)
        
        print(f"Running analysis from: {os.path.basename(notebook_path)}")
        print("This may take a minute...\n")
        
        # Run the notebook using nbconvert
        cmd = [
            sys.executable, 
            '-m', 'nbconvert', 
            '--to', 'notebook', 
            '--execute',
            '--output', output_file,
            notebook_path
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Wait for the process to complete with a timeout
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='replace')
                print(f"Error executing notebook: {stderr_text}")
                return None
            print("\nAnalysis completed successfully!")
            return output_file
        except subprocess.TimeoutExpired:
            process.kill()
            print("Execution timed out (10 minutes)")
            return None
            
    except Exception as e:
        print(f"Error executing notebook: {str(e)}")
        return None

def extract_results_from_file(output_file):
    """Extract power flow analysis results from the output file"""
    try:
        if output_file is None or not os.path.exists(output_file):
            return "No results to display."
        
        # Read the file as a notebook
        import nbformat
        with open(output_file, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        results = []
        in_results_section = False
        
        for cell in nb.cells:
            if cell.cell_type == 'code' and cell.outputs:
                for output in cell.outputs:
                    if 'text' in output and '=== Power Flow Analysis ===' in str(output.get('text', '')):
                        in_results_section = True
                        results.append(output.get('text', ''))
                    elif 'text' in output and in_results_section:
                        results.append(output.get('text', ''))
        
        if results:
            return ''.join(results)
        else:
            # Try to find any output that might contain power flow results
            for cell in nb.cells:
                if cell.cell_type == 'code' and cell.outputs:
                    for output in cell.outputs:
                        if 'text' in output and any(term in str(output.get('text', '')) for term in 
                                                 ['Power Flow', 'System Configuration', 'Voltage Profile']):
                            results.append(output.get('text', ''))
            
            if results:
                return ''.join(results)
            else:
                return "No power flow analysis results found in the output."
    
    except Exception as e:
        print(f"Error extracting results: {str(e)}")
        return "Error extracting results from the output file."

def find_and_move_svg_files(notebook_name):
    """Find SVG files in CSS/SLD diagram folder and move them to the correct location"""
    # Check if SVG files are in CSS/SLD diagram folder
    css_sld_path = os.path.join('CSS', 'SLD diagram')
    
    if os.path.exists(css_sld_path):
        svg_files = glob.glob(os.path.join(css_sld_path, '*.svg'))
        
        if svg_files:
            print(f"Found {len(svg_files)} SVG files in CSS/SLD diagram folder. Moving to main SLD diagram folder...")
            
            for svg_file in svg_files:
                filename = os.path.basename(svg_file)
                # Try to move the file to the main SLD diagram folder
                try:
                    shutil.move(svg_file, os.path.join('SLD diagram', filename))
                    print(f"Moved: {filename}")
                except Exception as e:
                    print(f"Error moving {filename}: {e}")
                    # Try copying instead
                    try:
                        shutil.copy2(svg_file, os.path.join('SLD diagram', filename))
                        print(f"Copied: {filename}")
                    except Exception as e2:
                        print(f"Error copying file: {e2}")
            
            return True
    
    return False

def modify_notebook_sld_path(notebook_path):
    """Create a temporary copy of the notebook with corrected SLD path"""
    import nbformat
    
    try:
        # Read the notebook
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Create a new notebook with modified paths
        modified_cells = []
        
        for cell in nb.cells:
            if cell.cell_type == 'code':
                # Look for SLD diagram paths
                if "os.path.join('SLD diagram'" in cell.source or "os.path.join(\"SLD diagram\"" in cell.source:
                    # Fix the path to use absolute path
                    modified_source = cell.source.replace(
                        "os.path.join('SLD diagram'", 
                        "os.path.join(os.path.abspath('SLD diagram')"
                    ).replace(
                        "os.path.join(\"SLD diagram\"", 
                        "os.path.join(os.path.abspath('SLD diagram')"
                    )
                    cell.source = modified_source
            
            modified_cells.append(cell)
        
        nb.cells = modified_cells
        
        # Write the modified notebook to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.ipynb')
        os.close(fd)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        
        return temp_path
        
    except Exception as e:
        print(f"Error modifying notebook: {e}")
        return notebook_path

def run_analysis(choice, notebooks):
    """Run the selected analysis and display results"""
    if not notebooks or choice not in notebooks:
        print(f"Invalid selection: {choice}. Please select a valid number.")
        return
    
    selected = notebooks[choice]
    print(f"Running analysis for: {selected['name']}\n")
    
    # Check if the notebook exists in CSS folder
    if not os.path.exists(selected['path']):
        print(f"Error: Notebook not found at {selected['path']}.")
        print("Make sure all analysis notebooks are in the CSS folder.")
        return
    
    # Make sure SLD diagram folder exists in the root directory
    os.makedirs('SLD diagram', exist_ok=True)
    
    # Create a symlink or junction to ensure notebooks in CSS can find the SLD diagram folder
    css_sld_path = os.path.join('CSS', 'SLD diagram')
    
    # Remove any existing symlink/junction
    if os.path.exists(css_sld_path):
        # For Windows, we need to handle directory junctions differently
        if os.name == 'nt':  # Windows
            import subprocess
            subprocess.run(['rmdir', css_sld_path], shell=True)
        else:  # Unix-like
            os.remove(css_sld_path)
    
    # Create a new symlink/junction
    # For Windows
    if os.name == 'nt':
        import subprocess
        # Get absolute paths
        target = os.path.abspath('SLD diagram')
        link_name = os.path.abspath(css_sld_path)
        # Create directory junction
        subprocess.run(['mklink', '/J', link_name, target], shell=True)
    else:  # Unix-like
        # Create symbolic link
        os.symlink(os.path.abspath('SLD diagram'), css_sld_path)
    
    # Execute the notebook
    output_file = run_notebook_with_subprocess(selected['path'])
    
    # Extract and display results
    if output_file:
        results = extract_results_from_file(output_file)
        print("\n=== POWER FLOW ANALYSIS RESULTS ===")
        print(results)
        
        # Clean up temporary files
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary file: {str(e)}")
    
    # Check for SVG files in the SLD diagram folder
    svg_files = glob.glob('SLD diagram/*.svg')
    if svg_files:
        print(f"\nFound {len(svg_files)} SLD diagrams in 'SLD diagram' folder:")
        for file in sorted(svg_files):
            print(f"- {os.path.basename(file)}")
    else:
        print("\nNo SVG diagrams found in the 'SLD diagram' folder.")
        print("SVG files might not have been generated. Check the analysis execution.")

def main():
    print("=" * 60)
    print("POWER SYSTEM ANALYSIS TOOL")
    print("=" * 60)
    print("\nThis tool allows you to run different power flow analyses and generate SLD diagrams.")
    
    # List available notebooks
    notebooks = list_available_notebooks()
    
    if not notebooks:
        print("No analysis configurations found. Please add notebook files to the CSS folder.")
        return
    
    while True:
        print("\nSelect an option:")
        print("1. Run a specific analysis")
        print("2. List generated SVG diagrams")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            selection = input("\nEnter the number of the analysis to run: ")
            try:
                selection = int(selection)
                run_analysis(selection, notebooks)
            except ValueError:
                print("Please enter a valid number.")
        
        elif choice == '2':
            svg_files = glob.glob('SLD diagram/*.svg')
            if svg_files:
                print(f"\nFound {len(svg_files)} SVG diagrams in SLD diagram folder:")
                for file in sorted(svg_files):
                    print(f"- {os.path.basename(file)}")
            else:
                print("\nNo SVG diagrams found in the SLD diagram folder.")
        
        elif choice == '3':
            print("Exiting the program.")
            break
        
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()