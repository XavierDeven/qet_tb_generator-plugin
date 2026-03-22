# QET Terminal Block Generator

Script that generates terminal blocks & connectors for QElectroTech.
Forked from Raul Roda.

## Installation

```bash
pip install .
```

### Linux specific requirements
On Linux, you might need to install `python3-tk` manually if it's not already on your system:
```bash
sudo apt install python3-tk
```

## Usage

Run the command:
```bash
qet_tb_generator [path_to_qet_file]
```

If no file is provided, a dialog will open to select your QElectroTech project.
