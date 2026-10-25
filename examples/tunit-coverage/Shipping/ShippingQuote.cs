namespace Shipping;

public static class ShippingQuote
{
    public static int Calculate(int orderTotal, bool expedited)
    {
        if (expedited)
        {
            return 12;
        }

        if (orderTotal >= 50)
        {
            return 0;
        }

        return 5;
    }
}
