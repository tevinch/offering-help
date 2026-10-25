using Shipping;
using TUnit.Assertions;
using TUnit.Assertions.Extensions;
using TUnit.Core;

namespace Shipping.Tests;

public class ShippingQuoteTests
{
    [Test]
    public async Task Standard_order_below_threshold_costs_five()
    {
        await Assert.That(ShippingQuote.Calculate(49, expedited: false)).IsEqualTo(5);
    }

    [Test]
    public async Task Standard_order_at_threshold_is_free()
    {
        await Assert.That(ShippingQuote.Calculate(50, expedited: false)).IsEqualTo(0);
    }

}
