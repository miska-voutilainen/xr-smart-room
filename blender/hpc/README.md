# Rendering the Blender scene on a GPU cluster (Torque/PBS + Singularity)

Published copy, redacted: account names, hosts, keys and usage figures are placeholders.
The scripts were used on RTU's HPC cluster with NVIDIA L40S cards; any Torque/PBS cluster with Singularity works.

| file | what |
|---|---|
| `Dockerfile` | Ubuntu 24.04 + the X11/GL libs Blender links against + the official Blender 5.2.2 Linux tarball |
| `render.sh` | the PBS job: pins the GPU, picks the Cycles device, renders a frame range |
| `worker.sh` | long-lived PBS job that renders tasks dropped into a queue dir, so each render skips the queue wait |
| `submit` | workstation side: packs the .blend, copies it through a jump host, submits, waits, fetches the frames |

## Placeholders to fill in

- `<HPC_USER>` in the `#PBS -o /home/<HPC_USER>/...` lines of `render.sh` and `worker.sh` (PBS directives cannot
  read environment variables; the path must be absolute).
- `PI_HOST`: environment variable for `submit`, the ssh alias of the jump host. On that host an ssh alias `hpc` must
  point at the cluster login node (user, key, hostname live in that host's `~/.ssh/config`, never in this repo).

## Measured (2026-10-13)

One L40S, `main.blend` hero camera, 1920x1080, 512 adaptive samples, OIDN denoise, compositor:
61.8 s render, 67.5 s for the whole Blender process, 1.9 GB of GPU memory. CUDA works; OptiX is listed but untested.

## SSH

Keep a single master connection to the login node and run everything through it (`ssh -M -S <socket>`,
`ControlPersist`). Login nodes may rate-limit or block hosts that open many SSH connections.

## One-time setup: the image

```bash
cd hpc
curl -O https://download.blender.org/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz
curl -s https://download.blender.org/release/Blender5.2/blender-5.2.2.sha256 | grep linux-x64 | sha256sum -c -
podman build -t localhost/blender:5.2.2 .
podman save --format docker-archive localhost/blender:5.2.2 | gzip -1 > blender-5.2.2.tar.gz   # ~1 GB
```

On the cluster, in `~/blender-test`:

```bash
gunzip -f blender-5.2.2.tar.gz
module load singularity
singularity build blender-5.2.2.sif docker-archive://blender-5.2.2.tar
rm blender-5.2.2.tar
```

## Each render

`PI_HOST=<jump host> hpc/submit <file.blend> <tag> [CAM=Cam_122209] [SAMPLES=64] [PCT=50]`
blocks until done and writes `renders/hpc/<tag>/frame_0001.png` + `log.txt`.

`render.sh` knobs, through `qsub -v`: `START`, `END` (default 1, 1), `BLEND` (default `main.blend`),
`DEVICE` (`CUDA` default, or `OPTIX`), `CAM`, `SAMPLES`, `PCT`, `OUT`.

## Gotchas

- `#PBS -o` must be an absolute path: a relative one resolves against the submit directory and the log can be lost.
- Pin the GPU: `CUDA_VISIBLE_DEVICES` arrives empty in a job and the node runs other users' jobs on the other cards.
  `render.sh` sets it from `PBS_GPUFILE`.
- Cycles device prefs do not persist in `-b`: `render.sh` sets the device every run and fails if it is missing.
- Blender 5.2.2 ships `sm_86` cubins (used on the L40S, sm_89) and a `compute_75` PTX (compiled on first use elsewhere).
- `EGL Error (0x3009)` lines are harmless in background mode.
- Singularity starts in `$HOME`, not the image's `WORKDIR`: `render.sh` uses absolute paths.
- External images must be packed before upload (`submit` does it per image).
