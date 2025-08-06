#!/bin/bash

# Activate virtual environment
cd /home/zakee/homeupdate
source venv/bin/activate

# Function to check Python files
check_python_files() {
    local dir_name=$1
    echo "\n🔍 Checking $dir_name files..."
    echo "================================"
    
    find . -name "$dir_name.py" -type f | while read -r file; do
        echo -n "Checking $file... "
        if python -m py_compile "$file" 2>/dev/null; then
            echo "✅ $file"
        else
            echo -e "\n❌ Error in $file:"
            python -m py_compile "$file"
            echo ""
        fi
    done
}

# Check models, views, and urls files
for dir_type in "models" "views" "urls"; do
    check_python_files "$dir_type"
done

echo "\n✅ All checks completed!"
