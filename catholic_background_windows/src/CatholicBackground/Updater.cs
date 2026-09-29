// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;
using System.Runtime.InteropServices;

namespace CatholicBackground;

/// <summary>Downloads the image, composes one wallpaper per monitor and sets it.</summary>
public sealed class Updater
{
    private readonly SemaphoreSlim _lock = new(1, 1);

    public AppSettings Settings { get; } = AppSettings.Load();
    public bool Busy { get; private set; }

    /// <summary>Raised on the UI thread when the state or the wallpaper changes.</summary>
    public event EventHandler? Changed;

    /// <summary>
    /// Downloads the image of the wallpaper day and changes the wallpaper if it is different
    /// from the current one (or always, if force is true). The server may have several images a
    /// day. An automatic check also ends a day chosen with "Use as wallpaper": back to today.
    /// </summary>
    public async Task<(bool Ok, string Message)> CheckAsync(bool force, bool automatic = false)
    {
        await _lock.WaitAsync();
        SetBusy(true);
        try
        {
            if (automatic && Settings.ShowDate.Length > 0)
            {
                Settings.ShowDate = "";
                Settings.Save();
                force = true;
            }

            DownloadedImage image;
            try
            {
                image = await ServerClient.FetchAsync(Settings.WallpaperUrl());
            }
            catch (ServerException e)
            {
                return Record(false, $"{e.Message} The current wallpaper has been kept.");
            }

            if (!force && image.Hash == Settings.ImageHash && File.Exists(Paths.OriginalImage) && File.Exists(Settings.PreviewFile))
                return Record(true, "The image has not changed.");

            Directory.CreateDirectory(Paths.DataDirectory);
            await File.WriteAllBytesAsync(Paths.OriginalImage, image.Bytes);
            Settings.ImageHash = image.Hash;
            Settings.Title = image.TitleWithYear;
            Settings.Author = image.Author;

            var error = await ComposeAndSetAsync();
            return error is null ? Record(true, "The wallpaper has been updated.") : Record(false, error);
        }
        finally
        {
            SetBusy(false);
            _lock.Release();
        }
    }

    /// <summary>Makes a day the wallpaper until the next automatic check (today: back to normal).</summary>
    public Task<(bool Ok, string Message)> UseDayAsWallpaperAsync(DateTime day)
    {
        Settings.ShowDate = day.Date == DateTime.Today ? "" : day.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
        Settings.Save();
        return CheckAsync(force: true);
    }

    /// <summary>Composes again from the saved image (options, monitors or taskbar changed).</summary>
    public async Task<string?> RecomposeAsync()
    {
        if (!File.Exists(Paths.OriginalImage))
            return null;
        await _lock.WaitAsync();
        SetBusy(true);
        try
        {
            var error = await ComposeAndSetAsync();
            Settings.Save();
            Changed?.Invoke(this, EventArgs.Empty);
            return error;
        }
        finally
        {
            SetBusy(false);
            _lock.Release();
        }
    }

    /// <summary>Must be called on the UI thread. Returns an error message or null.</summary>
    private async Task<string?> ComposeAndSetAsync()
    {
        try
        {
            var monitors = DesktopWallpaper.ActiveMonitors();
            if (monitors.Count == 0)
                return "Windows did not report any monitor.";
            var screens = Screen.AllScreens;
            var bytes = await File.ReadAllBytesAsync(Paths.OriginalImage);
            var mode = Settings.Background;
            var color = Composer.ParseColor(Settings.BackgroundColor);
            var stamp = DateTime.UtcNow.Ticks;
            Directory.CreateDirectory(Paths.WallpaperDirectory);

            // Image work outside the UI thread
            var (files, fill, preview) = await Task.Run(() =>
            {
                using var image = Composer.Load(bytes);
                var files = new Dictionary<string, string>();
                Color fill = Color.Black;
                string? preview = null;
                int index = 0;
                foreach (var monitor in monitors)
                {
                    var screen = screens.FirstOrDefault(s => s.Bounds == monitor.Bounds);
                    var free = screen is null
                        ? new Rectangle(Point.Empty, monitor.Bounds.Size)
                        : new Rectangle(screen.WorkingArea.X - monitor.Bounds.X, screen.WorkingArea.Y - monitor.Bounds.Y,
                                        screen.WorkingArea.Width, screen.WorkingArea.Height);
                    using var bitmap = Composer.Compose(image, monitor.Bounds.Size, free, mode, color, out fill);
                    // A new file name every time, so that Windows notices the change
                    var path = Path.Combine(Paths.WallpaperDirectory, $"{stamp}-{index++}.jpg");
                    Composer.SaveJpeg(bitmap, path);
                    files[monitor.Id] = path;
                    if (preview is null || screen?.Primary == true)
                        preview = path;
                }
                return (files, fill, preview);
            });

            DesktopWallpaper.Set(files, fill);
            Settings.PreviewFile = preview ?? "";

            // Remove the previous wallpapers
            foreach (var old in Directory.GetFiles(Paths.WallpaperDirectory))
            {
                if (!files.ContainsValue(old))
                {
                    try { File.Delete(old); } catch (IOException) { }
                }
            }
            return null;
        }
        catch (Exception e) when (e is COMException or IOException or UnauthorizedAccessException or ArgumentException or ExternalException)
        {
            return $"Could not set the wallpaper: {e.Message}";
        }
    }

    private (bool, string) Record(bool ok, string message)
    {
        Settings.LastCheck = DateTime.Now;
        Settings.LastCheckResult = message;
        Settings.Save();
        Changed?.Invoke(this, EventArgs.Empty);
        return (ok, message);
    }

    private void SetBusy(bool busy)
    {
        Busy = busy;
        Changed?.Invoke(this, EventArgs.Empty);
    }

    public static string DescribeInterval(int minutes) =>
        minutes % 60 == 0 ? (minutes == 60 ? "hour" : $"{minutes / 60} hours") : $"{minutes} minutes";
}
