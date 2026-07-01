<img width="450" alt="image" src="https://github.com/user-attachments/assets/8f718cab-7fe2-456e-9981-c6f2f8f71255" />

# Mercury
Mercury is a fantasy console loosely inspired by CHIP-8 and it's derivatives.

## Installation
You can install straight from GitHub.
```sh
pip install git+https://github.com/las-r/mercury.git
```

## Usage
```sh
# Run emulator
mercury <program.bin>

# Assemble source
mercury --asm <source.asm> <program.bin>

# Convert image to MercuryASM
mercury --conv <image.png> <output.asm>
```

## Specification
Check `SPEC.txt` at root.