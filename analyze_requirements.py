import os

HEAVY_PACKAGES = {
    "torch": "Very large (often >1GB). Consider removing or replacing with a lighter ML lib.",
    "tensorflow": "Extremely large. Use only if absolutely necessary.",
    "jupyter": "Heavy IDE/development environment. Not needed in production.",
    "jupyterlab": "Same as jupyter – dev-only.",
    "notebook": "Related to Jupyter – remove for production.",
    "matplotlib": "Large visualization library. Only include if used.",
    "seaborn": "Built on matplotlib – remove unless plotting is required.",
    "scikit-learn": "Heavy ML library. Use only if essential.",
    "pandas": "Heavy for some use-cases. Replace with lighter alternatives if possible.",
    "ipython": "Development shell – remove in production.",
    "nbconvert": "Only needed for Jupyter exports.",
    "nbformat": "Same as above – Jupyter-related.",
    "plotly": "Large plotting library. Remove unless used.",
    "opencv-python": "Huge package. Use only if you need image processing.",
    "pyarrow": "Large binary dependency. Often optional.",
    "sympy": "Symbolic math – large and niche.",
    "openai": "Heavy due to dependencies; keep only if you're calling OpenAI APIs."
}

def analyze_requirements(path="requirements.txt"):
    if not os.path.exists(path):
        print(f"❌ No file found at {path}")
        return

    with open(path, "r") as f:
        lines = f.readlines()

    print(f"🔍 Analyzing {path}...\n")
    for line in lines:
        pkg = line.strip().split("==")[0].lower()
        if pkg in HEAVY_PACKAGES:
            print(f"⚠️  {pkg}: {HEAVY_PACKAGES[pkg]}")
    print("\n✅ Done. Consider removing or replacing the packages above to reduce image size.")

if __name__ == "__main__":
    analyze_requirements()
