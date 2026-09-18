# Academic Distributed-Algorithm Pseudocode Style Guide (Event-Driven Algol/Pascal Tradition)

## 1. Style Positioning

- **Paradigm**: Event-driven state machine, used to describe distributed algorithms such as network protocols, switch/Worker coordination, and collective communication (AllReduce).
- **Syntactic lineage**: Inherits the Algol/Pascal tradition, emphasizing readability and proof-friendliness over executability.
- **Core goal**: Clearly express the complete logic of "state initialization → event triggering → state transition → network primitives".

## 2. Basic Syntax Rules

### 2.1 Variables and Scope

- Types are inferred implicitly; no type keywords are declared.
- **Arrays / multidimensional tables**: dimensions are declared with square brackets, subscripts separated by commas.
  - Examples: `pool[2, s]`, `seen[2, s, n]`, `count[s]`
- **Field access**: packet/message fields use the dot `p.field`.
  - Examples: `p.idx`, `p.wid`, `p.ver`, `p.vector`, `p.off`

### 2.2 Assignment and Initialization (Strictly Distinguished)

| Symbol | Meaning | Example |
| ------ | ------ | ------ |
| `<-` | **The sole assignment operator** (left arrow) | `pool[p.idx] <- pool[p.idx] + p.vector` |
| `:= {0}` | **Bulk initialization** (zeroing arrays/variables) | `pool[s], count[s] := {0}` |
| `=` | **Equality comparison** (since `<-` already occupies assignment) | `if count[p.idx] = 0 then` |

- The initialization block allows multiple variables side by side: `pool[2, s], count[2, s], seen[2, s, n] := {0}`

### 2.3 Arithmetic and Logical Operators

- **Multiplication**: must use the middle dot `·` (Unicode U+00B7); `*` or `×` is forbidden.
  - Examples: `k·i`, `p.off + k·s`
- **Modulo**: `%`
- **Logical**: keyword forms `and`, `or`, `not`; do not use `&&` / `||` / `!`
- **Comparison**: `=` (equal), `!=` (not equal), `<`, `>`, `<=`, `>=`

### 2.4 Control Flow

- **Conditional**: `if condition then ... else ...`
  - `then` and `else` are explicit keywords and may not be omitted.
  - Branches for true/false conditions use indentation; do not use `begin/end` or braces.
- **Counting loop**: `for i in start:end do ...` (both endpoints inclusive; step defaults to 1)
- **Infinite / event loop**: `repeat ... until condition` (executed at least once)

### 2.5 Array Slicing and Vector Operations

- **Slice syntax**: `U[p.off : p.off+k]` (keep spaces around the colon)
- **Vector addition**: implicit element-wise addition, using `+` directly.
  - Example: `pool[p.ver, p.idx] <- pool[p.ver, p.idx] + p.vector`

## 3. Event-Driven Structure (Core Framework)

The body of an algorithm consists of **state initialization** and **event handlers**; no conventional `main()` entry is allowed.

### 3.1 State Initialization Block

```text
Initialize State:
  n = number of workers
  pool[s], count[s] := {0}
```

- Write `Initialize State:` flush left; subsequent state variables are indented and aligned.
- Natural language is allowed to describe constants, e.g. `n = number of workers`.

### 3.2 Event Handlers

| Event Type | Syntax Template |
| -------- | -------- |
| Packet received | `upon receive packet p(field1, field2, ...) :` |
| Timeout | `upon timeout p /* Handler Label */ :` |

- **Parameter list**: fields of the packet are declared in parentheses after the event name, e.g. `p(wid, ver, idx, off, vector)`.
- **Handler label**: handlers such as timeouts may be annotated with `/* Comment */` after the parameters.
- Logic inside an event handler is uniformly indented; branches stay aligned.

## 4. Network Primitives (First-Class Operations)

The following keywords are used directly as statements; they are not treated as function calls and take no parentheses:

| Primitive | Semantics | Example |
| ------ | ------ | ------ |
| `send p` | Unicast send | `send p` |
| `multicast p` | Multicast/broadcast the aggregation result | `multicast p` |
| `forward p to dst` | Unicast forward to the specified destination | `forward p to p.wid` |
| `drop p` | Drop the current packet | `drop p` |
| `recieve p(...)` | Receive event (an event keyword, not an active call) | `upon receive p(idx, off, vector)` |

## 5. State Management Conventions

### 5.1 Two-Version Ping-Pong (Reliable Transmission)

- Use the binary version number `ver ∈ {0, 1}`, toggled via `(p.ver+1)%2`.
- State tables are partitioned by version dimension: `pool[2, s]`, `count[2, s]`, `seen[2, s, n]`.

### 5.2 Mod-n Counting Trick

- Counters increment with `% n`; **returning to 0 means "exactly all received"**.

  ```text
  count[p.ver, p.idx] <- (count[p.ver, p.idx] + 1) % n
  if count[p.ver, p.idx] = 0 then
    // aggregation complete
  ```

### 5.3 Bitmap Deduplication

- `seen[ver, idx, wid]` records whether a particular worker has already contributed.
- When a new version is set, **clear the old-version bitmap in the same step** to prepare for the next round:

  ```text
  seen[p.ver, p.idx, p.wid] <- 1
  seen[(p.ver+1)%2, p.idx, p.wid] <- 0
  ```

## 6. Naming Conventions

| Category | Style | Example |
| ------ | ------ | ------ |
| State variables | lowercase full words, descriptive | `pool`, `count`, `seen`, `timer` |
| Packets/messages | single letter `p` or `pkt` | `p` |
| Packet fields | lowercase abbreviations | `idx`, `off`, `ver`, `wid`, `vector` |
| Global data/matrices | uppercase single letters or abbreviations | `U`, `A` |
| Constants/parameters | uppercase single letters | `k` (chunk size), `s` (number of slots), `n` (number of nodes) |
| Index variables | single letters | `i`, `j` |

## 7. Comments and Typography

- **End-of-line comments**: use `// comment text`, to explain the intent of the algorithm.
- **Handler labels**: use `/* Label */`, e.g. `/* Timeout Handler */`.
- **Indentation**: use 2 spaces (in examples it may look like 2 spaces or aligned tab stops; unify to 2 spaces).
- **Blank lines**: separate event handlers with blank lines to improve readability.

## 8. Complete Example Template

The following template demonstrates all syntax and structural rules; newly generated algorithms should follow the same pattern:

```text
Initialize State:
  n = number of workers
  s = number of slots
  k = chunk size
  pool[2, s], count[2, s], seen[2, s, n] := {0}

upon receive packet p(wid, ver, idx, off, vector):
  if seen[p.ver, p.idx, p.wid] = 0 then
    seen[p.ver, p.idx, p.wid] <- 1
    seen[(p.ver+1)%2, p.idx, p.wid] <- 0
    count[p.ver, p.idx] <- (count[p.ver, p.idx] + 1) % n
    if count[p.ver, p.idx] = 1 then
      pool[p.ver, p.idx] <- p.vector
    else
      pool[p.ver, p.idx] <- pool[p.ver, p.idx] + p.vector
    if count[p.ver, p.idx] = 0 then
      p.vector <- pool[p.ver, p.idx]
      multicast p
    else
      drop p
  else
    if count[p.ver, p.idx] = 0 then
      p.vector <- pool[p.ver, p.idx]
      forward p to p.wid
    else
      drop p

upon timeout p /* Timeout Handler */:
  send p
  start_timer(p)
```
