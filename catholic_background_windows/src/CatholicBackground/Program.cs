// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

namespace CatholicBackground;

internal static class Program
{
    private const string InstanceName = @"Local\CatholicBackground-5b8f0f2e";

    [STAThread]
    private static void Main(string[] args)
    {
        // Only one instance: a second launch opens the settings of the running one
        using var mutex = new Mutex(true, InstanceName, out bool firstInstance);
        if (!firstInstance)
        {
            try
            {
                using var existing = EventWaitHandle.OpenExisting(InstanceName + "-show");
                existing.Set();
            }
            catch (WaitHandleCannotBeOpenedException)
            {
            }
            return;
        }
        using var showEvent = new EventWaitHandle(false, EventResetMode.AutoReset, InstanceName + "-show");

        ApplicationConfiguration.Initialize();
        using var app = new TrayApplication(showSettings: !Autostart.LaunchedAtStartup(args));
        var registration = ThreadPool.RegisterWaitForSingleObject(showEvent, (_, _) => app.ShowSettingsFromAnyThread(),
            null, Timeout.Infinite, executeOnlyOnce: false);
        Application.Run(app);
        registration.Unregister(null);
    }
}
