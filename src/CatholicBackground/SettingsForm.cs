// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Diagnostics;

namespace CatholicBackground;

/// <summary>Settings window: today's image, server, check interval, background and startup.</summary>
public sealed class SettingsForm : Form
{
    private readonly TrayApplication _app;
    private Updater Updater => _app.Updater;

    private readonly PictureBox _preview = new() { SizeMode = PictureBoxSizeMode.Zoom, Dock = DockStyle.Fill, BackColor = SystemColors.ControlDark };
    private readonly Label _title = new() { AutoSize = true, Font = new Font(SystemFonts.MessageBoxFont!.FontFamily, 11f, FontStyle.Bold) };
    private readonly Label _author = new() { AutoSize = true };
    private readonly Label _status = new() { AutoSize = true, ForeColor = SystemColors.GrayText, MaximumSize = new Size(520, 0) };
    private readonly TextBox _url = new() { Anchor = AnchorStyles.Left | AnchorStyles.Right, Width = 300 };
    private readonly NumericUpDown _interval = new()
    {
        Minimum = AppSettings.MinCheckInterval, Maximum = AppSettings.MaxCheckInterval, Increment = 5, Width = 70,
    };
    private readonly RadioButton _blur = new() { Text = "Blurred image", AutoSize = true };
    private readonly RadioButton _average = new() { Text = "Average color of the image", AutoSize = true };
    private readonly RadioButton _color = new() { Text = "Color:", AutoSize = true };
    private readonly Button _colorButton = new() { Width = 56, Height = 24, FlatStyle = FlatStyle.Flat };
    private readonly CheckBox _startup = new() { Text = "Start with Windows", AutoSize = true };
    private readonly Button _test = new() { Text = "Test", AutoSize = true };
    private readonly Button _default = new() { Text = "Default", AutoSize = true };
    private readonly Button _refresh = new() { Text = "Refresh wallpaper", AutoSize = true };
    private readonly Button _apply = new() { Text = "Apply", AutoSize = true, Enabled = false };
    private readonly Button _close = new() { Text = "Close", AutoSize = true };

    private Color _chosenColor;
    private bool _startupEnabled;
    private string _shownPreview = "";

    public SettingsForm(TrayApplication app)
    {
        _app = app;
        AutoScaleDimensions = new SizeF(96f, 96f);
        AutoScaleMode = AutoScaleMode.Dpi;
        Font = SystemFonts.MessageBoxFont!;
        Text = "Catholic Background of the Day";
        Icon = AppIcon.Load();
        StartPosition = FormStartPosition.CenterScreen;
        MaximizeBox = false;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        ClientSize = new Size(560, 700);

        BuildLayout();
        LoadValues();
        UpdateView();

        Updater.Changed += OnUpdaterChanged;
        FormClosed += (_, _) =>
        {
            Updater.Changed -= OnUpdaterChanged;
            _preview.Image?.Dispose();
        };
    }

    private void BuildLayout()
    {
        var root = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, Padding = new Padding(14), AutoScroll = true };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        // Today's image
        var previewPanel = new Panel { Height = 290, Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 8) };
        previewPanel.Controls.Add(_preview);
        root.Controls.Add(previewPanel);
        root.Controls.Add(_title);
        root.Controls.Add(_author);
        root.Controls.Add(_status);

        // Server
        var server = new GroupBox { Text = "Server", Dock = DockStyle.Fill, AutoSize = true, Margin = new Padding(0, 12, 0, 0) };
        var serverGrid = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 4, Padding = new Padding(4) };
        serverGrid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        serverGrid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        serverGrid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        serverGrid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        serverGrid.Controls.Add(new Label { Text = "URL:", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 0);
        serverGrid.Controls.Add(_url, 1, 0);
        serverGrid.Controls.Add(_test, 2, 0);
        serverGrid.Controls.Add(_default, 3, 0);
        var intervalRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        intervalRow.Controls.Add(_interval);
        intervalRow.Controls.Add(new Label { Text = "minutes", AutoSize = true, Margin = new Padding(3, 6, 3, 0) });
        serverGrid.Controls.Add(new Label { Text = "Check every:", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 1);
        serverGrid.Controls.Add(intervalRow, 1, 1);
        serverGrid.SetColumnSpan(intervalRow, 3);
        server.Controls.Add(serverGrid);
        root.Controls.Add(server);

        // Around the image
        var around = new GroupBox { Text = "Around the image", Dock = DockStyle.Fill, AutoSize = true, Margin = new Padding(0, 8, 0, 0) };
        var aroundFlow = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, FlowDirection = FlowDirection.TopDown, Padding = new Padding(4) };
        var colorRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        colorRow.Controls.Add(_color);
        colorRow.Controls.Add(_colorButton);
        aroundFlow.Controls.Add(new Label
        {
            Text = "The image is always shown complete and as big as possible. Choose how to fill the rest of the screen:",
            AutoSize = true, MaximumSize = new Size(500, 0), Margin = new Padding(3, 3, 3, 6),
        });
        aroundFlow.Controls.Add(_blur);
        aroundFlow.Controls.Add(_average);
        aroundFlow.Controls.Add(colorRow);
        around.Controls.Add(aroundFlow);
        root.Controls.Add(around);

        _startup.Margin = new Padding(3, 10, 3, 3);
        root.Controls.Add(_startup);

        // Buttons
        var buttons = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 4, Margin = new Padding(0, 12, 0, 0) };
        buttons.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        buttons.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        buttons.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        var about = new LinkLabel { Text = "About", AutoSize = true, Anchor = AnchorStyles.Left };
        about.LinkClicked += (_, _) => ShowAbout();
        var left = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        left.Controls.Add(_refresh);
        left.Controls.Add(about);
        buttons.Controls.Add(left, 0, 0);
        buttons.Controls.Add(_apply, 2, 0);
        buttons.Controls.Add(_close, 3, 0);
        root.Controls.Add(buttons);

        Controls.Add(root);
        AcceptButton = _apply;
        CancelButton = _close;

        // Events
        _url.TextChanged += (_, _) => UpdateApply();
        _interval.ValueChanged += (_, _) => UpdateApply();
        foreach (var radio in new[] { _blur, _average, _color })
            radio.CheckedChanged += (_, _) => { _colorButton.Enabled = _color.Checked; UpdateApply(); };
        _startup.CheckedChanged += (_, _) => UpdateApply();
        _colorButton.Click += (_, _) => ChooseColor();
        _default.Click += (_, _) => _url.Text = AppSettings.DefaultServerUrl;
        _test.Click += async (_, _) => await TestAsync();
        _refresh.Click += async (_, _) => await Updater.CheckAsync(force: true);
        _apply.Click += async (_, _) => await ApplyAsync();
        _close.Click += (_, _) => Close();
    }

    private async void LoadValues()
    {
        var s = Updater.Settings;
        _url.Text = s.ServerUrl;
        _interval.Value = s.CheckInterval;
        _blur.Checked = s.Background == "blur";
        _average.Checked = s.Background == "average";
        _color.Checked = s.Background == "color";
        _chosenColor = Composer.ParseColor(s.BackgroundColor);
        _colorButton.BackColor = _chosenColor;
        _colorButton.Enabled = _color.Checked;
        try
        {
            _startupEnabled = await Autostart.IsEnabledAsync();
        }
        catch (Exception)
        {
            _startupEnabled = false;
        }
        _startup.Checked = _startupEnabled;
        UpdateApply();
    }

    private string SelectedBackground => _color.Checked ? "color" : _average.Checked ? "average" : "blur";

    private bool UrlChanged => _url.Text.Trim() != Updater.Settings.ServerUrl;
    private bool BackgroundChanged => SelectedBackground != Updater.Settings.Background ||
        (SelectedBackground == "color" && Composer.ToHex(_chosenColor) != Updater.Settings.BackgroundColor.ToLowerInvariant());
    private bool IntervalChanged => (int)_interval.Value != Updater.Settings.CheckInterval;
    private bool StartupChanged => _startup.Checked != _startupEnabled;

    private void UpdateApply() =>
        _apply.Enabled = !Updater.Busy && (UrlChanged || BackgroundChanged || IntervalChanged || StartupChanged);

    private void OnUpdaterChanged(object? sender, EventArgs e) => UpdateView();

    private void UpdateView()
    {
        var s = Updater.Settings;
        _title.Text = string.IsNullOrEmpty(s.Title) ? "No image yet" : s.Title;
        _author.Text = s.Author;
        var interval = $"The server is checked every {Updater.DescribeInterval(s.CheckInterval)}.";
        _status.Text = Updater.Busy ? "Checking the server\u2026"
            : s.LastCheck is { } when ? $"{interval} Last check at {when:t}: {s.LastCheckResult}" : interval;
        _refresh.Enabled = _test.Enabled = !Updater.Busy;
        UpdateApply();

        if (s.PreviewFile != _shownPreview)
        {
            _shownPreview = s.PreviewFile;
            var old = _preview.Image;
            _preview.Image = null;
            old?.Dispose();
            if (File.Exists(s.PreviewFile))
            {
                // Load without keeping the file locked
                using var stream = new FileStream(s.PreviewFile, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                using var image = Image.FromStream(stream);
                _preview.Image = new Bitmap(image);
            }
        }
    }

    private void ChooseColor()
    {
        using var dialog = new ColorDialog { Color = _chosenColor, FullOpen = true };
        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            _chosenColor = dialog.Color;
            _colorButton.BackColor = _chosenColor;
            UpdateApply();
        }
    }

    private async Task TestAsync()
    {
        _test.Enabled = false;
        try
        {
            var image = await ServerClient.FetchAsync(_url.Text);
            var what = string.Join(", ", new[] { image.Title.Length > 0 ? image.Title : "an image without title", image.Author }
                .Where(t => t.Length > 0));
            MessageBox.Show(this, $"Connection OK: {what} ({image.Size.Width}\u00d7{image.Size.Height}).", Text,
                MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (ServerException e)
        {
            MessageBox.Show(this, e.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            _test.Enabled = !Updater.Busy;
        }
    }

    private async Task ApplyAsync()
    {
        var url = _url.Text.Trim();
        try
        {
            ServerClient.UrlForToday(url);
        }
        catch (ServerException e)
        {
            MessageBox.Show(this, e.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        bool urlChanged = UrlChanged, backgroundChanged = BackgroundChanged, intervalChanged = IntervalChanged;
        var s = Updater.Settings;
        s.ServerUrl = url;
        s.Background = SelectedBackground;
        s.BackgroundColor = Composer.ToHex(_chosenColor);
        s.CheckIntervalMinutes = (int)_interval.Value;
        s.Save();

        if (intervalChanged)
            _app.RestartTimer();

        if (StartupChanged)
        {
            var error = await Autostart.SetEnabledAsync(_startup.Checked);
            if (error is not null)
                MessageBox.Show(this, error, Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            _startupEnabled = await Autostart.IsEnabledAsync();
            _startup.Checked = _startupEnabled;
        }

        if (urlChanged)
            await Updater.CheckAsync(force: true);
        else if (backgroundChanged)
        {
            var error = await Updater.RecomposeAsync();
            if (error is not null)
                MessageBox.Show(this, error, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        UpdateView();
    }

    private void ShowAbout()
    {
        var version = typeof(SettingsForm).Assembly.GetName().Version?.ToString(3) ?? "";
        MessageBox.Show(this,
            $"Catholic Background of the Day {version}\n\n" +
            "Sets a Catholic artwork as your wallpaper every day.\n\n" +
            "\u00a9 2026 Luis Llana <luis.llana.diaz@gmail.com>\n" +
            "License: GNU General Public License v3.0 or later.",
            "About", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}
