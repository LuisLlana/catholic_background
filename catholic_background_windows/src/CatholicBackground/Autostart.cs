// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using Microsoft.Win32;
using Windows.ApplicationModel;
using Windows.ApplicationModel.Activation;

namespace CatholicBackground;

/// <summary>
/// Starting with Windows: a StartupTask when packaged (MSIX, declared in the manifest),
/// the Run registry key otherwise.
/// </summary>
public static class Autostart
{
    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string ValueName = "CatholicBackground";
    private const string TaskId = "CatholicBackgroundStartup";
    public const string BackgroundArgument = "--background";

    public static async Task<bool> IsEnabledAsync()
    {
        if (Paths.IsPackaged)
        {
            var task = await StartupTask.GetAsync(TaskId);
            return task.State is StartupTaskState.Enabled or StartupTaskState.EnabledByPolicy;
        }
        using var key = Registry.CurrentUser.OpenSubKey(RunKey);
        return key?.GetValue(ValueName) is not null;
    }

    /// <summary>Returns an error message or null.</summary>
    public static async Task<string?> SetEnabledAsync(bool enabled)
    {
        if (Paths.IsPackaged)
        {
            var task = await StartupTask.GetAsync(TaskId);
            if (!enabled)
            {
                task.Disable();
                return null;
            }
            var state = await task.RequestEnableAsync();
            return state switch
            {
                StartupTaskState.Enabled or StartupTaskState.EnabledByPolicy => null,
                StartupTaskState.DisabledByUser =>
                    "Starting with Windows was disabled in Windows Settings. Enable it again in Settings > Apps > Startup.",
                _ => "Starting with Windows is disabled by a policy of this computer.",
            };
        }

        using var key = Registry.CurrentUser.CreateSubKey(RunKey);
        if (enabled)
            key.SetValue(ValueName, $"\"{Environment.ProcessPath}\" {BackgroundArgument}");
        else
            key.DeleteValue(ValueName, throwOnMissingValue: false);
        return null;
    }

    /// <summary>True when Windows started the application at login (no window then).</summary>
    public static bool LaunchedAtStartup(string[] args)
    {
        if (args.Contains(BackgroundArgument))
            return true;
        if (!Paths.IsPackaged)
            return false;
        try
        {
            return Windows.ApplicationModel.AppInstance.GetActivatedEventArgs()?.Kind == ActivationKind.StartupTask;
        }
        catch (Exception)
        {
            return false;
        }
    }
}
