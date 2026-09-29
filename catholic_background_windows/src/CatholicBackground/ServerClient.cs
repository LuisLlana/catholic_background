// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later

using System.Drawing;
using System.Security.Cryptography;
using System.Text.Json;

namespace CatholicBackground;

public sealed record DownloadedImage(
    byte[] Bytes, string Hash, Size Size,
    string Title, string Author, string Year, string Description, string Reason,
    string License, string Source, string EditUrl, string Language,
    IReadOnlyList<KeyValuePair<string, string>> Extra)
{
    /// <summary>"Title (year)", as shown in the tooltip of the tray icon.</summary>
    public string TitleWithYear => ServerClient.FormatTitle(Title, Year);
}

public sealed record ContentLanguage(string Code, string Name);

/// <summary>
/// Access to the Catholic background of the day server.
/// Protocol: GET &lt;url&gt;?ts=&lt;Unix timestamp of the local midnight of the day&gt;&amp;lang=&lt;language&gt;[&amp;caption=0]
///   -> {"image": "&lt;base64&gt;", "title", "author", "date", "description", "reason", "license", "source",
///       "extra", "language", "edit_url", ...}
/// </summary>
public static class ServerClient
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(60) };

    private static Uri ParseBase(string baseUrl)
    {
        if (!Uri.TryCreate(baseUrl.Trim(), UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
            throw new ServerException("The URL must start with http:// or https://.");
        return uri;
    }

    /// <summary>Address of the image of a day, keeping any other query parameters of the base URL.</summary>
    public static Uri RequestUrl(string baseUrl, DateTime day, string language, bool label)
    {
        var uri = ParseBase(baseUrl);
        long ts = new DateTimeOffset(day.Date).ToUnixTimeSeconds();
        var parameters = uri.Query.TrimStart('?')
            .Split('&', StringSplitOptions.RemoveEmptyEntries)
            .Where(p => p.Split('=')[0] is not ("ts" or "lang" or "caption"))
            .Append($"ts={ts}");
        if (language.Length > 0)
            parameters = parameters.Append($"lang={Uri.EscapeDataString(language)}");
        if (!label)
            parameters = parameters.Append("caption=0");
        return new UriBuilder(uri) { Query = string.Join("&", parameters) }.Uri;
    }

    /// <summary>Throws ServerException if the URL is not valid.</summary>
    public static void Validate(string baseUrl) => ParseBase(baseUrl);

    public static string FormatTitle(string title, string date)
    {
        title = title.Trim();
        date = date.Trim();
        if (title.Length > 0 && date.Length > 0)
            return $"{title} ({date})";
        return title.Length > 0 ? title : date;
    }

    private static async Task<string> GetAsync(Uri url, CancellationToken cancellationToken)
    {
        try
        {
            using var response = await Http.GetAsync(url, cancellationToken);
            if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
                throw new ServerException("There is no image for this day.");
            if (!response.IsSuccessStatusCode)
                throw new ServerException($"The server answered with HTTP {(int)response.StatusCode} {response.ReasonPhrase}.");
            return await response.Content.ReadAsStringAsync(cancellationToken);
        }
        catch (HttpRequestException e)
        {
            throw new ServerException($"Could not connect to the server: {e.Message}");
        }
        catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new ServerException("The server did not answer in time.");
        }
    }

    public static async Task<DownloadedImage> FetchAsync(Uri url, CancellationToken cancellationToken = default)
    {
        var body = await GetAsync(url, cancellationToken);
        JsonElement root;
        try
        {
            root = JsonDocument.Parse(body).RootElement;
        }
        catch (JsonException)
        {
            throw new ServerException("The server did not answer with JSON.");
        }
        if (root.ValueKind != JsonValueKind.Object ||
            !root.TryGetProperty("image", out var imageElement) || imageElement.ValueKind != JsonValueKind.String)
            throw new ServerException("The answer of the server has no \"image\" field.");

        var base64 = imageElement.GetString()!;
        if (base64.StartsWith("data:", StringComparison.Ordinal))
            base64 = base64[(base64.IndexOf(',') + 1)..];
        byte[] bytes;
        try
        {
            bytes = Convert.FromBase64String(base64);
        }
        catch (FormatException)
        {
            throw new ServerException("The \"image\" field is not valid base64.");
        }

        Size size;
        try
        {
            using var stream = new MemoryStream(bytes);
            using var image = Image.FromStream(stream, useEmbeddedColorManagement: false, validateImageData: true);
            size = image.Size;
        }
        catch (ArgumentException)
        {
            throw new ServerException("The \"image\" field does not contain an image that Windows can read (use JPEG or PNG).");
        }

        var extra = new List<KeyValuePair<string, string>>();
        if (root.TryGetProperty("extra", out var extraElement) && extraElement.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in extraElement.EnumerateObject())
            {
                var value = Text(property.Value);
                if (value.Length > 0)
                    extra.Add(new(property.Name, value));
            }
        }

        return new DownloadedImage(
            bytes, Convert.ToHexString(SHA1.HashData(bytes)).ToLowerInvariant(), size,
            Get(root, "title"), Get(root, "author"), Get(root, "date"), Get(root, "description"), Get(root, "reason"),
            Get(root, "license"), Get(root, "source"), Get(root, "edit_url"), Get(root, "language"), extra);
    }

    /// <summary>Languages of the content offered by the server (Spanish and English if it cannot be asked).</summary>
    public static async Task<IReadOnlyList<ContentLanguage>> LanguagesAsync(string baseUrl, CancellationToken cancellationToken = default)
    {
        var fallback = new[] { new ContentLanguage("es", "Español"), new ContentLanguage("en", "English") };
        try
        {
            var uri = ParseBase(baseUrl);
            var address = new UriBuilder(uri) { Path = uri.AbsolutePath.TrimEnd('/') + "/languages", Query = "" }.Uri;
            var root = JsonDocument.Parse(await GetAsync(address, cancellationToken)).RootElement;
            var found = root.GetProperty("languages").EnumerateArray()
                .Select(l => new ContentLanguage(Get(l, "code"), Get(l, "name")))
                .Where(l => l.Code.Length > 0)
                .ToList();
            return found.Count > 0 ? found : fallback;
        }
        catch (Exception e) when (e is ServerException or JsonException or KeyNotFoundException or InvalidOperationException)
        {
            return fallback;
        }
    }

    private static string Get(JsonElement root, string name) =>
        root.TryGetProperty(name, out var value) ? Text(value).Trim() : "";

    private static string Text(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.String => value.GetString() ?? "",
        JsonValueKind.Number => value.GetRawText(),
        _ => "",
    };
}

public sealed class ServerException(string message) : Exception(message);
