// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Globalization;

namespace CatholicBackground;

/// <summary>Settings: server, language, label, how to fill the screen, interval and startup.</summary>
public sealed class SettingsDialog : Form
{
    private readonly TrayApplication _app;
    private Updater Updater => _app.Updater;

    private readonly TextBox _url = new() { Anchor = AnchorStyles.Left | AnchorStyles.Right, Width = 320 };
    private readonly Button _test = new() { Text = "Test", AutoSize = true };
    private readonly Button _default = new() { Text = "Default", AutoSize = true };
    private readonly ComboBox _language = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 260 };
    private readonly CheckBox _label = new() { Text = "Show the reason, title and author below the artwork", AutoSize = true };
    private readonly NumericUpDown _interval = new()
    {
        Minimum = AppSettings.MinCheckInterval, Maximum = AppSettings.MaxCheckInterval, Increment = 5, Width = 70,
    };
    private readonly RadioButton _blur = new() { Text = "Blurred image", AutoSize = true };
    private readonly RadioButton _average = new() { Text = "Average color of the image", AutoSize = true };
    private readonly RadioButton _color = new() { Text = "Color:", AutoSize = true };
    private readonly Button _colorButton = new() { Width = 56, Height = 24, FlatStyle = FlatStyle.Flat };
    private readonly CheckBox _startup = new() { Text = "Start with Windows", AutoSize = true };
    private readonly Button _ok = new() { Text = "OK", AutoSize = true, DialogResult = DialogResult.OK };
    private readonly Button _cancel = new() { Text = "Cancel", AutoSize = true, DialogResult = DialogResult.Cancel };

    private Color _chosenColor;
    private bool _startupEnabled;

    /// <summary>After ApplyAsync: the server or the language changed (the texts of the day must be loaded again).</summary>
    public bool TextsChanged { get; private set; }

    private sealed record LanguageItem(string Code, string Name)
    {
        public override string ToString() => Name;
    }

    public SettingsDialog(TrayApplication app)
    {
        _app = app;
        AutoScaleDimensions = new SizeF(96f, 96f);
        AutoScaleMode = AutoScaleMode.Dpi;
        Font = SystemFonts.MessageBoxFont!;
        Text = "Settings";
        Icon = AppIcon.Load();
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = MinimizeBox = false;
        ShowInTaskbar = false;
        AutoSize = true;
        AutoSizeMode = AutoSizeMode.GrowAndShrink;

        BuildLayout();
        LoadValues();
    }

    private void BuildLayout()
    {
        var root = new TableLayoutPanel { AutoSize = true, ColumnCount = 1, Padding = new Padding(14) };

        var server = new GroupBox { Text = "Server", AutoSize = true, Dock = DockStyle.Fill };
        var grid = new TableLayoutPanel { AutoSize = true, ColumnCount = 4, Dock = DockStyle.Fill, Padding = new Padding(4) };
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        grid.Controls.Add(new Label { Text = "URL:", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 0);
        grid.Controls.Add(_url, 1, 0);
        grid.Controls.Add(_test, 2, 0);
        grid.Controls.Add(_default, 3, 0);
        var intervalRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        intervalRow.Controls.Add(_interval);
        intervalRow.Controls.Add(new Label { Text = "minutes", AutoSize = true, Margin = new Padding(3, 6, 3, 0) });
        grid.Controls.Add(new Label { Text = "Check every:", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 1);
        grid.Controls.Add(intervalRow, 1, 1);
        grid.SetColumnSpan(intervalRow, 3);
        server.Controls.Add(grid);
        root.Controls.Add(server);

        var texts = new GroupBox { Text = "Texts", AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(3, 8, 3, 3) };
        var textsGrid = new TableLayoutPanel { AutoSize = true, ColumnCount = 2, Dock = DockStyle.Fill, Padding = new Padding(4) };
        textsGrid.Controls.Add(new Label { Text = "Language:", AutoSize = true, Anchor = AnchorStyles.Left }, 0, 0);
        textsGrid.Controls.Add(_language, 1, 0);
        textsGrid.Controls.Add(_label, 0, 1);
        textsGrid.SetColumnSpan(_label, 2);
        texts.Controls.Add(textsGrid);
        root.Controls.Add(texts);

        var around = new GroupBox { Text = "Around the image", AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(3, 8, 3, 3) };
        var aroundFlow = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.TopDown, Dock = DockStyle.Fill, Padding = new Padding(4) };
        var colorRow = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0) };
        colorRow.Controls.Add(_color);
        colorRow.Controls.Add(_colorButton);
        aroundFlow.Controls.Add(new Label
        {
            Text = "The image is always shown complete and as big as possible. Choose how to fill the rest of the screen:",
            AutoSize = true, MaximumSize = new Size(480, 0), Margin = new Padding(3, 3, 3, 6),
        });
        aroundFlow.Controls.AddRange([_blur, _average, colorRow]);
        around.Controls.Add(aroundFlow);
        root.Controls.Add(around);

        _startup.Margin = new Padding(6, 10, 3, 3);
        root.Controls.Add(_startup);

        var buttons = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.RightToLeft, Dock = DockStyle.Fill, Margin = new Padding(0, 12, 0, 0) };
        buttons.Controls.AddRange([_cancel, _ok]);
        root.Controls.Add(buttons);

        Controls.Add(root);
        AcceptButton = _ok;
        CancelButton = _cancel;

        foreach (var radio in new[] { _blur, _average, _color })
            radio.CheckedChanged += (_, _) => _colorButton.Enabled = _color.Checked;
        _colorButton.Click += (_, _) => ChooseColor();
        _default.Click += (_, _) => _url.Text = AppSettings.DefaultServerUrl;
        _test.Click += async (_, _) => await TestAsync();
        _ok.Click += (_, e) =>
        {
            try
            {
                ServerClient.Validate(_url.Text);
            }
            catch (ServerException error)
            {
                MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                DialogResult = DialogResult.None;
            }
        };
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
        _label.Checked = s.ShowLabel;

        var system = CultureInfo.CurrentUICulture;
        var systemName = system.NativeName.Length > 0 ? char.ToUpper(system.NativeName[0]) + system.NativeName[1..] : system.Name;
        _language.Items.Add(new LanguageItem("", $"System language ({systemName})"));
        _language.SelectedIndex = 0;
        try
        {
            _startupEnabled = await Autostart.IsEnabledAsync();
        }
        catch (Exception)
        {
            _startupEnabled = false;
        }
        _startup.Checked = _startupEnabled;

        foreach (var language in await ServerClient.LanguagesAsync(s.ServerUrl))
        {
            if (IsDisposed)
                return;
            _language.Items.Add(new LanguageItem(language.Code, language.Name));
            if (language.Code == s.Language)
                _language.SelectedIndex = _language.Items.Count - 1;
        }
    }

    private string SelectedBackground => _color.Checked ? "color" : _average.Checked ? "average" : "blur";
    private string SelectedLanguage => (_language.SelectedItem as LanguageItem)?.Code ?? "";

    private void ChooseColor()
    {
        using var dialog = new ColorDialog { Color = _chosenColor, FullOpen = true };
        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            _chosenColor = dialog.Color;
            _colorButton.BackColor = _chosenColor;
        }
    }

    private async Task TestAsync()
    {
        _test.Enabled = false;
        try
        {
            var url = ServerClient.RequestUrl(_url.Text, DateTime.Today, Updater.Settings.LanguageCode(), label: false);
            var image = await ServerClient.FetchAsync(url);
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
            _test.Enabled = true;
        }
    }

    /// <summary>Saves the settings and updates the wallpaper if needed (after the dialog is accepted).</summary>
    public async Task ApplyAsync(IWin32Window owner)
    {
        var s = Updater.Settings;
        var url = _url.Text.Trim();
        bool urlChanged = url != s.ServerUrl;
        bool languageChanged = SelectedLanguage != s.Language;
        bool labelChanged = _label.Checked != s.ShowLabel;
        bool backgroundChanged = SelectedBackground != s.Background ||
            (SelectedBackground == "color" && Composer.ToHex(_chosenColor) != s.BackgroundColor.ToLowerInvariant());
        bool intervalChanged = (int)_interval.Value != s.CheckInterval;

        s.ServerUrl = url;
        s.Language = SelectedLanguage;
        s.ShowLabel = _label.Checked;
        s.Background = SelectedBackground;
        s.BackgroundColor = Composer.ToHex(_chosenColor);
        s.CheckIntervalMinutes = (int)_interval.Value;
        s.Save();
        TextsChanged = urlChanged || languageChanged;

        if (intervalChanged)
            _app.RestartTimer();

        if (_startup.Checked != _startupEnabled)
        {
            var error = await Autostart.SetEnabledAsync(_startup.Checked);
            if (error is not null)
                MessageBox.Show(owner, error, Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // The language and the label change the image (the label is drawn by the server)
        if (urlChanged || languageChanged || labelChanged)
            await Updater.CheckAsync(force: true);
        else if (backgroundChanged)
        {
            var error = await Updater.RecomposeAsync();
            if (error is not null)
                MessageBox.Show(owner, error, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }
}
