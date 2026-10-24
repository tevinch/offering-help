using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Input;
using Avalonia.Themes.Simple;
using Avalonia.Threading;
using System.Text.Json;

namespace RelayCommandName;

public class App : Application
{
    public override void Initialize() => Styles.Add(new SimpleTheme());
}

internal static class Program
{
    [STAThread]
    public static int Main()
    {
        try
        {
            AppBuilder.Configure<App>()
                .UseHeadless(new AvaloniaHeadlessPlatformOptions { UseHeadlessDrawing = true })
                .SetupWithoutStarting();

            var original = new TestViewModel();
            var window = new TestWindow { DataContext = original };
            var main = window.FindControl<Button>("MainButton")!;
            var control = window.FindControl<Button>("ControlButton")!;
            int mainClicks = 0;
            int controlClicks = 0;
            main.Click += (_, _) => mainClicks++;
            control.Click += (_, _) => controlClicks++;
            window.Show();
            Dispatcher.UIThread.RunJobs();

            var snapshots = new List<object>();
            void Snapshot()
            {
                Dispatcher.UIThread.RunJobs();
                var model = (TestViewModel)window.DataContext!;
                snapshots.Add(new {
                    Calls = model.ClickCount,
                    Text = window.FindControl<TextBlock>("MainCount")!.Text,
                    ControlCalls = model.ControlCount,
                    ControlText = window.FindControl<TextBlock>("ControlCount")!.Text,
                    MainClickEvents = mainClicks,
                    ControlClickEvents = controlClicks
                });
            }
            void Click(Button button)
            {
                var point = button.TranslatePoint(
                    new Point(button.Bounds.Width / 2, button.Bounds.Height / 2), window)
                    ?? throw new InvalidOperationException("Button is not in the window");
                window.MouseMove(point);
                window.MouseDown(point, MouseButton.Left);
                window.MouseUp(point, MouseButton.Left);
                Dispatcher.UIThread.RunJobs();
            }

            Snapshot();
            Click(main);
            Snapshot();
            Click(main);
            Snapshot();
            window.DataContext = new TestViewModel();
            Snapshot();
            Click(main);
            Snapshot();
            Click(control);
            Snapshot();
            window.Close();
            Console.WriteLine(JsonSerializer.Serialize(new {
                Snapshots = snapshots,
                OriginalCalls = original.ClickCount,
                OriginalControlCalls = original.ControlCount
            }));
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            return 2;
        }
    }
}
