# Find the normalized range containing an address

For a `netipx.IPSet`, this example returns the containing normalized range and
its index into a prepared sorted snapshot. Use that index for diagnostic values
assigned to the normalized ranges. It uses the public `Ranges()` and
`IPRange.Contains()` APIs; no upstream change is needed.

## Run

With Go installed, run from this directory:

```sh
go test ./...
go run ./cmd/example
go run ./cmd/example 192.0.2.7 2001:db8::b 192.0.2.9
```

The example builds arbitrary inclusive IPv4 and IPv6 ranges, including overlaps,
adjacent ranges and removals. It prints the normalized snapshot and then the
query results. The last command ends with:

```text
192.0.2.7 -> index=0 range=192.0.2.3-192.0.2.8 label="segment-0"
2001:db8::b -> index=4 range=2001:db8::b-2001:db8::11 label="segment-4"
192.0.2.9 -> no match
```

Malformed addresses are reported on stderr, other queries still run, and the
built executable exits with status 2. A valid address outside the set is an
ordinary no-match result.

## Use the helper

Import this example as `lookup` and `go4.org/netipx`:

```go
import (
    "fmt"
    "net/netip"

    lookup "github.com/tevinch/offering-help/examples/containing-range"
    "go4.org/netipx"
)
```

Prepare once after building your set:

```go
var builder netipx.IPSetBuilder
builder.AddRange(netipx.MustParseIPRange("192.0.2.3-192.0.2.8"))
builder.AddRange(netipx.MustParseIPRange("192.0.2.9-192.0.2.12"))
set, err := builder.IPSet()
if err != nil {
    panic(err)
}

index := lookup.New(set)
// These two adjacent inputs became one normalized range.
labels := []string{"combined segment"}

r, i, found := index.Find(netip.MustParseAddr("192.0.2.7"))
if found {
    fmt.Printf("%v index=%d label=%q\n", r, i, labels[i])
    // 192.0.2.3-192.0.2.12 index=0 label="combined segment"
}
```

`index.Ranges()` returns an inspection copy in the same order as the returned
indices. Assign one sidecar value per range in that snapshot. `New` takes the
snapshot once; `Find` performs a binary search in O(log r) time for r normalized
ranges. The measured lookups allocate no memory. Creating another set may
change the range order or count, so create its index and sidecar values together.

A miss returns an invalid range, index `-1`, and `false`. Empty indices and a nil
source set behave as empty sets. Queries keep native address semantics:
IPv4-mapped IPv6 addresses are not implicitly converted to IPv4, and scoped IPv6
addresses and invalid addresses do not match.

## Normalized labels and original labels

Normalization does not preserve source boundaries. For example:

```text
source-A: 192.0.2.3-192.0.2.4
source-B: 192.0.2.5-192.0.2.6

normalized[0]: 192.0.2.3-192.0.2.6
```

Addresses from either source return index 0. The resulting set is identical to
one built from a single `192.0.2.3-192.0.2.6` input. The original labels are not
stored in the set and cannot be recovered from it. This helper's sidecars are
assigned **after normalization**. Keep original metadata separately and define
how overlapping, merged or split inputs combine if you need source-level labels.

## Verification and version

The example pins the current published module pseudo-version
`go4.org/netipx v0.0.0-20260823151212-3075585bcbeb`; it is not a tagged stable
release. Scripted checks passed with Go 1.27.2 on macOS arm64.

The eight top-level tests check exact normalized ranges and indices, sidecar
selection, endpoints and gaps, 512 native membership comparisons across both
address families, mapped/zoned/invalid cases, snapshot and input preservation,
repeated lookups, the merge counterexample, and complete executable-example
output. A separate clean-copy build and native CLI check verified the actual
process output; a wrong-index mutation failed that output check even though
the process exited successfully. These checks do not establish adoption or
performance on another application's data.

See the official [`IPSet.Ranges`](https://pkg.go.dev/go4.org/netipx#IPSet.Ranges)
and [`IPRange.Contains`](https://pkg.go.dev/go4.org/netipx#IPRange.Contains)
documentation. The helper is [MIT licensed](LICENSE); netipx retains its
[BSD-style license](https://github.com/go4org/netipx/blob/3075585bcbeb7a9f042662e543b03efe900018be/LICENSE).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
