#!/bin/bash

# Number of additional batches to run (current one is Batch 1)
EXTRA_BATCHES=2

echo "🔄 Queueing system started. Will run $EXTRA_BATCHES more batches."

for ((i=1; i<=EXTRA_BATCHES; i++)); do
    echo "⏳ [Batch $i/$EXTRA_BATCHES] Waiting for current job 'data-gen-parallel' to complete..."
    
    # Wait for completion (timeout 6 hours per batch)
    kubectl wait --for=condition=complete job/data-gen-parallel -n heimr-core --timeout=21600s
    
    if [ $? -ne 0 ]; then
        echo "❌ Job failed or timed out. Stopping queue."
        exit 1
    fi
    
    echo "✅ Batch complete. Cleaning up..."
    kubectl delete job data-gen-parallel -n heimr-core
    
    # Optional: Wait a moment for pods to terminate fully
    sleep 30
    
    echo "🚀 Starting next batch..."
    kubectl apply -f k8s/base/pipeline/job-parallel.yaml
    
    echo "✅ Batch submitted."
done

echo "🎉 All batches completed! We should have ~12k files now."
