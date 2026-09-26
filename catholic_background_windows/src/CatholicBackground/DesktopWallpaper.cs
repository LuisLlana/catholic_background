// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;
using System.Runtime.InteropServices;

namespace CatholicBackground;

/// <summary>Windows' IDesktopWallpaper: a different wallpaper for each monitor.</summary>
public static class DesktopWallpaper
{
    public sealed record Monitor(string Id, Rectangle Bounds);

    public static IReadOnlyList<Monitor> ActiveMonitors()
    {
        var wallpaper = (IDesktopWallpaper)new DesktopWallpaperClass();
        var monitors = new List<Monitor>();
        uint count = wallpaper.GetMonitorDevicePathCount();
        for (uint i = 0; i < count; i++)
        {
            try
            {
                string id = wallpaper.GetMonitorDevicePathAt(i);
                var rect = wallpaper.GetMonitorRECT(id);   // fails for monitors that are not connected
                if (rect.Right > rect.Left && rect.Bottom > rect.Top)
                    monitors.Add(new Monitor(id, Rectangle.FromLTRB(rect.Left, rect.Top, rect.Right, rect.Bottom)));
            }
            catch (COMException)
            {
            }
        }
        return monitors;
    }

    /// <summary>Sets one file per monitor, shown complete ("Fit") over the given color.</summary>
    public static void Set(IReadOnlyDictionary<string, string> filesByMonitor, Color background)
    {
        var wallpaper = (IDesktopWallpaper)new DesktopWallpaperClass();
        wallpaper.SetBackgroundColor((uint)(background.R | (background.G << 8) | (background.B << 16)));
        wallpaper.SetPosition(DesktopWallpaperPosition.Fit);
        foreach (var (monitor, file) in filesByMonitor)
            wallpaper.SetWallpaper(monitor, file);
    }

    private enum DesktopWallpaperPosition
    {
        Center = 0,
        Tile = 1,
        Stretch = 2,
        Fit = 3,
        Fill = 4,
        Span = 5,
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Rect
    {
        public int Left, Top, Right, Bottom;
    }

    [ComImport, Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IDesktopWallpaper
    {
        void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string? monitorId, [MarshalAs(UnmanagedType.LPWStr)] string wallpaper);

        [return: MarshalAs(UnmanagedType.LPWStr)]
        string GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string? monitorId);

        [return: MarshalAs(UnmanagedType.LPWStr)]
        string GetMonitorDevicePathAt(uint monitorIndex);

        uint GetMonitorDevicePathCount();

        Rect GetMonitorRECT([MarshalAs(UnmanagedType.LPWStr)] string monitorId);

        void SetBackgroundColor(uint color);

        uint GetBackgroundColor();

        void SetPosition(DesktopWallpaperPosition position);

        DesktopWallpaperPosition GetPosition();

        void SetSlideshow(IntPtr items);

        IntPtr GetSlideshow();

        void SetSlideshowOptions(int options, uint slideshowTick);

        void GetSlideshowOptions(out int options, out uint slideshowTick);

        void AdvanceSlideshow([MarshalAs(UnmanagedType.LPWStr)] string? monitorId, int direction);

        int GetStatus();

        void Enable([MarshalAs(UnmanagedType.Bool)] bool enable);
    }

    [ComImport, Guid("C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD")]
    private class DesktopWallpaperClass
    {
    }
}
