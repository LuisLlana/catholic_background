// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Diagnostics;

namespace CatholicBackground;

/// <summary>
/// Main window: the image of any day, as big as possible, with its data; choice of the day,
/// "Use as wallpaper", "Edit this image" and the settings.
/// </summary>
public sealed class MainWindow : Form
{
    private static readonly Color ReasonColor = Color.FromArgb(176, 122, 20);

    private readonly TrayApplication _app;
    private Updater Updater => _app.Updater;

    private readonly Button _previous = new() { Text = "\u25C0", AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink };
    private readonly DateTimePicker _date = new() { Format = DateTimePickerFormat.Long, Width = 250 };
    private readonly Button _next = new() { Text = "\u25B6", AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink };
    private readonly Button _today = new() { Text = "Today", AutoSize = true };
    private readonly Button _use = new() { Text = "Use as wallpaper", AutoSize = true };
    private readonly Button _edit = new() { Text = "Edit this image", AutoSize = true };
    private readonly Button _settings = new() { Text = "Settings\u2026", AutoSize = true };
    private readonly Button _refresh = new() { Text = "Refresh wallpaper", AutoSize = true };
    private readonly Label _note = new() { AutoSize = true, ForeColor = SystemColors.GrayText, Margin = new Padding(3, 6, 3, 0) };
    private readonly PictureBox _picture = new() { Dock = DockStyle.Fill, SizeMode = PictureBoxSizeMode.Zoom, BackColor = Color.FromArgb(235, 235, 235) };
    private readonly Label _message = new() { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleCenter, ForeColor = SystemColors.GrayText, Visible = false };
    private readonly FlowLayoutPanel _info = new() { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, Padding = new Padding(12, 0, 0, 0) };
    private readonly Label _status = new() { AutoSize = true, ForeColor = SystemColors.GrayText, Margin = new Padding(3, 8, 3, 3) };
    private readonly ToolTip _tips = new();

    private DateTime _viewDay = DateTime.Today;
    private DownloadedImage? _day;
    private CancellationTokenSource? _loading;
    private bool _settingDate;

    public MainWindow(TrayApplication app)
    {
        _app = app;
        AutoScaleDimensions = new SizeF(96f, 96f);
        AutoScaleMode = AutoScaleMode.Dpi;
        Font = SystemFonts.MessageBoxFont!;
        Text = "Catholic Background of the Day";
        Icon = AppIcon.Load();
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(1120, 720);
        MinimumSize = new Size(760, 520);

        BuildLayout();
        Updater.Changed += OnUpdaterChanged;
        FormClosed += (_, _) =>
        {
            Updater.Changed -= OnUpdaterChanged;
            _loading?.Cancel();
            _picture.Image?.Dispose();
        };
        UpdateStatus();
        _ = LoadDayAsync(DateTime.Today);
    }

    private void BuildLayout()
    {
        var root = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4, Padding = new Padding(12) };
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));

        // Choice of the day ... actions
        var bar = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 3, Margin = new Padding(0) };
        bar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        bar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        var days = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        _date.Margin = new Padding(3, 5, 3, 3);
        days.Controls.AddRange([_previous, _date, _next, _today]);
        var actions = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        actions.Controls.AddRange([_use, _edit, _settings]);
        bar.Controls.Add(days, 0, 0);
        bar.Controls.Add(actions, 2, 0);
        root.Controls.Add(bar, 0, 0);
        root.Controls.Add(_note, 0, 1);

        // The image (two thirds) and its data
        var content = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Margin = new Padding(0, 8, 0, 0) };
        content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 66));
        content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 34));
        var imageArea = new Panel { Dock = DockStyle.Fill, Margin = new Padding(0) };
        imageArea.Controls.Add(_message);
        imageArea.Controls.Add(_picture);
        content.Controls.Add(imageArea, 0, 0);
        content.Controls.Add(_info, 1, 0);
        root.Controls.Add(content, 0, 2);

        var bottom = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 3, Margin = new Padding(0) };
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        var about = new LinkLabel { Text = "About", AutoSize = true, Anchor = AnchorStyles.Right, Margin = new Padding(8, 8, 3, 3) };
        about.LinkClicked += (_, _) => ShowAbout();
        bottom.Controls.Add(_status, 0, 0);
        bottom.Controls.Add(_refresh, 1, 0);
        bottom.Controls.Add(about, 2, 0);
        root.Controls.Add(bottom, 0, 3);

        Controls.Add(root);

        _tips.SetToolTip(_previous, "Previous day");
        _tips.SetToolTip(_next, "Next day");
        _tips.SetToolTip(_edit, "Opens the page of the artwork in the content manager");
        _previous.Click += (_, _) => _ = LoadDayAsync(_viewDay.AddDays(-1));
        _next.Click += (_, _) => _ = LoadDayAsync(_viewDay.AddDays(1));
        _today.Click += (_, _) => _ = LoadDayAsync(DateTime.Today);
        _date.ValueChanged += (_, _) =>
        {
            if (!_settingDate)
                _ = LoadDayAsync(_date.Value.Date);
        };
        _use.Click += async (_, _) =>
        {
            await Updater.UseDayAsWallpaperAsync(_viewDay);
            UpdateStatus();
        };
        _edit.Click += (_, _) => OpenInBrowser(_day?.EditUrl);
        _settings.Click += async (_, _) => await ShowSettingsAsync();
        _refresh.Click += async (_, _) => await Updater.CheckAsync(force: true);
        _info.SizeChanged += (_, _) => FitInfoWidth();
    }

    // ---------------------------------------------------------------- the day

    public async Task LoadDayAsync(DateTime day)
    {
        _loading?.Cancel();
        var loading = _loading = new CancellationTokenSource();
        _viewDay = day.Date;
        _settingDate = true;
        _date.Value = _viewDay;
        _settingDate = false;
        _day = null;
        ShowMessage("Loading\u2026");
        UpdateStatus();

        DownloadedImage image;
        try
        {
            // The artwork alone: the window shows its data next to it
            var url = ServerClient.RequestUrl(Updater.Settings.ServerUrl, _viewDay, Updater.Settings.LanguageCode(), label: false);
            image = await ServerClient.FetchAsync(url, loading.Token);
        }
        catch (OperationCanceledException)
        {
            return;
        }
        catch (ServerException e)
        {
            if (loading == _loading)
            {
                ShowMessage(e.Message);
                ShowInfo(null);
            }
            return;
        }
        if (loading != _loading)
            return;

        _day = image;
        var old = _picture.Image;
        using (var stream = new MemoryStream(image.Bytes))
        using (var decoded = Image.FromStream(stream))
            _picture.Image = new Bitmap(decoded);
        old?.Dispose();
        _message.Visible = false;
        _picture.Visible = true;
        ShowInfo(image);
        UpdateStatus();
    }

    private void ShowMessage(string text)
    {
        _message.Text = text;
        _message.Visible = true;
        _picture.Visible = false;
    }

    private void ShowInfo(DownloadedImage? image)
    {
        _info.SuspendLayout();
        _info.Controls.Clear();
        if (image is not null)
        {
            Label Add(string text, Font? font = null, Color? color = null, int top = 0)
            {
                var label = new Label { Text = text, AutoSize = true, Margin = new Padding(0, top, 0, 2) };
                if (font is not null)
                    label.Font = font;
                if (color is not null)
                    label.ForeColor = color.Value;
                _info.Controls.Add(label);
                return label;
            }

            if (image.Reason.Length > 0)
                Add(image.Reason, new Font(Font, FontStyle.Bold), ReasonColor);
            Add(image.Title.Length > 0 ? image.Title : "Untitled", new Font(Font.FontFamily, Font.Size * 1.8f));
            var authorYear = string.Join(", ", new[] { image.Author, image.Year }.Where(t => t.Length > 0));
            if (authorYear.Length > 0)
                Add(authorYear, new Font(Font.FontFamily, Font.Size * 1.2f));
            if (image.Description.Length > 0)
                Add(image.Description, top: 10);

            // Additional data, license and source
            var details = new TableLayoutPanel { AutoSize = true, ColumnCount = 2, Margin = new Padding(0, 12, 0, 0) };
            details.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            details.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            var rows = image.Extra.ToList();
            if (image.License.Length > 0)
                rows.Add(new("License", image.License));
            foreach (var (name, value) in rows)
            {
                details.Controls.Add(new Label { Text = name, AutoSize = true, Font = new Font(Font, FontStyle.Bold), Margin = new Padding(0, 2, 10, 2) });
                details.Controls.Add(new Label { Text = value, AutoSize = true, Margin = new Padding(0, 2, 0, 2), Tag = "value" });
            }
            if (image.Source.Length > 0)
            {
                details.Controls.Add(new Label { Text = "Source", AutoSize = true, Font = new Font(Font, FontStyle.Bold), Margin = new Padding(0, 2, 10, 2) });
                var link = new LinkLabel { Text = image.Source, AutoSize = true, Margin = new Padding(0, 2, 0, 2), Tag = "value" };
                link.LinkClicked += (_, _) => OpenInBrowser(image.Source);
                details.Controls.Add(link);
            }
            if (details.Controls.Count > 0)
                _info.Controls.Add(details);
        }
        _info.ResumeLayout();
        FitInfoWidth();
    }

    /// <summary>Texts wrap within the column of the data.</summary>
    private void FitInfoWidth()
    {
        int width = Math.Max(120, _info.ClientSize.Width - _info.Padding.Horizontal - SystemInformation.VerticalScrollBarWidth);
        foreach (Control control in _info.Controls)
        {
            if (control is Label label)
                label.MaximumSize = new Size(width, 0);
            else if (control is TableLayoutPanel table)
            {
                int nameWidth = table.Controls.OfType<Label>().Where(l => l.Tag is null).Select(l => l.PreferredWidth + 10).DefaultIfEmpty(0).Max();
                foreach (var value in table.Controls.OfType<Label>().Where(l => l.Tag is "value"))
                    value.MaximumSize = new Size(Math.Max(80, width - nameWidth), 0);
            }
        }
    }

    // ---------------------------------------------------------------- state

    private void OnUpdaterChanged(object? sender, EventArgs e) => UpdateStatus();

    private void UpdateStatus()
    {
        var s = Updater.Settings;
        var wallpaperDay = s.WallpaperDay();
        bool isWallpaper = _viewDay == wallpaperDay;
        _use.Text = isWallpaper ? "\u2713 This is your wallpaper" : "Use as wallpaper";
        _use.Enabled = !isWallpaper && !Updater.Busy && _day is not null;
        _edit.Visible = _day is not null && _day.EditUrl.Length > 0;
        _today.Enabled = _viewDay != DateTime.Today;
        _refresh.Enabled = !Updater.Busy;
        _note.Visible = wallpaperDay != DateTime.Today;
        _note.Text = $"The wallpaper shows the image of {wallpaperDay:D} until the next automatic check, which returns to today.";
        var interval = $"The server is checked every {Updater.DescribeInterval(s.CheckInterval)}.";
        _status.Text = Updater.Busy ? "Checking the server\u2026"
            : s.LastCheck is { } when ? $"{interval} Last check at {when:t}: {s.LastCheckResult}" : interval;
    }

    private async Task ShowSettingsAsync()
    {
        using var dialog = new SettingsDialog(_app);
        if (dialog.ShowDialog(this) != DialogResult.OK)
            return;
        await dialog.ApplyAsync(this);
        if (dialog.TextsChanged)
            await LoadDayAsync(_viewDay);
        UpdateStatus();
    }

    private void OpenInBrowser(string? url)
    {
        if (string.IsNullOrEmpty(url))
            return;
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception e) when (e is System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            MessageBox.Show(this, $"Could not open the browser: {e.Message}", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private void ShowAbout()
    {
        var version = typeof(MainWindow).Assembly.GetName().Version?.ToString(3) ?? "";
        MessageBox.Show(this,
            $"Catholic Background of the Day {version}\n\n" +
            "Sets a Catholic artwork as your wallpaper every day.\n\n" +
            "\u00a9 2026 Luis Llana <luis.llana.diaz@gmail.com>\n" +
            "License: GNU General Public License v3.0 or later.",
            "About", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}
