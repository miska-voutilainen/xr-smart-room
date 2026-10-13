import math
import matplotlib.pyplot as plt

# Room in cm, origin bottom-left, x right, y up.
W, H = 650, 250
PILLAR_W, PILLAR_H = 25, 20
LEFT_LOW, LEFT_TOP = 115, 40
DOOR = H - PILLAR_H - LEFT_TOP - LEFT_LOW  # opening, derived: labels on left don't close
LEAF = 85

assert PILLAR_W + 75 + 150 + 400 == W
assert 70 + 160 + 20 == H
assert PILLAR_H + LEFT_TOP + DOOR + LEFT_LOW == H and DOOR == 75

BG, FG = "#191919", "white"
fig, ax = plt.subplots(figsize=(13, 6), facecolor=BG)
ax.set_facecolor(BG)
line = dict(color=FG, lw=2, solid_capstyle="round")


def seg(x1, y1, x2, y2, **kw):
    ax.plot([x1, x2], [y1, y2], **{**line, **kw})


def label(x, y, s, **kw):
    ax.text(x, y, s, color=FG, fontsize=12, ha="center", va="center", **kw)


# Walls
seg(0, 0, W, 0)                      # bottom
seg(W, 0, W, H)                      # right
seg(0, H, W, H)                      # top
seg(0, 0, 0, LEFT_LOW)               # left, lower
seg(0, LEFT_LOW + DOOR, 0, H)        # left, upper (incl. pillar side)

# Pillar in top-left corner
seg(PILLAR_W, H, PILLAR_W, H - PILLAR_H, lw=3)
seg(0, H - PILLAR_H, PILLAR_W, H - PILLAR_H, lw=3)

# Door leaf, hinged at bottom of opening
dx = math.sqrt(LEAF**2 - DOOR**2)
seg(0, LEFT_LOW, dx, LEFT_LOW + DOOR)

# Segment ticks
t = 5
for x in (PILLAR_W + 75, PILLAR_W + 75 + 150):
    seg(x, H - t, x, H + t, lw=1.5)
for y in (H - 70, 20):
    seg(W - t, y, W + t, y, lw=1.5)

# Labels
label(PILLAR_W / 2 + 3, H - PILLAR_H - 8, "25")
label(PILLAR_W + 12, H - PILLAR_H / 2, "20")
label(PILLAR_W + 75 / 2, H - 10, "75")
label(PILLAR_W + 75 + 150 / 2, H - 10, "150")
label(PILLAR_W + 75 + 150 + 400 / 2, H - 10, "400")
label(12, H - PILLAR_H - LEFT_TOP + 8, "40")
label(dx / 2 + 10, LEFT_LOW + DOOR / 2, "85")
label(15, LEFT_LOW / 2, "115")
label(W - 15, H - 35, "70")
label(W - 18, 20 + 80, "160")
label(W - 15, 10, "20")
label(W / 2, -15, "650")

ax.set_aspect("equal")
ax.set_xlim(-20, W + 20)
ax.set_ylim(-30, H + 20)
ax.axis("off")
fig.savefig("room_plan.png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
