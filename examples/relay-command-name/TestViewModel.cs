using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace RelayCommandName;

public partial class TestViewModel : ObservableObject
{
    [ObservableProperty]
    private int clickCount;

    [ObservableProperty]
    private int controlCount;

    [RelayCommand]
    private void OnPointerPressed() => ClickCount++;

    [RelayCommand]
    private void AsdfPointerPressed() => ControlCount++;
}
