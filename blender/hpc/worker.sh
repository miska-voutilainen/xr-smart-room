#!/bin/bash
# Long-lived render worker: holds one L40S and renders tasks dropped by hpc/submit, so each render skips
# the ~10 min PBS queue wait. Costs ~0.37 units/h while held, idle or not. Exits after walltime or 45 min idle.
#   qsub worker.sh            (from ~/blender-test; hpc/submit --worker does this)
# Task = ~/blender-test/jobs/<tag>/ with scene.blend + env (VAR=val lines); hpc/submit creates queue/<tag>.ready.
# Claim is an atomic mv of the .ready file, so several workers can share the queue.
#PBS -N bworker
#PBS -q fast
#PBS -l nodes=1:ppn=8:gpus=1,feature=l40s,walltime=08:00:00,mem=16gb
#PBS -j oe
#PBS -o /home/<HPC_USER>/blender-test/out/
cd "$HOME/blender-test"
Q=$HOME/blender-test/queue; mkdir -p "$Q"
id=${PBS_JOBID%%.*}
idle=$(date +%s)
echo "worker $PBS_JOBID on $(hostname) start=$(date -Is)"
while [ $(( $(date +%s) - idle )) -lt 2700 ]; do
  touch "$Q/.alive_$id"
  for r in "$Q"/*.ready; do
    [ -e "$r" ] || continue
    t=$(basename "$r" .ready)
    mv "$r" "$Q/$t.claimed_$id" 2>/dev/null || continue
    echo "task $t $(date -Is)"
    ( set -a; . "jobs/$t/env"; bash render.sh ) > "jobs/$t/log.txt" 2>&1
    touch "jobs/$t/done"; rm -f "$Q/$t.claimed_$id"
    idle=$(date +%s)
  done
  sleep 3
done
rm -f "$Q/.alive_$id"
echo "worker idle, exit $(date -Is)"
