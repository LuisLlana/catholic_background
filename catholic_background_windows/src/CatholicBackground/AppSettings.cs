// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Text.Json;
using System.Text.Json.Serialization;

namespace CatholicBackground;

/// <summary>Configuration and state, stored as JSON in the data folder.</summary>
public sealed class AppSettings
{
    public const string DefaultServerUrl = "https://simba.fdi.ucm.es/background";
    public const int DefaultCheckInterval = 30;
    public const int MinCheckInterval = 5;
    public const int MaxCheckInterval = 24 * 60;

    // Configuration
    public string ServerUrl { get; set; } = DefaultServerUrl;
    /// <summary>"blur", "average" or "color"</summary>
    public string Background { get; set; } = "blur";
    public string BackgroundColor { get; set; } = "#000000";
    public int CheckIntervalMinutes { get; set; } = DefaultCheckInterval;
    /// <summary>Language of the texts ("" = the language of Windows).</summary>
    public string Language { get; set; } = "";
    /// <summary>Label below the artwork (drawn by the server).</summary>
    public bool ShowLabel { get; set; } = true;
    /// <summary>Day used as wallpaper ("yyyy-MM-dd") until the next automatic check; "" = today.</summary>
    public string ShowDate { get; set; } = "";

    // State
    public string ImageHash { get; set; } = "";
    public string Title { get; set; } = "";
    public string Author { get; set; } = "";
    public DateTime? LastCheck { get; set; }
    public string LastCheckResult { get; set; } = "";
    /// <summary>Composed wallpaper of the primary monitor (for the preview).</summary>
    public string PreviewFile { get; set; } = "";
    /// <summary>Whether the first run already enabled starting with Windows.</summary>
    public bool AutostartInitialized { get; set; }

    [JsonIgnore]
    public int CheckInterval => Math.Clamp(CheckIntervalMinutes, MinCheckInterval, MaxCheckInterval);

    /// <summary>Language asked to the server: the chosen one or that of Windows ("es-es").</summary>
    public string LanguageCode() =>
        Language.Length > 0 ? Language : System.Globalization.CultureInfo.CurrentUICulture.Name.ToLowerInvariant();

    /// <summary>Day of the wallpaper: the one chosen with "Use as wallpaper", or today.</summary>
    public DateTime WallpaperDay() =>
        DateTime.TryParseExact(ShowDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.None, out var day) ? day.Date : DateTime.Today;

    public Uri WallpaperUrl() => ServerClient.RequestUrl(ServerUrl, WallpaperDay(), LanguageCode(), ShowLabel);

    private static string FilePath => Path.Combine(Paths.DataDirectory, "settings.json");

    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(FilePath))
                return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(FilePath), JsonOptions) ?? new AppSettings();
        }
        catch (Exception)
        {
            // Corrupt file: start again with the defaults
        }
        return new AppSettings();
    }

    public void Save()
    {
        Directory.CreateDirectory(Paths.DataDirectory);
        var tmp = FilePath + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(this, JsonOptions));
        File.Move(tmp, FilePath, overwrite: true);
    }
}
