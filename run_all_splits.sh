#!/bin/bash
# Run all 20 test splits in parallel batches
# Batch size: 5 splits at a time to avoid system overload

BATCH_SIZE=5
TOTAL_SPLITS=20
OUTPUT_DIR="test_split_results"

echo "Starting parallel test execution: $TOTAL_SPLITS splits in batches of $BATCH_SIZE"
echo "=================================================================="

# Function to run a single split
run_split() {
    local split_num=$1
    echo "[Split $split_num/$TOTAL_SPLITS] Starting..."

    poetry run pytest tests/ \
        --splits $TOTAL_SPLITS \
        --group $split_num \
        --tb=short \
        -v \
        2>&1 | tee "$OUTPUT_DIR/split_${split_num}_output.txt"

    local exit_code=$?
    echo "[Split $split_num/$TOTAL_SPLITS] Completed with exit code: $exit_code"
    return $exit_code
}

# Run splits in batches
for ((batch_start=1; batch_start<=TOTAL_SPLITS; batch_start+=BATCH_SIZE)); do
    batch_end=$((batch_start + BATCH_SIZE - 1))
    if [ $batch_end -gt $TOTAL_SPLITS ]; then
        batch_end=$TOTAL_SPLITS
    fi

    echo ""
    echo "==================================================================="
    echo "Running batch: splits $batch_start to $batch_end"
    echo "==================================================================="

    # Start splits in parallel
    pids=()
    for ((i=batch_start; i<=batch_end; i++)); do
        run_split $i &
        pids+=($!)
    done

    # Wait for all splits in this batch to complete
    echo "Waiting for batch to complete..."
    for pid in "${pids[@]}"; do
        wait $pid
    done

    echo "Batch complete: splits $batch_start to $batch_end"
done

echo ""
echo "==================================================================="
echo "All splits completed. Results saved to $OUTPUT_DIR/"
echo "==================================================================="
