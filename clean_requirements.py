# clean_requirements.py

remove_list = [
    "ipython", "ipython_pygments_lexers", "jupyterlab", "jupyterlab_git",
    "matplotlib", "matplotlib-inline", "nbconvert", "nbformat", "plotly",
    "seaborn", "sympy", "torch", "openai", "pandas", "scikit-learn"
]

with open("requirements.txt", "r") as infile:
    lines = infile.readlines()

with open("requirements.cleaned.txt", "w") as outfile:
    for line in lines:
        pkg = line.strip().split("==")[0].lower()
        if any(pkg.startswith(rm) for rm in remove_list):
            print(f"🗑️  Removing: {line.strip()}")
            continue
        outfile.write(line)
