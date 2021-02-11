Cyberpunk Material Importer
=========
This is a simple import script that will attempt recreate the material on the current actively selected mesh. Minor manual tweaks are still needed to the material for better accuracy.

### Prerequisites
- A recent version of CP77Tools
- The entire `base\surfaces\` directory uncooked to png format
- All mltemplates in those directories extracted to json using the `cr2w -c` function
- The mlsetup setup of your choice also `-c` extracted
- The required mlmask and its content uncooked to png
- Mesh must already have a material and have a standard Principled BSDF shader on it
