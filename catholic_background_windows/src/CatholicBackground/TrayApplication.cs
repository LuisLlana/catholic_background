// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using Microsoft.Win32;

namespace CatholicBackground;

/// <summary>Icon in the notification area, periodic checks and the settings window.</summary>
public sealed class TrayApplication : ApplicationContext
{
    private readonly Updater _updater = new();
    private readonly NotifyIcon _icon;
    private readonly System.Windows.Forms.Timer _checkTimer = new();
    private readonly System.Windows.Forms.Timer _startupTimer = new() { Interval = 5000 };
    private readonly System.Windows.Forms.Timer _recomposeTimer = new() { Interval = 1500 };
    private readonly Control _invoker = new();
    private SettingsForm? _settingsForm;

    public Updater Updater => _updater;

    public TrayApplication(bool showSettings)
    {
        _invoker.CreateControl();

        var menu = new ContextMenuStrip();
        menu.Items.Add("Settings\u2026", null, (_, _) => ShowSettings());
        menu.Items.Add("Refresh wallpaper", null, async (_, _) => await _updater.CheckAsync(force: true));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Exit", null, (_, _) => ExitThread());
        menu.Items[0].Font = new Font(menu.Items[0].Font, FontStyle.Bold);

        _icon = new NotifyIcon
        {
            Icon = AppIcon.Load(SystemInformation.SmallIconSize),
            Text = "Catholic Background of the Day",
            ContextMenuStrip = menu,
            Visible = true,
        };
        _icon.MouseClick += (_, e) =>
        {
            if (e.Button == MouseButtons.Left)
                ShowSettings();
        };

        _updater.Changed += (_, _) => UpdateTooltip();
        UpdateTooltip();

        // First check shortly after starting, then every CheckInterval minutes
        _startupTimer.Tick += async (_, _) =>
        {
            _startupTimer.Stop();
            await EnsureAutostartInitializedAsync();
            await _updater.CheckAsync(force: false);
        };
        _startupTimer.Start();
        _checkTimer.Tick += async (_, _) => await _updater.CheckAsync(force: false);
        RestartTimer();

        // Monitors, resolution or taskbar changed: compose again (after they settle)
        _recomposeTimer.Tick += async (_, _) =>
        {
            _recomposeTimer.Stop();
            await _updater.RecomposeAsync();
        };
        SystemEvents.DisplaySettingsChanged += OnDisplayChanged;
        SystemEvents.UserPreferenceChanged += OnUserPreferenceChanged;
        SystemEvents.PowerModeChanged += OnPowerModeChanged;

        if (showSettings)
            ShowSettings();
    }

    public void RestartTimer()
    {
        _checkTimer.Stop();
        _checkTimer.Interval = _updater.Settings.CheckInterval * 60 * 1000;
        _checkTimer.Start();
    }

    public void ShowSettings()
    {
        if (_settingsForm is null || _settingsForm.IsDisposed)
            _settingsForm = new SettingsForm(this);
        _settingsForm.Show();
        if (_settingsForm.WindowState == FormWindowState.Minimized)
            _settingsForm.WindowState = FormWindowState.Normal;
        _settingsForm.Activate();
    }

    public void ShowSettingsFromAnyThread() => _invoker.BeginInvoke(ShowSettings);

    private async Task EnsureAutostartInitializedAsync()
    {
        // The first time, start with Windows by default (the user can turn it off)
        if (_updater.Settings.AutostartInitialized)
            return;
        _updater.Settings.AutostartInitialized = true;
        _updater.Settings.Save();
        if (!Paths.IsPackaged)   // packaged: enabled by the manifest
            await Autostart.SetEnabledAsync(true);
    }

    private void UpdateTooltip()
    {
        var text = string.IsNullOrEmpty(_updater.Settings.Title)
            ? "Catholic Background of the Day"
            : $"Catholic Background of the Day\n{_updater.Settings.Title}";
        _icon.Text = text.Length > 127 ? text[..126] + "\u2026" : text;
    }

    private void OnDisplayChanged(object? sender, EventArgs e) => _invoker.BeginInvoke(ScheduleRecompose);

    private void OnUserPreferenceChanged(object? sender, UserPreferenceChangedEventArgs e)
    {
        // The taskbar moved or changed size
        if (e.Category is UserPreferenceCategory.Desktop or UserPreferenceCategory.General)
            _invoker.BeginInvoke(ScheduleRecompose);
    }

    private void OnPowerModeChanged(object? sender, PowerModeChangedEventArgs e)
    {
        if (e.Mode == PowerModes.Resume)
            _invoker.BeginInvoke(async () => await _updater.CheckAsync(force: false));
    }

    private void ScheduleRecompose()
    {
        _recomposeTimer.Stop();
        _recomposeTimer.Start();
    }

    protected override void ExitThreadCore()
    {
        SystemEvents.DisplaySettingsChanged -= OnDisplayChanged;
        SystemEvents.UserPreferenceChanged -= OnUserPreferenceChanged;
        SystemEvents.PowerModeChanged -= OnPowerModeChanged;
        _icon.Visible = false;
        _settingsForm?.Close();
        base.ExitThreadCore();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _icon.Dispose();
            _checkTimer.Dispose();
            _startupTimer.Dispose();
            _recomposeTimer.Dispose();
            _invoker.Dispose();
        }
        base.Dispose(disposing);
    }
}
