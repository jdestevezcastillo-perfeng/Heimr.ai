#!/bin/bash
set -e

# Directory setup
mkdir -p content/wiki

# Copy README as Home content
echo "Copying README.md..."
cp ../README.md content/readme.md

# Copy Wiki contents
echo "Copying Wiki..."
cp ../docs/wiki/*.md content/wiki/

# Generate Wiki Index (List of files)
# Creates a JSON array of filenames: ["01-introduction.md", "02-architecture.md"]
echo "Generating Wiki Index..."
ls content/wiki | jq -R -s 'split("\n")[:-1]' > content/wiki_index.json

echo "Website build complete. Content ready in website/content/"
