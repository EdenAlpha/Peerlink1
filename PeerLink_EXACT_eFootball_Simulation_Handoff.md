# PeerLink — EXACT eFootball Simulation Core Handoff

You are taking over the PeerLink eFootball synthetic-opponent project.

## ABSOLUTE REQUIREMENT

The target is **NOT** a similar football simulator, a close approximation, a visually equivalent simulation, or a deterministic engine that only agrees with itself.

The target is:

> **THE EXACT SAME RELEVANT eFOOTBALL SIMULATION.**

Meaning:

```text
same initial eFootball state
+ same RNG state
+ same ordered controller/gameplay commands
+ same update order
+ same simulation-critical native routines
=
same resulting football world state
```

If stock eFootball says the ball is at X, player 7 is at Y, action state is Z and RNG state is R, PeerLink must arrive at X, Y, Z and R too. Not approximately. Not “close enough.” Any unexplained divergence is a failure until resolved.

The core principle is:

> **What happens in stock eFootball must happen in PeerLink’s shadow simulation as well.**

---

# PRIMARY STRATEGY

Do **not** rebuild eFootball from scratch if the original simulation code can be executed.

Preferred route:

```text
eFootball libUE4.so
│
├── graphics                 DROP
├── camera                   DROP
├── UI                       DROP
├── audio                    DROP
├── crowd/stadium rendering  DROP
├── presentation             DROP
│
└── deterministic gameplay simulation
      ├── command processing
      ├── player locomotion
      ├── player actions
      ├── ball physics
      ├── collisions/contact
      ├── traps/possession
      ├── passes/shots/tackles
      ├── root motion if gameplay-critical
      ├── off-ball movement
      ├── team positioning
      ├── switching
      ├── stamina/attributes if critical
      ├── RNG
      └── match update/tick
```

The objective is:

> **Find the real gameplay engine already inside `libUE4.so`, isolate its simulation-critical dependency closure, and execute that original ARM64 code headlessly.**

Do not voluntarily translate hundreds of Konami routines into new equations if direct native execution works.

---

# EXACT BUILD

Target Android build:

```text
package: jp.konami.pesam
versionName: 11.0.1
versionCode: 311000101
```

Exact `libUE4.so`:

```text
SHA-256:
2ac4ff17ac8ad713d9531c2601e38a3c8335e02ea882ba2dc4445c191c1298cd

Build ID:
f18d381f3b4e9aa1db097227b1fbb670
```

Known prior lab path:

```text
/mnt/data/efootball_lab/extracted/libUE4.so
```

If not present, recover this exact build and verify the hash before trusting offsets.

---

# MAJOR BREAKTHROUGH ALREADY ACHIEVED

Another AI successfully proved that **original Konami simulation code can execute headlessly**.

The original ball physics kernel:

```text
0x6ea0958
```

was executed outside the full game under a custom ARM64 Unicorn harness.

This is the most important fact to preserve.

It means this strategy is viable:

```text
original Konami simulation code
+
minimal compatibility environment
-
graphics/audio/UI/full Unreal presentation
```

Do **not** retreat back to “write our own football engine.”

---

# ORIGINAL BALL ENGINE ALREADY ISOLATED

Live ball has two consecutive 296-byte state buffers:

```text
ball + 0x030
ball + 0x158
```

Each is:

```text
0x128 = 296 bytes
```

Both initialized by:

```text
0x6d82418
```

Known/strong state layout:

```text
BallPhysicsState

+0x000  Vec3 position                 PROVEN
+0x00C  Vec3 linear velocity          PROVEN
+0x018  Vec3 angular/rotational state STRONG/near-proven
+0x028  timer-like state
...
+0x090  physics state byte
+0x091  physics substate byte
+0x094  state/index
+0x098  Quaternion orientation        PROVEN
...
+0x128  end
```

Native chain:

```text
BallPhysicsState
  ↓
0x6ea1e90
  ↓
0x6ea20fc
  ↓
0x6ea0958
```

Reported headless execution result:

```text
dependency closure:
~118 functions
~12.7 KB code

0 indirect calls in the kernel closure
```

This is excellent news. One real simulation subsystem is already compact enough to isolate.

---

# EXACT BALL TIMESTEP

Native code returns:

```text
27.0
```

then computes:

```text
dt = 1.0 / 27.0
```

before calling the ball physics kernel.

Therefore the ball physics **substep** is native-proven as:

```text
1/27 second
```

Do not assume replay sample Hz is also 27. Determine the relationship between outer match update, replay record rate, and number of 1/27 ball substeps by tracing the live scheduler.

---

# BALL PHYSICS BEHAVIOR ALREADY PROVEN HEADLESS

The original kernel was run with results consistent with native constants:

```text
gravity ≈ 9.80665
ground contact height = 0.1086859330534935
air drag active
Magnus/spin active
ground clamp active
```

This was not a reimplementation. It was execution of original eFootball machine code.

That is the model for the rest of the project.

---

# DO NOT WASTE TIME CRACKING WESYS AGAIN

The PESDB `FF 22 83 WESYS` format was already solved.

For the `0x22` variant:

```text
x = 0xED5B2960
y = 0x4A523B4E
z = 0xF3A31BAD

w = ((orig_size << 16) | comp_size) & 0xFFFFFFFF
```

For each complete 32-bit payload word:

```python
t = (x ^ (x << 11)) & 0xFFFFFFFF

x, y, z, prev = y, z, w, w

w = (
    prev
    ^ (((prev >> 11) ^ t) >> 8)
    ^ t
) & 0xFFFFFFFF

payload_word ^= w
```

Trailing 1–3 bytes remain plaintext.

Then:

```text
zlib decompress
```

This successfully decoded current eFootball database files in prior work.

**Use this immediately. Do not rediscover it.**

---

# DATABASE/ASSET KNOWLEDGE

Current decoded/known data includes:

```text
Player.bin
PlayerSkill.bin
Playstyle.bin
Tactics.bin
TacticsFormation.bin
Team.bin
CoachTactics.bin
CoachTacticsFormation.bin
```

Known current structures included:

```text
Team.bin:
981 × 1600-byte records

Tactics.bin:
1780 × 12-byte records

TacticsFormation.bin:
19580 × 12-byte records
= 11 formation entries per tactics entry
```

Use these for exact team/player/tactical initialization when needed.

---

# REPLAY ORACLE — CRITICAL

Tutorial `.rep/.trep` files are the ground-truth state oracle.

Native-proven `.rep`:

```text
44,400-byte header
+
1,200 × 10,976-byte state records
```

Exact:

```text
44,400 + 1200×10,976 = 13,215,600
```

Each 10,976-byte state:

```text
808 bytes global/special state
+
31 × 328-byte entity blocks
```

Exact:

```text
808 + 31×328 = 10,976
```

The first 22 entity blocks map to the 22 players.

Therefore every sample provides:

```text
22 × 328-byte exact player replay states
```

Use this for differential verification.

---

# EXACT PLAYER REPLAY POSITION

Inside each 328-byte player state:

```text
+0xB6 signed int16 X
+0xB8 signed int16 Y
+0xBA signed int16 Z
```

Decode:

```text
coordinate = signed_int16 / 256.0
```

The native writer uses float × 256 followed by signed conversion/truncation/clamping.

A second 3D vector exists around:

```text
+0xC4
+0xC6
+0xC8
```

also `/256`.

Do not invent semantics for unknown fields. Trace writers and consumers.

---

# BALL REPLAY STATE

Inside global replay state:

```text
global +0x2D4
global +0x2F0
global +0x30C
```

are three 28-byte ball-related slots.

Active ball representation includes approximately:

```text
+00..0F  quaternion
+10      int16 X
+12      int16 Y
+14      int16 Z
+16      slot/type byte
+17      player-reference byte
+18..    flags
```

XYZ decode using `/256`.

The byte at `+0x17` is native-proven to use global player indexing:

```text
side * 11 + localPlayer
```

giving 0..21 or 255 for none/invalid.

Do not call it “owner” unless the exact producer/consumer proves that semantic.

---

# REPLAY WRITERS

Player path around:

```text
0x6f4625c
→
0x728d7e0
```

Ball path around:

```text
0x6e94cec
→
0x728d930
```

Ball replay position comes from:

```text
LiveBall +0x30
```

which is the start of the real 296-byte BallPhysicsState.

Ball replay quaternion comes from:

```text
LiveBall +0xC8
```

which equals:

```text
0x30 + 0x98
```

—the orientation quaternion inside that same live physics state.

This gives a direct bridge:

```text
original live simulation state
→ original simulation code
→ native replay serializer
→ .rep ground truth
```

---

# `.trep`

Native-proven format:

```text
12-byte header
+
1,200 × 844-byte records
```

Use `.trep` for action/trajectory context alongside `.rep`.

Controlled tutorial actions include clearing, dribbling, matchup, passing, shooting, sliding, tackling, through-pass and switch-sides.

---

# COMMAND SYSTEM

Known online command architecture:

```text
24 controller slots

each slot:
0xB4 = 180 bytes
```

There are approximately 11 compact tagged event/command subchannels inside each slot.

A previous claim that the native system used one universally proven “5-byte MatchCommand” was wrong. Do not repeat it.

Continue tracing:

```text
network/P2P
→ compact tagged command
→ 180-byte controller state
→ gameplay consumer
```

Recover exact meanings for movement, sprint, pass, through-pass, lofted pass, shoot, clear, tackle, matchup, switching, and press/hold/release semantics.

---

# MOST IMPORTANT NEXT TARGET: FULL MATCH SIMULATION TICK

The ball proof is done.

Now climb upward and find the smallest original Konami function/object that advances the **entire deterministic football world**.

Look around:
- `ProcessMatchMain.cpp`
- replay writer callers
- live player update
- live ball update
- MatchOnline command consumer
- frame/update counter
- per-player loops
- team/off-ball logic

You want the equivalent of:

```text
MatchSimulation::Update(commands, dt)
```

even if that is not its actual name.

Once found:

1. Build its transitive dependency graph.
2. Classify dependencies as KEEP / STUB / DROP.
3. Preserve only deterministic simulation dependencies.

---

# KEEP / STUB / DROP RULE

## KEEP
Anything capable of changing deterministic match state:

```text
command processing
player movement
player action states
ball physics
collisions
contact
possession/trapping
passes
shots
tackles
team/off-ball movement
player switching
RNG
simulation timing
root-motion if gameplay-relevant
animation-state pieces if collision/contact depends on them
```

## DROP
Pure presentation:

```text
renderer
GPU
materials
textures
stadium graphics
crowd graphics
camera
UI
menus
audio
presentation effects
```

## STUB
Systems required only to satisfy dependencies but not alter gameplay state:

```text
logging
telemetry
analytics
UI callbacks
unused online backend pieces
presentation callbacks
```

Do not strip something merely because it sounds visual. If root motion/contact depends on animation state, keep the simulation portion without rendering it.

---

# PREFERRED EXECUTION ROUTES

## Route A — best
Execute the original gameplay routines on ARM64 Android directly, using a minimal JNI/native harness if practical.

## Route B — already proven feasible
Use a custom loader/emulator such as Unicorn. The original ball kernel already works this way. Extend that strategy upward.

## Route C — last resort
Operation-for-operation lift/reimplementation only when a specific original routine genuinely cannot be executed in isolation.

Do not default to Route C.

---

# BUILD A DEPENDENCY CLOSURE, NOT A NEW ENGINE

The winning architecture should look like:

```text
Original libUE4.so gameplay code
            │
            ├─ simulation-critical closure
            │       ↓
            │   headless harness
            │
            └─ everything else ignored/stubbed
```

The goal is not necessarily to physically carve a new `.so` immediately.

First prove:

```text
minimal runtime
+
original match tick
+
real state
+
real commands
=
native next state
```

Then optimize packaging.

---

# EXACTNESS ACCEPTANCE TEST

The final test is not “it runs.”

It is:

```text
Konami:
S0 + C0 → S1
S1 + C1 → S2
S2 + C2 → S3

PeerLink headless native core:
S0 + C0 → S1'
S1' + C1 → S2'
S2' + C2 → S3'
```

Required:

```text
S1' == S1
S2' == S2
S3' == S3
...
```

Use raw replay bytes, decoded player/ball states, checksums and first-divergence reports.

If there is a mismatch, report:

```text
sample N
entity/player
offset
expected raw
actual raw
expected decoded
actual decoded
```

Then trace the responsible missing state/routine.

**No unexplained mismatch is acceptable.**

---

# RNG IS MANDATORY

Exact equality requires exact RNG.

Find:
- algorithm
- state location
- seed initialization
- per-match seed
- consumption order
- relationship to any `RP_RAND_SEED` network/session value

If original full match routines are executed, preserving original RNG call order becomes much easier.

Do not fake RNG.

---

# PLAYER ENGINE IS THE NEXT MAJOR PROOF

The next concrete milestone should be:

> **Original Konami player locomotion/action code executes headlessly.**

Use controlled tutorials:
- dribbling for movement
- passing for movement + kick
- matchup/tackling for defensive actions

Input:

```text
real initial player state
real command state
real parameters
```

Run original native code.

Compare against the next 328-byte `.rep` player block.

---

# THEN FULL MATCH TICK

After ball + player:

```text
original command system
+
original player engine
+
original ball engine
+
original collision/contact
+
original team logic
+
original RNG
```

Then run the highest-level deterministic update function.

Target:

```text
exact initial state
+
exact commands
+
original stripped native tick
=
exact next eFootball state
```

Repeat across a full tutorial sequence, then a real P2P match.

---

# DO NOT WASTE TIME

Do NOT:
- crack WESYS again
- write another generic football engine
- fit physics constants by eye
- call visual similarity “success”
- spend the session describing architecture without executing code
- rebuild the ball kernel when original execution already works
- polish PeerLink AI yet
- work on room creation yet
- accept “close enough”

---

# REQUIRED WORK STYLE

Aggressively pursue exact equivalence.

For every subsystem ask:

> Can I execute the original Konami routine?

For every dependency ask:

> Does this affect deterministic match state?

For every claim ask:

> What native/replay evidence proves it?

Maintain:

```text
PROVEN
HIGH CONFIDENCE
HYPOTHESIS
RETRACTED
```

Correct mistakes immediately. Do not build on false leads.

---

# WHAT COUNTS AS A REAL BREAKTHROUGH

Examples:

```text
Original player locomotion routine executes headlessly
```

```text
Original command processor consumes reconstructed controller state
```

```text
Minimal dependency closure for full player update recovered
```

```text
Original match-level update executes without renderer/audio/UI
```

```text
One tutorial replay reproduces 1,200/1,200 state records exactly
```

```text
Real P2P command stream + same initial state keeps PeerLink native core synchronized with stock eFootball
```

That is success.

---

# FINAL VISION

PeerLink ultimately needs:

```text
Stock eFootball
      ↕
P2P commands
      ↕
PeerLink
  ├── exact stripped eFootball simulation
  ├── exact world state
  ├── strong adaptive AI
  └── exact command encoder
```

The simulation underneath PeerLink must be:

> **the same relevant deterministic eFootball simulation, not an imitation.**

What happens on stock eFootball must happen in PeerLink’s shadow world as well.

No shortcuts on exactness.

Start from the already-working original ball-kernel harness and climb upward until the original full deterministic match simulation can run headlessly.
