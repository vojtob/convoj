"""Nahrada drawio / magick v testoch: zapise vystupny subor (za -o, inak posledny argument)."""
import sys

args = sys.argv[1:]
out = args[args.index('-o') + 1] if '-o' in args else args[-1]
with open(out, 'w') as f:
    f.write('generated\n')
