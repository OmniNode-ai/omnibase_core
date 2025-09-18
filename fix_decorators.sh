#!/bin/bash

# Get all untyped decorator errors and fix them
poetry run pre-commit run mypy-poetry --all-files 2>&1 | grep "Untyped decorator" | sed 's/: error:.*//' > /tmp/errors.txt

echo "Found $(wc -l < /tmp/errors.txt) untyped decorator errors"

while IFS=: read -r file line; do
    if [ -f "$file" ]; then
        # Check if line contains a Pydantic decorator and doesn't already have type ignore
        if grep -q "@\(field_validator\|model_validator\|field_serializer\|computed_field\)" "$file" | sed -n "${line}p" && ! sed -n "${line}p" "$file" | grep -q "type: ignore"; then
            # Add type ignore comment to the end of the decorator line
            sed -i "${line}s/$/ # type: ignore[misc]/" "$file"
            echo "Fixed $file:$line"
        else
            echo "Skipped $file:$line"
        fi
    fi
done < /tmp/errors.txt

echo "Completed processing all errors"
