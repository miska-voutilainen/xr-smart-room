#!/bin/bash
# Render frames of a .blend with Blender 5.2.2 (container) on one GPU of RTU's HPC cluster Rudens.
# Submit from ~/blender-test on the cluster:
#   qsub render.sh                                    frame 1 of main.blend, CUDA
#   qsub -v START=1,END=50 render.sh                  frames 1..50 in one job
#   qsub -v BLEND=other.blend,DEVICE=OPTIX render.sh  OPTIX is listed on driver 550 but untested
#   qsub -v BLEND=jobs/t/x.blend,OUT=jobs/t,CAM=Cam_122209,SAMPLES=64,PCT=50 render.sh   (what hpc/submit does)
# Frames land in ~/blender-test/$OUT/frame_####.png (OUT default out), the log in ~/blender-test/out/blender.o<jobid>.
#PBS -N blender
#PBS -q fast
#PBS -l nodes=1:ppn=8:gpus=1,feature=l40s,walltime=02:00:00,mem=16gb
#PBS -j oe
#PBS -o /home/<HPC_USER>/blender-test/out/
cd "$HOME/blender-test"
source /etc/profile.d/modules.sh
module load singularity
export START=${START:-1} END=${END:-1} BLEND=${BLEND:-main.blend} DEVICE=${DEVICE:-CUDA} OUT=${OUT:-out} CAM=${CAM:-} SAMPLES=${SAMPLES:-} PCT=${PCT:-}

# GPU pin: CUDA_VISIBLE_DEVICES arrives empty and the node runs other users' jobs on the other cards.
# Same rule as HPC-server's job.sh: uuid when the cgroup fence holds, PBS index otherwise.
mapfile -t uuids < <(nvidia-smi --query-gpu=uuid --format=csv,noheader 2>/dev/null)
if [ "${#uuids[@]}" -eq "$(grep -c . "$PBS_GPUFILE")" ]; then
  gpus=$(IFS=,; echo "${uuids[*]}")
else
  gpus=$(sed 's/.*-gpu//' "$PBS_GPUFILE" | paste -sd, -)
fi
export CUDA_VISIBLE_DEVICES=$gpus SINGULARITYENV_CUDA_VISIBLE_DEVICES=$gpus
echo "job=$PBS_JOBID node=$(hostname) gpus=$gpus blend=$BLEND frames=$START-$END device=$DEVICE start=$(date -Is)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

# Cycles device prefs do not persist in -b, so set them every run.
time singularity exec --nv --bind /scratch blender-5.2.2.sif /opt/blender/blender \
  -b "$BLEND" -t 8 --python-exit-code 1 --python-expr '
import os, bpy
kind = os.environ["DEVICE"]
p = bpy.context.preferences.addons["cycles"].preferences
p.compute_device_type = kind
p.get_devices()
for d in p.devices:
    d.use = d.type == kind
used = [d.name for d in p.devices if d.use]
print("USING", kind, used)
if not used:
    raise RuntimeError("no %s device found" % kind)
s = bpy.context.scene
s.cycles.device = "GPU"
if os.environ["CAM"]:
    c = bpy.data.objects[os.environ["CAM"]]
    s.camera = c
    if "res_x" in c:                       # photo cameras carry their own aspect (render/cameras.py)
        s.render.resolution_x, s.render.resolution_y = c["res_x"], c["res_y"]
    if "ev100" in c:                       # exposed like its photo, as render/_compare.py does
        s.view_settings.exposure += 9.34 - c["ev100"]
if os.environ["SAMPLES"]:
    s.cycles.samples = int(os.environ["SAMPLES"])
if os.environ["PCT"]:
    s.render.resolution_percentage = int(os.environ["PCT"])
print("CAM", s.camera.name, s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage, "SAMPLES", s.cycles.samples, "EXP %.2f" % s.view_settings.exposure)
' -o "$HOME/blender-test/$OUT/frame_####" -F PNG -s "$START" -e "$END" -a 2>&1 | grep -v "EGL Error\|Sample [0-9]"
echo "end=$(date -Is)"
