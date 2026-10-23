package containingrange

import (
	"net/netip"
	"sort"

	"go4.org/netipx"
)

// Index holds a prepared copy of an immutable set's normalized ranges.
// Its zero value is an empty index.
type Index struct {
	ranges []netipx.IPRange
}

// New prepares an index once. A nil set produces an empty index.
func New(set *netipx.IPSet) Index {
	if set == nil {
		return Index{}
	}
	return Index{ranges: set.Ranges()}
}

// Ranges returns an inspection copy in the order used by Find's indices.
// Assign sidecar values to this normalized order after building the set.
func (x Index) Ranges() []netipx.IPRange {
	return append([]netipx.IPRange(nil), x.ranges...)
}

// Find returns the containing normalized range and its snapshot index.
// A miss returns an invalid range, -1, false.
func (x Index) Find(addr netip.Addr) (netipx.IPRange, int, bool) {
	if !addr.IsValid() || addr.Zone() != "" {
		return netipx.IPRange{}, -1, false
	}
	// Normalized ranges have increasing upper bounds and do not overlap.
	i := sort.Search(len(x.ranges), func(i int) bool {
		return x.ranges[i].To().Compare(addr) >= 0
	})
	if i < len(x.ranges) && x.ranges[i].Contains(addr) {
		return x.ranges[i], i, true
	}
	return netipx.IPRange{}, -1, false
}
