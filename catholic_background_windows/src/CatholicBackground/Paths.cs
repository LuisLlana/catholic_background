// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Runtime.InteropServices;

namespace CatholicBackground;

/// <summary>Where the application keeps its files, whether it is packaged (MSIX) or not.</summary>
public static class Paths
{
    private const int AppModelErrorNoPackage = 15700;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetCurrentPackageFullName(ref int packageFullNameLength, char[]? packageFullName);

    /// <summary>True when running from an MSIX package (e.g. installed from the Microsoft Store).</summary>
    public static bool IsPackaged { get; } = DetectPackage();

    private static bool DetectPackage()
    {
        try
        {
            int length = 0;
            return GetCurrentPackageFullName(ref length, null) != AppModelErrorNoPackage;
        }
        catch (Exception)
        {
            return false;
        }
    }

    /// <summary>
    /// Data folder. For packaged apps, writes to %LOCALAPPDATA% are redirected to the
    /// package folder, so the real path is used: Windows (Explorer) must be able to read
    /// the wallpaper files from there.
    /// </summary>
    public static string DataDirectory { get; } = IsPackaged
        ? Windows.Storage.ApplicationData.Current.LocalFolder.Path
        : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CatholicBackground");

    public static string OriginalImage => Path.Combine(DataDirectory, "original");
    public static string WallpaperDirectory => Path.Combine(DataDirectory, "wallpapers");
}
