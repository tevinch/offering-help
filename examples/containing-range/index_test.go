package containingrange_test

import (
	"net/netip"
	"reflect"
	"testing"

	lookup "github.com/tevinch/offering-help/examples/containing-range"
	"go4.org/netipx"
)

func makeSet(t *testing.T) (*netipx.IPSet, []netipx.IPRange) {
	t.Helper()
	inputs := []netipx.IPRange{
		netipx.MustParseIPRange("192.0.2.3-192.0.2.8"),
		netipx.MustParseIPRange("192.0.2.7-192.0.2.12"),
		netipx.MustParseIPRange("192.0.2.13-192.0.2.17"),
		netipx.MustParseIPRange("192.0.2.30-192.0.2.32"),
		netipx.MustParseIPRange("2001:db8::3-2001:db8::8"),
		netipx.MustParseIPRange("2001:db8::7-2001:db8::c"),
		netipx.MustParseIPRange("2001:db8::d-2001:db8::11"),
	}
	original := append([]netipx.IPRange(nil), inputs...)
	var builder netipx.IPSetBuilder
	for _, r := range inputs {
		builder.AddRange(r)
	}
	builder.RemoveRange(netipx.MustParseIPRange("192.0.2.9-192.0.2.10"))
	builder.RemoveRange(netipx.MustParseIPRange("2001:db8::9-2001:db8::a"))
	set, err := builder.IPSet()
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(inputs, original) {
		t.Fatal("building the set changed the original inputs")
	}
	return set, inputs
}

func TestContainingNormalizedRangeAndIndex(t *testing.T) {
	set, _ := makeSet(t)
	index := lookup.New(set)
	wantRanges := []string{
		"192.0.2.3-192.0.2.8", "192.0.2.11-192.0.2.17", "192.0.2.30-192.0.2.32",
		"2001:db8::3-2001:db8::8", "2001:db8::b-2001:db8::11",
	}
	ranges := index.Ranges()
	if len(ranges) != len(wantRanges) {
		t.Fatalf("normalized ranges = %v", ranges)
	}
	for i, want := range wantRanges {
		if ranges[i].String() != want {
			t.Fatalf("normalized[%d] = %v, want %s", i, ranges[i], want)
		}
	}
	// Values belong to the normalized snapshot, not to the original input rows.
	labels := []string{"first", "second", "third", "fourth", "fifth"}
	cases := []struct {
		address string
		index   int
		label   string
	}{
		{"192.0.2.2", -1, ""}, {"192.0.2.3", 0, "first"}, {"192.0.2.7", 0, "first"},
		{"192.0.2.8", 0, "first"}, {"192.0.2.9", -1, ""}, {"192.0.2.10", -1, ""},
		{"192.0.2.11", 1, "second"}, {"192.0.2.17", 1, "second"}, {"192.0.2.18", -1, ""},
		{"192.0.2.29", -1, ""}, {"192.0.2.30", 2, "third"}, {"192.0.2.32", 2, "third"},
		{"192.0.2.33", -1, ""}, {"2001:db8::2", -1, ""}, {"2001:db8::3", 3, "fourth"},
		{"2001:db8::8", 3, "fourth"}, {"2001:db8::9", -1, ""}, {"2001:db8::a", -1, ""},
		{"2001:db8::b", 4, "fifth"}, {"2001:db8::11", 4, "fifth"}, {"2001:db8::12", -1, ""},
		{"::ffff:192.0.2.3", -1, ""}, {"2001:db8::3%example", -1, ""},
	}
	for _, tc := range cases {
		t.Run(tc.address, func(t *testing.T) {
			address := netip.MustParseAddr(tc.address)
			r, i, found := index.Find(address)
			if i != tc.index || found != (tc.index >= 0) {
				t.Fatalf("Find(%v) = %v, %d, %v; want index %d", address, r, i, found, tc.index)
			}
			if found && (r.String() != wantRanges[tc.index] || labels[i] != tc.label) {
				t.Fatalf("wrong range/sidecar: %v, %q", r, labels[i])
			}
			if !found && r.IsValid() {
				t.Fatal("miss returned a valid range")
			}
			if found != set.Contains(address) {
				t.Fatal("membership differs from IPSet.Contains")
			}
		})
	}
}

func TestNativeMembershipAcrossBothFamilies(t *testing.T) {
	set, _ := makeSet(t)
	index := lookup.New(set)
	for _, start := range []string{"192.0.2.0", "2001:db8::"} {
		address := netip.MustParseAddr(start)
		for n := 0; n < 256; n++ {
			r, _, found := index.Find(address)
			if found != set.Contains(address) || (found && !r.Contains(address)) {
				t.Fatalf("membership mismatch for %v", address)
			}
			address = address.Next()
		}
	}
}

func TestMappedAddressesKeepNativeSemantics(t *testing.T) {
	var builder netipx.IPSetBuilder
	builder.AddRange(netipx.MustParseIPRange("::ffff:192.0.2.3-::ffff:192.0.2.5"))
	set, err := builder.IPSet()
	if err != nil {
		t.Fatal(err)
	}
	index := lookup.New(set)
	for _, text := range []string{"::ffff:192.0.2.2", "::ffff:192.0.2.3", "::ffff:192.0.2.5", "::ffff:192.0.2.6", "192.0.2.3"} {
		addr := netip.MustParseAddr(text)
		_, _, found := index.Find(addr)
		if found != set.Contains(addr) {
			t.Fatalf("mapped membership mismatch for %s", text)
		}
		want := text == "::ffff:192.0.2.3" || text == "::ffff:192.0.2.5"
		if found != want {
			t.Fatalf("Find(%s) = %v, want %v", text, found, want)
		}
	}
}

func TestPreparedSnapshotIsIndependentAndReused(t *testing.T) {
	set, inputs := makeSet(t)
	index := lookup.New(set)
	original := set.Ranges()
	inputs[0] = netipx.MustParseIPRange("198.51.100.1-198.51.100.2")
	other := set.Ranges()
	other[0] = inputs[0]
	exposed := index.Ranges()
	exposed[0] = inputs[0]
	var later netipx.IPSetBuilder
	later.AddSet(set)
	later.Add(netip.MustParseAddr("192.0.2.100"))
	if _, err := later.IPSet(); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(set.Ranges(), original) || !reflect.DeepEqual(index.Ranges(), original) {
		t.Fatal("caller/builder changes mutated the set or prepared snapshot")
	}
	addr := netip.MustParseAddr("192.0.2.3")
	want := netipx.MustParseIPRange("192.0.2.3-192.0.2.8")
	if allocations := testing.AllocsPerRun(100, func() {
		r, i, ok := index.Find(addr)
		if !ok || i != 0 || r != want {
			t.Errorf("prepared lookup changed: %v, %d, %v", r, i, ok)
		}
	}); allocations != 0 {
		t.Fatalf("lookup allocated %v times per call", allocations)
	}
}

func TestEmptyInvalidAndZonedQueries(t *testing.T) {
	set, _ := makeSet(t)
	for _, index := range []lookup.Index{{}, lookup.New(nil), lookup.New(&netipx.IPSet{})} {
		if r, i, ok := index.Find(netip.MustParseAddr("192.0.2.3")); ok || i != -1 || r.IsValid() {
			t.Fatalf("empty lookup = %v, %d, %v", r, i, ok)
		}
	}
	for _, addr := range []netip.Addr{{}, netip.MustParseAddr("2001:db8::3%example")} {
		if r, i, ok := lookup.New(set).Find(addr); ok || i != -1 || r.IsValid() || set.Contains(addr) {
			t.Fatalf("invalid/zoned lookup = %v, %d, %v", r, i, ok)
		}
	}
}

func TestNormalizationCannotRecoverOriginalLabels(t *testing.T) {
	type source struct{ bounds, label string }
	inputs := []source{{"192.0.2.3-192.0.2.4", "source-A"}, {"192.0.2.5-192.0.2.6", "source-B"}}
	var adjacent, broad netipx.IPSetBuilder
	for _, row := range inputs {
		adjacent.AddRange(netipx.MustParseIPRange(row.bounds))
	}
	broad.AddRange(netipx.MustParseIPRange("192.0.2.3-192.0.2.6"))
	first, err := adjacent.IPSet()
	if err != nil {
		t.Fatal(err)
	}
	second, err := broad.IPSet()
	if err != nil {
		t.Fatal(err)
	}
	if !first.Equal(second) || len(first.Ranges()) != 1 || first.Ranges()[0].String() != "192.0.2.3-192.0.2.6" {
		t.Fatal("expected distinct source boundaries to normalize to the same set")
	}
	index := lookup.New(first)
	for _, query := range []string{"192.0.2.3", "192.0.2.6"} {
		r, i, ok := index.Find(netip.MustParseAddr(query))
		if !ok || i != 0 || r.String() != "192.0.2.3-192.0.2.6" {
			t.Fatal("both original sources must refer to the same normalized range")
		}
	}
}
