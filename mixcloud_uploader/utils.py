import sys

def input_with_default(prompt: str, default: str) -> str:
    if default:
        response = input(f'{prompt} [default: {default}] ').strip()
        return response or default
    else:
        response = None
        while not response:
            response = input(f'{prompt} ')
        return response

def pretty_box(lines: list[str]) -> str:
    width = max(len(line) for line in lines)
    hbar = f"+-{width * '-'}-+"
    return '\n'.join([
        hbar,
        *(f'| {line.ljust(width)} |' for line in lines),
        hbar,
    ])

def confirm(prompt: str):
    response = input(f'{prompt} [y/n] ').strip().lower()
    if response and response != 'y':
        sys.exit(1)
